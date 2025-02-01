from configparser import ConfigParser
from io import IOBase
from os import PathLike
from pathlib import Path, PurePath
from vollerei.abc.launcher.game import GameABC
from vollerei.common import ConfigFile, functions
from vollerei.common.api import resource
from vollerei.common.enums import GameType, VoicePackLanguage, GameChannel
from vollerei.exceptions.game import (
    GameAlreadyUpdatedError,
    GameNotInstalledError,
    PreDownloadNotAvailable,
)
from vollerei.game.launcher import api
from vollerei.game.hsr import functions as hsr_functions
from vollerei.game.genshin import functions as genshin_functions
from vollerei.game.zzz import functions as zzz_functions
from vollerei import paths
from vollerei.utils import download


class Game(GameABC):
    """
    Manages the game installation

    For Star Rail and Zenless Zone Zero:

    Since channel detection isn't implemented yet, most functions assume you're
    using the overseas version of the game. You can override channel by setting
    the property `channel_override` to the channel you want to use.
    """

    def __init__(
        self, game_type: GameType, path: PathLike = None, cache_path: PathLike = None
    ):
        self._path: Path | None = Path(path) if path else None
        if not cache_path:
            cache_path = paths.cache_path
        cache_path = Path(cache_path)
        self._game_type = game_type
        self.cache: Path = cache_path.joinpath(f"game/{self._game_type.name.lower()}/")
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

        Returns:
            Path: The path to the game data folder.
        """
        try:
            match self._game_type:
                case GameType.Genshin:
                    match self.get_channel():
                        case GameChannel.China:
                            return self._path.joinpath("YuanShen_Data")
                        case GameChannel.Overseas:
                            return self._path.joinpath("GenshinImpact_Data")
                case GameType.HSR:
                    return self._path.joinpath("StarRail_Data")
                case GameType.ZZZ:
                    return self._path.joinpath("ZenlessZoneZero_Data")
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
        match self._game_type:
            case GameType.Genshin:
                match self.get_channel():
                    case GameChannel.China:
                        if not self._path.joinpath("YuanShen.exe").exists():
                            return False
                    case GameChannel.Overseas:
                        if not self._path.joinpath("GenshinImpact.exe").exists():
                            return False
            case GameType.HSR:
                if not self._path.joinpath("StarRail.exe").exists():
                    return False
            case GameType.ZZZ:
                if not self._path.joinpath("ZenlessZoneZero.exe").exists():
                    return False
        if not self.data_folder().is_dir():
            return False
        if self.get_version() == (0, 0, 0):
            return False
        return True

    def get_channel(self) -> GameChannel:
        """
        Gets the current game channel.

        Only works for Genshin and Star Rail version 1.0.5, other versions will return
        the overridden channel or GameChannel.Overseas if no channel is overridden.

        This is not needed for game patching, since the patcher will automatically
        detect the channel.

        Returns:
            GameChannel: The current game channel.
        """
        match self._game_type:
            case GameType.HSR:
                return (
                    hsr_functions.get_channel(self)
                    or self._channel_override
                    or GameChannel.Overseas
                )
            case GameType.Genshin:
                return (
                    genshin_functions.get_channel(self)
                    or self._channel_override
                    or GameChannel.Overseas
                )
            case _:
                return self._channel_override or GameChannel.Overseas

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

        Only works for the global version of the game, not the Chinese one (since I don't have
        them installed to test).

        This method is meant to keep compatibility with the official launcher only.
        """
        cfg_file = self._path.joinpath("config.ini")
        if cfg_file.exists():
            cfg = ConfigFile(cfg_file)
            cfg.set("general", "game_version", self.get_version_str())
            cfg.save()
        else:
            cfg_dict = {
                "general": {
                    "channel": 1,
                    "cps": "hyp_hoyoverse",
                    "game_version": self.get_version_str(),
                    "sub_channel": 0,
                    # This probably should be fetched from the server but well
                    "plugin_n06mjyc2r3_version": "1.1.0",
                    "uapc": None,  # Honestly what's this?
                }
            }

            match self._game_type:
                case GameType.Genshin:
                    cfg_dict["general"]["uapc"] = {
                        "hk4e_global": {"uapc": "f55586a8ce9f_"},
                        "hyp": {"uapc": "f55586a8ce9f_"},
                    }
                case GameType.HSR:
                    cfg_dict["general"]["uapc"] = {
                        "hkrpg_global": {"uapc": "f5c7c6262812_"},
                        "hyp": {"uapc": "f55586a8ce9f_"},
                    }
                case GameType.ZZZ:
                    cfg_dict["general"]["uapc"] = {
                        "nap_global": {"uapc": "f55586a8ce9f_"},
                        "hyp": {"uapc": "f55586a8ce9f_"},
                    }
            cfg = ConfigParser()
            cfg.read_dict(cfg_dict)
            cfg.write(cfg_file.open("w"))

    def get_version(self) -> tuple[int, int, int]:
        """
        Gets the current installed game version.

        Credits to An Anime Team for the code that does the magic, see the source
        in `hsr/functions.py`, `genshin/functions.py` and `zzz/functions.py` for more info

        If the above method fails, it'll fallback to read the config.ini file
        for the version, which is not recommended (as described in
        `get_version_config()` docs)

        This returns (0, 0, 0) if the version could not be found
        (usually indicates the game is not installed), and in fact `is_installed()` uses
        this method to check if the game is installed too.

        Returns:
            tuple[int, int, int]: The version as a tuple of integers.
        """
        match self._game_type:
            case GameType.HSR:
                return hsr_functions.get_version(self)
            case GameType.Genshin:
                return genshin_functions.get_version(self)
            case GameType.ZZZ:
                return zzz_functions.get_version(self)
            case _:
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
        voicepacks = []
        blacklisted_words = ["SFX"]
        audio_package: Path
        match self._game_type:
            case GameType.Genshin:
                audio_package = self.data_folder().joinpath(
                    "StreamingAssets/AudioAssets/"
                )
                if audio_package.joinpath("AudioPackage").is_dir():
                    audio_package = audio_package.joinpath("AudioPackage")
            case GameType.HSR:
                audio_package = self.data_folder().joinpath(
                    "Persistent/Audio/AudioPackage/Windows/"
                )
            case GameType.ZZZ:
                audio_package = self.data_folder().joinpath(
                    "StreamingAssets/Audio/Windows/Full/"
                )
        for child in audio_package.iterdir():
            if child.resolve().is_dir() and child.name not in blacklisted_words:
                name = child.name
                if name.startswith("English"):
                    name = "English"
                voicepack: VoicePackLanguage
                try:
                    if self._game_type == GameType.ZZZ:
                        voicepack = VoicePackLanguage.from_zzz_name(child.name)
                    else:
                        voicepack = VoicePackLanguage[name]
                    voicepacks.append(voicepack)
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
            game = api.get_game_package(
                game_type=self._game_type, channel=channel
            ).pre_download
            if not game:
                raise PreDownloadNotAvailable("Pre-download version is not available.")
            return game
        return api.get_game_package(game_type=self._game_type, channel=channel).main

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
            game_info (resource.Game): The game information to use for repair.
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

    def install_archive(self, archive_file: PathLike | IOBase) -> None:
        """
        Applies an install archive to the game, it can be the game itself or a
        voicepack one.

        `archive_file` can be a path to the archive file or a file-like object,
        like if you have very high amount of RAM and want to download the archive
        to memory instead of disk, this can be useful for you.

        Args:
            archive_file (PathLike | IOBase): The archive file.
        """
        if not isinstance(archive_file, IOBase):
            archive_file = Path(archive_file)
        functions.install_archive(self, archive_file)

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
