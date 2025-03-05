#!/usr/bin/env python3
"""
Assemble a NeRF dataset from batch folders.

Each batch folder (inside the input directory) must contain:
  1. A CSV file named "metadata.csv". The CSV file must have a header and
     then one row per image. Each row is:
         image_filename, m00, m01, ..., m33, focal
  2. PNG images whose filenames appear in the CSV.

The script aggregates all images, the corresponding 4x4 pose matrices, and
the focal length (assumed identical across all CSV files) into a single NPZ file
with the following keys:
    - images: (N, X, Y, 3)
    - poses: (N, 4, 4)
    - focal: (1,)

Usage:
    blender --background --python assemble-dataset.py -- \
        --input <batches_folder> [--output dataset.npz]
"""

import argparse
import csv
import os
import sys
from PIL import Image
import numpy as np


def strip_blender_argv():
    """Remove everything before '--' from `sys.argv`"""
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--") + 1:]
    else:
        return []


def parse_args():
    """Parse command-line arguments."""
    argv = strip_blender_argv()
    parser = argparse.ArgumentParser(
        description="Assemble NeRF dataset from batch folders."
    )
    parser.add_argument(
        "--input",
        required=True,
        help=(
            "Input directory containing batch folders. Each subfolder (named "
            "like 'batchXX') must contain a metadata.csv file and PNG images."
        ),
    )
    parser.add_argument(
        "--output",
        default="dataset.npz",
        help="Name of the output NPZ file (default: dataset.npz).",
    )
    return parser.parse_args(argv)


def get_batch_folders(input_dir):
    """
    Get a list of batch subdirectories from the input directory.

    Only subdirectories whose names start with 'batch' (case insensitive)
    are considered.
    """
    batch_folders = []
    for item in os.listdir(input_dir):
        item_path = os.path.join(input_dir, item)
        if os.path.isdir(item_path) and item.lower().startswith("batch"):
            batch_folders.append(item_path)
    batch_folders.sort()
    return batch_folders


def image_to_rgb_array(image_path):
    """
    Reads the image file and returns it array interpretation.

    Returns:
      image: numpy array (RGB image)
    """
    with Image.open(image_path) as img:
        img_rgb = img.convert("RGB")
        return np.array(img_rgb)


def process_batch(batch_dir):
    """
    Process a single batch folder.

    Reads the metadata.csv file and loads the corresponding images.
    Returns:
      images: list of numpy arrays (RGB images)
      poses: list of 4x4 numpy arrays (camera poses)
      focal: focal value (float) from this batch (assumed constant).
    """
    metadata_path = os.path.join(batch_dir, "metadata.csv")
    images = []
    poses = []
    focal = None

    with open(metadata_path, newline="") as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader, None)  # skip header
        for row in reader:
            if len(row) < 18:
                continue
            filename = row[0]
            try:
                pose_vals = [float(val) for val in row[1:17]]
            except ValueError:
                continue
            pose_matrix = np.array(pose_vals).reshape(4, 4)
            current_focal = float(row[17])
            if focal is None:
                focal = current_focal
            elif focal != current_focal:
                print(f"Warning: focal value mismatch in {batch_dir} for {filename}")
            image_path = os.path.join(batch_dir, filename)
            if not os.path.exists(image_path):
                print(f"Warning: {image_path} not found.")
                continue
            images.append(image_to_rgb_array(image_path))
            poses.append(pose_matrix)
    return images, poses, focal


def process_all_batches(input_dir):
    """
    Process all batch folders in the input directory.

    Returns:
      all_images: list of numpy arrays (RGB images)
      all_poses: list of 4x4 numpy arrays (camera poses)
      focal_value: the focal value (float) (from the first batch)
    """
    all_images = []
    all_poses = []
    focal_value = None

    batch_folders = get_batch_folders(input_dir)
    if not batch_folders:
        print("No batch folders found in the input directory.")
        return all_images, all_poses, focal_value

    for batch in batch_folders:
        print(f"Processing batch folder: {batch}")
        images, poses, focal = process_batch(batch)
        print(f"  Loaded {len(images)} images from {batch}.")
        all_images.extend(images)
        all_poses.extend(poses)
        if focal_value is None:
            focal_value = focal
        elif focal != focal_value:
            print(
                f"Warning: focal value in {batch} differs from previous value. "
                f"Using {focal_value}."
            )
    return all_images, all_poses, focal_value


def main():
    """Main function to assemble the dataset."""
    args = parse_args()
    input_dir = args.input
    output_file = args.output

    images, poses, focal = process_all_batches(input_dir)
    if not images:
        print("No images loaded. Exiting.")
        return

    images_np = np.array(images)  # shape (N, X, Y, 3)
    poses_np = np.array(poses)    # shape (N, 4, 4)
    focal_np = np.array([focal])   # shape (1,)

    print(f"Total images: {len(images)}")
    print(f"Image resolution: {images[0].shape}")
    print(f"Focal value: {focal}")

    np.savez_compressed(output_file, images=images_np, poses=poses_np, focal=focal_np)
    print(f"Dataset saved to {output_file}")


if __name__ == "__main__":
    main()
