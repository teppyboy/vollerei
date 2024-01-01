from hashlib import md5
from io import IOBase
from os import PathLike
from pathlib import Path
from vollerei.abc.launcher.game import GameABC
from vollerei.common import ConfigFile, functions
from vollerei.common.api import resource
from vollerei.exceptions.game import GameNotInstalledError, PreDownloadNotAvailable
from vollerei.hsr.constants import MD5SUMS
from vollerei.hsr.launcher.enums import GameChannel
from vollerei.hsr.launcher import api
from vollerei.paths import cache_path


class Game(GameABC):
    """
    Manages the game installation

    Since channel detection isn't implemented yet, most functions assume you're
    using the overseas version of the game. You can override channel by setting
    the property `channel_override` to the channel you want to use.
    """

    def __init__(self, path: PathLike = None):
        self._path: Path | None = Path(path) if path else None
        self._cache: Path = cache_path.joinpath("game")
        self._version_override: tuple[int, int, int] | None = None
        self._channel_override: GameChannel | None = None

    @property
    def version_override(self) -> tuple[int, int, int] | None:
        """
        Override the game version.

        This can be useful if you want to override the version of the game
        and additionally working around bugs.
        """
        return self._version_override

    @version_override.setter
    def version_override(self, version: tuple[int, int, int] | str | None):
        if isinstance(version, str):
            version = tuple(int(i) for i in version.split("."))
        self._version_override = version

    @property
    def channel_override(self) -> GameChannel | None:
        """
        Override the game channel.

        Because game channel detection isn't implemented yet, you may need
        to use this for some functions to work.

        This can be useful if you want to override the channel of the game
        and additionally working around bugs.
        """
        return self._channel_override

    @channel_override.setter
    def channel_override(self, channel: GameChannel | str | None):
        if isinstance(channel, str):
            channel = GameChannel[channel]
        self._channel_override = channel

    @property
    def path(self) -> Path | None:
        """
        Path to the game folder.
        """
        return self._path

    @path.setter
    def path(self, path: PathLike):
        self._path = Path(path)

    def data_folder(self) -> Path:
        """
        Path to the game data folder.
        """
        try:
            return self._path.joinpath("StarRail_Data")
        except AttributeError:
            raise GameNotInstalledError("Game path is not set.")

    def is_installed(self) -> bool:
        """
        Check if the game is installed.

        Returns:
            bool: True if the game is installed, False otherwise.
        """
        if self._path is None:
            return False
        if (
            not self._path.joinpath("StarRail.exe").exists()
            or not self._path.joinpath("StarRailBase.dll").exists()
            or not self._path.joinpath("StarRail_Data").exists()
        ):
            return False
        if self.get_version() == (0, 0, 0):
            return False
        return True

    def get_version_config(self) -> tuple[int, int, int]:
        """
        Get the current installed game version from config.ini.

        Using this is not recommended, as only official launcher creates
        and uses this file, instead you should use `get_version()`.

        This returns (0, 0, 0) if the version could not be found.

        Returns:
            tuple[int, int, int]: Game version.
        """
        cfg_file = self._path.joinpath("config.ini")
        if not cfg_file.exists():
            return (0, 0, 0)
        cfg = ConfigFile(cfg_file)
        if "General" not in cfg.sections():
            return (0, 0, 0)
        if "game_version" not in cfg["General"]:
            return (0, 0, 0)
        version_str = cfg["General"]["game_version"]
        if version_str.count(".") != 2:
            return (0, 0, 0)
        try:
            version = tuple(int(i) for i in version_str.split("."))
        except Exception:
            return (0, 0, 0)
        return version

    def get_version(self) -> tuple[int, int, int]:
        """
        Get the current installed game version.

        Credits to An Anime Team for the code that does the magic:
        https://github.com/an-anime-team/anime-game-core/blob/main/src/games/star_rail/game.rs#L49

        If the above method fails, it'll fallback to read the config.ini file
        for the version, which is not recommended (as described in
        `get_version_config()` docs)

        This returns (0, 0, 0) if the version could not be found
        (usually indicates the game is not installed), and in fact `is_installed()` uses
        this method to check if the game is installed too.

        Returns:
            tuple[int, int, int]: The version as a tuple of integers.
        """

        data_file = self.data_folder().joinpath("data.unity3d")
        if not data_file.exists():
            return (0, 0, 0)

        def bytes_to_int(byte_array: list[bytes]) -> int:
            bytes_as_int = int.from_bytes(byte_array, byteorder="big")
            actual_int = bytes_as_int - 48  # 48 is the ASCII code for 0
            return actual_int

        allowed = [48, 49, 50, 51, 52, 53, 54, 55, 56, 57]
        version_bytes: list[list[bytes]] = [[], [], []]
        version_ptr = 0
        correct = True
        try:
            with self.data_folder().joinpath("data.unity3d").open("rb") as f:
                f.seek(0x7D0)  # 2000 in decimal
                for byte in f.read(10000):
                    match byte:
                        case 0:
                            version_bytes = [[], [], []]
                            version_ptr = 0
                            correct = True
                        case 46:
                            version_ptr += 1
                            if version_ptr > 2:
                                correct = False
                        case 38:
                            if (
                                correct
                                and len(version_bytes[0]) > 0
                                and len(version_bytes[1]) > 0
                                and len(version_bytes[2]) > 0
                            ):
                                return (
                                    bytes_to_int(version_bytes[0]),
                                    bytes_to_int(version_bytes[1]),
                                    bytes_to_int(version_bytes[2]),
                                )
                        case _:
                            if correct and byte in allowed:
                                version_bytes[version_ptr].append(byte)
                            else:
                                correct = False
        except Exception:
            pass
        # Fallback to config.ini
        return self.get_version_config()

    def version_as_str(self, version: tuple[int, int, int]) -> str:
        """
        Convert a version tuple to a string.

        Returns:
            str: The version as a string.
        """
        return ".".join(str(i) for i in version)

    def get_channel(self) -> GameChannel:
        """
        Get the current game channel.

        Only works for Star Rail version 1.0.5, other versions will return the
        overridden channel or None if no channel is overridden.

        This is not needed for game patching, since the patcher will automatically
        detect the channel.

        Returns:
            GameChannel: The current game channel.
        """
        version = self._version_override or self.get_version()
        if version == (1, 0, 5):
            for channel, v in MD5SUMS["1.0.5"].values():
                for file, md5sum in v.values():
                    if (
                        md5(self._path.joinpath(file).read_bytes()).hexdigest()
                        != md5sum
                    ):
                        continue
                    match channel:
                        case "cn":
                            return GameChannel.China
                        case "os":
                            return GameChannel.Overseas
        else:
            return

    def _get_game(self, pre_download: bool) -> resource.Game:
        channel = self._channel_override or self.get_channel()
        if pre_download:
            game = api.get_resource(channel=channel).pre_download_game
            if not game:
                raise PreDownloadNotAvailable("Pre-download version is not available.")
            return game
        return api.get_resource(channel=channel).game

    def get_update(self, pre_download: bool = False) -> resource.Diff | None:
        """
        Get the current game update.

        Returns a `Diff` object that contains the update information or
        None if the game is not installed or already up-to-date.
        """
        if not self.is_installed():
            return None
        version = self.version_as_str(self._version_override or self.get_version())
        for diff in self._get_game(pre_download=pre_download).diffs:
            if diff.version == version:
                return diff
        return None

    def apply_update_archive(
        self, archive_file: PathLike | IOBase, auto_repair: bool = True
    ) -> None:
        """
        Apply an update archive to the game, it can be the game update or a
        voicepack update.

        `archive_file` can be a path to the archive file or a file-like object,
        like if you have very high amount of RAM and want to download the update
        to memory instead of disk, this can be useful for you.

        `auto_repair` is used to determine whether to repair the file if it's
        broken. If it's set to False, then it'll raise an exception if the file
        is broken.

        Args:
            archive_file (PathLike | IOBase): The archive file.
            auto_repair (bool, optional): Whether to repair the file if it's broken.
        """
        if not self.is_installed():
            raise GameNotInstalledError("Game is not installed.")
        if not isinstance(archive_file, IOBase):
            archive_file = Path(archive_file)
        # Hello hell again, dealing with HDiffPatch and all the things again.
        functions.apply_update_archive(self, archive_file, auto_repair=auto_repair)

    def install_update(
        self, update_info: resource.Diff = None, auto_repair: bool = True
    ):
        """
        Install an update from a `Diff` object.

        You may want to download the update manually and pass it to
        `apply_update_archive()` instead for better control.

        Args:
            update_info (Diff, optional): The update information. Defaults to None.
        """
        if not self.is_installed():
            raise GameNotInstalledError("Game is not installed.")
        if not update_info:
            update_info = self.get_update()
        pass
