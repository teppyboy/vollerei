class LAUNCHER_API:
    """Launcher API constants."""

    RESOURCE_PATH: str = "mdk/launcher/api/resource"
    OS: dict = {
        "url": "https://hkrpg-launcher-static.hoyoverse.com/hkrpg_global/",
        "params": {
            "channel_id": 1,
            "key": "vplOVX8Vn7cwG8yb",
            "launcher_id": 35,
        },
    }
    ASIA: dict = {}
    CN: dict = {
        "url": "https://api-launcher.mihoyo.com/hkrpg_cn/mdk/launcher/api/resource",
        "params": {
            "channel_id": 1,
            "key": "6KcVuOkbcqjJomjZ",
            "launcher_id": 33,
        },
    }


LATEST_VERSION = (7, 2, 0)
