from abc import ABC, abstractmethod

from vollerei.abc.launcher.game import GameABC


class PatcherABC(ABC):
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def patch_game(self, game: GameABC):
        pass

    @abstractmethod
    def unpatch_game(self, game: GameABC):
        pass
