# Generate NeRF dataset using Blender Python API

Run
```
blender --background --python generate-batch.py -- \
		--model_path /path/to/model.glb --num_images 10 --output_dir /path/to/output
```

Note: on headless systems (like WSL) before running you are required to set these environmental variables to be able to run on CPU.
```bash
export LIBGL_ALWAYS_SOFTWARE=1
export MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
```
