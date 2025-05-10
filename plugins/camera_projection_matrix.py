import os
import bpy
from plugins import IPlugin

class CameraProjectionMatrix(IPlugin):
    """For each camera view, save the 3 by 4 projection matrix as JSON."""

    def on_camera_created(self, scene, camera_obj, index, output_path):
        # source: https://docs.blender.org/api/current/bpy.types.Object.html#bpy.types.Object.calc_matrix_camera
        depsgraph = bpy.context.evaluated_depsgraph_get()
        cam_eval = camera_obj.evaluated_get(depsgraph)

        res_x = scene.render.resolution_x
        res_y = scene.render.resolution_y
        scale = scene.render.resolution_percentage / 100.0
        mat4 = cam_eval.calc_matrix_camera(
            depsgraph,
            x=int(res_x * scale),
            y=int(res_y * scale),
            scale_x=1,
            scale_y=1
        )

        proj3x4 = [
            [mat4[0][0], mat4[0][1], mat4[0][2], mat4[0][3]],
            [mat4[1][0], mat4[1][1], mat4[1][2], mat4[1][3]],
            [mat4[2][0], mat4[2][1], mat4[2][2], mat4[2][3]],
        ]

        txt = "\n".join(" ".join(f"{v:.10f}" for v in row) for row in proj3x4)
        out_path = os.path.join(output_path, f"{index:03d}_camera_projection_matrix.txt")
        with open(out_path, "w") as f:
            f.write(txt)
