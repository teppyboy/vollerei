from enum import Enum
from shutil import copy2, rmtree
from packaging import version
from vollerei.abc.patcher import PatcherABC
from vollerei.common import telemetry
from vollerei.exceptions.game import GameNotInstalledError
from vollerei.exceptions.patcher import (
    VersionNotSupportedError,
    PatcherError,
    PatchUpdateError,
)
from vollerei.hsr.launcher.game import Game, GameChannel
from vollerei.utils import download_and_extract, Git, Xdelta3
from vollerei.paths import tools_data_path
from vollerei.hsr.constants import ASTRA_REPO, JADEITE_REPO


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

    By default this will use Jadeite as it is maintained and more stable.
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
        """
        Patch type, can be either Astra or Jadeite
        """
        return self._patch_type

    @patch_type.setter
    def patch_type(self, value: PatchType):
        self._patch_type = value

    def _update_astra(self):
        self._git.pull_or_clone(ASTRA_REPO, self._astra)

    def _update_jadeite(self):
        release_info = self._git.get_latest_release(JADEITE_REPO)
        file = self._git.get_latest_release_dl(release_info)[0]
        file_version = release_info["tag_name"][1:]  # Remove "v" prefix
        current_version = None
        if self._jadeite.joinpath("version").exists():
            with open(self._jadeite.joinpath("version"), "r") as f:
                current_version = f.read()
        if current_version:
            if version.parse(file_version) <= version.parse(current_version):
                return
        download_and_extract(file, self._jadeite)
        with open(self._jadeite.joinpath("version"), "w") as f:
            f.write(file_version)

    def update_patch(self):
        """
        Update the patch
        """
        try:
            match self._patch_type:
                case PatchType.Astra:
                    self._update_astra()
                case PatchType.Jadeite:
                    self._update_jadeite()
        except Exception as e:
            raise PatchUpdateError("Failed to update patch.") from e

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
        # Backup and patch
        for file in ["UnityPlayer.dll", "StarRailBase.dll"]:
            game.path.joinpath(file).rename(game.path.joinpath(f"{file}.bak"))
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

    def _unpatch_astra(self, game: Game):
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
        # Restore
        for file in ["UnityPlayer.dll", "StarRailBase.dll"]:
            if game.path.joinpath(f"{file}.bak").exists():
                game.path.joinpath(file).unlink()
                game.path.joinpath(f"{file}.bak").rename(game.path.joinpath(file))
        # Remove files
        for file in self._astra.joinpath(f"{file_type}/files/").rglob("*"):
            if file.suffix == ".bat":
                continue
            file_rel = file.relative_to(self._astra.joinpath(f"{file_type}/files/"))
            game_path = game.path.joinpath(file_rel)
            if game_path.is_file():
                game_path.unlink()
            elif game_path.is_dir():
                try:
                    game_path.rmdir()
                except OSError:
                    pass

    def _unpatch_jadeite(self):
        rmtree(self._jadeite, ignore_errors=True)

    def patch_game(self, game: Game):
        """
        Patch the game

        If you use Jadeite (by default), this will just download Jadeite files
        and won't actually patch the game because Jadeite will do that automatically.

        Args:
            game (Game): The game to patch
        """
        if not game.is_installed():
            raise PatcherError(GameNotInstalledError("Game is not installed"))
        match self._patch_type:
            case PatchType.Astra:
                self._patch_astra(game)
            case PatchType.Jadeite:
                return self._patch_jadeite()

    def unpatch_game(self, game: Game):
        """
        Unpatch the game

        If you use Jadeite (by default), this will just delete Jadeite files.
        Note that Honkai Impact 3rd uses Jadeite too, so executing this will
        delete the files needed by both games.

        Args:
            game (Game): The game to unpatch
        """
        if not game.is_installed():
            raise PatcherError(GameNotInstalledError("Game is not installed"))
        match self._patch_type:
            case PatchType.Astra:
                self._unpatch_astra(game)
            case PatchType.Jadeite:
                self._unpatch_jadeite()

    def check_telemetry(self) -> list[str]:
        """
        Check if telemetry servers are accessible by the user

        Returns:
            list[str]: A list of telemetry servers that are accessible
        """
        return telemetry.check_telemetry()

    def block_telemetry(self, telemetry_list: list[str] = None):
        """
        Block the telemetry servers

        If telemetry_list is not provided, it will be checked automatically.

        Args:
            telemetry_list (list[str], optional): A list of telemetry servers to block.
        """
        telemetry.block_telemetry(telemetry_list)
