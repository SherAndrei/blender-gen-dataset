"""
Camera-intrinsics plugin
========================
Writes **camera_intrinsics.txt** once per batch.

Format
------
Four lines, four space-separated values each 0 a full 4 x 4 intrinsic matrix:

    fx  0   cx  0
    0   fy  cy  0
    0   0   1   0
    0   0   0   1

Assumptions
-----------
* Zero skew and no lens distortion
* Intrinsics are the same for every rendered view
"""

import os
from plugins import IPlugin

class CameraIntrinsics(IPlugin):
    """Generate a 4x4 intrinsic matrix and write camera_intrinsics.txt."""

    def __init__(self, user_cfg, user_plugin_cfg):
        super().__init__(user_cfg, user_plugin_cfg)
        self._written = False

    def on_camera_created(self, scene, camera_obj, index, output_path):
        # write only once – when the first camera is spawned
        if self._written:
            return

        cam  = camera_obj.data
        rend = scene.render

        # Effective resolution (honours percentage slider)
        W = rend.resolution_x * rend.resolution_percentage / 100.0
        H = rend.resolution_y * rend.resolution_percentage / 100.0

        # Focal length in pixels
        fx = cam.lens * (W / cam.sensor_width)
        fy = cam.lens * (H / cam.sensor_height)

        cx = W / 2.0
        cy = H / 2.0

        K4 = [
            [fx,  0.0,  cx, 0.0],
            [0.0,  fy,  cy, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]

        txt = "\n".join(" ".join(f"{v:.10f}" for v in row) for row in K4)
        out_path = os.path.join(output_path, "camera_intrinsics.txt")
        with open(out_path, "w") as f:
            f.write(txt)

        print(f"[CameraIntrinsics] 4x4 intrinsics written → {out_path}")
        self._written = True
