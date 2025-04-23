# grid.py

A simple Python 3.11 script to tile PNG images into an N×M grid, filling any missing slots with transparent blanks.

## Features

- Recursively scans a directory for `.png` images.
- Arranges images into a grid of specified rows (N) and columns (M).
- Automatically fills empty slots with transparent blank images.
- Preserves original image dimensions (or uses a default size if the directory is empty).
- Outputs a single combined `.png` file with transparency support.

## Installation

Install dependencies using `poetry`:
```bash
poetry install
```

## Usage

See help
```
usage: grid.py [-h] input_dir N M output

Tile PNGs into an N×M grid.

positional arguments:
  input_dir   Directory containing .png files
  N           Number of rows
  M           Number of columns
  output      Output filename (e.g., grid.png)

options:
  -h, --help  show this help message and exit
```

## Examples

**Create a 2×3 grid** from images in `./images`:
```bash
poetry run python3.11 grid.py ./images 2 3 output_grid.png
```

