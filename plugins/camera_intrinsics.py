"""
Camera-intrinsics plugin
========================
Writes **camera_intrinsics.txt** once per batch.

Format
------
Four lines, four space-separated values each 0 a full 3 x 3 intrinsic matrix:

    fx  0   cx
    0   fy  cy
    0   0   1

Assumptions
-----------
* Zero skew and no lens distortion
* Intrinsics are the same for every rendered view
"""

import os
from plugins import IPlugin

import bpy
from mathutils import Matrix

# BKE_camera_sensor_size
# Source: https://github.com/blender/blender/blob/4de3172058bb1c4ab4dc6fd1d673462190d6ef54/source/blender/blenkernel/intern/camera.cc#L323
def get_sensor_size(sensor_fit, sensor_x, sensor_y):
    if sensor_fit == 'VERTICAL':
        return sensor_y
    return sensor_x

# BKE_camera_sensor_fit
# Source: https://github.com/blender/blender/blob/4de3172058bb1c4ab4dc6fd1d673462190d6ef54/source/blender/blenkernel/intern/camera.cc#L334
def get_sensor_fit(sensor_fit, size_x, size_y):
    if sensor_fit == 'AUTO':
        if size_x >= size_y:
            return 'HORIZONTAL'
        else:
            return 'VERTICAL'
    return sensor_fit

def get_calibration_matrix_K_from_blender(camd):
    """Build intrinsic camera parameters from Blender camera data.
       Source: https://blender.stackexchange.com/a/120063/236879
    """
    if camd.type != 'PERSP':
        raise ValueError('Non-perspective cameras not supported')
    scene = bpy.context.scene
    f_in_mm = camd.lens
    scale = scene.render.resolution_percentage / 100
    resolution_x_in_px = scale * scene.render.resolution_x
    resolution_y_in_px = scale * scene.render.resolution_y
    sensor_size_in_mm = get_sensor_size(camd.sensor_fit, camd.sensor_width, camd.sensor_height)
    sensor_fit = get_sensor_fit(
        camd.sensor_fit,
        scene.render.pixel_aspect_x * resolution_x_in_px,
        scene.render.pixel_aspect_y * resolution_y_in_px
    )
    pixel_aspect_ratio = scene.render.pixel_aspect_y / scene.render.pixel_aspect_x
    if sensor_fit == 'HORIZONTAL':
        view_fac_in_px = resolution_x_in_px
    else:
        view_fac_in_px = pixel_aspect_ratio * resolution_y_in_px
    pixel_size_mm_per_px = sensor_size_in_mm / f_in_mm / view_fac_in_px
    s_u = 1 / pixel_size_mm_per_px
    s_v = 1 / pixel_size_mm_per_px / pixel_aspect_ratio

    # Parameters of intrinsic calibration matrix K
    u_0 = resolution_x_in_px / 2 - camd.shift_x * view_fac_in_px
    v_0 = resolution_y_in_px / 2 + camd.shift_y * view_fac_in_px / pixel_aspect_ratio
    skew = 0 # only use rectangular pixels

    K = Matrix(
        ((s_u, skew, u_0,),
        (   0,  s_v, v_0,),
        (   0,    0,   1,)))
    return K

class CameraIntrinsics(IPlugin):
    """Generate a 3x3 intrinsic matrix and write camera_intrinsics.txt."""

    def __init__(self, user_cfg, user_plugin_cfg):
        super().__init__(user_cfg, user_plugin_cfg)
        self._written = False

    def on_camera_created(self, scene, camera_obj, index, output_path):
        # write only once – when the first camera is spawned
        if self._written:
            return

        cam  = camera_obj.data
        K4 = get_calibration_matrix_K_from_blender(cam)

        txt = "\n".join(" ".join(f"{v:.10f}" for v in row) for row in K4)
        out_path = os.path.join(output_path, "camera_intrinsics.txt")
        with open(out_path, "w") as f:
            f.write(txt)

        print(f"[CameraIntrinsics] 3x3 intrinsics written → {out_path}")
        self._written = True
