from cleo.commands.command import Command
from cleo.helpers import option
from platform import system
from vollerei.cli import utils
from vollerei.exceptions.game import GameError
from vollerei.hsr import Game, Patcher
from vollerei.exceptions.patcher import PatcherError, PatchUpdateError
from vollerei.hsr.patcher import PatchType

patcher = Patcher()


default_options = [
    option(
        "game-path",
        "g",
        description="Path to the game installation",
        flag=False,
        default=".",
    ),
    option("patch-type", "p", description="Patch type", flag=False),
    option("silent", "s", description="Silent mode"),
    option("noconfirm", "y", description="Do not ask for confirmation"),
]


class State:
    game: Game = None


def callback(
    command: Command,
):
    """
    Base callback for all commands
    """
    game_path = command.option("game-path")
    patch_type = command.option("patch-type")
    silent = command.option("silent")
    noconfirm = command.option("noconfirm")
    State.game: Game = Game(game_path)
    if patch_type is None:
        patch_type = PatchType.Jadeite
    elif isinstance(patch_type, str):
        patch_type = PatchType[patch_type]
    elif isinstance(patch_type, int):
        patch_type = PatchType(patch_type)
    patcher.patch_type = patch_type
    utils.silent_message = silent
    if noconfirm:
        utils.no_confirm = noconfirm
    command.add_style("warn", fg="yellow")


class PatchTypeCommand(Command):
    name = "hsr patch type"
    description = "Get the patch type of the game"
    options = default_options

    def handle(self):
        callback(command=self)
        self.line(f"<comment>Patch type:</comment> {patcher.patch_type.name}")


class UpdatePatchCommand(Command):
    name = "hsr patch update"
    description = "Updates the patch"
    options = default_options

    def handle(self):
        callback(command=self)
        progress = utils.ProgressIndicator(self)
        progress.start("Updating patch... ")
        try:
            patcher.update_patch()
        except PatchUpdateError as e:
            progress.finish(
                f"<error>Patch update failed with following error: {e} ({e.__context__})</error>"
            )
        else:
            progress.finish("<comment>Patch updated!</comment>")


class PatchInstallCommand(Command):
    name = "hsr patch install"
    description = "Installs the patch"
    options = default_options

    def jadeite(self):
        progress = utils.ProgressIndicator(self)
        progress.start("Installing patch... ")
        try:
            jadeite_dir = patcher.patch_game(game=State.game)
        except PatcherError as e:
            progress.finish(
                f"<error>Patch installation failed with following error: {e} ({e.__context__})</error>"
            )
            return
        progress.finish("<comment>Patch installed!</comment>")
        print()
        exe_path = jadeite_dir.joinpath("jadeite.exe")
        self.line(f"Jadeite executable is located at: <question>{exe_path}</question>")
        self.line(
            "You need to <warn>run the game using Jadeite</warn> to use the patch."
        )
        self.line(
            f'E.g: <question>I_WANT_A_BAN=1 {exe_path} "{State.game.path}"</question>'
        )
        print()
        self.line(
            "Please don't spread this project to public, we just want to play the game."
        )
        self.line(
            "And for your own sake, please only <warn>use test accounts</warn>, as there is an <warn>extremely high risk of getting banned.</warn>"
        )

    def astra(self):
        progress = utils.ProgressIndicator(self)
        progress.start("Installing patch... ")
        try:
            patcher.patch_game(game=State.game)
        except PatcherError as e:
            progress.finish(
                f"<error>Patch installation failed with following error: {e} ({e.__context__})</error>"
            )
            return
        progress.finish("<comment>Patch installed!</comment>")
        self.line()
        self.line(
            "Please don't spread this project to public, we just want to play the game."
        )
        self.line(
            "And for your own sake, please only use testing accounts, as there is an extremely high risk of getting banned."
        )

    def handle(self):
        callback(command=self)
        if system() == "Windows":
            self.line(
                "Windows is <comment>officialy supported</comment> by the game, so no patching is needed."
            )
        self.line(
            "By patching the game, <warn>you are violating the ToS of the game.</warn>"
        )
        if not self.confirm("Do you want to patch the game?"):
            self.line("<error>Patching aborted.</error>")
            return
        progress = utils.ProgressIndicator(self)
        progress.start("Checking telemetry hosts... ")
        telemetry_list = patcher.check_telemetry()
        if telemetry_list:
            progress.finish("<warn>Telemetry hosts were found.</warn>")
            self.line("Below is the list of telemetry hosts that need to be blocked:")
            print()
            for host in telemetry_list:
                self.line(f"{host}")
            print()
            self.line(
                "To prevent the game from sending data about the patch, "
                + "we need to <comment>block these hosts.</comment>"
            )
            if not self.confirm("Do you want to block them?"):
                self.line("<error>Patching aborted.</error>")
                self.line(
                    "<error>Please block these hosts manually then try again.</error>"
                )
                return
            try:
                patcher.block_telemetry(telemetry_list=telemetry_list)
            except Exception as e:
                self.line_error(
                    f"<error>Couldn't block telemetry hosts: {e.__context__}</error>"
                )
                # There's a good reason for this.
                if system() != "Windows":
                    self.line(
                        "<error>Cannot continue, please block them manually then try again.</error>"
                    )
                    return
                self.line("<warn>Continuing anyway...</warn>")
        else:
            progress.finish("<comment>No telemetry hosts found.</comment>")
        progress = utils.ProgressIndicator(self)
        progress.start("Updating patch... ")
        try:
            patcher.update_patch()
        except PatchUpdateError as e:
            progress.finish(
                f"<error>Patch update failed with following error: {e} ({e.__context__})</error>"
            )
        else:
            progress.finish("<comment>Patch updated.</comment>")
        match patcher.patch_type:
            case PatchType.Jadeite:
                self.jadeite()
            case PatchType.Astra:
                self.astra()


class GetVersionCommand(Command):
    name = "hsr version"
    description = "Gets the local game version"
    options = default_options

    def handle(self):
        callback(command=self)
        try:
            self.line(
                f"<comment>Version:</comment> {'.'.join(str(x) for x in State.game.get_version())}"
            )
        except GameError as e:
            self.line_error(f"<error>Couldn't get game version: {e}</error>")


commands = [
    PatchTypeCommand(),
    UpdatePatchCommand(),
    PatchInstallCommand(),
    GetVersionCommand(),
]
