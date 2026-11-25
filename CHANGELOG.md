# Changelog

All notable changes to PyXLoad are documented here.

## 1.1.21 — 2026-11-25

- Request an explicit borderless Aqua window style on Tk 9 and Tk 8.6.
+
## 1.1.20 — 2026-11-25

- Use managed windows at normal stacking level. Click to raise; other apps can
  cover the widgets. Remove full-screen polling and global mouse polling.

## 1.1.19 — 2026-11-25

- Hide and restore native AppKit windows without withdrawing or remapping Tk,
  preserving clicks, dragging and context menus.

## 1.1.18 — 2026-11-25

- Detect a frontmost full-screen application and explicitly hide CPU and GPU
  widgets until the normal desktop becomes active again.

## 1.1.17 — 2026-10-12

- Let AppKit alone manage floating window levels so widgets stay out of other
  applications' full-screen Spaces.

## 1.1.16 — 2026-07-26

- Use macOS `FullScreenPrimary`, rather than the misinterpreted
  `FullScreenNone`, to keep CPU and GPU on ordinary desktop Spaces and out of
  other applications' full-screen Spaces.

## 1.1.15 — 2026-07-26

- Combine macOS `Managed` and `FullScreenNone` collection behaviours so CPU
  and GPU remain visible in ordinary Spaces but not over full-screen apps.
- Make upgrades wait for the previous LaunchAgent to unload and retry
  bootstrap once, preventing transient launchctl error 5.

## 1.1.14 — 2026-07-26

- Keep CPU and GPU widgets out of macOS full-screen application Spaces while
  preserving Always on top in ordinary Spaces.

## 1.1.13 — 2026-07-23

- Draw logical-core saturation references at 1.5 px rather than 2 px.
- Reapply Always on top once, 750 ms after Aqua maps CPU and GPU windows.

## 1.1.12 — 2026-07-23

- Draw a double-width CPU reference line at each whole-machine saturation
  threshold: logical-core count, twice that count, and subsequent multiples.
  On the 16-core M4 Max these lines represent load 16, 32, 48, and so on.

## 1.1.11 — 2026-07-23

- Use `NSFloatingWindowLevel` rather than pop-up-menu level, keeping the load
  widgets above normal windows but below notifications and Control Center.
- Target CPU and GPU by their Cocoa window numbers without touching menus.

## 1.1.10 — 2026-07-22

- Repair the native floating level without periodically raising windows,
  eliminating sibling-widget flicker and context-menu ordering conflicts.

## 1.1.9 — 2026-07-22

- Reassert Tk and native floating levels after all widgets have mapped and
  every second thereafter, preventing the earlier CPU widget from falling
  behind newly active browser windows.

## 1.1.8 — 2026-07-22

- Never raise the withdrawn Tk application root when applying native window
  levels; only visible NSWindows are touched, eliminating the extra black
  square at launch.

## 1.1.7 — 2026-07-22

- Apply the floating level to every NSWindow owned by the PyXLoad process,
  avoiding unreliable title matching on borderless Aqua windows.
- Make **Always on top** a synchronized application-wide setting for CPU and
  GPU widgets.

## 1.1.6 — 2026-07-22

- Use native pop-up level 101 consistently and reassert it at the beginning
  and end of every drag.

## 1.1.5 — 2026-07-22

- Standardize the context-menu footer across all three companion apps:
  separator, **Always on top**, separator, **Quit PyXLoad**.

## 1.1.4 — 2026-07-22

- Match each CPU/GPU widget to its exact native NSWindow by a unique title.
- Use `NSStatusWindowLevel` for dependable persistence above normal
  application windows.

## 1.1.3 — 2026-07-22

- Enforce **Always on top** through the native macOS floating-window level for
  both CPU and GPU Toplevel widgets.

## 1.1.2 — 2026-07-22

- Add a cached launcher that automatically recovers when the selected Python
  version changes, while still requiring a working Tkinter module.

## 1.1.1 — 2026-07-22

- Open a widget's context menu on the first right-click even while the
  borderless accessory application is inactive.
- Poll the physical right mouse button through Quartz and suppress duplicate
  menus when Tk also delivers the native event.

## 1.1.0 — 2026-07-22

- Run the CPU and optional GPU graphs as widgets in one accessory application
  and one LaunchAgent.
- Make CPU permanent and add a context-menu check box that shows or hides the
  GPU widget without deleting its saved position.
- Keep GPU enabled when migrating an existing two-process installation; new
  installations begin with CPU only.
- Replace the two legacy LaunchAgents during installation.

## 1.0.1 — 2026-07-22

- Remember independent CPU and GPU window positions for every connected-
  display configuration and restore them when that arrangement returns.
- Preserve and automatically migrate the former single saved geometry.

## 1.0.0 — 2026-07-21

- Initial public release.
- Faithful Xaw StripChart-style CPU load graph.
- Apple Silicon GPU utilisation graph.
- Borderless floating macOS windows without Dock icons.
- Per-user installation and automatic login startup.
- FixedRegular support and kamari example configuration.
