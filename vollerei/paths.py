from pathlib import Path
from os import PathLike
from platformdirs import PlatformDirs


base_paths = PlatformDirs("vollerei", "tretrauit", roaming=True)
cache_path = base_paths.site_cache_path
data_path = base_paths.site_data_path
tools_data_path = data_path.joinpath("tools")
tools_cache_path = cache_path.joinpath("tools")
launcher_cache_path = cache_path.joinpath("launcher")
utils_cache_path = cache_path.joinpath("utils")


def change_base_path(path: PathLike):
    path = Path(path)
    global base_paths, tools_data_path, tools_cache_path, launcher_cache_path, utils_cache_path, cache_path, data_path
    cache_path = path.joinpath("cache")
    data_path = path.joinpath("data")
    tools_data_path = data_path.joinpath("tools")
    tools_cache_path = cache_path.joinpath("tools")
    launcher_cache_path = cache_path.joinpath("launcher")
    utils_cache_path = cache_path.joinpath("utils")
