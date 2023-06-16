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

    def is_installed(self) -> bool:
        if self._path is None:
            return False
        if (
            not self._path.joinpath("StarRail.exe").exists()
            or not self._path.joinpath("StarRailBase.dll").exists()
        ):
            return False

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
