from enum import Enum
from shutil import copy2
from distutils.version import StrictVersion
from vollerei.abc.patcher import PatcherABC
from vollerei.exceptions.game import GameNotInstalledError
from vollerei.exceptions.patcher import VersionNotSupportedError
from vollerei.hsr.launcher.game import Game, GameChannel
from vollerei.utils import download_and_extract, Git, Xdelta3
from vollerei.paths import tools_data_path
from vollerei.hsr.constants import astra_repo, jadeite_repo


class PatchType(Enum):
    """
    Patch type

    Astra: The old patch which patch the game directly (not recommended).
    Jadeite: The new patch which patch the game in memory by DLL injection.
    """

    Astra: int = 0
    Jadeite: int = 1


class Patcher(PatcherABC):
    """
    Patch helper for HSR.
    """

    def __init__(self, patch_type: PatchType = PatchType.Jadeite):
        self._patch_type: PatchType = patch_type
        self._path = tools_data_path.joinpath("patcher")
        self._path.mkdir(parents=True, exist_ok=True)
        self._jadeite = self._path.joinpath("jadeite")
        self._astra = self._path.joinpath("astra")
        self._git = Git()
        self._xdelta3 = Xdelta3()

    @property
    def patch_type(self) -> PatchType:
        return self._patch_type

    @patch_type.setter
    def patch_type(self, value: PatchType):
        self._patch_type = value

    def _update_astra(self):
        self._git.pull_or_clone(astra_repo, self._astra)

    def _update_jadeite(self):
        release_info = self._git.get_latest_release(jadeite_repo)
        file = self._git.get_latest_release_dl(release_info)[0]
        file_version = release_info["tag_name"][1:]  # Remove "v" prefix
        current_version = None
        if self._jadeite.joinpath("version").exists():
            with open(self._jadeite.joinpath("version"), "r") as f:
                current_version = f.read()
        if current_version:
            if StrictVersion(file_version) <= StrictVersion(current_version):
                return
        download_and_extract(file, self._jadeite)
        with open(self._jadeite.joinpath("version"), "w") as f:
            f.write(file_version)

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
        self._update_astra()
        file_type = None
        match game.get_channel():
            case GameChannel.China:
                file_type = "cn"
            case GameChannel.Overseas:
                file_type = "os"
        # Backup
        for file in ["UnityPlayer.dll", "StarRailBase.dll"]:
            game.path.joinpath(file).rename(game.path.joinpath(f"{file}.bak"))
        # Patch
        for file in ["UnityPlayer.dll", "StarRailBase.dll"]:
            self._xdelta3.patch_file(
                self._astra.joinpath(f"{file_type}/diffs/{file}.vcdiff"),
                game.path.joinpath(f"{file}.bak"),
                game.path.joinpath(file),
            )
        # Copy files
        for file in self._astra.joinpath(f"{file_type}/files/").rglob("*"):
            if file.suffix == ".bat":
                continue
            if file.is_dir():
                game.path.joinpath(
                    file.relative_to(self._astra.joinpath(f"{file_type}/files/"))
                ).mkdir(parents=True, exist_ok=True)
            copy2(
                file,
                game.path.joinpath(
                    file.relative_to(self._astra.joinpath(f"{file_type}/files/"))
                ),
            )

    def _patch_jadeite(self):
        """
        "Patch" the game with Jadeite patch.

        Unlike Astra patch, Jadeite patch does not modify the game files directly
        but uses DLLs to patch the game in memory and it has an injector to do that
        automatically.
        """
        self._update_jadeite()
        return self._jadeite

    def patch_game(self, game: Game):
        if not game.is_installed():
            raise GameNotInstalledError("Game is not installed")
        match self._patch_type:
            case PatchType.Astra:
                self._patch_astra(game)
            case PatchType.Jadeite:
                return self._patch_jadeite()

    def unpatch_game(self, game: Game):
        pass
