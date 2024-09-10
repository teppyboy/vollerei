import requests
from vollerei.common.api import resource
from vollerei.common.enums import GameChannel
from vollerei.constants import LAUNCHER_API


__all__ = ["GamePackage"]


def get_game_packages(
    channel: GameChannel = GameChannel.Overseas,
) -> list[resource.GameInfo]:
    """
    Get game packages information from the launcher API.

    Default channel is overseas.

    Args:
        channel: Game channel to get the resource information from.

    Returns:
        Resource: Game resource information.
    """
    resource_path: dict = None
    match channel:
        case GameChannel.Overseas:
            resource_path = LAUNCHER_API.OS
        case GameChannel.China:
            resource_path = LAUNCHER_API.CN
    return resource.from_dict(
        requests.get(
            resource_path["url"] + LAUNCHER_API.RESOURCE_PATH,
            params=resource_path["params"],
        ).json()["data"]
    )
