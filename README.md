# Generate Learning-based Multi-view Stereo dataset using Blender Python API

As it states in [Blender's Python API Overview](https://docs.blender.org/api/current/info_overview.html)

> Blender has an embedded Python interpreter which is loaded when Blender is started and stays active while Blender is running.

This repository provides ability to generate synthetic datasets using ***ONLY*** Blender executable without any additional dependency.

Script was tested on
```
❯ blender.exe --background --python-expr "import sys; print(sys.version)"
Blender 4.2.9 LTS (hash a10f621e649a built 2025-04-15 01:46:41)
3.11.7 (main, Jun 11 2024, 12:31:01) [GCC 11.2.1 20220127 (Red Hat 11.2.1-9)]

Blender quit
```

---
## Examples

See help
```
Blender 4.2.9 LTS (hash a10f621e649a built 2025-04-15 01:46:41)
usage: blender [-h] model_path output_directory [number_of_renders]

Script for generating rendered images of a 3D model using Blender, driven by config.toml.

positional arguments:
  model_path         Path to the 3D model file (OBJ, FBX, glTF, GLB).
  output_directory   Directory where the rendered images will be saved.
  number_of_renders  Number of images to generate per run.

options:
  -h, --help         show this help message and exit
  --dump-config      Dump user configuration as python dict and exit.
  --skip-render      Setup everything and skip render.
```

1. Export monkey mesh Suzanne from `blender` as `.glb` (or download it [here](https://sketchfab.com/3d-models/suzanne-blender-monkey-29a3463e8d314c8fbda620800019cfb9))
1. To generate one image into `output` directory use

   ```sh
   blender --background --python generate-batch.py -- suzanne.glb ./output
   ```

1. See result in `output` directory

   ![preview](./references/suzanne.png)

1. To generate 16 images from random locations into `output` directory use

   ```sh
   blender --background --python generate-batch.py -- suzanne.glb ./output 16
   ```

1. See result in `output` directory[^1]

   ![preview](./references/suzannes.png)

---
## Configuration

Script provides extensive configuration via user defined `config.toml`, see [config.default.toml](config.default.toml) for available parameters.

To dump parsed config and exit the program use

   ```sh
   blender --background --python generate-batch.py -- --dump-config
   ```

---
## Plugins

This project ships with a config‑driven plugin system that lets you bolt new functionality onto the rendering pipeline without touching the main script.

![preview](references/diamonds.png)

See available plugins and more in [PLUGINS.md](PLUGINS.md).

---
## Compatibility

The `compat/` directory contains helper scripts to restructure the output of this Blender dataset generator into formats compatible with popular neural rendering and 3D reconstruction frameworks:

### Available Converters:
1. **COLMAP** - Converts to standard COLMAP structure (images/, sparse/)
   ```sh
   python compat/to_colmap/to_colmap.py <input_dir> <output_dir>
   ```
2. **NSVF** - Prepares data for Neural Sparse Voxel Fields pipeline
   ```sh
   python compat/to_nsvf_dataset/to_nsvf_dataset.py <input_dir> <output_dir>
   ```
3. **IDR** - Formats data for Implicit Differentiable Renderer requirements
   ```sh
   python compat/to_idr_dataset/to_idr_dataset.py <input_dir> <output_dir>
   ```

---

## FAQ

See [FAQ.md](FAQ.md)

[^1]: this grid was made with [this](scripts/grid/)
