#!/usr/bin/env python3
import argparse
import os
from PIL import Image

def make_grid(input_dir: str, rows: int, cols: int, out_file: str) -> None:
    # Gather PNG files
    files = sorted(
        f for f in os.listdir(input_dir)
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif'))
    )

    # Load first image to get size
    if files:
        first = Image.open(os.path.join(input_dir, files[0]))
        w, h = first.size
    else:
        raise RuntimeError("No images found")

    # Create blank canvas
    grid = Image.new('RGBA', (cols * w, rows * h), (255, 255, 255, 0))

    # Paste images (or blanks) into grid
    for idx in range(rows * cols):
        row, col = divmod(idx, cols)
        x, y = col * w, row * h

        if idx < len(files):
            img = Image.open(os.path.join(input_dir, files[idx]))
            if img.mode == 'I;16':
                img = img.point(lambda i: i * (1 / 255)).convert("RGB")
            img = img.convert('RGBA')
        else:
            img = Image.new('RGBA', (w, h), (255, 255, 255, 0))

        # If image sizes vary, you could resize here:
        # img = img.resize((w, h))
        grid.paste(img, (x, y), img)

    # Save result
    grid.save(out_file)

def main():
    p = argparse.ArgumentParser(description="Tile PNGs into an N×M grid.")
    p.add_argument('input_dir', help="Directory containing .png files")
    p.add_argument('N', type=int, help="Number of rows")
    p.add_argument('M', type=int, help="Number of columns")
    p.add_argument('output', help="Output filename (e.g., grid.png)")
    args = p.parse_args()

    make_grid(args.input_dir, args.N, args.M, args.output)

if __name__ == '__main__':
    main()
