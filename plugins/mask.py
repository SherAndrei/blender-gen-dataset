from plugins import IPlugin

class Mask(IPlugin):
    """For each camera view generate corresponding mask of the object.
       Resulting mask is saved in `output` directory with name 'AAA_mask_BBB.png',
       where AAA stands for index in the dataset and BBB stands for frame number.
    """
    def __init__(self, cfg):
        super().__init__(cfg)
        self._last_input_socket = None


    def on_scene_created(self, scene, output_path):
        scene.use_nodes = True
        scene.render.use_compositing = True
        nodes = scene.node_tree.nodes

        view_layer = scene.view_layers[0]
        view_layer.use_pass_object_index = True

        self._rl = nodes.new(type="CompositorNodeRLayers")
        self._rl_index_output_socket = self._rl.outputs['IndexOB']

        self._file_out = nodes.new(type="CompositorNodeOutputFile")
        self._file_out.label = "MaskOutput"
        self._file_out.base_path = output_path
        self._file_out.format.file_format = 'PNG'

        for obj in scene.objects:
            if obj.type == 'MESH':
                obj.pass_index = 1


    def on_camera_created(self, scene, camera_obj, index, output_path):
        file_out = self._file_out
        # avoid rewriting previous masks by removing the socket to them
        if self._last_input_socket:
            file_out.file_slots.remove(self._last_input_socket)

        self._last_input_socket = file_out.file_slots.new(f"{index:03d}_mask_")
        scene.node_tree.links.new(self._rl_index_output_socket, self._last_input_socket)
