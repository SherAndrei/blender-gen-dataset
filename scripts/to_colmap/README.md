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
| **camera_projection_matrix**                           | 3 × 4 camera projection per view               | `###_camera_projection_matrix.txt`                      |
| **camera\_intrinsics**                   | Full 4 × 4 intrinsic matrix                    | `camera_intrinsics.txt`                                         |
| **mask** (optionally) | The BW images you want COLMAP to use          | `###_mask_###.png` |

Run the usual rendering command:

```bash
blender --background --python generate-batch.py -- scene.glb output_dir 100
```

After the batch you should have:

```
output_dir/
├── 000_camera_projection_matrix.txt
├── 000_mask_000.png
├── 000_render.png
├── 001_camera_projection_matrix.txt
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
2. **Handles optional masks** – if `012_mask_000.png` exists it is copied as
   `colmap_project/masks/012.png.png` (*this is the exact file‑naming rule
   COLMAP uses to apply per‑image alpha masks; see [FAQ](https://colmap.github.io/faq.html#mask-image-regions)*).
3. **Reads intrinsics** (`camera_intrinsics.txt`) and writes
   `colmap_project/cameras.txt` using the **OPENCV** model:

   ```
   # CAMERA_ID, MODEL, WIDTH, HEIGHT, FX, FY, CX, CY, K1, K2, P1, P2
   1 OPENCV 800 800 fx fy cx cy 0 0 0 0
   ```
4. **Reads every** `###_camera_projection_matrix.txt`, converts 3 × 4 *P*
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
└── sparse/
    └── 0/
        ├── cameras.txt
        └── images.txt
```

Continue with COLMAP steps below.

---

## 3 – Run COLMAP with known poses

1. **Create an empty database**

   ```bash
   colmap database_creator --database_path db.db
   ```
2. **Populate database from text files**

   ```bash
   colmap model_converter \
       --input_path cameras.txt,images.txt \
       --output_path sparse_init --output_type TXT \
       --database_path db.db        # writes cameras & images into DB
   ```
3. **Extract features** *(no pose estimation)*

   ```bash
   colmap feature_extractor \
       --database_path db.db \
       --image_path images \
       --ImageReader.single_camera 1 \
       --ImageReader.camera_model OPENCV \
       --ImageReader.camera_params fx,fy,cx,cy,0,0,0,0
   ```
4. *(Optional)* **Match features** and build a sparse model if you need it:

   ```bash
   colmap exhaustive_matcher --database_path db.db
   colmap mapper --database_path db.db --image_path images \
                 --input_path sparse_init --output_path sparse
   ```
5. **Dense reconstruction** directly from the known poses (or the refined
   sparse model):

   ```bash
   colmap image_undistorter  --image_path images --input_path sparse_init \
                             --output_path dense --output_type COLMAP
   colmap patch_match_stereo --workspace_path dense
   colmap stereo_fusion      --workspace_path dense --output_path dense/fused.ply
   ```

After `stereo_fusion` you will have a dense point cloud
`dense/fused.ply` reconstructed from the Blender‑generated views.

---

## 3 – Run COLMAP with known poses

1. (*Optionally*) **Create an empty project in output directory**

   ```bash
	 colmap project_generator --quality=extreme --random_seed=1 --output_path=path/to/output/project.ini
	 ```
1. **Create an empty database**

   ```bash
   colmap database_creator --database_path --random_seed=1 path/to/output/db.db
   ```
1. **Populate database from text files**

   ```bash
   colmap model_converter \
       --input_path cameras.txt,images.txt \
       --output_path sparse_init --output_type TXT \
       --database_path db.db        # writes cameras & images into DB
   ```
3. **Extract features** *(no pose estimation)*

   ```bash
   colmap feature_extractor \
       --database_path db.db \
       --image_path images \
       --ImageReader.single_camera 1 \
       --ImageReader.camera_model OPENCV \
       --ImageReader.camera_params fx,fy,cx,cy,0,0,0,0
   ```
4. *(Optional)* **Match features** and build a sparse model if you need it:

   ```bash
   colmap exhaustive_matcher --database_path db.db
   colmap mapper --database_path db.db --image_path images \
                 --input_path sparse_init --output_path sparse
   ```
5. **Dense reconstruction** directly from the known poses (or the refined
   sparse model):

   ```bash
   colmap image_undistorter  --image_path images --input_path sparse_init \
                             --output_path dense --output_type COLMAP
   colmap patch_match_stereo --workspace_path dense
   colmap stereo_fusion      --workspace_path dense --output_path dense/fused.ply
   ```

After `stereo_fusion` you will have a dense point cloud
`dense/fused.ply` reconstructed from the Blender‑generated views.

---

## 4 – FAQ

| Question                                     | Answer                                                                                                                                    |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| *What if my intrinsics vary per view?*       | Export a per‑view 4 × 4 matrix and write a separate **camera** entry (CAMERA\_ID > 1) for each image in `cameras.txt`.                    |
| *COLMAP complains about `wrong image paths`* | Ensure you copied/renamed the PNG files into the `images/` folder exactly as referenced in `images.txt`.                                  |
| *Can I skip sparse reconstruction entirely?* | Yes: as long as the database contains camera + image tables, you may run only `image_undistorter`, `patch_match_stereo`, `stereo_fusion`. |

[^1]: camera without distortions
