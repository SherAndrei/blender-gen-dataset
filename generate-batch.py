#!/usr/bin/env python3
"""
Script for generating realistic rendered images of a 3D model
from random camera positions using Blender.

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
import csv
import math
import os
import random
import sys

import bpy
import mathutils


def parse_args():
    """Parse command-line arguments passed after '--'."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    parser = argparse.ArgumentParser(
        description="Generate realistic rendered images of a 3D model."
    )
    parser.add_argument(
        "--model_path",
        type=str,
        required=True,
        help="Path to the 3D model file (OBJ, FBX, glTF, GLB).",
    )
    parser.add_argument(
        "--num_images",
        type=int,
        default=1,
        help="Number of images to generate.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="Directory where the rendered images will be saved.",
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


def add_fixed_light():
    """Add a fixed light source if not already added.
    
    The light is a Sun lamp placed at a fixed location.
    """
    if "FixedSun" in bpy.data.objects:
        return
    light_data = bpy.data.lights.new(name="FixedSun", type="SUN")
    light_data.energy = 5.0  # Adjust energy as needed
    light_obj = bpy.data.objects.new(name="FixedSun", object_data=light_data)
    light_obj.location = (5, -5, 10)
    bpy.context.scene.collection.objects.link(light_obj)


def setup_world():
    """Configure world settings to mimic Material Preview mode."""
    if bpy.context.scene.world is None:
        bpy.context.scene.world = bpy.data.worlds.new("World")
    world = bpy.context.scene.world
    world.use_nodes = True


def setup_render_engine():
    """Set render engine to Eevee and configure some settings."""
    scene = bpy.context.scene
    scene.render.resolution_x = 100
    scene.render.resolution_y = 100
    scene.render.resolution_percentage = 100
    if bpy.app.version > (4, 1, 0):
        scene.render.engine = "BLENDER_EEVEE_NEXT"
        scene.eevee.use_raytracing = True
    else:
        scene.render.engine = "BLENDER_EEVEE"
        scene.eevee.use_ssr = True
    # Enable ambient occlusion for extra realism.
     scene.eevee.use_gtao = True
    # Increase shadow pool size to avoid Shadow buffer full error
    scene.eevee.shadow_pool_size  = '1024'


def create_camera():
    """Create and return a new camera object."""
    cam_data = bpy.data.cameras.new("RandomCam")
    cam_obj = bpy.data.objects.new("RandomCam", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    return cam_obj


def look_at(obj, target):
    """
    Orient the object to look at the target point.
    
    Args:
        obj: The Blender object to orient (e.g., camera).
        target: mathutils.Vector representing the target point.
    """
    direction = target - obj.location
    quat = direction.to_track_quat("-Z", "Y")
    obj.rotation_euler = quat.to_euler()


def render_image(scene, output_filepath):
    """
    Render the current scene and save the image.
    
    Args:
        scene: The current Blender scene.
        output_filepath: Filepath where the image will be saved.
    """
    scene.render.filepath = output_filepath
    bpy.ops.render.render(write_still=True)


def generate_random_camera_position(radius=10.0):
    """
    Generate a random camera position on a sphere of the given radius.
    
    The elevation (phi) is chosen in [0, pi/2] so that the camera is above
    the object.
    
    Returns:
        Tuple (x, y, z) representing the camera location.
    """
    theta = random.uniform(0, 2 * math.pi)
    phi = random.uniform(0, math.pi / 2)
    x = radius * math.sin(phi) * math.cos(theta)
    y = radius * math.sin(phi) * math.sin(theta)
    z = radius * math.cos(phi)
    return (x, y, z)


def main():
    """Main function."""
    args = parse_args()

    # Ensure output directory exists.
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # Prepare CSV file for metadata.
    csv_filepath = os.path.join(args.output_dir, "metadata.csv")
    csv_file = open(csv_filepath, "w", newline="")
    csv_writer = csv.writer(csv_file)
    # Write header: filename, followed by 16 pose values, then focal.
    header = ["filename"] + [f"m{i}{j}" for i in range(4) for j in range(4)] + ["focal"]
    csv_writer.writerow(header)

    focal = 35

    # Clear scene and import model.
    clear_scene()
    import_model(args.model_path)

    # Set up world and render engine.
    setup_world()
    setup_render_engine()

    # Add a fixed single light source.
    add_fixed_light()

    # Assume the imported object is centered at origin.
    target = mathutils.Vector((0.0, 0.0, 0.0))
    scene = bpy.context.scene

    for i in range(args.num_images):
        # Create a camera.
        cam_obj = create_camera()
        cam_obj.location = generate_random_camera_position(radius=10.0)
        look_at(cam_obj, target)

        # Set camera parameters.
        cam_obj.data.lens = focal

        # Enable depth of field for a photographic effect.
        cam_obj.data.dof.use_dof = True
        focus_distance = (target - cam_obj.location).length
        cam_obj.data.dof.focus_distance = focus_distance
        cam_obj.data.dof.aperture_fstop = 2.8  # Lower f-stop for shallower depth of field

        scene.camera = cam_obj

        image_filename = f"render_{i:03d}.png"
        output_filepath = os.path.join(args.output_dir, image_filename)
        print(f"Rendering image {i+1}/{args.num_images} to {output_filepath}...")
        render_image(scene, output_filepath)

        # Get the camera's world transformation matrix.
        pose_matrix = cam_obj.matrix_world
        # Flatten the 4x4 matrix into a list of 16 values.
        pose_flat = [f"{elem:.6f}" for row in pose_matrix for elem in row]

        # Write CSV row: filename, flattened pose, focal.
        csv_writer.writerow([image_filename] + pose_flat + [f"{focal:.2f}"])

        # Define output file for this render.
        output_filepath = os.path.join(args.output_dir, f"render_{i:03d}.png")
        print(f"Rendering image {i+1}/{args.num_images} to {output_filepath}")
        render_image(scene, output_filepath)

        # Clean up: remove the camera.
        camera = cam_obj.data
        bpy.data.objects.remove(cam_obj, do_unlink=True)
        bpy.data.cameras.remove(camera, do_unlink=True)

    print("Rendering completed.")


if __name__ == "__main__":
    main()
