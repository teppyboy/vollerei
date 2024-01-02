from cleo.commands.command import Command
from cleo.helpers import option, argument
from platform import system
from vollerei.hsr.launcher.enums import GameChannel
from vollerei.cli import utils
from vollerei.exceptions.game import GameError
from vollerei.hsr import Game, Patcher
from vollerei.exceptions.patcher import PatcherError, PatchUpdateError
from vollerei.hsr.patcher import PatchType

patcher = Patcher()


default_options = [
    option("channel", "c", description="Game channel", flag=False, default="overseas"),
    option("force", "f", description="Force the command to run"),
    option(
        "game-path",
        "g",
        description="Path to the game installation",
        flag=False,
        default=".",
    ),
    option("patch-type", "p", description="Patch type", flag=False),
    option("temporary-path", "t", description="Temporary path", flag=False),
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
    channel = command.option("channel")
    silent = command.option("silent")
    noconfirm = command.option("noconfirm")
    temporary_path = command.option("temporary-path")
    if isinstance(channel, str):
        channel = GameChannel[channel.capitalize()]
    elif isinstance(channel, int):
        channel = GameChannel(channel)
    State.game: Game = Game(game_path, temporary_path)
    if channel:
        State.game.channel_override = channel
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


class UpdateCommand(Command):
    name = "hsr update"
    description = "Updates the local game if available"
    options = default_options + [
        option(
            "auto-repair", "R", description="Automatically repair the game if needed"
        ),
        option("pre-download", description="Pre-download the game if available"),
    ]

    def handle(self):
        callback(command=self)
        auto_repair = self.option("auto-repair")
        pre_download = self.option("pre-download")
        if auto_repair:
            self.line("<comment>Auto-repair is enabled.</comment>")
        progress = utils.ProgressIndicator(self)
        progress.start("Checking for updates... ")
        try:
            update_diff = State.game.get_update(pre_download=pre_download)
            game_info = State.game.get_remote_game(pre_download=pre_download)
        except Exception as e:
            progress.finish(
                f"<error>Update checking failed with following error: {e} ({e.__context__})</error>"
            )
            return
        if update_diff is None:
            progress.finish("<comment>Game is already updated.</comment>")
            return
        progress.finish("<comment>Update available.</comment>")
        self.line(
            f"The current version is: <comment>{State.game.get_version_str()}</comment>"
        )
        self.line(
            f"The latest version is: <comment>{game_info.latest.version}</comment>"
        )
        if not self.confirm("Do you want to update the game?"):
            self.line("<error>Update aborted.</error>")
            return
        self.line("Downloading update package...")
        out_path = State.game._cache.joinpath(update_diff.name)
        try:
            download_result = utils.download(
                update_diff.path, out_path, file_len=update_diff.size
            )
        except Exception as e:
            self.line_error(f"<error>Couldn't download update: {e}</error>")
            return

        if not download_result:
            self.line_error("<error>Download failed.</error>")
            return
        self.line("Download completed.")
        progress = utils.ProgressIndicator(self)
        progress.start("Applying update package...")
        try:
            State.game.apply_update_archive(out_path, auto_repair=auto_repair)
        except Exception as e:
            progress.finish(
                f"<error>Couldn't apply update: {e} ({e.__context__})</error>"
            )
            return
        progress.finish("<comment>Update applied.</comment>")
        self.line("Setting version config... ")
        self.set_version_config()
        self.line(
            f"The game has been updated to version: <comment>{State.game.get_version_str()}</comment>"
        )


class ApplyUpdateArchive(Command):
    name = "hsr update apply-archive"
    description = "Applies the update archive to the local game"
    arguments = [argument("path", description="Path to the update archive")]
    options = default_options + [
        option(
            "auto-repair", "R", description="Automatically repair the game if needed"
        ),
    ]

    def handle(self):
        callback(command=self)
        auto_repair = self.option("auto-repair")
        update_archive = self.argument("path")
        if auto_repair:
            self.line("<comment>Auto-repair is enabled.</comment>")
        progress = utils.ProgressIndicator(self)
        progress.start("Applying update package...")
        try:
            State.game.apply_update_archive(update_archive, auto_repair=auto_repair)
        except Exception as e:
            progress.finish(
                f"<error>Couldn't apply update: {e} ({e.__context__})</error>"
            )
            return
        progress.finish("<comment>Update applied.</comment>")
        self.line("Setting version config... ")
        try:
            State.game.set_version_config()
        except Exception as e:
            self.line_error(f"<warn>Couldn't set version config: {e}</warn>")
            self.line_error(
                "This won't affect the overall experience, but if you're using the official launcher"
            )
            self.line_error(
                "you may have to edit the file 'config.ini' manually to reflect the latest version."
            )
        self.line(
            f"The game has been updated to version: <comment>{State.game.get_version_str()}</comment>"
        )


commands = [
    ApplyUpdateArchive,
    UpdateCommand,
    PatchTypeCommand,
    UpdatePatchCommand,
    PatchInstallCommand,
    GetVersionCommand,
]
