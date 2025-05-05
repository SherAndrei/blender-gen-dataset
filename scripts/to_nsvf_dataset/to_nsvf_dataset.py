#!/usr/bin/env python3
"""
to_nsvf_dataset.py
==================
Re-packages the folder produced by *generate-batch.py* into the directory
layout used by **NSVF** (Neural Sparse Voxel Fields).

Expected input files
--------------------
<in_dir>/
    000_masked_000.png
    001_masked_001.png
    ...
    000_camera_projection_matrix.json   # 3x4 projection (K[R|t])
    001_camera_projection_matrix.json
    ...
    intrinsics.txt                      # 4x4 K
    bbox.txt                            # bounding box

Result
------
<out_dir>/
├── intrinsics.txt              (copied verbatim)
├── bbox.txt                    (copied verbatim)
├── rgb/
│   ├── 0.png
│   ├── 1.png
│   └── ...
└── pose/
    ├── 0.txt                   (4 rows, 4 cols, space-separated)
    ├── 1.txt
    └── ...
"""

from __future__ import annotations
import argparse
import json
import shutil
import sys
import re
from pathlib import Path
import numpy as np


RE_MASK = re.compile(r'^(\d+)_masked_.*\.png$')
RE_PROJ = re.compile(r'^(\d+)_camera_projection_matrix\.json$')


def parse_args() -> tuple[Path, Path]:
    p = argparse.ArgumentParser(description="Convert batch output → NSVF dataset")
    p.add_argument("input_dir",  type=Path)
    p.add_argument("output_dir", type=Path)
    a = p.parse_args()

    if not a.input_dir.is_dir():
        sys.exit(f"[ERR] {a.input_dir} is not a directory")

    return a.input_dir.resolve(), a.output_dir.resolve()


def load_projection(json_path: Path) -> np.ndarray:
    """Read 3x4 JSON matrix and return 4x4 pose matrix."""
    with open(json_path, "r") as f:
        mat = np.array(json.load(f), dtype=np.float64)
    if mat.shape != (3, 4):
        raise ValueError(f"{json_path} does not contain a 3x4 matrix")

    pose = np.eye(4, dtype=np.float64)
    pose[:3, :] = mat
    return pose


def save_pose_matrix(mat: np.ndarray, out_path: Path):
    """Write 4x4 matrix with rows separated by newline, elements by space."""
    lines = [" ".join(f"{v:.10f}" for v in row) for row in mat]
    out_path.write_text("\n".join(lines))


def main():
    in_dir, out_dir = parse_args()

    rgb_dir  = out_dir / "rgb"
    pose_dir = out_dir / "pose"
    rgb_dir.mkdir(parents=True, exist_ok=True)
    pose_dir.mkdir(parents=True, exist_ok=True)

    translate = {
        "camera_intrinsics.txt": "intrinsics.txt",
        "bounding_box.txt": "bbox.txt"
    }
    # copy intrinsics & bbox if present
    for fname in ("camera_intrinsics.txt", "bounding_box.txt"):
        src = in_dir / fname
        if src.exists():
            shutil.copy2(src, out_dir / translate[fname])
            print(f"[INFO] copied {fname} to {translate[fname]}")
        else:
            print(f"[WARN] {fname} not found in input directory.")

    # gather masked images
    mask_map = {}
    for f in in_dir.iterdir():
        m = RE_MASK.match(f.name)
        if m:
            idx = int(m.group(1))
            mask_map[idx] = f

    if not mask_map:
        sys.exit("[ERR] No *_masked_*.png files found.")

    # copy rgb & write pose
    for idx in sorted(mask_map.keys()):
        rgb_src = mask_map[idx]
        rgb_dst = rgb_dir / f"{idx}.png"
        shutil.copy2(rgb_src, rgb_dst)

        proj_json = in_dir / f"{idx:03d}_camera_projection_matrix.json"
        if not proj_json.exists():
            print(f"[WARN] projection for view {idx} is missing, skipping pose.")
            continue

        pose_mat = load_projection(proj_json)
        save_pose_matrix(pose_mat, pose_dir / f"{idx}.txt")

    print(f"[OK] NSVF dataset written to {out_dir}")


if __name__ == "__main__":
    main()
