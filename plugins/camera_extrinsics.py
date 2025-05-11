import os
import bpy
from plugins import IPlugin

import bpy
from mathutils import Matrix

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

class CameraExtrinsics(IPlugin):
    """For each camera view, save the 3 by 4 projection matrix as JSON."""

    def on_camera_created(self, scene, camera_obj, index, output_path):
        RT = get_3x4_RT_matrix_from_blender(camera_obj)

        txt = "\n".join(" ".join(f"{v:.10f}" for v in row) for row in RT)
        out_path = os.path.join(output_path, f"{index:03d}_camera_extrinsics.txt")
        with open(out_path, "w") as f:
            f.write(txt)
