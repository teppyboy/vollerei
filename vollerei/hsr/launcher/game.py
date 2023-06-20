from hashlib import md5
from os import PathLike
from pathlib import Path
from enum import Enum
from vollerei.abc.launcher.game import GameABC
from vollerei.hsr.constants import MD5SUMS


class GameChannel(Enum):
    Overseas = 0
    China = 1


class Game(GameABC):
    def __init__(self, path: PathLike = None):
        self._path: Path | None = Path(path) if path else None

    @property
    def path(self) -> Path | None:
        return self._path

    @path.setter
    def path(self, path: PathLike):
        self._path = Path(path)

    def data_folder(self) -> Path:
        return self._path.joinpath("StarRail_Data")

    def is_installed(self) -> bool:
        """
        Check if the game is installed.
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

    def get_version(self) -> tuple[int, int, int]:
        """
        Get the current installed game version.

        Credits to An Anime Team for the code that does the magic:
        https://github.com/an-anime-team/anime-game-core/blob/main/src/games/star_rail/game.rs#L49

        This returns (0, 0, 0) if the version could not be found
        (usually indicates the game is not installed)

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
        return (0, 0, 0)

    def get_version_str(self) -> str:
        """
        Same as get_version, but returns a string instead.

        Returns:
            str: The version as a string.
        """
        return ".".join(str(i) for i in self.get_version())

    def get_channel(self) -> GameChannel:
        """
        Get the current game channel.

        Only works for Star Rail version 1.0.5, other versions will return None

        Returns:
            GameChannel: The current game channel.
        """
        if self.get_version() == (1, 0, 5):
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
