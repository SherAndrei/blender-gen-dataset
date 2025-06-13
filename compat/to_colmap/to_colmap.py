#!/usr/bin/env python3
"""
Convert generate-batch.py output into a COLMAP project that uses **known camera poses**.
Source: https://colmap.github.io/faq.html#reconstruct-sparse-dense-model-from-known-camera-poses

• Images are renamed to three-digit IDs: 012_render.png  →  012.png
• If a mask file exists (012_mask_000.png) it is copied as 012.png.png
  ──> this matches COLMAP's “image_name.png.png” mask rule.
  Source: https://colmap.github.io/faq.html#mask-image-regions
• We create database for COLMAP:
  1. If camera is complex COLMAP suggests to change intrinsics manually.
  2. COLMAP does not guarantee order of indices for each image in database,
     but we want that order to correspond with indices in images.txt.
• Creates:
     sparse/manually_created/cameras.txt  (OPENCV model)
     sparse/manually_created/images.txt   (quaternion + translation)
     sparse/manually_created/points3D.txt (empty)
     images/ (RGB)
     masks/  (masks)
     preloaded.db

Usage
-----
python to_colmap.py <batch_dir> <colmap_project_dir>
"""

from __future__ import annotations
import argparse, shutil, re, sys
from pathlib import Path
import numpy as np

# import COLMAP's database helper (expected next to this script)
sys.path.append(str(Path(__file__).parent))
from database import COLMAPDatabase

RE_RENDER = re.compile(r'^(\d+)_render\.png$')
RE_MASK   = re.compile(r'^(\d+)_mask_.*\.png$')
RE_EXTR   = re.compile(r'^(\d+)_camera_extrinsics\.txt$')

def load_extrinsics(path: Path) -> np.ndarray:
    """3x4 -> 4x4 matrix."""
    mat = np.loadtxt(path, dtype=np.float64)
    if mat.shape != (3, 4):
        raise ValueError(f"{path} does not hold a 3x4 matrix")
    pose = np.eye(4, dtype=np.float64)
    pose[:3, :] = mat
    return pose

def load_intrinsics(path: Path) -> np.ndarray:
    """Read intrinsics and return a 3x3 matrix."""
    vals = np.loadtxt(path, dtype=np.float64)
    if vals.shape != (3, 3):
        raise ValueError(f"{path} does not hold a 3x3 matrix")
    K4 = np.eye(4, dtype=np.float64)
    K4[:3, :3] = vals
    return K4

def qvec_from_matrix(R: np.ndarray) -> np.ndarray:
    """COLMAP quaternion convention (qw,qx,qy,qz)"""
    qw = np.sqrt(max(0, 1 + R[0,0] + R[1,1] + R[2,2])) / 2
    qx = np.sign(R[2,1] - R[1,2]) * np.sqrt(max(0, 1 + R[0,0] - R[1,1] - R[2,2])) / 2
    qy = np.sign(R[0,2] - R[2,0]) * np.sqrt(max(0, 1 - R[0,0] + R[1,1] - R[2,2])) / 2
    qz = np.sign(R[1,0] - R[0,1]) * np.sqrt(max(0, 1 - R[0,0] - R[1,1] + R[2,2])) / 2
    return np.array([qw, qx, qy, qz])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_dir", type=Path)
    ap.add_argument("output_dir", type=Path)
    args = ap.parse_args()

    in_dir  = args.input_dir.resolve()
    out_dir = args.output_dir.resolve()
    img_dir = out_dir / "images"
    mask_dir = out_dir / "masks"
    sparse_model_dir = out_dir / "sparse" / "manually_created"
    img_dir.mkdir(parents=True, exist_ok=True)
    mask_dir.mkdir(parents=True, exist_ok=True)
    sparse_model_dir.mkdir(parents=True, exist_ok=True)

    db_path = out_dir / "preloaded.db"
    if db_path.exists(): db_path.unlink()
    db = COLMAPDatabase.connect(db_path)
    db.create_tables()

    K = load_intrinsics(in_dir / "camera_intrinsics.txt")
    fx, fy, cx, cy = K[0,0], K[1,1], K[0,2], K[1,2]
    # assume square resolution from principal point
    W = int(cx * 2)
    H = int(cy * 2)

    # source: https://github.com/colmap/colmap/blob/5d9222729ee2edac80c10281668a49312a7f9498/scripts/python/read_write_model.py#L62
    OPENCV_model = 4
    camera_id = db.add_camera(
        model=OPENCV_model,
        width=W, height=H,
        params=[fx,fy,cx,cy,0,0,0,0],
        prior_focal_length=True
    )

    with open(sparse_model_dir / "cameras.txt", "w") as f:
        f.write("# CAMERA_ID, MODEL, WIDTH, HEIGHT, "
                "FX, FY, CX, CY, K1, K2, P1, P2\n")
        f.write(f"{camera_id} OPENCV {W} {H} {fx} {fy} {cx} {cy} 0 0 0 0\n")

    with open(sparse_model_dir / "images.txt", "w") as f:
        f.write("# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")

    with open(sparse_model_dir / "points3D.txt", "w") as f:
        # should be empty
        pass

    entries = {}
    for f in in_dir.iterdir():
        if m:=RE_RENDER.match(f.name):
            idx = int(m.group(1)); entries.setdefault(idx,{})['rgb']=f
        elif m:=RE_MASK.match(f.name):
            idx = int(m.group(1)); entries.setdefault(idx,{})['mask']=f
        elif m:=RE_EXTR.match(f.name):
            idx = int(m.group(1)); entries.setdefault(idx,{})['extr']=f

    img_id = 0
    images_txt = sparse_model_dir / "images.txt"
    for idx in sorted(entries):
        e = entries[idx]
        if 'rgb' not in e or 'extr' not in e:
            print(f"[WARN] view {idx:03d} incomplete, skipping")
            continue

        dst_name = e["rgb"].name

        db.add_image(name=dst_name, camera_id=camera_id, image_id=img_id)
        print(f"[INFO] Image {dst_name} added to database with camera_id={camera_id}, image_id={img_id}")

        shutil.copy2(e['rgb'], img_dir / dst_name)
        print(f"[INFO] RGB copied: {e['rgb']} -> {img_dir / dst_name} ")

        if 'mask' in e:
            mask_name = mask_dir / f"{dst_name}.png"
            shutil.copy2(e['mask'], mask_name)
            print(f"[INFO] Mask copied: {e['mask']} -> {mask_name} ")

        # Loaded projection is conforming with opencv, that is
        #  - x is horizontal
        #  - y is down (to align to the actual pixel coordinate
        #    used in digital images)
        #  - right-handed: positive z look-at direction
        # COLMAP local camera coordinate system of an image defined like so:
        #  - x axis points to the right
        #  - y points to the bottom,
        #   and the Z axis to the front as seen from the image
        # No additional transposing required.
        # See https://colmap.github.io/format.html#images-txt

        Rt = load_extrinsics(e['extr'])
        R = Rt[:3, :3]
        q = qvec_from_matrix(R)
        t = Rt[:3, 3]

        with images_txt.open("a") as f:
            line = " ".join(map(str, [img_id, *q, *t, camera_id, dst_name]))
            f.write(line + "\n\n")

        img_id += 1

    db.commit()
    db.close()
    print(f"[OK] COLMAP project written to {out_dir}")

if __name__ == "__main__":
    main()
