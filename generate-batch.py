#!/usr/bin/env python3
"""
Script for generating rendered images of a 3D model using Blender, driven by config.toml.

Usage:
    blender --background --python generate-batch.py -- \
        /path/to/model.glb /path/to/output 10
"""

import argparse
import datetime
import math
import os
import random
import tomllib
import shutil
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
        description="Script for generating rendered images of a 3D model using "
        + "Blender, driven by config.toml."
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
    elif ext in ".blend":
        bpy.ops.wm.open_mainfile(filepath=model_path)
    else:
        raise ValueError("Unsupported model format: {}".format(ext))
    # Force update of scene after import.
    bpy.context.view_layer.update()


def safe_eval(expr) -> float:
    if isinstance(expr, (int, float)):
        return float(expr)
    from types import MappingProxyType
    """Evaluate a numeric Python expression in a restricted namespace."""
    allowed_names = MappingProxyType({"math": math, "pi": math.pi})
    try:
        value = eval(expr, {"__builtins__": {}}, allowed_names)
    except Exception as exc:
        raise argparse.ArgumentTypeError(f"Bad expression '{expr}': {exc}")
    if not isinstance(value, (int, float)):
        raise argparse.ArgumentTypeError(f"Expression '{expr}' did not return a number")
    return float(value)


def next_location_on_sphere(inc_start: float, inc_stop: float, inc_step: float, i: int, N: int):
    if not (0 <= i < N):
        raise ValueError("0 <= i < N must hold")
    if not (0 <= inc_start < (math.pi / 2)):
        raise ValueError("0 <= inc_start < (math.pi / 2) must hold")
    if not (0 < inc_stop <= (math.pi / 2)):
        raise ValueError("0 < inc_stop <= (math.pi / 2) must hold")
    if not (inc_start < inc_stop):
        raise ValueError("inc_start < inc_stop must hold")
    if not (inc_step > 0):
        raise ValueError("inc_step > 0 must hold")

    # `ceil` to include band on `inc_start` position
    n_bands = math.ceil((inc_stop - inc_start) / inc_step)
    locations_per_slice = (N + n_bands - 1) // n_bands
    current_slice = i // locations_per_slice
    inc = inc_start + inc_step * current_slice
    azi = (2 * math.pi * (i + 1)) / locations_per_slice
    return inc, azi


def spherical_to_cartesian(radius, inc, azi):
    """Convert spherical coords to Cartesian (x,y,z)."""
    x = radius * math.sin(inc) * math.cos(azi)
    y = radius * math.sin(inc) * math.sin(azi)
    z = radius * math.cos(inc)
    return x, y, z


def point_object_at(obj, target):
    direction = target - obj.location
    quat = direction.to_track_quat("-Z", "Y")
    obj.rotation_euler = quat.to_euler()


def setup_light(light_configuration, target):
    light_type = light_configuration.get('type', 'SUN')
    energy = light_configuration.get('energy', 1.0)
    mode = light_configuration.get('mode', 'uniform')

    mode_cfg = light_configuration[mode]
    if mode == 'uniform':
        amount = mode_cfg.get('amount', 3)
        radius = mode_cfg.get('radius', 10.0)
        inc_start = safe_eval(mode_cfg.get('inc_start', 'math.pi / 4'))
        inc_stop = safe_eval(mode_cfg.get('inc_stop', 'math.pi / 2'))
        inc_step = safe_eval(mode_cfg.get('inc_step', 'math.pi / 2'))

        for idx in range(amount):
          ld = bpy.data.lights.new(name=f"EvenSun{idx}", type=light_type)
          ld.energy = energy
          lo = bpy.data.objects.new(name=f"EvenSun{idx}", object_data=ld)

          inc, azi = next_location_on_sphere(inc_start, inc_stop, inc_step, idx, amount)
          lo.location = spherical_to_cartesian(radius, inc, azi)

          point_object_at(lo, target)

          bpy.context.scene.collection.objects.link(lo)

        return

    raise RuntimeError("unknown light mode")


def setup_world(world_configuration):
    """Configure world settings."""
    bpy.context.scene.world = bpy.data.worlds.new("World")
    world = bpy.context.scene.world

    world.use_nodes = True
    nodes = world.node_tree.nodes

    background_node = nodes['Background']
    background_node.inputs[1].default_value = world_configuration.get('strength', 1.0)

    color_input = world_configuration.get('color')
    if not color_input:
        return

    color_cfg = world_configuration[color_input]

    if world_configuration['color'] == 'environment_texture':
        environment_texture_node = world.node_tree.nodes.new(type="ShaderNodeTexEnvironment")
        image = bpy.data.images.load(color_cfg['path'])
        environment_texture_node.image = (image)

        world.node_tree.links.new(environment_texture_node.outputs['Color'], background_node.inputs['Color'])

    if world_configuration['color'] == 'image_texture':
        background_image_node = world.node_tree.nodes.new(type="ShaderNodeTexImage")
        image = bpy.data.images.load(color_cfg['path'])
        background_image_node.image = (image)
        background_image_node.extension = color_cfg['extension']

        # align background image to the window
        texture_coordinate = world.node_tree.nodes.new(type="ShaderNodeTexCoord")
        world.node_tree.links.new(texture_coordinate.outputs['Window'], background_image_node.inputs['Vector'])

        world.node_tree.links.new(background_image_node.outputs['Color'], background_node.inputs['Color'])


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
        scene.cycles.max_bounces = render_configuration['cycles']['max_bounces']
        scene.cycles.transparent_max_bounces = render_configuration['cycles']['transparent_max_bounces']
        scene.cycles.diffuse_bounces = render_configuration['cycles']['diffuse_bounces']
        scene.cycles.glossy_bounces = render_configuration['cycles']['glossy_bounces']
        scene.cycles.transmission_bounces = render_configuration['cycles']['transmission_bounces']
        scene.cycles.volume_bounces = render_configuration['cycles']['volume_bounces']
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

    cam_obj.data.lens_unit = "MILLIMETERS"
    cam_obj.data.lens = camera_configuration['lens'].get('focal_length', 50)
    cam_obj.data.clip_start = camera_configuration['lens'].get('clip_start', 0.1)
    cam_obj.data.clip_end = camera_configuration['lens'].get('clip_end', 1000)

    cam_obj.data.sensor_width = camera_configuration.get('sensor_width')
    cam_obj.data.sensor_height = camera_configuration.get('sensor_height')

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
    point_object_at(cam_obj, target)

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


def random_camera_location(camera_location_configuration):
    """Sample a random point on the upper hemisphere."""
    r_min   = safe_eval(camera_location_configuration.get("r_min", 1))
    r_max   = safe_eval(camera_location_configuration.get("r_max", 1))
    inc_min = safe_eval(camera_location_configuration.get("inc_min", 0))
    inc_max = safe_eval(camera_location_configuration.get("inc_max", 'math.pi/2'))
    azi_min = safe_eval(camera_location_configuration.get("azi_min", 0))
    azi_max = safe_eval(camera_location_configuration.get("azi_max", '2 * math.pi'))
    r = random.uniform(r_min, r_max)
    inc = random.uniform(inc_min, inc_max)
    azi = random.uniform(azi_min, azi_max)
    return spherical_to_cartesian(r, inc, azi)


def uniform_camera_location(camera_location_configuration, i, N):
    inc_start = safe_eval(camera_location_configuration.get('inc_start', 'math.pi / 4'))
    inc_stop = safe_eval(camera_location_configuration.get('inc_stop', 'math.pi / 2'))
    inc_step = safe_eval(camera_location_configuration.get('inc_step', 'math.pi / 2'))
    radius = camera_location_configuration.get("radius", 1.0)
    inc, azi = next_location_on_sphere(inc_start, inc_stop, inc_step, i, N)
    return spherical_to_cartesian(radius, inc, azi)


def get_camera_location(camera_location_configuration, i, N):
    mode = camera_location_configuration.get("mode", "uniform")

    if mode == "random":
      return random_camera_location(camera_location_configuration[mode])
    if mode == "uniform":
      return uniform_camera_location(camera_location_configuration[mode], i, N)

    raise RuntimeError("unknown camera location mode")


def load_config(path):
    """Load and return the TOML config as a dict."""
    with open(path, "rb") as f:
        return tomllib.load(f)


def discover_plugins(dirname):
    """ Discover the plugin classes contained in Python files, given a
        directory name to scan. Return a list of plugin classes.
    """
    import importlib
    import importlib.util
    import importlib.machinery
    def import_module_from_spec(spec):
        """Import module from found spec.
           Standard `import` does not work, since the script is not in path.
           Source: https://docs.python.org/3.11/library/importlib.html#importing-a-source-file-directly
        """
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    plugins = importlib.machinery.PathFinder().find_spec(dirname, __file__)
    if plugins is None:
        print(f"No module named {dirname!r} found, skip importing.")
        return list()
    plugins = import_module_from_spec(plugins)

    import pkgutil
    for finder, name, ispkg in pkgutil.iter_modules([dirname]):
        # since `plugins` package is already imported and is in sys.modules
        # Python can import its subpackages
        importlib.import_module(f"plugins.{name}")
    return getattr(plugins, 'IPluginRegistry').plugins


def main():
    """Main function."""
    args = parse_args()

    cfg = load_config('config.toml')

    model_path = args.model_path
    N = args.number_of_renders

    random.seed(cfg.get("seed"))

    output_dir = args.output_directory
    os.makedirs(output_dir, exist_ok=True)
    plugins = [P(cfg) for P in discover_plugins('plugins')]

    clear_scene()
    import_model(model_path)

    if (world_configuration := cfg.get('world')):
      setup_world(world_configuration)

    setup_render_engine(cfg.get('render'))

    # Assume the imported object is centered at origin.
    target = mathutils.Vector((0.0, 0.0, 0.0))

    if (light_configuration := cfg.get('light')):
      setup_light(light_configuration, target)

    scene = bpy.context.scene

    for plugin in plugins:
        plugin.on_scene_created(scene, output_dir)

    start_time = datetime.datetime.now()

    for i in range(N):
        cam_obj = create_camera(cfg['camera'])
        cam_obj.location = get_camera_location(cfg["camera"]["location"], i, N)
        point_camera_at(cam_obj, target)

        scene.camera = cam_obj

        for plugin in plugins:
            plugin.on_camera_created(scene, cam_obj, i, output_dir)

        image_filename = f"{i:03d}_render.png"
        output_filepath = os.path.join(output_dir, image_filename)
        print(f"Rendering image {i+1}/{N} to {output_filepath}...")
        render_image(scene, output_filepath)

        camera = cam_obj.data
        bpy.data.objects.remove(cam_obj, do_unlink=True)
        bpy.data.cameras.remove(camera, do_unlink=True)

    end_time = datetime.datetime.now()
    diff = end_time - start_time

    print("Rendering completed.")
    print("Total render time (hh:mm:ss): " + str(diff))
    print("Average seconds per image: " + str(diff.seconds / N))

    for plugin in plugins:
        plugin.on_rendering_completed(scene)

    shutil.copy2("config.toml", output_dir)


if __name__ == "__main__":
    main()
