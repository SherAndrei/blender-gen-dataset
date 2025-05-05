# to\_nsvf\_dataset.py

A small Python utility that reorganises the output of `generate‑batch.py`
into the folder layout expected by **NSVF** (Neural Sparse Voxel Fields).

---

## Features

* **Simple repack** – collects `*_masked_*.png` images, corresponding
  `*_camera_projection_matrix.json` files, plus `intrinsics.txt` and
  `bbox.txt`.
* Writes RGBA frames to **`rgb/###.png`** and camera poses to
  **`pose/###.txt`** (4 rows × 4 cols, space‑separated).
* Copies `intrinsics.txt` and `bbox.txt` verbatim into the dataset root.
* Skips views whose files are incomplete and prints a warning.

---

## Installation

Only **NumPy** is required.

```bash
poetry install    # installs numpy
```

(or `pip install numpy` if you prefer).

---

## Usage

```
usage: to_nsvf_dataset.py [-h] input_dir output_dir

Re‑package render folder into NSVF dataset.

positional arguments:
  input_dir    Directory produced by generate‑batch.py
  output_dir   Destination directory for the NSVF dataset

options:
  -h, --help   show this help message and exit
```

---

## Example

**Convert a batch render** in `./batch_output` to an NSVF dataset:

```bash
poetry run python3.11 to_nsvf_dataset.py ./batch_output ./nsvf_dataset
```

Resulting structure:

```
nsvf_dataset/
├── intrinsics.txt
├── bbox.txt
├── rgb/
│   ├── 0.png
│   ├── 1.png
│   └── ...
└── pose/
    ├── 0.txt
    ├── 1.txt
    └── ...
```

Each `pose/###.txt` contains a 4 × 4 camera matrix ready for NSVF
training and evaluation.
