import plugins

class Mask(plugins.IPlugin, plugins.RenderLayerToFileOutputMixin):
    """For each camera view generate corresponding mask of the object.
       Resulting mask is saved in `output` directory with name 'AAA_mask_BBB.png',
       where AAA stands for index in the dataset and BBB stands for frame number.
    """

    def __init__(self, cfg, plugin_cfg):
        self.plugin_cfg = plugin_cfg

    def on_scene_created(self, scene, output_path):
        rl = self.get_render_layer_node(scene)

        view_layer = scene.view_layers[0]
        view_layer.use_pass_object_index = True

        rl_index_output_socket = rl.outputs['IndexOB']

        default_grayscale = {
            "color_mode": "BW"
        }
        format_cfg = self.plugin_cfg.get("format", default_grayscale)
        file_out = self.create_file_output_node(scene, output_path, "mask", format_cfg)
        scene.node_tree.links.new(rl_index_output_socket, file_out.inputs[0])

        import re
        exclude = self.plugin_cfg.get("exclude_pattern", "")
        for obj in scene.objects:
            if re.search(obj.name, exclude):
                continue
            if obj.type == 'MESH':
                obj.pass_index = 1


    def on_camera_created(self, scene, camera_obj, index, output_path):
        return plugins.RenderLayerToFileOutputMixin.on_camera_created(self, scene, camera_obj, index, output_path)
