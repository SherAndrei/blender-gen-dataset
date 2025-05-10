import os
import bpy
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
        ((s_u, skew, u_0),
        (   0,  s_v, v_0),
        (   0,    0,   1)))
    return K


def get_3x4_RT_matrix_from_blender(cam):
    """
    Returns camera rotation and translation matrices from Blender.

    There are 3 coordinate systems involved:
        1. The World coordinates: "world"
           - right-handed
        2. The Blender camera coordinates: "bcam"
           - x is horizontal
           - y is up
           - right-handed: negative z look-at direction
        3. The desired computer vision camera coordinates: "cv"
           - x is horizontal
           - y is down (to align to the actual pixel coordinate
             used in digital images)
           - right-handed: positive z look-at direction

    Source: https://blender.stackexchange.com/a/120063/236879
    """
    # bcam stands for blender camera
    R_bcam2cv = Matrix(
        ((1, 0,  0),
        (0, -1, 0),
        (0, 0, -1)))

    # Transpose since the rotation is object rotation,
    # and we want coordinate rotation
    # R_world2bcam = cam.rotation_euler.to_matrix().transposed()
    # T_world2bcam = -1*R_world2bcam @ location
    #
    # Use matrix_world instead to account for all constraints
    location, rotation = cam.matrix_world.decompose()[0:2]
    R_world2bcam = rotation.to_matrix().transposed()

    # Convert camera location to translation vector used in coordinate changes
    # T_world2bcam = -1*R_world2bcam @ cam.location
    # Use location from matrix_world to account for constraints:
    T_world2bcam = -1*R_world2bcam @ location

    # Build the coordinate transform matrix from world to computer vision camera
    R_world2cv = R_bcam2cv@R_world2bcam
    T_world2cv = R_bcam2cv@T_world2bcam

    # put into 3x4 matrix
    RT = Matrix((
        R_world2cv[0][:] + (T_world2cv[0],),
        R_world2cv[1][:] + (T_world2cv[1],),
        R_world2cv[2][:] + (T_world2cv[2],)
        ))
    return RT

def get_3x4_P_matrix_from_blender(cam):
    K = get_calibration_matrix_K_from_blender(cam.data)
    RT = get_3x4_RT_matrix_from_blender(cam)
    return K@RT

class CameraProjectionMatrix(IPlugin):
    """For each camera view, save the 3 by 4 projection matrix as JSON."""

    def on_camera_created(self, scene, camera_obj, index, output_path):
        # source: https://docs.blender.org/api/current/bpy.types.Object.html#bpy.types.Object.calc_matrix_camera
        # UPD: calc_matrix_camera as it seems does not work in headless mode
        # https://blender.stackexchange.com/questions/285730/camera-projection-matrix-is-always-the-same

        proj3x4 = get_3x4_P_matrix_from_blender(camera_obj)

        txt = "\n".join(" ".join(f"{v:.10f}" for v in row) for row in proj3x4)
        out_path = os.path.join(output_path, f"{index:03d}_camera_projection_matrix.txt")
        with open(out_path, "w") as f:
            f.write(txt)
