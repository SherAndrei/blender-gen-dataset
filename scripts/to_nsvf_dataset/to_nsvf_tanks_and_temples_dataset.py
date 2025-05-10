#!/usr/bin/env python3
"""
to_nsvf_tanks_and_temples_dataset.py
============================
Convert the output folder of *generate-batch.py* into the directory
layout used by the **Tanks&Temples** template of NSVF.

Structure written
-----------------
<out_dir>/
├── intrinsics.txt        (4x4 matrix)
├── bbox.txt              (copied verbatim)
├── rgb/
│   ├── 0_000.png         ← training images  (prefix 0_)
│   ├── 0_001.png
│   ├── 1_070.png         ← testing images   (prefix 1_)
│   └── ...
└── pose/
    ├── 0_000.txt         ← 4x4 camera pose matrices
    ├── 0_001.txt
    ├── 1_070.txt
    └── ...
"""

from __future__ import annotations
import argparse
import shutil
import sys
import random
import re
from pathlib import Path
import numpy as np

RE_MASK = re.compile(r'^(\d+)_masked_.*\.png$')
RE_PROJ = re.compile(r'^(\d+)_camera_projection_matrix\.txt$')


def parse_args():
    p = argparse.ArgumentParser(
        description="Re‑package render folder into NSVF TanksAndTemples dataset"
    )
    p.add_argument("input_dir", type=Path,
                   help="folder produced by generate‑batch.py")
    p.add_argument("output_dir", type=Path,
                   help="destination dataset directory")
    p.add_argument("--split", type=float, default=0.7,
                   help="fraction of views used for training (default 0.7)")
    a = p.parse_args()
    if not a.input_dir.is_dir():
        sys.exit(f"[ERR] {a.input_dir} is not a directory")
    if not (0.0 < a.split < 1.0):
        sys.exit("[ERR] --split must be between 0 and 1")
    return a


def gather_views(src_dir: Path):
    """Return dict idx → {'img':Path,'proj':Path} for complete view triples."""
    table = {}
    for f in src_dir.iterdir():
        m_img = RE_MASK.match(f.name)
        m_prj = RE_PROJ.match(f.name)
        if m_img:
            idx = int(m_img.group(1))
            table.setdefault(idx, {})['img'] = f
        elif m_prj:
            idx = int(m_prj.group(1))
            table.setdefault(idx, {})['proj'] = f
    # remove incomplete
    complete = {k: v for k, v in table.items()
                if 'img' in v and 'proj' in v}
    return complete


def convert_intrinsics(path: Path) -> np.ndarray:
    """Read intrinsics and return a 4x4 matrix."""
    vals = np.loadtxt(path, dtype=np.float64)
    if vals.shape != (3, 3):
        raise ValueError(f"{path} does not hold a 3x3 matrix")
    K4 = np.eye(4, dtype=np.float64)
    K4[:3, :3] = vals
    return K4


def load_projection(path: Path) -> np.ndarray:
    """3x4 -> 4x4 matrix."""
    mat = np.loadtxt(path, dtype=np.float64)
    if mat.shape != (3, 4):
        raise ValueError(f"{path} does not hold a 3x4 matrix")
    pose = np.eye(4, dtype=np.float64)
    pose[:3, :] = mat
    return pose


def save_matrix(mat: np.ndarray, out_path: Path):
    lines = [" ".join(f"{v:.10f}" for v in row) for row in mat]
    out_path.write_text("\n".join(lines))


def main():
    args = parse_args()
    in_dir: Path = args.input_dir.resolve()
    out_dir: Path = args.output_dir.resolve()

    rgb_dir = out_dir / "rgb"
    pose_dir = out_dir / "pose"
    rgb_dir.mkdir(parents=True, exist_ok=True)
    pose_dir.mkdir(parents=True, exist_ok=True)

    # copy bbox.txt
    src = in_dir / "bounding_box.txt"
    if src.exists():
        shutil.copy2(src, out_dir / "bbox.txt")
        print(f"[INFO] bbox.txt written")
    else:
        sys.exit(f"[WARN] {src} missing, NSVF will complain.")

    # convert intrinsics
    intr_src = in_dir / "camera_intrinsics.txt"
    if not intr_src.exists():
        sys.exit("[ERR] camera_intrinsics.txt not found")
    K4 = convert_intrinsics(intr_src)
    save_matrix(K4, out_dir / "intrinsics.txt")
    print("[INFO] intrinsics.txt written")

    # gather views
    views = gather_views(in_dir)
    if not views:
        sys.exit("[ERR] No complete (image+pose) views found")

    indices = list(views.keys())
    n_total = len(indices)
    n_train = int(round(n_total * args.split))
    train_set = set(random.sample(indices, n_train))
    test_set  = set(indices) - train_set

    for idx in indices:
        prefix = "0_" if idx in train_set else "1_"
        tag = f"{prefix}{idx}"

        shutil.copy2(views[idx]['img'], out_dir / "rgb"  / f"{tag}.png")
        save_matrix(load_projection(views[idx]['proj']),
                    out_dir / "pose" / f"{tag}.txt")

    print(f"dataset saved to {out_dir}")
    print(f"train views: {len(train_set)}, test views: {len(test_set)}")
    print(f"[OK] dataset saved to {out_dir}")
    print(f"     training views: {n_train}, testing views: {len(indices)-n_train}")


if __name__ == "__main__":
    main()
