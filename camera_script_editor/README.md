# Camera Script Editor

Standalone GUI tool for editing Immersive Cinematics camera script JSON files.

## Run (source)

```bash
PYTHONPATH=src python3 -m camera_script_editor
```

## Build EXE (Windows)

1. Install dependencies:

```bash
python3 -m pip install pyinstaller
```

2. Build the executable:

```bash
pyinstaller --noconsole --onefile --name camera-script-editor src/camera_script_editor/app.py
```

The executable will be available under the `dist/` folder.

## Notes
- Default script directory points to the mod's bundled example scripts.
- Use the directory picker to switch to a live instance config folder.
