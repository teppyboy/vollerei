from traceback import print_exc
from vollerei.hsr import Game, Patcher
from vollerei.exceptions.patcher import PatcherError, PatchUpdateError
from vollerei.hsr.patcher import PatchType


class HSR:
    def __init__(
        self, game_path=None, patch_type: PatchType = PatchType.Jadeite
    ) -> None:
        self._game = Game(game_path)
        print("Game directory:", self._game.path)
        print("Game version:", self._game.get_version_str())
        self._patcher = Patcher()
        self._patcher.patch_type = patch_type

    # Double _ means private to prevent Fire from invoking it
    def patch_type(self):
        print("Patch type:", self._patcher.patch_type.name)

    def __update_patch(self):
        self.patch_type()
        print("Updating patch...", end=" ")
        try:
            self._patcher.update_patch()
        except PatchUpdateError as e:
            print("FAILED")
            print(f"Patch update failed with following error: {e} ({e.__context__})")
            print_exc()
            return False
        print("OK")
        return True

    def update_patch(self):
        self.__update_patch()

    def patch(self):
        if not self.__update_patch():
            return
        try:
            print("Patching game...", end=" ")
            jadelte_dir = self._patcher.patch_game(game=self._game)
        except PatcherError as e:
            print("FAILED")
            print(f"Patching failed with following error: {e}")
            return
        print("OK")
        exe_path = jadelte_dir.joinpath("jadeite.exe")
        print("Jadelte executable is located at:", exe_path)
        print(
            "Patching succeeded, but note that you need to run the game using Jadeite to use the patch."
        )
        print(f'E.g: I_WANT_A_BAN=1 {exe_path} "{self._game.path}"')
        print("And for your own sake, please only use testing accounts, as there is an extremely high risk of getting banned.")
