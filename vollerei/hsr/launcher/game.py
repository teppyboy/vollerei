from os import PathLike
from vollerei.game.launcher.manager import Game as CommonGame
from vollerei.common.enums import GameType


class Game(CommonGame):
    """
    Manages the game installation

    Since channel detection isn't implemented yet, most functions assume you're
    using the overseas version of the game. You can override channel by setting
    the property `channel_override` to the channel you want to use.
    """

    def __init__(self, path: PathLike = None, cache_path: PathLike = None):
        super().__init__(GameType.HSR, path, cache_path)
