# PyXLoad for macOS

A faithful, borderless `xload` clone for macOS, written in Python. PyXLoad
displays the one-minute CPU load average in a normal-level window
and adds an optional Apple Silicon GPU graph.

It preserves the behaviour of the Xaw `StripChart` behind the original
`xload`: one sample per horizontal pixel, filled one-pixel columns, integer
scale intervals, dynamic scaling and `jumpScroll` overflow.

## Highlights

- CPU load graph faithful to `xload` and Xaw `StripChart`
- optional Apple Silicon GPU utilisation widget, without `sudo`
- borderless windows; click to raise, right-click or Control-click for options
- no Dock or Command-Tab icon
- draggable from anywhere in the graph
- runs CPU and GPU widgets inside one application
- remembers each widget's size and position separately for every monitor arrangement
- starts automatically at login using one per-user LaunchAgent
- no Python dependencies beyond Tkinter
- supports the historic X11 Fixed 10×20 Mac conversion, `FixedRegular`

## Requirements

- macOS on Apple Silicon for the GPU graph
- Python 3.14 with Tkinter

With MacPorts:

```sh
sudo port install python314 py314-tkinter
```

The CPU graph also works on other macOS architectures. GPU collection uses
Apple's `IOGPU` registry and may vary between macOS and hardware versions.

## Installation

Double-click `install.command`, or run:

```sh
chmod +x install.command uninstall.command
./install.command
```

Installation itself does not require `sudo`. The scripts install PyXLoad in
`~/Applications/PyXLoad` and create one LaunchAgent in
`~/Library/LaunchAgents`.

The supplied profile reproduces Christian Pagé's setup on `kamari`:

| Graph | Geometry | Label | Unit per grid interval |
| --- | --- | --- | --- |
| CPU | `150x100+1640+154` | `kamari` | 1 load-average unit |
| GPU | `150x100+1640+260` | `kamari GPU` | 10 percentage points |

Both use a 3-second update period, black background, white histogram, magenta
grid and `FixedRegular` at native size 16.

CPU is always present. Use **GPU widget** in either graph's context menu to
show or hide the second widget; hiding it preserves all saved positions.

## Controls

- drag anywhere to move a window
- right-click or Control-click for the context menu
- Command-Q or Escape to quit for the current session
- use `uninstall.command` to unload the agents and move installed files to the
  Trash

Run `pyxload.py --help` for all options. Historical spellings such as
`-update`, `-scale`, `-geometry`, `-hl`, `-highlight`, `-label`, `-nolabel`,
`-jumpscroll` and `-fn` are accepted.

## Fidelity audit

The implementation was checked directly against the X.Org sources for
[`xload.c`](https://gitlab.freedesktop.org/xorg/app/xload),
`app-defaults/XLoad`, and libXaw
[`StripChart.c`](https://gitlab.freedesktop.org/xorg/lib/libxaw).

PyXLoad reproduces:

- the one-minute system load average
- the first sample after one update period
- the Xaw default update period of 10 seconds, with a one-second minimum
- minimum scale 1
- one filled vertical column of exactly one pixel per sample
- history starting at the left without stretching
- `jumpScroll=1`
- persistent dynamic scale state, including Xaw's exact-integer edge case
- scale reduction when the former maximum scrolls out or the chart repaints
- integer positioning of `scale - 1` reference lines
- a double-width reference at each logical-core multiple (for example 16, 32,
  48 on a 16-core Mac), marking one, two, or more runnable tasks per core
- a label area separate from the chart, so the graph cannot cover its text

Intentional macOS additions are the borderless window, contextual menu,
saved position, optional unfilled trace and GPU source. The obsolete X11
`-remote`/rwhod and keyboard-LED `-lights` modes are not implemented.

The GPU graph uses the identical StripChart mechanics after normalising one
scale unit to 10% utilisation.

## Historical companion font

The recommended typeface is Christian Pagé's preserved 2003 Mac conversion of
X11 Fixed 10×20:
[pagecp/x11-fixed-10x20](https://github.com/pagecp/x11-fixed-10x20).

PyXLoad remains usable with another fixed-width font when `FixedRegular` is not
installed.

## Licence

MIT. See [LICENSE](LICENSE).

The X.Org projects are referenced for behavioural compatibility; their source
code is not bundled or copied into this project.
