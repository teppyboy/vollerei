from vollerei.common.api import get_game_packages, resource
from vollerei.common.enums import GameChannel, GameType


def get_game_package(
    game_type: GameType, channel: GameChannel = GameChannel.Overseas
) -> resource.GameInfo:
    """
    Get game package information from the launcher API.

    Doesn't work with HI3 but well, we haven't implemented anything for that game yet.

    Default channel is overseas.

    Args:
        channel: Game channel to get the resource information from.

    Returns:
        GameInfo: Game resource information.
    """
    find_str: str
    match game_type:
        case GameType.HSR:
            find_str = "hkrpg"
        case GameType.Genshin:
            find_str = "hk4e"
        case GameType.ZZZ:
            find_str = "nap"
    game_packages = get_game_packages(channel=channel)
    for package in game_packages:
        if find_str in package.game.biz:
            return package
