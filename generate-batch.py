#!/usr/bin/env python3
"""
Script for generating rendered images of a 3D model using Blender, driven by config.toml.

Usage:
    blender --background --python generate-batch.py -- \
        /path/to/model.glb /path/to/output 10
"""

import argparse
import datetime
import logging
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
    return vars(parser.parse_args(argv))


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

    if not mode:
        return

    mode_cfg = light_configuration.get(mode, {})
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

    if color_input == 'environment_texture':
        environment_texture_node = world.node_tree.nodes.new(type="ShaderNodeTexEnvironment")
        image = bpy.data.images.load(color_cfg['path'])
        environment_texture_node.image = (image)

        world.node_tree.links.new(environment_texture_node.outputs['Color'], background_node.inputs['Color'])

    if color_input == 'image_texture':
        background_image_node = world.node_tree.nodes.new(type="ShaderNodeTexImage")
        image = bpy.data.images.load(color_cfg['path'])
        background_image_node.image = (image)
        background_image_node.extension = color_cfg.get('extension', 'CLIP')

        # align background image to the window
        texture_coordinate = world.node_tree.nodes.new(type="ShaderNodeTexCoord")
        world.node_tree.links.new(texture_coordinate.outputs['Window'], background_image_node.inputs['Vector'])

        world.node_tree.links.new(background_image_node.outputs['Color'], background_node.inputs['Color'])


def setup_render_engine(render_configuration):
    """Set render engine and configure some settings."""
    scene = bpy.context.scene
    scene.render.resolution_x = render_configuration.get('resolution_x', 200)
    scene.render.resolution_y = render_configuration.get('resolution_y', 200)
    scene.render.resolution_percentage = 100
    engine = render_configuration.get('engine', 'cycles')
    engine_cfg = render_configuration.get(engine, {})
    if engine == 'cycles':
        scene.render.engine = "CYCLES"
        scene.cycles.samples = render_configuration.get("samples", 1024)
        scene.cycles.use_denoising = engine_cfg.get("use_denoising", True)
        scene.cycles.use_adaptive_sampling = engine_cfg.get("use_adaptive_sampling", True)
        scene.cycles.max_bounces = engine_cfg.get('max_bounces', 1024)
        scene.cycles.transparent_max_bounces = engine_cfg.get('transparent_max_bounces', 1024)
        scene.cycles.diffuse_bounces = engine_cfg.get('diffuse_bounces', 1024)
        scene.cycles.glossy_bounces = engine_cfg.get('glossy_bounces', 1024)
        scene.cycles.transmission_bounces = engine_cfg.get('transmission_bounces', 1024)
        scene.cycles.volume_bounces = engine_cfg.get('volume_bounces', 1024)
        return
    if engine == 'eevee':
        if bpy.app.version > (4, 1, 0):
          scene.render.engine = "BLENDER_EEVEE_NEXT"
          scene.eevee.use_raytracing =  engine_cfg.get("use_raytracing", False)
        else:
          scene.render.engine = "BLENDER_EEVEE"
          scene.eevee.use_ssr = engine_cfg.get("use_ssr", False)

        scene.eevee.taa_render_samples = render_configuration.get("samples", False)
        scene.eevee.use_gtao = engine_cfg.get("use_gtao", False)
        scene.eevee.shadow_pool_size = engine_cfg.get("shadow_pool_size", 1024)
        return

    raise RuntimeError("unknown engine")


def create_camera(camera_configuration):
    """Create and configure a new camera object."""
    cam_data = bpy.data.cameras.new("RandomCam")
    cam_obj = bpy.data.objects.new("RandomCam", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)

    cam_obj.data.lens_unit = "MILLIMETERS"
    lens_cfg = camera_configuration.get('lens', {})
    cam_obj.data.lens = lens_cfg.get('focal_length', 50)
    cam_obj.data.clip_start = lens_cfg.get('clip_start', 0.1)
    cam_obj.data.clip_end = lens_cfg.get('clip_end', 1000)

    # APS-C Canon
    cam_obj.data.sensor_width = camera_configuration.get('sensor_width', 22.3)
    cam_obj.data.sensor_height = camera_configuration.get('sensor_height', 14.9)

    if camera_configuration.get('use_dof', False):
      cam_obj.data.dof.use_dof = True
      dof_cfg = camera_configuration.get('dof', {})
      cam_obj.data.dof.aperture_fstop = dof_cfg.get('aperture_fstop', 2.8)

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
    r_min   = safe_eval(camera_location_configuration.get("r_min", 10))
    r_max   = safe_eval(camera_location_configuration.get("r_max", 10))
    inc_min = safe_eval(camera_location_configuration.get("inc_min", 0))
    inc_max = safe_eval(camera_location_configuration.get("inc_max", math.pi/2))
    azi_min = safe_eval(camera_location_configuration.get("azi_min", 0))
    azi_max = safe_eval(camera_location_configuration.get("azi_max", 2 * math.pi))
    r = random.uniform(r_min, r_max)
    inc = random.uniform(inc_min, inc_max)
    azi = random.uniform(azi_min, azi_max)
    return spherical_to_cartesian(r, inc, azi)


def uniform_camera_location(camera_location_configuration, i, N):
    inc_start = safe_eval(camera_location_configuration.get('inc_start', math.pi / 4))
    inc_stop = safe_eval(camera_location_configuration.get('inc_stop', math.pi / 2))
    inc_step = safe_eval(camera_location_configuration.get('inc_step', math.pi / 2))
    radius = camera_location_configuration.get("radius", 10)
    inc, azi = next_location_on_sphere(inc_start, inc_stop, inc_step, i, N)
    return spherical_to_cartesian(radius, inc, azi)


def get_camera_location(camera_location_configuration, i, N):
    mode = camera_location_configuration.get("mode", "random")

    if mode == "random":
      return random_camera_location(camera_location_configuration.get(mode, {}))
    if mode == "uniform":
      return uniform_camera_location(camera_location_configuration.get(mode, {}), i, N)

    raise RuntimeError("unknown camera location mode")


def load_config(path):
    """Load and return the TOML config as a dict."""
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except OSError:
        logging.exception("Failed to open 'config.toml', using default values instead")
        return {}


def discover_plugins(dirname, cfg):
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
    registry = getattr(plugins, 'IPluginRegistry')

    import pkgutil
    plugins_instances = []
    for finder, name, ispkg in pkgutil.iter_modules([dirname]):
        # since `plugins` package is already imported and is in sys.modules
        # Python can import its subpackages
        importlib.import_module(f"plugins.{name}")
        new_plugin_class = registry.plugins[-1]
        try:
            new_plugin_instance = new_plugin_class(cfg)
            plugins_instances.append(new_plugin_instance)
        except Exception:
            logging.exception(f"Failed to init {name}, skipping")

    return plugins_instances


def main(args):
    """Main function."""
    config_file = 'config.toml'
    cfg = load_config(config_file)

    model_path = args['model_path']
    N = args['number_of_renders']
    output_dir = args['output_directory']

    random.seed(cfg.get("seed"))

    os.makedirs(output_dir, exist_ok=True)
    plugins = discover_plugins('plugins', cfg)

    clear_scene()
    import_model(model_path)

    setup_world(cfg.get('world', {}))

    setup_render_engine(cfg.get('render', {}))

    # Assume the imported object is centered at origin.
    target = mathutils.Vector((0.0, 0.0, 0.0))

    setup_light(cfg.get('light', {}), target)

    scene = bpy.context.scene

    for plugin in plugins:
        plugin.on_scene_created(scene, output_dir)

    start_time = datetime.datetime.now()

    for i in range(N):
        camera_cfg = cfg.get('camera', {})
        cam_obj = create_camera(camera_cfg)
        cam_obj.location = get_camera_location(camera_cfg.get("location", {}), i, N)
        point_camera_at(cam_obj, target)

        scene.camera = cam_obj

        for plugin in plugins:
            plugin.on_camera_created(scene, cam_obj, i, output_dir)

        image_filename = f"{i:03d}_render.png"
        output_filepath = os.path.join(output_dir, image_filename)
        print(f"Rendering image {i+1}/{N} to {output_filepath}...")
        render_image(scene, output_filepath)

        for plugin in plugins:
            plugin.on_another_render_completed(scene, cam_obj, i, output_dir)

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

    if os.path.isfile(config_file):
        shutil.copy2(config_file, output_dir)


if __name__ == "__main__":
    args = parse_args()
    main(args)
