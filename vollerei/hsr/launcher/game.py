from hashlib import md5
from io import IOBase
from os import PathLike
from pathlib import Path
from vollerei.abc.launcher.game import GameABC
from vollerei.common import ConfigFile, functions
from vollerei.common.api import resource
from vollerei.exceptions.game import (
    GameAlreadyUpdatedError,
    GameNotInstalledError,
    PreDownloadNotAvailable,
    ScatteredFilesNotAvailableError,
)
from vollerei.hsr.constants import MD5SUMS
from vollerei.hsr.launcher.enums import GameChannel
from vollerei.hsr.launcher import api
from vollerei import paths
from vollerei.utils import download


class Game(GameABC):
    """
    Manages the game installation

    Since channel detection isn't implemented yet, most functions assume you're
    using the overseas version of the game. You can override channel by setting
    the property `channel_override` to the channel you want to use.
    """

    def __init__(self, path: PathLike = None, cache_path: PathLike = None):
        self._path: Path | None = Path(path) if path else None
        if not cache_path:
            cache_path = paths.cache_path
        cache_path = Path(cache_path)
        self._cache: Path = cache_path.joinpath("game/hsr/")
        self._cache.mkdir(parents=True, exist_ok=True)
        self._version_override: tuple[int, int, int] | None = None
        self._channel_override: GameChannel | None = None

    @property
    def version_override(self) -> tuple[int, int, int] | None:
        """
        Overrides the game version.

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
        Overrides the game channel.

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
        Paths to the game folder.
        """
        return self._path

    @path.setter
    def path(self, path: PathLike):
        self._path = Path(path)

    def data_folder(self) -> Path:
        """
        Paths to the game data folder.
        """
        try:
            return self._path.joinpath("StarRail_Data")
        except AttributeError:
            raise GameNotInstalledError("Game path is not set.")

    def is_installed(self) -> bool:
        """
        Checks if the game is installed.

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
        Gets the current installed game version from config.ini.

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

    def set_version_config(self):
        """
        Sets the current installed game version to config.ini.

        This method is meant to keep compatibility with the official launcher only.
        """
        cfg_file = self._path.joinpath("config.ini")
        if not cfg_file.exists():
            raise FileNotFoundError("config.ini not found.")
        cfg = ConfigFile(cfg_file)
        cfg.set("General", "game_version", self.get_version_str())
        cfg.save()

    def get_version(self) -> tuple[int, int, int]:
        """
        Gets the current installed game version.

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

    def get_version_str(self) -> str:
        """
        Gets the current installed game version as a string.

        Because this method uses `get_version()`, you should read the docs of
        that method too.

        Returns:
            str: The version as a string.
        """
        return ".".join(str(i) for i in self.get_version())

    def get_channel(self) -> GameChannel:
        """
        Gets the current game channel.

        Only works for Star Rail version 1.0.5, other versions will return the
        overridden channel or GameChannel.Overseas if no channel is overridden.

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
            # if self._path.joinpath("StarRail_Data").is_dir():
            #     return GameChannel.Overseas
            # elif self._path.joinpath("StarRail_Data").exists():
            #     return GameChannel.China
            # No reliable method there, so we'll just return the overridden channel or
            # fallback to overseas.
            return self._channel_override or GameChannel.Overseas

    def get_remote_game(self, pre_download: bool = False) -> resource.Game:
        """
        Gets the current game information from remote.

        Args:
            pre_download (bool): Whether to get the pre-download version.
                Defaults to False.

        Returns:
            A `Game` object that contains the game information.
        """
        channel = self._channel_override or self.get_channel()
        if pre_download:
            game = api.get_resource(channel=channel).pre_download_game
            if not game:
                raise PreDownloadNotAvailable("Pre-download version is not available.")
            return game
        return api.get_resource(channel=channel).game

    def get_update(self, pre_download: bool = False) -> resource.Diff | None:
        """
        Gets the current game update.

        Args:
            pre_download (bool): Whether to get the pre-download version.
                Defaults to False.

        Returns:
            A `Diff` object that contains the update information or
            `None` if the game is not installed or already up-to-date.
        """
        if not self.is_installed():
            return None
        version = (
            ".".join(x for x in self._version_override)
            if self._version_override
            else self.get_version_str()
        )
        for diff in self.get_remote_game(pre_download=pre_download).diffs:
            if diff.version == version:
                return diff
        return None

    def repair_file(self, file: PathLike, pre_download: bool = False) -> None:
        """
        Repairs a game file.

        This will automatically handle backup and restore the file if the repair
        fails.

        Args:
            file (PathLike): The file to repair.
            pre_download (bool): Whether to get the pre-download version.
                Defaults to False.
        """
        if not self.is_installed():
            raise GameNotInstalledError("Game is not installed.")
        file = Path(file)
        if not file.is_relative_to(self._path):
            raise ValueError("File is not in the game folder.")
        game = self.get_remote_game(pre_download=pre_download)
        if game.latest.decompressed_path is None:
            raise ScatteredFilesNotAvailableError("Scattered files are not available.")
        url = game.latest.decompressed_path + "/" + file.relative_to(self._path)
        # Backup the file
        file.rename(file.with_suffix(file.suffix + ".bak"))
        try:
            # Download the file
            download(url, file.with_suffix(""))
        except Exception:
            # Restore the backup
            file.rename(file.with_suffix(""))
            raise
        else:
            # Delete the backup
            file.unlink(missing_ok=True)

    def apply_update_archive(
        self, archive_file: PathLike | IOBase, auto_repair: bool = True
    ) -> None:
        """
        Applies an update archive to the game, it can be the game update or a
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
                Defaults to True.
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
        Installs an update from a `Diff` object.

        You may want to download the update manually and pass it to
        `apply_update_archive()` instead for better control, and after that
        execute `set_version_config()` to set the game version.

        Args:
            update_info (Diff, optional): The update information. Defaults to None.
            auto_repair (bool, optional): Whether to repair the file if it's broken.
                Defaults to True.
        """
        if not self.is_installed():
            raise GameNotInstalledError("Game is not installed.")
        if not update_info:
            update_info = self.get_update()
        if not update_info or update_info.version == self.get_version_str():
            raise GameAlreadyUpdatedError("Game is already updated.")
        archive_file = self._cache.joinpath(update_info.name)
        download(update_info.path, archive_file)
        self.apply_update_archive(archive_file=archive_file, auto_repair=auto_repair)
        self.set_version_config()
