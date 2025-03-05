# Generate NeRF dataset using Blender Python API

As it states in [Blender's Python API Overview](https://docs.blender.org/api/current/info_overview.html)

> Blender has an embedded Python interpreter which is loaded when Blender is started and stays active while Blender is running.

We'll use Blender' Python interpreter to depend only on Blender version.
If this does not fit your needs, see [how to use system python](https://docs.blender.org/api/current/info_tips_and_tricks.html#bundled-python-extensions). One can also [build blender into a python module](https://developer.blender.org/docs/handbook/building_blender/python_module/).

These scripts were tested on
```
❯ blender.exe --background --python-expr "import sys; print(sys.version)"
Blender 4.3.2 (hash 32f5fdce0a0a built 2024-12-17 03:35:23)
3.11.9 (main, Oct 15 2024, 19:17:05) [MSC v.1929 64 bit (AMD64)]

Blender quit
```

---

To generate one batch of images run
```sh
blender --background --python generate-batch.py -- \
		--model_path /path/to/model.glb --num_images 10 --output_dir /path/to/output
```

To generate several batches in parallel run
```sh
./generate_batches.sh --model_path /path/to/model.glb \
    [--num_batches 1] [--num_images_per_batch 1] [--jobs <number>] [--output_dir <directory>]
```
or
```ps1
.\generate_batches.ps1 -model_path <path> [-num_batches <number>] [-num_images_per_batch <number>] [-jobs <number>] [-output_dir <directory>]
```

To assemble `.npz` dataset from batches we'll run `assemble-dataset.py`. This script requires `Pillow` package for converting images into rgb arrays. `Pillow` can be installed with
```sh
blender --background --python-expr "import sys; import subprocess; subprocess.check_call([sys.executable, \"-m\", \"pip\", \"install\", \"pillow\"])"
```

To assemble `.npz` dataset from batches run
```sh
blender --background --python assemble-dataset.py -- \
		--input <batches_folder> [--output dataset.npz]
```

Note: on headless systems (like WSL) before running you are required to set these environmental variables to be able to run on CPU.
```bash
export LIBGL_ALWAYS_SOFTWARE=1
export MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
```

Note: as it seems for now there is no support for in memory rendering. Sources:
* https://stackoverflow.com/a/58948767/15751315
* https://devtalk.blender.org/t/is-it-possible-to-store-keep-the-rendering-result-in-memory-only-and-avoid-doing-i-o/11852/2
* https://blender.stackexchange.com/q/289920
So, to speedup performance it is recommended to use RAMDISK, according to [this tutorial](https://web.archive.org/web/20180123110848/http://ubuntublog.org/tutorials/how-to-create-ramdisk-linux.htm)
```bash
sudo mkdir -p /media/generatormeta
sudo mount -t tmpfs -o size=1024M tmpfs /media/generatormeta/
```
