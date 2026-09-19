# Minecraft to Allumeria Skin Converter

A Python script to convert modern Minecraft skins (64x64) into the Allumeria skin format. Because Allumeria uses smaller body parts than Minecraft, this tool automatically upscales the output to preserve pixel-art detail. 

*screenshot*

## Features
- Converts standard 64x64 Minecraft skins to Allumeria format.
- Upscales output to 256x256 (4x scale) by default to maintain crisp pixel art.
- Supports Slim 3px-wide arm skins via the `--slim` flag.
- Uses nearest-neighbor resampling to prevent blurry textures.

## Requirements
- Python 3.x
- [Pillow](https://pillow.readthedocs.io/) (`pip install Pillow`)

## Usage

```bash
python Allumeria-skin-converter.py input.png [output.png] [--scale 4] [--slim]
