class LAUNCHER_API:
    """Launcher API constants."""

    RESOURCE_PATH: str = "hyp/hyp-connect/api/getGamePackages"
    OS: dict = {
        "url": "https://sg-hyp-api.hoyoverse.com/",
        "params": {
            "launcher_id": "VYTpXlbWo8",
        },
    }
    CN: dict = {
        "url": "https://hyp-api.mihoyo.com/",
        "params": {
            "launcher_id": "jGHBHlcOq1",
        },
    }


TELEMETRY_HOSTS = [
    # Global
    "log-upload-os.hoyoverse.com",
    "sg-public-data-api.hoyoverse.com",
    # China
    "dump.gamesafe.qq.com",
    "log-upload.mihoyo.com",
    "public-data-api.mihoyo.com",
]
HDIFFPATCH_GIT_URL = "https://github.com/sisong/HDiffPatch"
