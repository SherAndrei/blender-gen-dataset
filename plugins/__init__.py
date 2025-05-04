# Basic plugin infrastructure
# Sources:
# * https://eli.thegreenplace.net/2012/08/07/fundamental-concepts-of-plugin-infrastructures
# * https://gist.github.com/dorneanu/cce1cd6711969d581873a88e0257e312

class IPluginRegistry(type):
    plugins = []
    def __init__(cls, name, bases, attrs):
        if name != 'IPlugin':
            IPluginRegistry.plugins.append(cls)


class IPlugin(object, metaclass=IPluginRegistry):
    """ Plugin classes inherit from IPlugin. The methods below can be
        implemented to provide services.
    """

    def __init__(self, user_configuration, user_plugin_configuration):
        pass

    def on_scene_created(self, scene, output_path):
        pass

    def on_camera_created(self, scene, camera_obj, index, output_path):
        pass

    def on_another_render_completed(self, scene, camera_obj, index, output_path):
        pass

    def on_rendering_completed(self, scene):
        pass


class RenderLayerToFileOutputMixin:
    def get_render_layer_node(self, scene):
        scene.use_nodes = True
        scene.render.use_compositing = True

        nodes = scene.node_tree.nodes
        rl = nodes.get("Render Layers")
        if not rl:
            return nodes.new(type="CompositorNodeRLayers")
        return rl

    def create_file_output_node(self, scene, output_path, label, format_configuration):
        nodes = scene.node_tree.nodes
        file_out = nodes.new(type="CompositorNodeOutputFile")
        file_out.label = label
        file_out.base_path = output_path
        file_out.format.file_format = format_configuration.get("file_format", "PNG")
        file_out.format.color_mode = format_configuration.get("color_mode", "RGBA")
        file_out.format.color_depth = format_configuration.get("color_depth", '8')
        file_out.format.compression = format_configuration.get("compression", 15)

        self._file_out = file_out

        return file_out


    def on_camera_created(self, scene, camera_obj, index, output_path):
        node_output_file_slot_file = self._file_out.file_slots[0]
        label = self._file_out.label
        node_output_file_slot_file.path = f"{index:03d}_{label}_"
