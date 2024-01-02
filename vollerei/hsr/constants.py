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
    CN: dict = {
        "url": "https://api-launcher.mihoyo.com/hkrpg_cn/mdk/launcher/api/resource",
        "params": {
            "channel_id": 1,
            "key": "6KcVuOkbcqjJomjZ",
            "launcher_id": 33,
        },
    }


LATEST_VERSION = (1, 6, 0)
MD5SUMS = {
    "1.0.5": {
        "cn": {
            "StarRailBase.dll": "66c42871ce82456967d004ccb2d7cf77",
            "UnityPlayer.dll": "0c866c44bb3752031a8c12ffe935b26f",
        },
        "os": {
            "StarRailBase.dll": "8aa3790aafa3dd176678392f3f93f435",
            "UnityPlayer.dll": "f17b9b7f9b8c9cbd211bdff7771a80c2",
        },
    }
}
# Patches
ASTRA_REPO = "https://notabug.org/mkrsym1/astra"
JADEITE_REPO = "https://codeberg.org/mkrsym1/jadeite/"
