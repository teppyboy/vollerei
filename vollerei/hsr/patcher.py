from vollerei.abc.patcher import PatcherABC
from vollerei.exceptions.game import GameNotInstalledError
from vollerei.exceptions.patcher import VersionNotSupportedError
from vollerei.hsr.launcher.game import Game
from vollerei.utils.git import Git
from vollerei.constants import tools_data_path, astra_repo, jadeite_repo
from enum import Enum


class PatchType(Enum):
    """
    Patch type

    Astra: The old patch which patch the game directly (not recommended).
    Jadeite: The new patch which patch the game in memory by DLL injection.
    """

    Astra: int = 0
    Jadeite: int = 1


class Patcher(PatcherABC):
    def __init__(self, patch_type: PatchType = PatchType.Jadeite):
        self._patch_type: PatchType = patch_type
        self._path = tools_data_path.joinpath("patcher")
        self._git = Git()

    @property
    def patch_type(self) -> PatchType:
        return self._patch_type

    @patch_type.setter
    def patch_type(self, value: PatchType):
        self._patch_type = value

    def _update_astra(self):
        self._git.pull_or_clone(astra_repo, self._path.joinpath("astra"))

    def _update_jadeite(self):
        self._git.pull_or_clone(jadeite_repo, self._path.joinpath("jadeite"))

    def update_patch(self):
        match self._patch_type:
            case PatchType.Astra:
                self._update_astra()
            case PatchType.Jadeite:
                self._update_jadeite()

    def _patch_astra(self, game: Game):
        if game.get_version() != (1, 0, 5):
            raise VersionNotSupportedError(
                "Only version 1.0.5 is supported by Astra patch."
            )
        

    def _patch_jadeite(self, game: Game):
        pass

    def patch_game(self, game: Game):
        if not game.is_installed():
            raise GameNotInstalledError("Game is not installed")
