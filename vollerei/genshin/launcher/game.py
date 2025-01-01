from configparser import ConfigParser
from io import IOBase
from os import PathLike
from pathlib import Path, PurePath
from vollerei.abc.launcher.game import GameABC
from vollerei.common import ConfigFile, functions
from vollerei.common.api import resource
from vollerei.common.enums import VoicePackLanguage, GameChannel
from vollerei.exceptions.game import (
    GameAlreadyUpdatedError,
    GameNotInstalledError,
    PreDownloadNotAvailable,
)
from vollerei.genshin.launcher import api
from vollerei import paths
from vollerei.utils import download


class Game(GameABC):
    """
    Manages the game installation
    """

    def __init__(self, path: PathLike = None, cache_path: PathLike = None):
        self._path: Path | None = Path(path) if path else None
        if not cache_path:
            cache_path = paths.cache_path
        cache_path = Path(cache_path)
        self.cache: Path = cache_path.joinpath("game/genshin/")
        self.cache.mkdir(parents=True, exist_ok=True)
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
            match self.get_channel():
                case GameChannel.China:
                    return self._path.joinpath("YuanShen_Data")
                case GameChannel.Overseas:
                    return self._path.joinpath("GenshinImpact_Data")
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
        try:
            self.get_channel()
            if self.data_folder().is_dir():
                return True
        except GameNotInstalledError:
            return False
        if self.get_version() == (0, 0, 0):
            return False
        return True

    def get_channel(self) -> GameChannel:
        """
        Gets the current game channel.

        Returns:
            GameChannel: The current game channel.
        """
        if self._channel_override:
            return self._channel_override
        if not self.is_installed():
            raise GameNotInstalledError("Game path is not set.")
        if self._path.joinpath("YuanShen.exe").is_file():
            return GameChannel.China
        return GameChannel.Overseas

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
        # Fk u miHoYo
        if "general" in cfg.sections():
            version_str = cfg.get("general", "game_version", fallback="0.0.0")
        elif "General" in cfg.sections():
            version_str = cfg.get("General", "game_version", fallback="0.0.0")
        else:
            return (0, 0, 0)
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
        if cfg_file.exists():
            cfg = ConfigFile(cfg_file)
            cfg.set("general", "game_version", self.get_version_str())
            cfg.save()
        else:
            cfg = ConfigParser()
            cfg.read_dict(
                {
                    "general": {
                        "downloading_mode": None,
                        "channel": 1,
                        "cps": "hyp_hoyoverse",
                        "game_version": self.get_version_str(),
                        "sub_channel": 0,
                        # This is probably should be fetched from the server but well
                        "plugin_vt8u0pl2cc_version": "1.1.0",
                        # What's this in the Chinese version?
                        "uapc": {
                            "hk4e_global": {"uapc": "f55586a8ce9f_"},
                            "hyp": {"uapc": "f55586a8ce9f_"},
                        },  # Honestly what's this?
                    }
                }
            )
            cfg.write(cfg_file.open("w"))

    def get_version(self) -> tuple[int, int, int]:
        """
        Gets the current installed game version.

        Credits to An Anime Team for the code that does the magic:
        https://github.com/an-anime-team/anime-game-core/blob/main/src/games/genshin/game.rs#L52

        If the above method fails, it'll fallback to read the config.ini file
        for the version, which is not recommended (as described in
        `get_version_config()` docs)

        This returns (0, 0, 0) if the version could not be found
        (usually indicates the game is not installed), and in fact `is_installed()` uses
        this method to check if the game is installed too.

        Returns:
            tuple[int, int, int]: The version as a tuple of integers.
        """

        data_file = self.data_folder().joinpath("globalgamemanagers")
        if not data_file.exists():
            return self.get_version_config()

        def bytes_to_int(byte_array: list[bytes]) -> int:
            bytes_as_int = int.from_bytes(byte_array, byteorder="big")
            actual_int = bytes_as_int - 48  # 48 is the ASCII code for 0
            return actual_int

        version_bytes: list[list[bytes]] = [[], [], []]
        version_ptr = 0
        correct = True
        try:
            with data_file.open("rb") as f:
                f.seek(4000)
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
                        case 95:
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
                            if correct and byte in b"0123456789":
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

    def get_installed_voicepacks(self) -> list[VoicePackLanguage]:
        """
        Gets the installed voicepacks.

        Returns:
            list[VoicePackLanguage]: A list of installed voicepacks.
        """
        if not self.is_installed():
            raise GameNotInstalledError("Game is not installed.")
        audio_assets = self.data_folder().joinpath("StreamingAssets/AudioAssets/")
        if audio_assets.joinpath("AudioPackage").is_dir():
            audio_assets = audio_assets.joinpath("AudioPackage")
        voicepacks = []
        for child in audio_assets.iterdir():
            if child.resolve().is_dir():
                name = child.name
                if name.startswith("English"):
                    name = "English"
                try:
                    voicepacks.append(VoicePackLanguage[name])
                except (ValueError, KeyError):
                    pass
        return voicepacks

    def get_remote_game(
        self, pre_download: bool = False
    ) -> resource.Main | resource.PreDownload:
        """
        Gets the current game information from remote.

        Args:
            pre_download (bool): Whether to get the pre-download version.
                Defaults to False.

        Returns:
            A `Main` or `PreDownload` object that contains the game information.
        """
        channel = self._channel_override or self.get_channel()
        if pre_download:
            game = api.get_game_package(channel=channel).pre_download
            if not game:
                raise PreDownloadNotAvailable("Pre-download version is not available.")
            return game
        return api.get_game_package(channel=channel).main

    def get_update(self, pre_download: bool = False) -> resource.Patch | None:
        """
        Gets the current game update.

        Args:
            pre_download (bool): Whether to get the pre-download version.
                Defaults to False.

        Returns:
            A `Patch` object that contains the update information or
            `None` if the game is not installed or already up-to-date.
        """
        if not self.is_installed():
            return None
        version = (
            ".".join(str(x) for x in self._version_override)
            if self._version_override
            else self.get_version_str()
        )
        for patch in self.get_remote_game(pre_download=pre_download).patches:
            if patch.version == version:
                return patch
        return None

    def repair_file(
        self,
        file: PathLike,
        pre_download: bool = False,
        game_info: resource.Game = None,
    ) -> None:
        """
        Repairs a game file.

        This will automatically handle backup and restore the file if the repair
        fails.

        Args:
            file (PathLike): The file to repair.
            pre_download (bool): Whether to get the pre-download version.
                Defaults to False.
        """
        return self.repair_files([file], pre_download=pre_download, game_info=game_info)

    def repair_files(
        self,
        files: list[PathLike],
        pre_download: bool = False,
        game_info: resource.Game = None,
    ) -> None:
        """
        Repairs multiple game files.

        This will automatically handle backup and restore the file if the repair
        fails.

        Args:
            files (PathLike): The files to repair.
            pre_download (bool): Whether to get the pre-download version.
                Defaults to False.
        """
        functions.repair_files(
            self, files, pre_download=pre_download, game_info=game_info
        )

    def repair_game(self) -> None:
        """
        Tries to repair the game by reading "pkg_version" file and downloading the
        mismatched files from the server.
        """
        functions.repair_game(self)

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
        self, update_info: resource.Patch = None, auto_repair: bool = True
    ):
        """
        Installs an update from a `Patch` object.

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
        update_url = update_info.game_pkgs[0].url
        # Base game update
        archive_file = self.cache.joinpath(PurePath(update_url).name)
        download(update_url, archive_file)
        self.apply_update_archive(archive_file=archive_file, auto_repair=auto_repair)
        # Get installed voicepacks
        installed_voicepacks = self.get_installed_voicepacks()
        # Voicepack update
        for remote_voicepack in update_info.audio_pkgs:
            if remote_voicepack.language not in installed_voicepacks:
                continue
            # Voicepack is installed, update it
            archive_file = self.cache.joinpath(PurePath(remote_voicepack.url).name)
            download(remote_voicepack.url, archive_file)
            self.apply_update_archive(
                archive_file=archive_file, auto_repair=auto_repair
            )
        self.set_version_config()
