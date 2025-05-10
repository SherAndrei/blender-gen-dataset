#!/usr/bin/env python3
"""
Convert generate-batch.py output into a COLMAP project that uses **known camera poses**.
Source: https://colmap.github.io/faq.html#reconstruct-sparse-dense-model-from-known-camera-poses

• Images are renamed to three-digit IDs: 012_render.png  →  012.png
• If a mask file exists (012_mask_000.png) it is copied as 012.png.png
  ──> this matches COLMAP's “image_name.png.png” mask rule.
  Source: https://colmap.github.io/faq.html#mask-image-regions
• Creates:
     sparse/0/cameras.txt (OPENCV model)
     sparse/0/images.txt  (quaternion + translation)
     images/              (RGB)
     masks/               (masks)

Usage
-----
python to_colmap.py <batch_dir> <colmap_project_dir>
"""

from __future__ import annotations
import argparse, shutil, re
from pathlib import Path
from typing import Tuple
import numpy as np

RE_RENDER = re.compile(r'^(\d+)_render\.png$')
RE_MASK   = re.compile(r'^(\d+)_mask_.*\.png$')
RE_PROJ   = re.compile(r'^(\d+)_camera_projection_matrix\.txt$')

def load_inverted_projection(path: Path) -> np.ndarray:
    """3x4 -> 4x4 matrix."""
    mat = np.loadtxt(path, dtype=np.float64)
    if mat.shape != (3, 4):
        raise ValueError(f"{path} does not hold a 3x4 matrix")
    pose = np.eye(4, dtype=np.float64)
    pose[:3, :] = mat
    return pose
    return np.linalg.inv(pose)   # COLMAP wants C2W

def load_intrinsics(path: Path) -> np.ndarray:
    """Read intrinsics and return a 3x3 matrix."""
    vals = np.loadtxt(path, dtype=np.float64)
    if vals.shape != (3, 3):
        raise ValueError(f"{path} does not hold a 3x3 matrix")
    K4 = np.eye(4, dtype=np.float64)
    K4[:3, :3] = vals
    return K4

def qvec_tvec_from_matrix(M: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """COLMAP quaternion convention (qw,qx,qy,qz), t = -R*w."""
    R = M[:3, :3]
    t = M[:3, 3]
    qw = np.sqrt(max(0, 1 + R[0,0] + R[1,1] + R[2,2])) / 2
    qx = np.sign(R[2,1] - R[1,2]) * np.sqrt(max(0, 1 + R[0,0] - R[1,1] - R[2,2])) / 2
    qy = np.sign(R[0,2] - R[2,0]) * np.sqrt(max(0, 1 - R[0,0] + R[1,1] - R[2,2])) / 2
    qz = np.sign(R[1,0] - R[0,1]) * np.sqrt(max(0, 1 - R[0,0] - R[1,1] + R[2,2])) / 2
    return np.array([qw, qx, qy, qz]), -R @ t

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_dir", type=Path)
    ap.add_argument("output_dir", type=Path)
    args = ap.parse_args()

    in_dir  = args.input_dir.resolve()
    out_dir = args.output_dir.resolve()
    img_dir = out_dir / "images"
    mask_dir = out_dir / "masks"
    sparse_model_dir = out_dir / "sparse" / "0"
    img_dir.mkdir(parents=True, exist_ok=True)
    mask_dir.mkdir(parents=True, exist_ok=True)
    sparse_model_dir.mkdir(parents=True, exist_ok=True)

    K = load_intrinsics(in_dir / "camera_intrinsics.txt")
    fx, fy, cx, cy = K[0,0], K[1,1], K[0,2], K[1,2]
    # assume square resolution from principal point
    W = int(cx * 2)
    H = int(cy * 2)

    with open(sparse_model_dir / "cameras.txt", "w") as f:
        f.write("# CAMERA_ID, MODEL, WIDTH, HEIGHT, "
                "FX, FY, CX, CY, K1, K2, P1, P2\n")
        f.write(f"1 OPENCV {W} {H} {fx} {fy} {cx} {cy} 0 0 0 0\n")

    with open(sparse_model_dir / "images.txt", "w") as f:
        f.write("# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")

    entries = {}
    for f in in_dir.iterdir():
        if m:=RE_RENDER.match(f.name):
            idx = int(m.group(1)); entries.setdefault(idx,{})['rgb']=f
        elif m:=RE_MASK.match(f.name):
            idx = int(m.group(1)); entries.setdefault(idx,{})['mask']=f
        elif m:=RE_PROJ.match(f.name):
            idx = int(m.group(1)); entries.setdefault(idx,{})['proj']=f

    img_id = 0
    images_txt = sparse_model_dir / "images.txt"
    for idx in sorted(entries):
        e = entries[idx]
        if 'rgb' not in e or 'proj' not in e:
            print(f"[WARN] view {idx:03d} incomplete, skipping")
            continue

        dst_name = f"{idx:03d}.png"
        shutil.copy2(e['rgb'], img_dir / dst_name)

        if 'mask' in e:
            shutil.copy2(e['mask'], mask_dir / f"{dst_name}.png")

        # see https://colmap.github.io/format.html#images-txt
        M = load_inverted_projection(e['proj'])
        q, t = qvec_tvec_from_matrix(M)
        with images_txt.open("a") as f:
            line = " ".join(map(str, [img_id, *q, *t, 1, dst_name]))
            f.write(line + "\n\n")

        img_id += 1

    print(f"[OK] COLMAP project written to {out_dir}")

if __name__ == "__main__":
    main()
