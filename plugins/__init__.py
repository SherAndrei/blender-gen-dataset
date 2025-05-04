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
