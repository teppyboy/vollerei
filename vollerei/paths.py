from pathlib import Path
from os import PathLike
from platformdirs import PlatformDirs


class Paths:
    """
    Manages the paths
    """

    base_paths = PlatformDirs("vollerei", "tretrauit", roaming=True)
    cache_path = base_paths.site_cache_path
    data_path = base_paths.site_data_path
    tools_data_path = data_path.joinpath("tools")
    tools_cache_path = cache_path.joinpath("tools")
    launcher_cache_path = cache_path.joinpath("launcher")
    utils_cache_path = cache_path.joinpath("utils")

    @staticmethod
    def set_base_path(path: PathLike):
        path = Path(path)
        Paths.base_paths = path
        Paths.cache_path = Paths.base_paths.joinpath("Cache")
        Paths.data_path = Paths.base_paths
        Paths.tools_data_path = Paths.data_path.joinpath("tools")
        Paths.tools_cache_path = Paths.cache_path.joinpath("tools")
        Paths.launcher_cache_path = Paths.cache_path.joinpath("launcher")
        Paths.utils_cache_path = Paths.cache_path.joinpath("utils")


# Aliases
base_paths = Paths.base_paths
cache_path = Paths.cache_path
data_path = Paths.data_path
tools_data_path = Paths.tools_data_path
tools_cache_path = Paths.tools_cache_path
launcher_cache_path = Paths.launcher_cache_path
utils_cache_path = Paths.utils_cache_path


def set_base_path(path: PathLike):
    Paths.set_base_path(path)
    global base_paths, cache_path, data_path, tools_data_path, tools_cache_path, launcher_cache_path, utils_cache_path
    base_paths = Paths.base_paths
    cache_path = Paths.cache_path
    data_path = Paths.data_path
    tools_data_path = Paths.tools_data_path
    tools_cache_path = Paths.tools_cache_path
    launcher_cache_path = Paths.launcher_cache_path
    utils_cache_path = Paths.utils_cache_path
