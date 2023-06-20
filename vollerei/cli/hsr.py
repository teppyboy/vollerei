from traceback import print_exc
from platform import system
from vollerei.cli.utils import ask
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
            return False
        print("OK")
        return True

    def update_patch(self):
        self.__update_patch()

    def __patch_jadeite(self):
        try:
            print("Installing patch...", end=" ")
            jadeite_dir = self._patcher.patch_game(game=self._game)
        except PatcherError as e:
            print("FAILED")
            print(f"Patching failed with following error: {e}")
            return
        print("OK")
        exe_path = jadeite_dir.joinpath("jadeite.exe")
        print("Jadeite executable is located at:", exe_path)
        print()
        print("=" * 15)
        print(
            "Installation succeeded, but note that you need to run the game using "
            + "Jadeite to use the patch."
        )
        print()
        print(f'E.g: I_WANT_A_BAN=1 {exe_path} "{self._game.path}"')
        print()
        print(
            "Please don't spread this project to public, we just want to play the game."
        )
        print(
            "And for your own sake, please only use testing accounts, as there is an "
            + "extremely high risk of getting banned."
        )
        print("=" * 15)

    def __patch_astra(self):
        try:
            print("Patching game...", end=" ")
            self._patcher.patch_game(game=self._game)
        except PatcherError as e:
            print("FAILED")
            print(f"Patching failed with following error: {e}")
            return
        print("OK")

    def patch(self):
        if system() == "Windows":
            print(
                "Windows is supported officialy by the game, so no patching is needed."
            )
            if not ask("Do you still want to patch?"):
                print("Patching aborted.")
                return
        telemetry_list = self._patcher.check_telemetry()
        if telemetry_list:
            print("Telemetry hosts found: ")
            for host in telemetry_list:
                print(f" - {host}")
            if not ask(
                "Do you want to block these hosts? (Without blocking you can't use the patch)"
            ):
                print("Patching aborted.")
                return
            try:
                self._patcher.block_telemetry(telemetry_list=telemetry_list)
            except Exception as e:
                print("Couldn't block telemetry hosts:", e)
                if system() != "Windows":
                    print("Cannot continue, please block them manually then try again.")
                    return
                print("Continuing anyway...")
        if not self.__update_patch():
            return
        match self._patcher.patch_type:
            case PatchType.Jadeite:
                self.__patch_jadeite()
            case PatchType.Astra:
                self.__patch_astra()
