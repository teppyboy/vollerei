from vollerei.common.api import get_game_packages, resource
from vollerei.common.enums import GameChannel


def get_game_package(channel: GameChannel = GameChannel.Overseas) -> resource.GameInfo:
    """
    Get game package information from the launcher API.

    Default channel is overseas.

    Args:
        channel: Game channel to get the resource information from.

    Returns:
        Resource: Game resource information.
    """
    game_packages = get_game_packages(channel=channel)
    for package in game_packages:
        if "hk4e" in package.game.biz:
            return package
