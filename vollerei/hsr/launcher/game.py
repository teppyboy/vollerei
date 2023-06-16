from hashlib import md5
from os import PathLike
from pathlib import Path
from enum import Enum
from vollerei.abc.launcher.game import GameABC
from vollerei.hsr.constants import md5sums


class GameChannel(Enum):
    Overseas = 0
    China = 1


class Game(GameABC):
    def __init__(self, path: PathLike = None):
        self._path: Path | None = Path(path) if path else None

    @property
    def path(self) -> Path | None:
        return self._path

    def data_folder(self) -> Path:
        return self._path.joinpath("StarRail_Data")

    def is_installed(self) -> bool:
        if self._path is None:
            return False
        if (
            not self._path.joinpath("StarRail.exe").exists()
            or not self._path.joinpath("StarRailBase.dll").exists()
        ):
            return False

    def get_version(self) -> tuple[int, int, int]:
        """
        Get the current installed game version.

        Credits to An Anime Team for the code that does the magic:
        https://github.com/an-anime-team/anime-game-core/blob/main/src/games/star_rail/game.rs#L49
        """
        allowed = [48, 49, 50, 51, 52, 53, 54, 55, 56, 57]
        version_bytes: list[bytes] = [0, 0, 0]
        version_ptr = 0
        correct = True
        with self.data_folder().joinpath("data.unity3d").open("rb") as f:
            f.seek(0x7D0)  # 2000 in decimal
            for byte in f.read(10000):
                match byte:
                    case 0:
                        version_bytes = [0, 0, 0]
                        version_ptr = 0
                        correct = True
                    case 46:
                        version_ptr += 1
                        if version_ptr > 2:
                            correct = False
                    case 38:
                        if (
                            correct
                            and version_bytes[0] > 0
                            and version_bytes[1] > 0
                            and version_bytes[2] > 0
                        ):
                            # TODO: The below code is not correct.
                            return (
                                int(version_bytes[0]),
                                int(version_bytes[1]),
                                int(version_bytes[2]),
                            )
                    case _:
                        if correct and byte in allowed:
                            version_bytes[version_ptr] += byte
                        else:
                            correct = False
        return (0, 0, 0)

    def get_channel(self) -> GameChannel:
        if self.get_version() == (1, 0, 5):
            for channel, v in md5sums["1.0.5"].values():
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
