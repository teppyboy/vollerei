from abc import ABC, abstractmethod
from os import PathLike
from pathlib import Path
from typing import Any


class GameABC(ABC):
    """
    Manages the game installation
    """

    path: Path
    version_override: tuple[int, int, int] | None
    channel_override: Any

    def __init__(self, path: PathLike = None):
        pass

    def data_folder(self) -> Path:
        """
        Get the game data folder
        """
        pass

    def is_installed(self) -> bool:
        """
        Check if the game is installed
        """
        pass

    def install_game(self, game_path: PathLike = None):
        """
        Install the game

        If path is not specified then it'll use self.path, if that is
        not specified too then it'll raise an exception.

        Args:
            game_path (PathLike, optional): Path to install the game to.

        Returns:
            None
        """
        pass

    def install_game_from_archive(
        self, archive: PathLike, game_path: PathLike = None
    ) -> None:
        """
        Install the game from an archive

        If path is not specified then it'll use self.path, if that is
        not specified too then it'll raise an exception.

        Args:
            archive (PathLike): Path to the archive.
            game_path (PathLike, optional): Path to install the game to.
        """

    def install_update_from_archive(
        self, archive: PathLike, game_path: PathLike = None
    ) -> None:
        """
        Install the update from an archive

        Args:
            archive (PathLike): Path to the archive
            game_path (PathLike, optional): Path to the game. Defaults to None.
        """
        pass

    def get_version(self) -> tuple[int, int, int]:
        """
        Get the game version

        If the game is not installed, it'll return (0, 0, 0).
        """
        pass

    def get_update(self):
        """
        Get the game update
        """
        pass

    def get_channel(self):
        """
        Get the game channel
        """
        pass
