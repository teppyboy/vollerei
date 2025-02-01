from os import PathLike
from vollerei.game.launcher.manager import Game as CommonGame
from vollerei.common.enums import GameType


class Game(CommonGame):
    """
    Manages the game installation
    """

    def __init__(self, path: PathLike = None, cache_path: PathLike = None):
        super().__init__(GameType.Genshin, path, cache_path)
