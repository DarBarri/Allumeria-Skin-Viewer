# Allumeria 3D Skin Viewer

A minimal, standalone 3D skin viewer for Allumeria. Built entirely with Python's standard `tkinter` and `Pillow`, it allows you to interactively preview your converted skins without needing to launch the game.

![alt text](https://github.com/DarBarri/Allumeria-Skin-Viewer/blob/main/Screenshot.png?raw=true)

## Features
- Interactive 3D orbit and zoom controls.
- Toggle visibility of individual body parts (Head, Torso, Arms, Legs, Hair/Accessories).
- Drag-and-drop support to quickly load new skins (requires optional `tkinterdnd2`).
- `--watch` mode to automatically refresh the 3D model when you save over the PNG in your image editor.
- Preset camera angles (Front, Back, Left, Right, Top, Bottom).

## Requirements
- Python 3.x
- [Pillow](https://pillow.readthedocs.io/) (`pip install Pillow`)
- `tkinter` (Included in standard Python desktop installations)
- *(Optional)* `tkinterdnd2` for Drag-and-Drop support (`pip install tkinterdnd2`)

## Usage

```bash
python Allumeria-skin-viewer.py skin.png [--watch]
```

If no file is provided, a file picker dialog will open.

## Controls

   Action         |      Control
Orbit / Rotate    |  Left Mouse Drag
Zoom,             |  Mouse Wheel
Refresh Texture   |  R / Space
Reset Camera      |  F
Preset Views      |  1" (Front), "2" (Right), "3" (Back), "4" (Left), "5" (Top), "6 (Bottom)
Quit              |  Esc


## Known Bugs

Allumeria >64x64 Texture Bug: Allumeria itself that turns any skins higher than 64x64 into a chaotic mess for online players. While this viewer can render higher resolutions (like 128x128 or 256x256) perfectly fine for local previewing
