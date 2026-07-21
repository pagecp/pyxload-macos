#!/bin/bash
set -euo pipefail

for LABEL in com.page.pyxload.cpu com.page.pyxload.gpu; do
    AGENT="$HOME/Library/LaunchAgents/$LABEL.plist"
    launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
    if [[ -e "$AGENT" ]]; then
        mv "$AGENT" "$HOME/.Trash/$LABEL.plist"
    fi
done
if [[ -d "$HOME/Applications/PyXLoad" ]]; then
    mv "$HOME/Applications/PyXLoad" "$HOME/.Trash/PyXLoad"
fi

echo "PyXLoad CPU et GPU ont été désinstallés (fichiers placés dans la Corbeille)."
read -r -p "Appuie sur Entrée pour fermer."
