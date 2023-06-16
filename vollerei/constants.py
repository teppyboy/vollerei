from platformdirs import PlatformDirs

# Common
telemetry_hosts = [
    # Global
    "log-upload-os.hoyoverse.com",
    "sg-public-data-api.hoyoverse.com",
    # China
    "dump.gamesafe.qq.com",
    "log-upload.mihoyo.com",
    "public-data-api.mihoyo.com",
]

# HSR
astra_repo = "https://notabug.org/mkrsym1/astra"
jadeite_repo = "https://codeberg.org/mkrsym1/jadeite/"
hsr_latest_version = (1, 1, 0)

base_dirs = PlatformDirs("vollerei", "tretrauit", roaming=True)
tools_data_path = base_dirs.site_data_path.joinpath("tools")
tools_cache_path = base_dirs.site_cache_path.joinpath("tools")
tools_cache_path.mkdir(parents=True, exist_ok=True)
launcher_cache_path = base_dirs.site_cache_path.joinpath("launcher")
launcher_cache_path.mkdir(parents=True, exist_ok=True)
utils_cache_path = base_dirs.site_cache_path.joinpath("utils")
utils_cache_path.mkdir(parents=True, exist_ok=True)
