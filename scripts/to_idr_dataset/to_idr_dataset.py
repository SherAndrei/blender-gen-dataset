#!/usr/bin/env python3
"""
Convert an output folder produced by `generate-batch.py`
into an IDR‑compatible dataset directory.

Usage
-----
python to_idr_dataset.py <input_dir> <output_dir>

Resulting structure (example)
-----------------------------
output_dir/
├── image/
│   ├── 000.png
│   ├── 001.png
│   └── ...
├── mask/
│   ├── 000.png
│   ├── 001.png
│   └── ...
└── cameras.npz
"""

from __future__ import annotations
import argparse
import json
import re
import shutil
import sys
from pathlib import Path
import numpy as np

RE_RGB   = re.compile(r'^(\d+)_render\.png$')
RE_MASK  = re.compile(r'^(\d+)_mask_.*\.png$')
RE_PROJ  = re.compile(r'^(\d+)_camera_projection_matrix\.json$')
RE_SCALE = re.compile(r'^normalization_matrix\.json$')        # optional

def parse_args() -> tuple[Path, Path]:
    p = argparse.ArgumentParser(description="Re‑package render folder into IDR dataset")
    p.add_argument("input_dir",  type=Path, help="folder with *_render.png etc.")
    p.add_argument("output_dir", type=Path, help="where to create IDR dataset")
    a = p.parse_args()
    if not a.input_dir.is_dir():
        sys.exit(f"[ERR] {a.input_dir} is not a directory")
    return a.input_dir.resolve(), a.output_dir.resolve()

def collect_files(in_dir: Path):
    """Return dict idx→{'rgb':Path,'mask':Path,'proj':Path}"""
    table: dict[int, dict[str, Path]] = {}
    for f in in_dir.iterdir():
        m_rgb  = RE_RGB.match(f.name)
        m_mask = RE_MASK.match(f.name)
        m_proj = RE_PROJ.match(f.name)

        if m_rgb:
            idx = int(m_rgb.group(1))
            table.setdefault(idx, {})['rgb'] = f
        elif m_mask:
            idx = int(m_mask.group(1))
            table.setdefault(idx, {})['mask'] = f
        elif m_proj:
            idx = int(m_proj.group(1))
            table.setdefault(idx, {})['proj'] = f
    return table

def load_projection(path: Path) -> np.ndarray:
    mat = np.loadtxt(path, dtype=np.float64)
    if mat.shape != (3, 4):
        raise ValueError(f"{path} is not a 3x4 matrix")
    # lift to 4×4 world_mat
    world_mat = np.zeros((4,4), dtype=np.float64)
    world_mat[:3,:] = mat
    world_mat[3,3]  = 1.0
    return world_mat

def main():
    in_dir, out_dir = parse_args()
    file_map = collect_files(in_dir)

    if not file_map:
        sys.exit("[ERR] No matching render/mask/projection files found.")

    (out_dir / "image").mkdir(parents=True, exist_ok=True)
    (out_dir / "mask" ).mkdir(parents=True, exist_ok=True)

    world_mats = {}
    scale_mats = {}

    # optional global scale_mat.json (one for all cameras)
    scale_json = next((p for p in in_dir.iterdir() if RE_SCALE.match(p.name)), None)
    if scale_json:
        with open(scale_json, "r") as f:
            scale_template = np.array(json.load(f), dtype=np.float64)
    else:
        scale_template = np.eye(4, dtype=np.float64)

    for idx in sorted(file_map.keys()):
        entry             = file_map[idx]
        missing_keys      = {"rgb","mask","proj"} - entry.keys()
        if missing_keys:
            print(f"[WARN] view {idx:03d} missing {missing_keys}, skipping.")
            continue

        # copy images
        rgb_dst  = out_dir / "image" / f"{idx:03d}.png"
        mask_dst = out_dir / "mask"  / f"{idx:03d}.png"
        shutil.copy2(entry["rgb"],  rgb_dst)
        shutil.copy2(entry["mask"], mask_dst)

        # load projection & store
        world_mats[f"world_mat_{idx}"] = load_projection(entry["proj"])
        scale_mats[f"scale_mat_{idx}"] = scale_template

    # save cameras.npz (compressed)
    np.savez_compressed(out_dir / "cameras.npz", **world_mats, **scale_mats)
    print(f"[OK] Created IDR dataset at {out_dir}")

if __name__ == "__main__":
    main()
