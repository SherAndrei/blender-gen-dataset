"""
Bounding-box plugin
===================
Writes **bounding_box.txt** - a single line with

    x_min  y_min  z_min  x_max  y_max  z_max  initial_voxel_size

This is the format expected by many NeRF/Tensor field pipelines.
"""

import os
import re
import logging

from mathutils import Vector
from plugins import IPlugin

class BoundingBox(IPlugin):
    """Compute scene bounding-box and save bbox.txt."""

    def __init__(self, cfg, plugin_cfg):
        self._plugin_cfg = plugin_cfg

    def on_scene_created(self, scene, output_path):

        inf = float("inf")
        x_min = y_min = z_min =  inf
        x_max = y_max = z_max = -inf
        found = False

        exclude = self._plugin_cfg.get("exclude_pattern", "")
        for obj in scene.objects:
            if re.search(obj.name, exclude):
                print("true")
                logging.info(f"[BBox] skip {obj.name} (matches exclude_regex)")
                continue

            found = True
            mat = obj.matrix_world
            for corner in obj.bound_box:  # eight local‑space points
                world = mat @ Vector(corner)
                x_min = min(x_min, world.x)
                y_min = min(y_min, world.y)
                z_min = min(z_min, world.z)
                x_max = max(x_max, world.x)
                y_max = max(y_max, world.y)
                z_max = max(z_max, world.z)

        if not found:
            logging.warning("[BBox] no valid mesh objects found - bbox.txt not written")
            return

        voxel_size = self._plugin_cfg.get("voxel_size")
        if not voxel_size:
            max_dim = max(x_max - x_min, y_max - y_min, z_max - z_min)
            voxel_size = max_dim / 128

        bbox_line = f"{x_min} {y_min} {z_min} {x_max} {y_max} {z_max} {voxel_size}"
        out_file  = os.path.join(output_path, "bounding_box.txt")
        with open(out_file, "w") as f:
            f.write(bbox_line + "\n")

        print(f"[BBox] bbox.txt saved to {out_file}")
