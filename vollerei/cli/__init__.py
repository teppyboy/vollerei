from pathlib import Path
from vollerei import __version__
from vollerei.cli.hsr import HSR
from vollerei.hsr import PatchType


class CLI:
    def __init__(self, game_path: str = None, patch_type=None) -> None:
        """
        Vollerei CLI
        """
        print(f"Vollerei v{__version__}")
        if not game_path:
            game_path = Path.cwd()
        game_path = Path(game_path)
        if patch_type is None:
            patch_type = PatchType.Jadeite
        elif isinstance(patch_type, str):
            patch_type = PatchType[patch_type]
        elif isinstance(patch_type, int):
            patch_type = PatchType(patch_type)
        self.hsr = HSR(game_path=game_path, patch_type=patch_type)
