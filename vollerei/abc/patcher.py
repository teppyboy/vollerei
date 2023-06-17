from abc import ABC, abstractmethod

from vollerei.abc.launcher.game import GameABC


class PatcherABC(ABC):
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def patch_game(self, game: GameABC):
        """
        Patch the game

        If the game is not installed then it'll raise `GameNotInstalledError`, if the
        game version is not supported then it'll raise `VersionNotSupportedError` and
        if the patching fails then it'll raise `PatchingFailedError`.

        Args:
            game (Game): Game instance to patch
        """
        pass

    @abstractmethod
    def unpatch_game(self, game: GameABC):
        """
        Unpatch the game

        This method unpatch the game by restoring backups and removing the patch files.
        It'll fail if you removed the backup files, in that case you'll have to repair
        the game.

        If the game is not installed then it'll raise `GameNotInstalledError` and if the
        unpatching fails then it'll raise `UnpatchingFailedError`.
        """
        pass

    @abstractmethod
    def check_telemetry(self):
        pass

    @abstractmethod
    def block_telemetry(self):
        pass
