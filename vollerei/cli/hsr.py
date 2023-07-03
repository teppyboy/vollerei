from traceback import print_exc
from platform import system
from vollerei.cli.utils import ask, msg
from vollerei.exceptions.game import GameError
from vollerei.hsr import Game, Patcher
from vollerei.exceptions.patcher import PatcherError, PatchUpdateError
from vollerei.hsr.patcher import PatchType
import typer


app = typer.Typer()
patcher = Patcher()


class State:
    game: Game = None


@app.callback()
def callback(game_path: str = None, patch_type: str = None):
    """
    Manages the Honkai: Star Rail installation

    This manages the game installation and handle the patching process automatically.
    """
    State.game: Game = Game(game_path)
    if patch_type is None:
        patch_type = PatchType.Jadeite
    elif isinstance(patch_type, str):
        patch_type = PatchType[patch_type]
    elif isinstance(patch_type, int):
        patch_type = PatchType(patch_type)
    patcher.patch_type = patch_type


@app.command()
def patch_type():
    print("Patch type:", patcher.patch_type.name)


@app.command()
def update_patch():
    patch_type()
    msg("Updating patch...", end=" ")
    try:
        patcher.update_patch()
    except PatchUpdateError as e:
        print("FAILED")
        print(f"Patch update failed with following error: {e} ({e.__context__})")
        return False
    msg("OK")
    return True


def _patch_jadeite():
    try:
        msg("Installing patch...", end=" ")
        jadeite_dir = patcher.patch_game(game=State.game)
    except PatcherError as e:
        print("FAILED")
        print("Patching failed with following error:", e)
        print_exc()
        return
    print("OK")
    exe_path = jadeite_dir.joinpath("jadeite.exe")
    msg("Jadeite executable is located at: ", end="")
    print(exe_path)
    msg()
    msg("=" * 15)
    msg(
        "Installation succeeded, but note that you need to run the game using "
        + "Jadeite to use the patch."
    )
    msg()
    msg(f'E.g: I_WANT_A_BAN=1 {exe_path} "{State.game.path}"')
    msg()
    msg("Please don't spread this project to public, we just want to play the game.")
    msg(
        "And for your own sake, please only use testing accounts, as there is an "
        + "extremely high risk of getting banned."
    )
    msg("=" * 15)


def _patch_astra(self):
    try:
        msg("Patching game...", end=" ")
        patcher.patch_game(game=State.game)
    except PatcherError as e:
        print("FAILED")
        print(f"Patching failed with following error: {e}")
        return
    print("OK")


def patch(self):
    if system() == "Windows":
        msg("Windows is supported officialy by the game, so no patching is needed.")
    msg("By patching you are breaking the ToS, use at your own risk.")
    if not ask("Do you want to patch the game?"):
        print("Patching aborted.")
        return
    msg("Checking telemetry hosts...", end=" ")
    telemetry_list = patcher.check_telemetry()
    if telemetry_list:
        msg("FOUND")
        print("Telemetry hosts found:")
        for host in telemetry_list:
            print(f"{host}")
        msg(
            "To prevent the game from sending data about the patch, "
            + "we need to block these hosts."
        )
        if not ask("Do you want to block these hosts?"):
            print("Patching aborted.")
            print("Please block these hosts manually then try again.")
            return
        try:
            patcher.block_telemetry(telemetry_list=telemetry_list)
        except Exception as e:
            print("Couldn't block telemetry hosts:", e)
            if system() != "Windows":
                print("Cannot continue, please block them manually then try again.")
                return
            print("Continuing anyway...")
    else:
        msg("OK")
    if not update_patch():
        return
    match patcher.patch_type:
        case PatchType.Jadeite:
            _patch_jadeite()
        case PatchType.Astra:
            _patch_astra()


@app.command()
def get_version():
    try:
        print(State.game.get_version_str())
    except GameError as e:
        print("Couldn't get game version:", e)
