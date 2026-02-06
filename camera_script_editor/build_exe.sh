#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install --upgrade pyinstaller
pyinstaller --noconsole --onefile --name camera-script-editor src/camera_script_editor/app.py
