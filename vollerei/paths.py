from pathlib import Path
from platformdirs import PlatformDirs


base_paths = PlatformDirs("vollerei", "tretrauit", roaming=True)
tools_data_path: Path = None
tools_cache_path: Path = None
launcher_cache_path: Path = None
utils_cache_path: Path = None


def init_paths():
    global tools_data_path, tools_cache_path, launcher_cache_path, utils_cache_path
    tools_data_path = base_paths.site_data_path.joinpath("tools")
    tools_cache_path = base_paths.site_cache_path.joinpath("tools")
    launcher_cache_path = base_paths.site_cache_path.joinpath("launcher")
    utils_cache_path = base_paths.site_cache_path.joinpath("utils")
    tools_data_path.mkdir(parents=True, exist_ok=True)
    tools_cache_path.mkdir(parents=True, exist_ok=True)
    launcher_cache_path.mkdir(parents=True, exist_ok=True)
    utils_cache_path.mkdir(parents=True, exist_ok=True)
