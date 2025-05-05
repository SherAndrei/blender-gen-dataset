import json
import logging
import math
import os
import re

from plugins import IPlugin

import mathutils

class NormalizationMatrix(IPlugin):
    """Computes the 4 by 4 scale matrix that brings the scene hull into the unit sphere."""

    def __init__(self, cfg, plugin_cfg):
        self._exclude = plugin_cfg.get("exclude_pattern", "")

    def on_scene_created(self, scene, output_path):
        min_x = min_y = min_z =  float('inf')
        max_x = max_y = max_z = -float('inf')
        found = False

        for obj in scene.objects:
            if re.search(obj.name, self._exclude):
                logging.info(f"[NormalizationMatrix] skip {obj.name} (matches exclude_regex)")
                continue

            found = True
            mat = obj.matrix_world
            for corner in obj.bound_box:
                co = mat @ mathutils.Vector(corner)
                min_x = min(co.x, min_x)
                min_y = min(co.y, min_y)
                min_z = min(co.z, min_z)
                max_x = max(co.x, max_x)
                max_y = max(co.y, max_y)
                max_z = max(co.z, max_z)

        if not found:
            logging.warning("[NormalizationMatrix] no valid mesh objects found - normalization_matrix.json not written")
            return

        hx = (max_x - min_x) / 2.0
        hy = (max_y - min_y) / 2.0
        hz = (max_z - min_z) / 2.0

        R = math.sqrt(hx*hx + hy*hy + hz*hz) if (hx or hy or hz) else 1.0
        s = 1.0 / R

        scale_mat = [
            [   s, 0.0, 0.0, 0.0 ],
            [ 0.0,   s, 0.0, 0.0 ],
            [ 0.0, 0.0,   s, 0.0 ],
            [ 0.0, 0.0, 0.0, 1.0 ],
        ]

        fn = os.path.join(output_path, "normalization_matrix.json")
        with open(fn, "w") as f:
            json.dump(scale_mat, f, indent=None)
