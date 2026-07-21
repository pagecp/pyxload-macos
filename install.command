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
    echo "Aucun Python avec tkinter n’a été trouvé."
    echo "Avec MacPorts et Python 3.14 : sudo port install python314 py314-tkinter"
    read -r -p "Appuie sur Entrée pour fermer."
    exit 1
fi

mkdir -p "$APP_DIR" "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
cp "$SOURCE_DIR/pyxload.py" "$APP_DIR/pyxload.py"
chmod 755 "$APP_DIR/pyxload.py"

install_agent() {
    local label="$1" source="$2" geometry="$3" name="$4"
    local agent="$HOME/Library/LaunchAgents/$label.plist"
    launchctl bootout "gui/$UID/$label" 2>/dev/null || true
    plutil -create xml1 "$agent"
    plutil -insert Label -string "$label" "$agent"
    plutil -insert ProgramArguments -xml "<array><string>$PYTHON</string><string>$APP_DIR/pyxload.py</string><string>-geometry</string><string>$geometry</string><string>-fn</string><string>FixedRegular</string><string>--font-size</string><string>16</string><string>-update</string><string>3</string><string>-hl</string><string>magenta</string><string>-bg</string><string>black</string><string>-fg</string><string>white</string><string>-label</string><string>$name</string><string>--source</string><string>$source</string></array>" "$agent"
    plutil -insert RunAtLoad -bool true "$agent"
    plutil -insert KeepAlive -bool false "$agent"
    plutil -insert ProcessType -string Interactive "$agent"
    plutil -insert StandardOutPath -string "$HOME/Library/Logs/PyXLoad.log" "$agent"
    plutil -insert StandardErrorPath -string "$HOME/Library/Logs/PyXLoad.log" "$agent"
    plutil -lint "$agent"
    launchctl bootstrap "gui/$UID" "$agent"
    launchctl kickstart -k "gui/$UID/$label"
}

# CPU reprend exactement l'emplacement xload; GPU est juste en dessous.
install_agent "com.page.pyxload.cpu" "load" "150x100+1640+154" "kamari"
install_agent "com.page.pyxload.gpu" "gpu" "150x100+1640+260" "kamari GPU"

echo
echo "PyXLoad CPU et GPU sont installés et démarreront à chaque login."
echo "Python utilisé : $PYTHON"
echo "Pour les retirer, double-clique sur uninstall.command."
read -r -p "Appuie sur Entrée pour fermer."
