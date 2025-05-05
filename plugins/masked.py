"""
Masked-RGB plugin
=================
Outputs `###_masked_XXX.png` - an image that contains **only the target
object**; every other pixel is fully transparent.

How it works
------------
1.  Enables Object-Index pass on the first ViewLayer.
2.  In the compositor:
    * RenderLayers → **ID Mask** (index=1) → **Set Alpha** with the RGB
      image, making the mask the new alpha channel.
    * FileOutput node writes PNG (RGBA) into the batch folder.
3.  Before rendering the very first frame, world transparency is turned on
   (`scene.render.film_transparent = True`) so background pixels inherit the
   zero-alpha value.

No per‑frame Python code is needed – Blender’s compositor handles everything.
"""

import os
import bpy
import plugins

class MaskedRGB(plugins.IPlugin, plugins.RenderLayerToFileOutputMixin):
    """Create transparent-background RGBs using the compositor."""

    def __init__(self, user_cfg, plugin_cfg):
        self.plugin_cfg = plugin_cfg

    # called once, before first render
    def on_scene_created(self, scene, output_path):
        rl = self.get_render_layer_node(scene)
        scene.render.film_transparent = True   # let alpha pass through

        view_layer = scene.view_layers[0]
        view_layer.use_pass_object_index = True

        nodes = scene.node_tree.nodes
        links = scene.node_tree.links

        pseudorandom_number = rl.as_pointer() % 0x7fffffff
        # ID Mask to get binary mask from IndexOB==1
        idmask = nodes.new(type="CompositorNodeIDMask")
        idmask.index = pseudorandom_number
        idmask.use_antialiasing = True

        # Set Alpha – combine RGB with mask into transparent RGBA
        set_alpha = nodes.new(type="CompositorNodeSetAlpha")

        # File‑output node
        format_cfg = self.plugin_cfg.get("format", {})
        file_out = self.create_file_output_node(scene, output_path, "masked", format_cfg)

        # Wire the graph
        links.new(rl.outputs['IndexOB'], idmask.inputs['ID value'])
        links.new(rl.outputs['Image'],   set_alpha.inputs['Image'])
        links.new(idmask.outputs['Alpha'], set_alpha.inputs['Alpha'])
        links.new(set_alpha.outputs["Image"], file_out.inputs[0])

        import re
        exclude = self.plugin_cfg.get("exclude_pattern", "")
        for obj in scene.objects:
            if re.search(obj.name, exclude):
                continue
            if obj.type == 'MESH':
                obj.pass_index = pseudorandom_number


    def on_camera_created(self, scene, camera_obj, index, output_path):
        return plugins.RenderLayerToFileOutputMixin.on_camera_created(self, scene, camera_obj, index, output_path)


