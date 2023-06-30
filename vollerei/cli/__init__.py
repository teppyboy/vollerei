from pathlib import Path
from vollerei import __version__
from vollerei.cli.hsr import HSR
from vollerei.hsr import PatchType
from vollerei.cli import utils
from vollerei.cli.utils import msg


class CLI:
    def __init__(
        self,
        game_path: str = None,
        patch_type=None,
        noconfirm: bool = False,
        silent: bool = False,
    ) -> None:
        """
        Vollerei CLI
        """
        utils.silent_message = silent
        msg(f"Vollerei v{__version__}")
        if noconfirm:
            msg("User requested to automatically answer yes to all questions.")
            utils.no_confirm = noconfirm
        if not game_path:
            game_path = Path.cwd()
        game_path = Path(game_path)
        hsr_patch_type = patch_type
        if patch_type is None:
            hsr_patch_type = PatchType.Jadeite
        elif isinstance(patch_type, str):
            hsr_patch_type = PatchType[patch_type]
        elif isinstance(patch_type, int):
            hsr_patch_type = PatchType(patch_type)
        self.hsr = HSR(game_path=game_path, patch_type=hsr_patch_type)
