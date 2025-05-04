from plugins import IPlugin

class Depth(IPlugin):
    """For each camera view generate corresponding depth map of the object.
       Resulting depth map is saved in `output` directory with name 'AAA_depth_BBB.png',
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
        view_layer.use_pass_z = True

        self._rl = nodes.get("Render Layers")
        if not self._rl:
            self._rl = nodes.new(type="CompositorNodeRLayers")

        rl_depth_output_socket = self._rl.outputs['Depth']
        normalize_node = nodes.new(type="CompositorNodeNormalize")

        scene.node_tree.links.new(rl_depth_output_socket, normalize_node.inputs[0])
        self._normalize_output_socket = normalize_node.outputs[0]

        file_out = nodes.new(type="CompositorNodeOutputFile")
        file_out.label = "DepthOutput"
        file_out.base_path = output_path
        file_out.format.file_format = 'PNG'
        file_out.format.color_depth = '16'
        file_out.format.color_mode = 'BW'
        self._file_out = file_out


    def on_camera_created(self, scene, camera_obj, index, output_path):
        file_out = self._file_out
        # avoid rewriting previous depth by removing the socket to them
        if self._last_input_socket:
            file_out.file_slots.remove(self._last_input_socket)

        self._last_input_socket = file_out.file_slots.new(f"{index:03d}_depth_")
        scene.node_tree.links.new(self._normalize_output_socket, self._last_input_socket)
