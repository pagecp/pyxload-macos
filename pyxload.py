#!/usr/bin/env python3
"""A small, dependency-free xload clone for macOS."""

from __future__ import annotations

import argparse
import copy
import ctypes
import json
import os
import plistlib
import signal
import socket
import subprocess
import sys
import time
import tkinter as tk
import tkinter.font as tkfont
from collections import deque
from pathlib import Path

from display_profiles import display_signature


APP_NAME = "PyXLoad"
STATE_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
SETTINGS_FILE = STATE_DIR / "settings.json"


def activate_macos_app() -> None:
    if sys.platform != "darwin":
        return
    try:
        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        send_id = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p,
                                   ctypes.c_void_p)(("objc_msgSend", objc))
        send_bool = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p,
                                     ctypes.c_bool)(("objc_msgSend", objc))
        app = send_id(objc.objc_getClass(b"NSApplication"),
                      objc.sel_registerName(b"sharedApplication"))
        send_bool(app, objc.sel_registerName(b"activateIgnoringOtherApps:"), True)
    except (OSError, AttributeError, TypeError):
        pass


def use_macos_accessory_mode() -> None:
    """Hide the Python/Tk application from the Dock and Command-Tab."""
    if sys.platform != "darwin":
        return
    try:
        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/AppKit.framework/AppKit"
        )
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        send_id = ctypes.CFUNCTYPE(
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
        )(("objc_msgSend", objc))
        send_integer = ctypes.CFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long
        )(("objc_msgSend", objc))
        app_class = objc.objc_getClass(b"NSApplication")
        shared_application = objc.sel_registerName(b"sharedApplication")
        set_policy = objc.sel_registerName(b"setActivationPolicy:")
        application = send_id(app_class, shared_application)
        # NSApplicationActivationPolicyAccessory = 1
        send_integer(application, set_policy, 1)
    except (OSError, AttributeError, TypeError):
        # The graph remains usable if a future macOS changes this API.
        pass


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Floating xload clone for macOS")
    parser.add_argument("-update", "--update", type=float, default=10.0,
                        help="refresh interval in seconds (default: 10)")
    parser.add_argument("-scale", "--scale", type=int, default=1,
                        help="minimum number of scale lines (default: 1)")
    parser.add_argument("-geometry", "--geometry", default="120x120+30+70",
                        help="initial Tk geometry")
    parser.add_argument("-fg", "--foreground", default="black")
    parser.add_argument("-bg", "--background", default="white")
    parser.add_argument("-hl", "-highlight", "--highlight", default="black",
                        help="grid colour")
    parser.add_argument("-label", "--label", default=socket.gethostname())
    parser.add_argument("-nolabel", "--no-label", action="store_true",
                        help="do not display the label above the graph")
    parser.add_argument("-jumpscroll", "--jump-scroll", type=int, default=1,
                        help="pixels shifted left at the right edge (default: 1)")
    parser.add_argument("-fn", "--font", default="FixedRegular")
    parser.add_argument("--font-size", type=int, default=16,
                        help="native font size (default: 16)")
    parser.add_argument("--source", choices=("load", "gpu"), default="load")
    parser.add_argument("--history", type=int, default=900,
                        help="maximum stored samples")
    parser.add_argument("--not-floating", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--window-frame", action="store_true",
                        help="show the normal title bar and window border")
    parser.add_argument("--no-fill", action="store_true",
                        help="draw a line instead of a filled graph")
    parser.add_argument("--show-values", action="store_true",
                        help="show numeric values as well as the label")
    parser.add_argument("--reset-position", action="store_true")
    args = parser.parse_args()
    if args.update < 1.0:
        parser.error("--update must be at least 1 second, as in xload")
    if args.scale <= 0:
        parser.error("--scale must be greater than zero")
    if args.history < 2:
        parser.error("--history must be at least 2")
    if args.jump_scroll < 1:
        parser.error("--jump-scroll must be at least 1")
    return args


class PyXLoad:
    def __init__(self, root: tk.Toplevel, args: argparse.Namespace,
                 manager: "PyXLoadApp") -> None:
        self.root = root
        self.args = args
        self.manager = manager
        self.samples: deque[float] = deque(maxlen=args.history)
        self.scale = args.scale
        self.max_value = 0.0
        self.cpu_count = max(os.cpu_count() or 1, 1)
        self.after_id: str | None = None
        self.last_gpu_error: str | None = None
        self.state_file = STATE_DIR / f"state-{args.source}.json"
        self.drag_origin: tuple[int, int, int, int] | None = None
        self.display_key = display_signature()
        self.display_monitor_id: str | None = None
        self.last_menu_time = 0.0

        root.title(f"{APP_NAME} {args.source}")
        root.minsize(100, 60)
        if not args.window_frame:
            root.withdraw()
            # Aqua can retain window chrome with overrideredirect alone.
            # Tk's native plain style removes title bar, border and controls.
            if root.tk.call("tk", "windowingsystem") == "aqua":
                # Aqua makes override-redirect windows full-screen auxiliaries.
                # Keep the window managed, even if the borderless style fails.
                try:
                    # Tk 9: no style bits means no title bar or traffic lights.
                    root.attributes("-stylemask", "")
                except tk.TclError:
                    # Tk 8.6: explicitly request noTitleBar, not just noShadow.
                    try:
                        root.tk.call("::tk::unsupported::MacWindowStyle",
                                     "style", root._w, "plain",
                                     "noTitleBar noShadow")
                    except tk.TclError as error:
                        print(f"{APP_NAME}: borderless style unavailable: {error}",
                              file=sys.stderr)
            else:
                root.overrideredirect(True)
        root.attributes("-topmost", False)
        root.protocol("WM_DELETE_WINDOW", self.quit)

        geometry = args.geometry
        if not args.reset_position:
            geometry = self.load_geometry() or geometry
        root.geometry(geometry)

        self.canvas = tk.Canvas(root, background=args.background,
                                highlightthickness=0, takefocus=True)
        self.canvas.pack(fill="both", expand=True)
        self.display_font = tkfont.Font(root=root, family=args.font,
                                        size=args.font_size)
        self.text_line_height = self.display_font.metrics("linespace")
        self.canvas.bind("<Configure>", self.resize)
        self.canvas.bind("<Button-2>", self.show_menu)
        self.canvas.bind("<Button-3>", self.show_menu)
        self.canvas.bind("<Control-Button-1>", self.show_menu)
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drag)
        root.bind("<Command-q>", lambda _event: self.quit())
        root.bind("<Escape>", lambda _event: self.quit())

        self.menu = tk.Menu(root, tearoff=False)
        self.gpu_var = tk.BooleanVar(value=manager.gpu_enabled)
        self.menu.add_checkbutton(label="GPU widget", variable=self.gpu_var,
                                  command=lambda: manager.set_gpu_enabled(
                                      self.gpu_var.get()))
        self.menu.add_command(label="Reset scale",
                              command=self.reset_scale)
        self.menu.add_separator()
        self.menu.add_command(label="Quit PyXLoad", command=manager.quit,
                              accelerator="⌘Q")

        if not args.window_frame:
            root.after_idle(root.deiconify)
        # Xaw StripChart schedules its first acquisition after one period.
        self.after_id = self.root.after(round(args.update * 1000), self.sample)
        self.display_monitor_id = root.after(2000, self.monitor_displays)

    def load_geometry(self) -> str | None:
        try:
            value = json.loads(self.state_file.read_text(encoding="utf-8"))
            geometry = value.get("display_geometries", {}).get(self.display_key)
            if geometry:
                return geometry
            return value.get("geometry")
        except (OSError, ValueError, TypeError):
            return None

    def save_geometry(self) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                value = json.loads(self.state_file.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                value = {}
            value.setdefault("display_geometries", {})[self.display_key] = \
                self.root.geometry()
            value["geometry"] = self.root.geometry()
            self.state_file.write_text(
                json.dumps(value, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def monitor_displays(self) -> None:
        new_key = display_signature()
        if new_key != self.display_key:
            self.display_key = new_key
            try:
                value = json.loads(self.state_file.read_text(encoding="utf-8"))
                geometry = value.get("display_geometries", {}).get(new_key)
                if geometry:
                    self.root.geometry(geometry)
            except (OSError, ValueError, TypeError):
                pass
        self.display_monitor_id = self.root.after(2000, self.monitor_displays)

    def reset_scale(self) -> None:
        self.scale = self.args.scale
        self.repaint_scale()
        self.draw()

    def resize(self, _event: tk.Event | None = None) -> None:
        """Match an Xaw expose/resize: recompute scale, then repaint."""
        self.repaint_scale()
        self.draw()

    def show_menu(self, event: tk.Event) -> str:
        self.show_menu_at(event.x_root, event.y_root)
        return "break"

    def show_menu_at(self, x: int, y: int) -> None:
        now = time.monotonic()
        if now - self.last_menu_time < 0.5:
            return
        self.last_menu_time = now
        activate_macos_app()
        self.root.lift()
        self.menu.tk_popup(x, y)

    def start_drag(self, event: tk.Event) -> None:
        activate_macos_app()
        self.root.lift()
        self.drag_origin = (
            event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y()
        )

    def drag(self, event: tk.Event) -> None:
        if self.drag_origin is None:
            return
        mouse_x, mouse_y, window_x, window_y = self.drag_origin
        self.root.geometry(
            f"+{window_x + event.x_root - mouse_x}+{window_y + event.y_root - mouse_y}"
        )

    def stop_drag(self, _event: tk.Event) -> None:
        if self.drag_origin is None:
            return
        self.drag_origin = None
        self.save_geometry()

    def sample(self) -> None:
        # Xaw StripChart advances exactly one pixel for each sample.  At the
        # right edge it keeps width - jumpScroll points, leaving the cleared
        # columns to be filled by subsequent updates.
        chart_width = max(self.canvas.winfo_width(), 2)
        capacity = min(chart_width, self.args.history)
        if len(self.samples) >= capacity:
            keep = max(capacity - self.args.jump_scroll, 0)
            while len(self.samples) > keep:
                self.samples.popleft()
            old_max = self.max_value
            self.max_value = max(
                (sample / self.scale_unit() for sample in self.samples),
                default=0.0,
            )
            # MoveChart repaints only if discarding data changed max_value.
            if self.max_value != old_max:
                self.repaint_scale()
        if self.args.source == "gpu":
            value = self.read_gpu_utilisation()
        else:
            value = os.getloadavg()[0]
        if value is not None:
            normalized = value / self.scale_unit()
            if normalized > self.max_value:
                self.max_value = normalized
                # draw_it expands only when the new maximum is strictly above
                # the current scale, not when it is exactly equal.
                if self.max_value > self.scale:
                    self.repaint_scale()
            self.samples.append(value)
        self.draw()
        self.after_id = self.root.after(round(self.args.update * 1000), self.sample)

    def read_gpu_utilisation(self) -> float | None:
        """Read Apple Silicon GPU utilisation from IOGPU, without sudo."""
        try:
            result = subprocess.run(
                ["/usr/sbin/ioreg", "-r", "-c", "IOGPU", "-d", "1", "-a"],
                check=True, capture_output=True, timeout=2,
            )
            tree = plistlib.loads(result.stdout)
            value = self.find_key(tree, "Device Utilization %")
            if value is None:
                value = self.find_key(tree, "Device Utilisation %")
            if value is None:
                raise KeyError("Device Utilization % absent de IOGPU")
            self.last_gpu_error = None
            return max(0.0, min(float(value), 100.0))
        except (OSError, subprocess.SubprocessError, plistlib.InvalidFileException,
                KeyError, TypeError, ValueError) as error:
            message = str(error)
            if message != self.last_gpu_error:
                print(f"PyXLoad GPU: {message}", file=sys.stderr, flush=True)
            self.last_gpu_error = message
            return None

    @classmethod
    def find_key(cls, value: object, wanted: str) -> object | None:
        if isinstance(value, dict):
            if wanted in value:
                return value[wanted]
            for child in value.values():
                found = cls.find_key(child, wanted)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = cls.find_key(child, wanted)
                if found is not None:
                    return found
        return None

    def scale_unit(self) -> float:
        """Return the value represented by one horizontal scale interval."""
        # XLoad uses one load-average unit per interval.  GPU utilisation has
        # no historical XLoad unit, so ten percentage points keeps the same
        # StripChart behaviour without drawing up to 99 lines in 100 pixels.
        return 10.0 if self.args.source == "gpu" else 1.0

    def repaint_scale(self) -> None:
        """Apply repaint_window()'s scale calculation from StripChart.c."""
        if self.samples or self.scale <= self.max_value:
            scale = int(self.max_value + 1.0)
        else:
            scale = self.args.scale
        self.scale = max(self.args.scale, scale)

    def draw(self) -> None:
        canvas = self.canvas
        width = max(canvas.winfo_width(), 2)
        height = max(canvas.winfo_height(), 2)
        canvas.delete("all")

        visible = list(self.samples)[-width:]
        scale = self.scale
        scale_unit = self.scale_unit()
        display_max = scale * scale_unit
        # xload puts its Label widget above the StripChart.  Reserve the same
        # kind of independent text band so a high filled graph can never paint
        # behind white label glyphs and make them appear to disappear.
        text_rows = (0 if self.args.no_label else 1) + \
                    (1 if self.args.show_values else 0)
        graph_top = 3 + self.text_line_height * text_rows + 2
        if text_rows == 0:
            graph_top = 0
        graph_bottom = height
        graph_height = max(graph_bottom - graph_top, 1)

        if visible:
            # Xaw StripChart uses one x pixel per sample and leaves the
            # unrecorded area on the right empty; it never stretches history.
            line_points: list[float] = []
            for index, value in enumerate(visible):
                x = index
                y = int(graph_bottom -
                        graph_height * min(value / display_max, 1.0))
                if self.args.no_fill:
                    line_points.extend((x, y))
                else:
                    canvas.create_line(x, y, x, graph_bottom,
                                       fill=self.args.foreground, width=1)
            if self.args.no_fill and len(line_points) >= 4:
                canvas.create_line(*line_points, fill=self.args.foreground,
                                   width=1)

        # Xaw StripChart draws scale - 1 reference lines.  Every interval is
        # always one load unit for CPU, or ten percentage points for GPU.
        # More lines appear and their spacing tightens as the scale grows.
        for part in range(1, scale):
            # StripChart.c deliberately uses integer division here.
            y = graph_top + part * (graph_height // scale)
            canvas.create_line(0, y, width, y, fill=self.args.highlight)
        if self.args.source == "load":
            # Emphasize whole-machine saturation: on a 16-core Mac, load 16
            # means an average of one runnable task per core. Repeat at 32,
            # 48, ... when the dynamic XLoad scale grows that far.
            threshold = self.cpu_count
            while threshold <= display_max:
                y = round(graph_bottom -
                          graph_height * threshold / display_max)
                canvas.create_line(0, y, width, y,
                                   fill=self.args.highlight, width=1.5)
                threshold += self.cpu_count
        if not self.args.no_label:
            canvas.create_text(4, 3, anchor="nw", fill=self.args.foreground,
                               font=self.display_font, text=self.args.label)

        if self.args.show_values:
            if self.args.source == "gpu":
                current = self.samples[-1] if self.samples else 0.0
                value_text = f"GPU {current:.0f}%"
            else:
                load1, load5, load15 = os.getloadavg()
                value_text = f"{load1:.2f} {load5:.2f} {load15:.2f}"
            values_y = 3 + (0 if self.args.no_label else self.text_line_height)
            canvas.create_text(4, values_y, anchor="nw",
                               fill=self.args.foreground,
                               font=self.display_font,
                               text=value_text)
            canvas.create_text(width - 4, values_y, anchor="ne",
                               fill=self.args.foreground,
                               font=self.display_font,
                               text=(f"max {display_max:.0f}%" if
                                     self.args.source == "gpu" else
                                     f"max {scale}"))
        elif self.args.source == "gpu" and self.last_gpu_error:
            canvas.create_text(width / 2, height / 2, anchor="center",
                               fill=self.args.highlight, font=("Menlo", 8),
                               width=max(width - 10, 20), text="GPU indisponible")

    def shutdown(self) -> None:
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.display_monitor_id is not None:
            self.root.after_cancel(self.display_monitor_id)
            self.display_monitor_id = None
        self.save_geometry()
        self.root.destroy()

    def quit(self) -> None:
        self.manager.quit()


class PyXLoadApp:
    """One accessory application containing the CPU and optional GPU widgets."""
    def __init__(self, root: tk.Tk, args: argparse.Namespace) -> None:
        self.root, self.args = root, args
        self.widgets: dict[str, PyXLoad] = {}
        root.withdraw()
        self.gpu_enabled = self.load_gpu_enabled()
        signal.signal(signal.SIGTERM, lambda *_unused: self.quit())
        root.bind_all("<Command-q>", lambda _event: self.quit())
        self.create_widget("load")
        if self.gpu_enabled:
            self.create_widget("gpu")

    def load_gpu_enabled(self) -> bool:
        try:
            return bool(json.loads(SETTINGS_FILE.read_text(
                encoding="utf-8")).get("gpu_enabled"))
        except (OSError, ValueError, TypeError):
            # Preserve the former two-process installation on first upgrade.
            return (STATE_DIR / "state-gpu.json").exists()

    def save_settings(self) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps({
            "gpu_enabled": self.gpu_enabled}, indent=2), encoding="utf-8")

    def widget_args(self, source: str) -> argparse.Namespace:
        args = copy.copy(self.args)
        args.source = source
        if source == "gpu":
            args.geometry = "150x100+1640+260"
            args.label = f"{self.args.label} GPU"
        return args

    def create_widget(self, source: str) -> None:
        if source in self.widgets:
            return
        window = tk.Toplevel(self.root)
        self.widgets[source] = PyXLoad(
            window, self.widget_args(source), self)

    def set_gpu_enabled(self, enabled: bool) -> None:
        self.gpu_enabled = bool(enabled)
        if self.gpu_enabled:
            self.create_widget("gpu")
        elif "gpu" in self.widgets:
            self.widgets.pop("gpu").shutdown()
        for widget in self.widgets.values():
            widget.gpu_var.set(self.gpu_enabled)
        self.save_settings()

    def quit(self) -> None:
        for widget in list(self.widgets.values()):
            try:
                widget.shutdown()
            except tk.TclError:
                pass
        self.widgets.clear()
        try:
            self.root.destroy()
        except tk.TclError:
            pass


def main() -> None:
    args = arguments()
    root = tk.Tk()
    use_macos_accessory_mode()
    PyXLoadApp(root, args)
    root.mainloop()


if __name__ == "__main__":
    main()
