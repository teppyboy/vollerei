from os import PathLike
from pathlib import Path
from vollerei.abc.launcher.game import GameABC


class Game(GameABC):
    def __init__(self, path: PathLike = None):
        self.path: Path | None = Path(path) if path else None

    def is_installed(self) -> bool:
        if self.path is None:
            return False
        if (
            not self.path.joinpath("StarRail.exe").exists()
            or not self.path.joinpath("StarRailBase.dll").exists()
        ):
            return False
