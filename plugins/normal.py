from plugins import IPlugin

class Normal(IPlugin):
    """For each camera view generate corresponding normal map of the object.
       Resulting mask is saved in `output` directory with name 'AAA_normal_BBB.png',
       where AAA stands for index in the dataset and BBB stands for frame number.
    """

    def __init__(self, cfg, plugin_cfg):
        self._rl = None
        self._last_input_socket = None


    def on_scene_created(self, scene, output_path):
        scene.use_nodes = True
        scene.render.use_compositing = True
        nodes = scene.node_tree.nodes

        view_layer = scene.view_layers[0]
        view_layer.use_pass_normal = True

        self._rl = nodes.get("Render Layers")
        if not self._rl:
            self._rl = nodes.new(type="CompositorNodeRLayers")

        self._rl_normal_output_socket = self._rl.outputs['Normal']

        self._file_out = nodes.new(type="CompositorNodeOutputFile")
        self._file_out.label = "NormalOutput"
        self._file_out.base_path = output_path
        self._file_out.format.file_format = 'PNG'
        self._file_out.format.color_mode  = 'RGB'

    def on_camera_created(self, scene, camera_obj, index, output_path):
        file_out = self._file_out
        # avoid rewriting previous normals by removing the socket to them
        if self._last_input_socket is not None:
            file_out.file_slots.remove(self._last_input_socket)

        slot_name = f"{index:03d}_normal_"
        self._last_input_socket = self._file_out.file_slots.new(slot_name)

        scene.node_tree.links.new(self._rl_normal_output_socket, self._last_input_socket)
