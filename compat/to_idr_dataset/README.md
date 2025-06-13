# to\_idr\_dataset.py

A Python utility that repackages the output of `generate‑batch.py` into an **IDR‑compatible** dataset folder (images, masks, `cameras.npz`).
The resulting structure can be fed directly to the preprocessing scripts in the *Implicit Differentiable Renderer* repository.

---

## Features

* **Zero‑copy** repack: simply gathers `*_render.png`, `*_mask_*.png`, and `*_camera_projection_matrix.json` pairs.
* Builds a compressed `cameras.npz` with keys `world_mat_###` and `scale_mat_###`—exactly what IDR’s `preprocess_cameras.py` expects.
* Drops RGB frames into `image/` and their masks into `mask/`, renaming all files to three‑digit IDs (`000.png`, `001.png`, …).
* Accepts `normalization_matrix.json` (global normalization matrix); falls back to identity if absent.
* Gracefully skips incomplete views and prints a concise warning.

---

## Installation

No external libraries besides **NumPy** are required.

```bash
poetry install  # installs numpy
```

*(or simply `pip install numpy` if you don’t use Poetry).*

---

## Usage

```
usage: to_idr_dataset.py [-h] input_dir output_dir

Re‑package render folder into IDR dataset.

positional arguments:
  input_dir    Directory produced by generate‑batch.py
  output_dir   Destination directory for the IDR dataset

options:
  -h, --help   show this help message and exit
```

---

## Examples

**Convert a batch render** located in `./batch_output` into an IDR dataset under `./idr_dataset`:

```bash
poetry run python3.11 to_idr_dataset.py ./batch_output ./idr_dataset
```

After the command completes you will have

```
idr_dataset/
├── image/
│   ├── 000.png
│   ├── 001.png
│   └── ...
├── mask/
│   ├── 000.png
│   ├── 001.png
│   └── ...
└── cameras.npz
```

