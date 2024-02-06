from configparser import ConfigParser
from io import IOBase
from os import PathLike
from pathlib import Path
from vollerei.abc.launcher.game import GameABC
from vollerei.common import ConfigFile, functions
from vollerei.common.api import resource
from vollerei.common.enums import VoicePackLanguage
from vollerei.exceptions.game import (
    GameAlreadyUpdatedError,
    GameNotInstalledError,
    PreDownloadNotAvailable,
    ScatteredFilesNotAvailableError,
)
from vollerei.hi3.launcher.enums import GameChannel
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
        self.cache: Path = cache_path.joinpath("game/hi3/")
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
