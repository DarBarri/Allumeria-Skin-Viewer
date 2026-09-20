# Allumeria 3D Skin Viewer

A minimal, standalone 3D skin viewer for Allumeria. Built entirely with Python's standard `tkinter` and `Pillow`.

![alt text](https://github.com/DarBarri/Allumeria-Skin-Viewer/blob/main/Screenshot.png?raw=true)

## Features
- Interactive 3D orbit and zoom controls.
- Toggle visibility of individual body parts (Head, Torso, Arms, Legs, Hair/Accessories).
- Drag-and-drop support to quickly load new skins (requires optional `tkinterdnd2`).
- `--watch` mode to automatically refresh the 3D model when you save over the PNG in your image editor.
- Preset camera angles (Front, Back, Left, Right, Top, Bottom).

## Requirements
- Python 3.x
- [Pillow](https://pillow.readthedocs.io/)
- `tkinter` (Included in standard Python desktop installations)
- *(Optional)* `tkinterdnd2` for Drag-and-Drop support

## Usage

```bash
python Allumeria-skin-viewer.py skin.png [--watch]
```

If no file is provided, a file picker dialog will open.

## Controls

|     Action        |      Control        |
|-------------------|---------------------|
| Orbit / Rotate    |  Left Mouse Drag    |
| Zoom,             |  Mouse Wheel        |
| Refresh Texture   |  R / Space          |
| Reset Camera      |  F                  | 
| Preset Views      | 1 - 6, top - bottom |
| Quit              |  Esc                |


## Known Bugs

Allumeria >64x64 Texture Bug: Allumeria turns any skins higher than 64x64 into a chaotic mess for online players.
