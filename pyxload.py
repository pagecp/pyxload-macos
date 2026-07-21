#!/usr/bin/env python3
"""A small, dependency-free xload clone for macOS."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import plistlib
import signal
import socket
import subprocess
import sys
import tkinter as tk
import tkinter.font as tkfont
from collections import deque
from pathlib import Path


APP_NAME = "PyXLoad"
STATE_DIR = Path.home() / "Library" / "Application Support" / APP_NAME


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


def make_macos_windows_square() -> None:
    """Force Tk's NSWindow to be square, borderless and shadowless."""
    if sys.platform != "darwin":
        return
    try:
        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]

        def selector(name: str) -> int:
            return objc.sel_registerName(name.encode("ascii"))

        send_id = ctypes.CFUNCTYPE(
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
        )(("objc_msgSend", objc))
        send_count = ctypes.CFUNCTYPE(
            ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p
        )(("objc_msgSend", objc))
        send_id_index = ctypes.CFUNCTYPE(
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong
        )(("objc_msgSend", objc))
        send_ulong = ctypes.CFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong
        )(("objc_msgSend", objc))
        send_bool = ctypes.CFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool
        )(("objc_msgSend", objc))
        send_float = ctypes.CFUNCTYPE(
            None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_double
        )(("objc_msgSend", objc))

        app_class = objc.objc_getClass(b"NSApplication")
        application = send_id(app_class, selector("sharedApplication"))
        windows = send_id(application, selector("windows"))
        count = send_count(windows, selector("count"))
        for index in range(count):
            window = send_id_index(windows, selector("objectAtIndex:"), index)
            send_ulong(window, selector("setStyleMask:"), 0)
            send_bool(window, selector("setHasShadow:"), False)
            content = send_id(window, selector("contentView"))
            if content:
                send_bool(content, selector("setWantsLayer:"), True)
                layer = send_id(content, selector("layer"))
                if layer:
                    send_float(layer, selector("setCornerRadius:"), 0.0)
                    send_bool(layer, selector("setMasksToBounds:"), False)
    except (OSError, AttributeError, TypeError):
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
    parser.add_argument("--not-floating", action="store_true",
                        help="do not keep the window above normal windows")
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
    def __init__(self, root: tk.Tk, args: argparse.Namespace) -> None:
        self.root = root
        self.args = args
        self.samples: deque[float] = deque(maxlen=args.history)
        self.scale = args.scale
        self.max_value = 0.0
        self.after_id: str | None = None
        self.last_gpu_error: str | None = None
        self.state_file = STATE_DIR / f"state-{args.source}.json"
        self.drag_origin: tuple[int, int, int, int] | None = None

        root.title(APP_NAME)
        root.minsize(100, 60)
        if not args.window_frame:
            root.withdraw()
            # Aqua can retain window chrome with overrideredirect alone.
            # Tk's native plain style removes title bar, border and controls.
            try:
                root.tk.call("::tk::unsupported::MacWindowStyle", "style",
                             root._w, "plain", "none")
            except tk.TclError:
                pass
            root.overrideredirect(True)
        root.attributes("-topmost", not args.not_floating)
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
        self.floating_var = tk.BooleanVar(value=not args.not_floating)
        self.menu.add_checkbutton(label="Toujours au-dessus",
                                  variable=self.floating_var,
                                  command=self.toggle_floating)
        self.menu.add_command(label="Réinitialiser l’échelle",
                              command=self.reset_scale)
        self.menu.add_separator()
        self.menu.add_command(label="Quitter", command=self.quit,
                              accelerator="⌘Q")

        signal.signal(signal.SIGTERM, lambda *_unused: self.quit())
        if not args.window_frame:
            root.after_idle(self.show_borderless)
        # Xaw StripChart schedules its first acquisition after one period.
        self.after_id = self.root.after(round(args.update * 1000), self.sample)

    def show_borderless(self) -> None:
        """Map the Aqua window, then enforce borderless mode once more."""
        self.root.overrideredirect(True)
        self.root.deiconify()
        self.root.update_idletasks()
        try:
            self.root.tk.call("::tk::unsupported::MacWindowStyle", "style",
                              self.root._w, "plain", "none")
        except tk.TclError:
            pass
        self.root.tk.call("wm", "overrideredirect", self.root._w, 1)
        make_macos_windows_square()
        self.root.attributes("-topmost", not self.args.not_floating)
        self.root.lift()

    def load_geometry(self) -> str | None:
        try:
            value = json.loads(self.state_file.read_text(encoding="utf-8"))
            return value.get("geometry")
        except (OSError, ValueError, TypeError):
            return None

    def save_geometry(self) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(
                json.dumps({"geometry": self.root.geometry()}),
                encoding="utf-8",
            )
        except OSError:
            pass

    def toggle_floating(self) -> None:
        self.root.attributes("-topmost", self.floating_var.get())

    def reset_scale(self) -> None:
        self.scale = self.args.scale
        self.repaint_scale()
        self.draw()

    def resize(self, _event: tk.Event | None = None) -> None:
        """Match an Xaw expose/resize: recompute scale, then repaint."""
        self.repaint_scale()
        self.draw()

    def show_menu(self, event: tk.Event) -> None:
        self.menu.tk_popup(event.x_root, event.y_root)

    def start_drag(self, event: tk.Event) -> None:
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

    def quit(self) -> None:
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.save_geometry()
        self.root.destroy()


def main() -> None:
    args = arguments()
    root = tk.Tk()
    use_macos_accessory_mode()
    PyXLoad(root, args)
    root.mainloop()


if __name__ == "__main__":
    main()
