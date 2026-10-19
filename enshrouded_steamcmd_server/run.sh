#!/usr/bin/with-contenv bash
set -euo pipefail
umask 077

SERVER_DIR=/share/enshrouded/server
mkdir -p "$SERVER_DIR" /share/enshrouded/savegame /share/enshrouded/logs "$WINEPREFIX"
# Validate the password before downloading or exposing the server.
python3 /configure.py
UPDATE_ON_START=$(python3 -c 'import json; print(str(json.load(open("/data/options.json"))["update_on_start"]).lower())')

if [[ "$UPDATE_ON_START" == true || ! -f "$SERVER_DIR/enshrouded_server.exe" ]]; then
    python3 /update.py
fi

[[ -f "$SERVER_DIR/enshrouded_server.exe" ]] || { echo "Server executable missing" >&2; exit 1; }
# Reapply after updates in case Steam replaced the configuration.
python3 /configure.py
cd "$SERVER_DIR"
echo "[Enshrouded] Starting; persistent logs: /share/enshrouded/logs"
exec python3 /services.py
