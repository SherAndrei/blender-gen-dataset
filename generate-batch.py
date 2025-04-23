#!/usr/bin/env python3
"""
Script for generating rendered images of a 3D model
from random camera positions using Blender, driven by config.toml.

Usage:
    blender --background --python generate-batch.py -- \
        --model_path /path/to/model.glb --num_images 10 --output_dir /path/to/output

The script:
    - Clears the current scene.
    - Imports the 3D model (supports OBJ, FBX, glTF, GLB).
    - Sets up the render engine (Eevee) with world and light settings
      approximating Blender's Material Preview mode.
    - Adds a fixed single light source.
    - For each image, creates a camera at a random position on a sphere
      (radius=10) above the object, points it to the origin,
      enables depth of field and renders the image.
"""

import argparse
import math
import os
import random
import tomllib
import sys

import bpy
import mathutils


def strip_blender_argv():
    """Remove everything before '--' from `sys.argv`"""
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--") + 1:]
    else:
        return []


def parse_args():
    """Parse command-line arguments passed after '--'."""
    argv = strip_blender_argv()
    parser = argparse.ArgumentParser(
        description="Script for generating rendered images of a 3D model from "
        + "random camera positions using Blender, driven by config.toml."
    )
    parser.add_argument(
        "model_path",
        type=str,
        help="Path to the 3D model file (OBJ, FBX, glTF, GLB).",
    )
    parser.add_argument(
        "output_directory",
        type=str,
        help="Directory where the rendered images will be saved.",
    )
    parser.add_argument(
        "number_of_renders",
        type=int,
        default=1,
        nargs='?',
        help="Number of images to generate per run.",
    )
    return parser.parse_args(argv)


def clear_scene():
    """Delete all objects from the current scene."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    # Also clear meshes, cameras, lights, etc.
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)
    for block in bpy.data.cameras:
        bpy.data.cameras.remove(block)
    for block in bpy.data.lights:
        bpy.data.lights.remove(block)


def import_model(model_path):
    """Import a 3D model based on its file extension."""
    ext = os.path.splitext(model_path)[1].lower()
    print("Data are loaded, start creating Blender stuff")
    if ext == ".obj":
        bpy.ops.import_scene.obj(filepath=model_path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=model_path)
    elif ext in (".gltf", ".glb"):
        bpy.ops.import_scene.gltf(filepath=model_path)
    else:
        raise ValueError("Unsupported model format: {}".format(ext))
    # Force update of scene after import.
    bpy.context.view_layer.update()


def add_fixed_light(light_configuration):
    """Evenly illuminate the object from six directions."""

    energy = light_configuration.get('energy', 10)
    # distance from origin for each sun lamp
    radius = light_configuration.get('radius', 10.0)

    # Six cardinal directions
    directions = [
        (1,  0,  0), (-1,  0,  0),
        (0,  1,  0), ( 0, -1,  0),
        (0,  0,  1), ( 0,  0, -1),
    ]

    for idx, dir_vec in enumerate(directions):
        # Create a Sun lamp
        ld = bpy.data.lights.new(name=f"EvenSun{idx}", type='SUN')
        ld.energy = energy
        lo = bpy.data.objects.new(name=f"EvenSun{idx}", object_data=ld)

        # Position it out on the sphere
        lo.location = [d * radius for d in dir_vec]

        # Rotate so its negative Z axis points toward the origin
        rot = mathutils.Vector(dir_vec).to_track_quat('-Z', 'Y').to_euler()
        lo.rotation_euler = rot

        bpy.context.scene.collection.objects.link(lo)


def setup_world():
    """Configure world settings to mimic Material Preview mode."""
    if bpy.context.scene.world is None:
        bpy.context.scene.world = bpy.data.worlds.new("World")
    world = bpy.context.scene.world
    world.use_nodes = True


def setup_render_engine(render_configuration):
    """Set render engine and configure some settings."""
    scene = bpy.context.scene
    scene.render.resolution_x = render_configuration['resolution_x']
    scene.render.resolution_y = render_configuration['resolution_y']
    scene.render.resolution_percentage = 100
    if render_configuration["engine"] == 'cycles':
        scene.render.engine = "CYCLES"
        scene.cycles.samples = render_configuration["samples"]
        scene.cycles.use_denoising = render_configuration['cycles']["use_denoising"]
        scene.cycles.use_adaptive_sampling = render_configuration['cycles']["use_adaptive_sampling"]
    elif render_configuration['engine'] == 'eevee':
        if bpy.app.version > (4, 1, 0):
          scene.render.engine = "BLENDER_EEVEE_NEXT"
          scene.eevee.use_raytracing =  render_configuration['eevee']["use_raytracing"]
        else:
          scene.render.engine = "BLENDER_EEVEE"
          scene.eevee.use_ssr = render_configuration['eevee']["use_ssr"]

        scene.eevee.taa_render_samples = render_configuration["samples"]
        scene.eevee.use_gtao = render_configuration['eevee']["use_gtao"]
        scene.eevee.shadow_pool_size = render_configuration['eevee']["shadow_pool_size"]


def create_camera(camera_configuration):
    """Create and configure a new camera object."""
    cam_data = bpy.data.cameras.new("RandomCam")
    cam_obj = bpy.data.objects.new("RandomCam", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)

    cam_obj.data.lens = camera_configuration['focal_length']

    if camera_configuration['use_dof']:
      cam_obj.data.dof.use_dof = True
      cam_obj.data.dof.aperture_fstop = camera_configuration['dof']['aperture_fstop']

    return cam_obj


def point_camera_at(cam_obj, target):
    """
    Orient the object to look at the target point.

    Args:
        obj: The Blender object to orient (e.g., camera).
        target: mathutils.Vector representing the target point.
    """
    direction = target - cam_obj.location
    quat = direction.to_track_quat("-Z", "Y")
    cam_obj.rotation_euler = quat.to_euler()

    if cam_obj.data.dof.use_dof:
      focus_distance = (target - cam_obj.location).length
      cam_obj.data.dof.focus_distance = focus_distance


def render_image(scene, output_filepath):
    """
    Render the current scene and save the image.

    Args:
        scene: The current Blender scene.
        output_filepath: Filepath where the image will be saved.
    """
    scene.render.filepath = output_filepath
    bpy.ops.render.render(write_still=True)


def spherical_to_cartesian(radius, inc, azi):
    """Convert spherical coords to Cartesian (x,y,z)."""
    x = radius * math.sin(inc) * math.cos(azi)
    y = radius * math.sin(inc) * math.sin(azi)
    z = radius * math.cos(inc)
    return x, y, z


def random_camera_position(camera_position_configuration):
    """Sample a random point on the upper hemisphere."""
    r = random.uniform(camera_position_configuration["r_min"], camera_position_configuration["r_max"])
    inc = random.uniform(camera_position_configuration["inc_min"], camera_position_configuration["inc_max"])
    azi = random.uniform(camera_position_configuration["azi_min"], camera_position_configuration["azi_max"])
    return spherical_to_cartesian(r, inc, azi)


def load_config(path="config.toml"):
    """Load and return the TOML config as a dict."""
    with open(path, "rb") as f:
        return tomllib.load(f)


def main():
    """Main function."""
    args = parse_args()
    cfg = load_config()

    model_path = args.model_path
    N = args.number_of_renders

    if cfg.get("seed") is not None:
      random.seed(cfg["seed"])

    output_dir = args.output_directory
    os.makedirs(output_dir, exist_ok=True)

    clear_scene()
    import_model(model_path)

    setup_world()
    setup_render_engine(cfg.get('render'))

    add_fixed_light(cfg.get('light'))

    # Assume the imported object is centered at origin.
    target = mathutils.Vector((0.0, 0.0, 0.0))
    scene = bpy.context.scene

    for i in range(N):
        cam_obj = create_camera(cfg['camera'])
        cam_obj.location = random_camera_position(cfg["camera"]["position"])
        point_camera_at(cam_obj, target)

        scene.camera = cam_obj

        image_filename = f"render_{i:03d}.png"
        output_filepath = os.path.join(output_dir, image_filename)
        print(f"Rendering image {i+1}/{N} to {output_filepath}...")
        render_image(scene, output_filepath)

        # Clean up: remove the camera.
        camera = cam_obj.data
        bpy.data.objects.remove(cam_obj, do_unlink=True)
        bpy.data.cameras.remove(camera, do_unlink=True)

    print("Rendering completed.")


if __name__ == "__main__":
    main()
