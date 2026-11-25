#!/bin/bash
set -euo pipefail

APP_DIR="$HOME/Applications/PyXLoad"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"

PYTHON=""
for candidate in /opt/local/bin/python3.14 /opt/local/bin/python3.13 /opt/local/bin/python3.12 /opt/local/bin/python3.11 /usr/local/bin/python3 /opt/homebrew/bin/python3 /usr/bin/python3; do
    if [[ -x "$candidate" ]] && "$candidate" -c 'import tkinter' >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
done

if [[ -z "$PYTHON" ]]; then
    echo "No Python installation with tkinter was found."
    echo "With MacPorts and Python 3.14: sudo port install python314 py314-tkinter"
    read -r -p "Press Return to close."
    exit 1
fi

mkdir -p "$APP_DIR" "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
cp "$SOURCE_DIR/pyxload.py" "$SOURCE_DIR/display_profiles.py" "$APP_DIR/"
cp "$SOURCE_DIR/python-launcher" "$APP_DIR/"
chmod 755 "$APP_DIR/pyxload.py" "$APP_DIR/python-launcher"
printf '%s\n' "$PYTHON" > "$APP_DIR/.python-path"

for OLD_LABEL in com.page.pyxload.cpu com.page.pyxload.gpu; do
    launchctl bootout "gui/$UID/$OLD_LABEL" 2>/dev/null || true
    rm -f "$HOME/Library/LaunchAgents/$OLD_LABEL.plist"
done

LABEL="com.page.pyxload"
AGENT="$HOME/Library/LaunchAgents/$LABEL.plist"
launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
for _attempt in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    launchctl print "gui/$UID/$LABEL" >/dev/null 2>&1 || break
    sleep 0.1
done
plutil -create xml1 "$AGENT"
plutil -insert Label -string "$LABEL" "$AGENT"
plutil -insert ProgramArguments -xml "<array><string>$APP_DIR/python-launcher</string><string>$APP_DIR/pyxload.py</string><string>-geometry</string><string>150x100+1640+154</string><string>-fn</string><string>FixedRegular</string><string>--font-size</string><string>16</string><string>-update</string><string>3</string><string>-hl</string><string>magenta</string><string>-bg</string><string>black</string><string>-fg</string><string>white</string><string>-label</string><string>kamari</string></array>" "$AGENT"
plutil -insert RunAtLoad -bool true "$AGENT"
plutil -insert KeepAlive -bool false "$AGENT"
plutil -insert ProcessType -string Interactive "$AGENT"
plutil -insert StandardOutPath -string "$HOME/Library/Logs/PyXLoad.log" "$AGENT"
plutil -insert StandardErrorPath -string "$HOME/Library/Logs/PyXLoad.log" "$AGENT"
plutil -lint "$AGENT"
if ! launchctl bootstrap "gui/$UID" "$AGENT"; then
    launchctl bootout "gui/$UID" "$AGENT" 2>/dev/null || true
    sleep 1
    launchctl bootstrap "gui/$UID" "$AGENT"
fi
launchctl kickstart -k "gui/$UID/$LABEL"

echo
echo "PyXLoad is installed and will start at every login."
echo "The CPU widget is permanent; enable or hide GPU widget in the context menu."
echo "Python: $PYTHON"
echo "To remove it, double-click uninstall.command."
read -r -p "Press Return to close."
