import requests

from vollerei.common.api import Resource
from vollerei.hsr.constants import LAUNCHER_API
from vollerei.hsr.launcher.enums import GameChannel


def get_resource(channel: GameChannel = GameChannel.Overseas) -> Resource:
    """
    Get game resource information from the launcher API.

    Args:
        channel: Game channel to get the resource information from.

    Returns:
        Resource: Game resource information.
    """
    resource_path: dict
    match channel:
        case GameChannel.Overseas:
            resource_path = LAUNCHER_API.OS
        case GameChannel.China:
            resource_path = LAUNCHER_API.CN
    return Resource.from_dict(
        requests.get(
            resource_path["url"] + LAUNCHER_API.RESOURCE_PATH,
            params=resource_path["params"],
        ).json()["data"]
    )
