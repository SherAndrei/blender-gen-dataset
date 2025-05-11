# Using Blender‐generated data with COLMAP (known camera poses)

This note explains **how to turn the output of `generate‑batch.py` plus its
plugins into a ready‑to‑run COLMAP project** that skips camera pose
estimation and goes straight to dense MVS / meshing.

> The workflow follows the *“Reconstruct sparse/dense model from known camera
> poses”* recipe from the official
> [COLMAP FAQ](https://colmap.github.io/faq.html#reconstruct-sparse-dense-model-from-known-camera-poses).

---

## 1 – Render the scene with the required plugins

Enable at least the following plugins in *config.toml*:

| Plugin                                   | Why it is needed                               | Output file(s)                                           |
| ---------------------------------------- | ---------------------------------------------- | -------------------------------------------------------- |
| **camera_extrinsics** | 3x4 camera extrinsic matrix per view               | `###_camera_extrinsics.txt`                      |
| **camera\_intrinsics**                   | Full 4x4 intrinsic matrix                    | `camera_intrinsics.txt`                                         |
| **mask** (optionally) | The BW images you want COLMAP to use          | `###_mask_###.png` |

Run the usual rendering command:

```bash
blender --background --python generate-batch.py -- scene.glb output_dir 100
```

After the batch you should have:

```
output_dir/
├── 000_camera_extrinsics.txt
├── 000_mask_000.png
├── 000_render.png
├── 001_camera_extrinsics.txt
├── ...
├── camera_intrinsics.txt
```

---

## 2 – Convert plugin output with `to_colmap.py`

Run the helper script:

```bash
poetry run python to_colmap.py ./output_dir ./colmap_project
```

## What the script does

1. **Renames images** – `012_render.png` → `012.png` and copies them to
   `colmap_project/images/`.
1. **Handles optional masks** – if `012_mask_000.png` exists it is copied as
   `colmap_project/masks/012.png.png` (*this is the exact file‑naming rule
   COLMAP uses to apply per‑image alpha masks; see [FAQ](https://colmap.github.io/faq.html#mask-image-regions)*).
1. **Creates COLMAP database** (`preloaded.db`) — initializes each required table
  (*this allows to skip manual matching of images and camera indices*). Database is initialized using [this](https://github.com/colmap/colmap/blob/5d9222729ee2edac80c10281668a49312a7f9498/scripts/python/database.py) script.
1. **Reads intrinsics** (`camera_intrinsics.txt`) and writes them to database and to
   `colmap_project/cameras.txt` using the **OPENCV** model:

   ```
   # CAMERA_ID, MODEL, WIDTH, HEIGHT, FX, FY, CX, CY, K1, K2, P1, P2
   1 OPENCV 800 800 fx fy cx cy 0 0 0 0
   ```
1. **Adds images to database** with correct camera_id and image_id.
1. **Reads every** `###_camera_extrinsics.txt`, converts 3 × 4 *Rt*
   to camera‑to‑world quaternion + translation, and appends a line to
   `colmap_project/images.txt`:

   ```
   # IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME
   0 qw qx qy qz tx ty tz 1 000.png
   ```

After the script finishes, the folder looks like:

```
colmap_project/
├── images/
│   ├── 000.png
│   ├── 001.png
│   └── ...
├── masks/           # only if original masks existed
│   ├── 000.png.png
│   ├── 001.png.png
│   └── ...
├── preloaded.db
└── sparse/
    └── manually_created/
        ├── cameras.txt
        ├── points3D.txt
        └── images.txt
```

Continue with COLMAP steps below.

---

## 3 – Run COLMAP with known poses

1. Recompute features from the images of the known camera poses as follows:

   ```bash
   colmap feature_extractor \
      --database_path ./colmap_project/preloaded.db \
      --image_path ./colmap_project/images \
      --ImageReader.mask_path ./colmap_project/masks
   ```

   Since we use `preloaded.db`, COLMAP should use present images, masks and camera settings.
   <details>

   <summary>Example of COLMAP log</summary>

   ```
   I20250510 20:49:53.332645 36308 feature_extraction.cc:258] Processed file [191/200]
   I20250510 20:49:53.338730 36308 feature_extraction.cc:261]   Name:            190_render.png
   I20250510 20:49:53.348786 36308 feature_extraction.cc:270]   Dimensions:      224 x 224
   I20250510 20:49:53.358615 36308 feature_extraction.cc:273]   Camera:          #1 - OPENCV
   I20250510 20:49:53.370881 36308 feature_extraction.cc:276]   Focal Length:    502.24px (Prior)
   I20250510 20:49:53.370965 36308 feature_extraction.cc:280]   Features:        346
   I20250510 20:49:53.371224 36308 feature_extraction.cc:258] Processed file [192/200]
   I20250510 20:49:53.371460 36308 feature_extraction.cc:261]   Name:            191_render.png
   I20250510 20:49:53.371499 36308 feature_extraction.cc:270]   Dimensions:      224 x 224
   I20250510 20:49:53.371557 36308 feature_extraction.cc:273]   Camera:          #1 - OPENCV
   I20250510 20:49:53.371591 36308 feature_extraction.cc:276]   Focal Length:    502.24px (Prior)
   I20250510 20:49:53.371626 36308 feature_extraction.cc:280]   Features:        363
   ```
   Note the "(Prior)" mark and matching cameras.

   </details>
1. Match features and triangulate all observations of registered images in an existing model using the feature matches in a database.

   ```bash
   colmap exhaustive_matcher \ # or alternatively any other matcher
       --database_path ./colmap_project/preloaded.db

   colmap point_triangulator \
       --database_path ./colmap_project/preloaded.db \
       --image_path ./colmap_project/images \
       --input_path ./colmap_project/sparse/manually_created \
       --output_path ./colmap_project/sparse/triangulated
   ```
1. Compute dense model as follows
   ```bash
   colmap image_undistorter \
       --image_path ./colmap_project/images \
       --input_path ./colmap_project/sparse/triangulated \
       --output_path ./colmap_project/dense/

   colmap patch_match_stereo \
       --workspace_path ./colmap_project/dense/

   colmap stereo_fusion \
       --workspace_path ./colmap_project/dense/ \
       --workspace_path ./colmap_project/dense/fused.ply
   ```

---

## 4 – FAQ

| Question                                     | Answer                                                                                                                                    |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| *What if my intrinsics vary per view?*       | Export a per‑view 4 × 4 matrix and write a separate **camera** entry (CAMERA\_ID > 1) for each image in `cameras.txt`.                    |
| *COLMAP complains about `wrong image paths`* | Ensure you copied/renamed the PNG files into the `images/` folder exactly as referenced in `images.txt`.                                  |
| *Can I skip sparse reconstruction entirely?* | Yes: as long as the database contains camera + image tables, you may run only `image_undistorter`, `patch_match_stereo`, `stereo_fusion`. |

[^1]: camera without distortions

---

![preview](prior_poses-cameras.png)
