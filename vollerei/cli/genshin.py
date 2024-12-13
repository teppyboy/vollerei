import traceback
from cleo.commands.command import Command
from cleo.helpers import option, argument
from pathlib import PurePath
from vollerei.common.enums import GameChannel, VoicePackLanguage
from vollerei.cli import utils
from vollerei.exceptions.game import GameError
from vollerei.genshin import Game
from vollerei import paths


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
    option("noconfirm", "y", description="Do not ask for confirmation (yes to all)"),
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
    channel = command.option("channel")
    silent = command.option("silent")
    noconfirm = command.option("noconfirm")
    temporary_path = command.option("temporary-path")
    if isinstance(channel, str):
        channel = GameChannel[channel.capitalize()]
    elif isinstance(channel, int):
        channel = GameChannel(channel)
    if temporary_path:
        paths.set_base_path(temporary_path)
    State.game = Game(game_path, temporary_path)
    if channel:
        State.game.channel_override = channel
    utils.silent_message = silent
    if noconfirm:
        utils.no_confirm = noconfirm

        def confirm(
            question: str, default: bool = False, true_answer_regex: str = r"(?i)^y"
        ):
            command.line(
                f"<question>{question} (yes/no)</question> [<comment>{'yes' if default else 'no'}</comment>] y"
            )
            return True

        command.confirm = confirm
    command.add_style("warn", fg="yellow")


def set_version_config(self: Command):
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


class VoicepackListInstalled(Command):
    name = "genshin voicepack list-installed"
    description = "Get the installed voicepacks"
    options = default_options

    def handle(self):
        callback(command=self)
        installed_voicepacks_str = [
            f"<comment>{x.name}</comment>"
            for x in State.game.get_installed_voicepacks()
        ]
        self.line(f"Installed voicepacks: {', '.join(installed_voicepacks_str)}")


class VoicepackList(Command):
    name = "genshin voicepack list"
    description = "Get all available voicepacks"
    options = default_options + [
        option("pre-download", description="Pre-download the game if available"),
    ]

    def handle(self):
        callback(command=self)
        pre_download = self.option("pre-download")
        remote_game = State.game.get_remote_game(pre_download=pre_download)
        available_voicepacks_str = [
            f"<comment>{x.language.name} ({x.language.value})</comment>"
            for x in remote_game.latest.voice_packs
        ]
        self.line(f"Available voicepacks: {', '.join(available_voicepacks_str)}")


class VoicepackInstall(Command):
    name = "genshin voicepack install"
    description = (
        "Installs the specified installed voicepacks"
    )
    options = default_options + [
        option("pre-download", description="Pre-download the game if available"),
    ]
    arguments = [
        argument(
            "language", description="Languages to install", multiple=True, optional=True
        )
    ]

    def handle(self):
        callback(command=self)
        pre_download = self.option("pre-download")
        # Typing manually because pylance detect it as Any
        languages: list[str] = self.argument("language")
        # Get installed voicepacks
        language_objects = []
        for language in languages:
            language = language.lower()
            try:
                language_objects.append(VoicePackLanguage[language.capitalize()])
            except KeyError:
                try:
                    language_objects.append(VoicePackLanguage.from_remote_str(language))
                except ValueError:
                    self.line_error(f"<error>Invalid language: {language}</error>")
        if len(language_objects) == 0:
            self.line_error(
                "<error>No valid languages specified, you must specify a language to install</error>"
            )
            return
        progress = utils.ProgressIndicator(self)
        progress.start("Fetching install package information... ")
        try:
            game_info = State.game.get_remote_game(pre_download=pre_download)
        except Exception as e:
            progress.finish(
                f"<error>Fetching failed with following error: {e} \n{traceback.format_exc()}</error>"
            )
            return
        progress.finish(
            "<comment>Installation information fetched successfully.</comment>"
        )
        if not self.confirm("Do you want to install the specified voicepacks?"):
            self.line("<error>Installation aborted.</error>")
            return
        # Voicepack update
        for remote_voicepack in game_info.major.audio_pkgs:
            if remote_voicepack.language not in language_objects:
                continue
            self.line(
                f"Downloading install package for language: <comment>{remote_voicepack.language.name}</comment>... "
            )
            archive_file = State.game.cache.joinpath(PurePath(remote_voicepack.url).name)
            try:
                download_result = utils.download(
                    remote_voicepack.url, archive_file, file_len=remote_voicepack.size
                )
            except Exception as e:
                self.line_error(f"<error>Couldn't download package: {e}</error>")
                return
            if not download_result:
                self.line_error("<error>Download failed.</error>")
                return
            self.line("Download completed.")
            progress = utils.ProgressIndicator(self)
            progress.start("Installing package...")
            try:
                State.game.install_archive(archive_file)
            except Exception as e:
                progress.finish(
                    f"<error>Couldn't apply package: {e} \n{traceback.format_exc()}</error>"
                )
                return
            progress.finish(
                f"<comment>Package applied for language {remote_voicepack.language.name}.</comment>"
            )
        self.line(
            f"The voicepacks have been installed to version: <comment>{State.game.get_version_str()}</comment>"
        )


class VoicepackUpdate(Command):
    name = "genshin voicepack update"
    description = (
        "Updates the specified installed voicepacks, if not specified, updates all"
    )
    options = default_options + [
        option(
            "auto-repair", "R", description="Automatically repair the game if needed"
        ),
        option("pre-download", description="Pre-download the game if available"),
        option(
            "from-version", description="Update from a specific version", flag=False
        ),
    ]
    arguments = [
        argument(
            "language", description="Languages to update", multiple=True, optional=True
        )
    ]

    def handle(self):
        callback(command=self)
        auto_repair = self.option("auto-repair")
        pre_download = self.option("pre-download")
        from_version = self.option("from-version")
        # Typing manually because pylance detect it as Any
        languages: list[str] = self.argument("language")
        if auto_repair:
            self.line("<comment>Auto-repair is enabled.</comment>")
        if from_version:
            self.line(f"Updating from version: <comment>{from_version}</comment>")
            State.game.version_override = from_version
        # Get installed voicepacks
        if len(languages) == 0:
            self.line(
                "<comment>No languages specified, updating all installed voicepacks...</comment>"
            )
        installed_voicepacks = State.game.get_installed_voicepacks()
        if len(languages) > 0:
            languages = [x.lower() for x in languages]
            # Support both English and en-us and en
            installed_voicepacks = [
                x
                for x in installed_voicepacks
                if x.name.lower() in languages
                or x.value.lower() in languages
                or x.name.lower()[:2] in languages
            ]
        installed_voicepacks_str = [
            f"<comment>{str(x.name)}</comment>" for x in installed_voicepacks
        ]
        self.line(f"Updating voicepacks: {', '.join(installed_voicepacks_str)}")
        progress = utils.ProgressIndicator(self)
        progress.start("Checking for updates... ")
        try:
            update_diff = State.game.get_update(pre_download=pre_download)
            game_info = State.game.get_remote_game(pre_download=pre_download)
        except Exception as e:
            progress.finish(
                f"<error>Update checking failed with following error: {e} \n{traceback.format_exc()}</error>"
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
        # Voicepack update
        for remote_voicepack in update_diff.voice_packs:
            if remote_voicepack.language not in installed_voicepacks:
                continue
            # Voicepack is installed, update it
            self.line(
                f"Downloading update package for language: <comment>{remote_voicepack.language.name}</comment>... "
            )
            archive_file = State.game.cache.joinpath(remote_voicepack.name)
            try:
                download_result = utils.download(
                    remote_voicepack.path, archive_file, file_len=update_diff.size
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
                State.game.apply_update_archive(
                    archive_file=archive_file, auto_repair=auto_repair
                )
            except Exception as e:
                progress.finish(
                    f"<error>Couldn't apply update: {e} \n{traceback.format_exc()}</error>"
                )
                return
            progress.finish(
                f"<comment>Update applied for language {remote_voicepack.language.name}.</comment>"
            )
        set_version_config(self=self)
        self.line(
            f"The game has been updated to version: <comment>{State.game.get_version_str()}</comment>"
        )


class GetVersionCommand(Command):
    name = "genshin version"
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


class InstallCommand(Command):
    name = "genshin install"
    description = (
        "Installs the latest version of the game to the specified path (default: current directory). "
        + "Note that this will not install the default voicepack (English), you need to install it manually."
    )
    options = default_options + [
        option("pre-download", description="Pre-download the game if available"),
    ]

    def handle(self):
        callback(command=self)
        pre_download = self.option("pre-download")
        progress = utils.ProgressIndicator(self)
        progress.start("Fetching install package information... ")
        try:
            game_info = State.game.get_remote_game(pre_download=pre_download)
        except Exception as e:
            progress.finish(
                f"<error>Fetching failed with following error: {e} \n{traceback.format_exc()}</error>"
            )
            return
        progress.finish(
            "<comment>Installation information fetched successfully.</comment>"
        )
        if not self.confirm("Do you want to install the game?"):
            self.line("<error>Installation aborted.</error>")
            return
        self.line("Downloading install package...")
        first_pkg_out_path = None
        for game_pkg in game_info.major.game_pkgs:
            out_path = State.game.cache.joinpath(PurePath(game_pkg.url).name)
            if not first_pkg_out_path:
                first_pkg_out_path = out_path
            try:
                download_result = utils.download(
                    game_pkg.url, out_path, file_len=game_pkg.size
                )
            except Exception as e:
                self.line_error(
                    f"<error>Couldn't download install package: {e}</error>"
                )
                return
            if not download_result:
                self.line_error("<error>Download failed.</error>")
                return
        self.line("Download completed.")
        progress = utils.ProgressIndicator(self)
        progress.start("Installing package...")
        try:
            State.game.install_archive(first_pkg_out_path)
        except Exception as e:
            progress.finish(
                f"<error>Couldn't install package: {e} \n{traceback.format_exc()}</error>"
            )
            return
        progress.finish("<comment>Package applied for the base game.</comment>")
        self.line("Setting version config... ")
        State.game.version_override = game_info.major.version
        set_version_config()
        State.game.version_override = None
        self.line(
            f"The game has been installed to version: <comment>{State.game.get_version_str()}</comment>"
        )


class UpdateCommand(Command):
    name = "genshin update"
    description = "Updates the local game if available"
    options = default_options + [
        option(
            "auto-repair", "R", description="Automatically repair the game if needed"
        ),
        option("pre-download", description="Pre-download the game if available"),
        option(
            "from-version", description="Update from a specific version", flag=False
        ),
    ]

    def handle(self):
        callback(command=self)
        auto_repair = self.option("auto-repair")
        pre_download = self.option("pre-download")
        from_version = self.option("from-version")
        if auto_repair:
            self.line("<comment>Auto-repair is enabled.</comment>")
        if from_version:
            self.line(f"Updating from version: <comment>{from_version}</comment>")
            State.game.version_override = from_version
        progress = utils.ProgressIndicator(self)
        progress.start("Checking for updates... ")
        try:
            update_diff = State.game.get_update(pre_download=pre_download)
            game_info = State.game.get_remote_game(pre_download=pre_download)
        except Exception as e:
            progress.finish(
                f"<error>Update checking failed with following error: {e} \n{traceback.format_exc()}</error>"
            )
            return
        if update_diff is None or isinstance(game_info.major, str | None):
            progress.finish("<comment>Game is already updated.</comment>")
            return
        progress.finish("<comment>Update available.</comment>")
        self.line(
            f"The current version is: <comment>{State.game.get_version_str()}</comment>"
        )
        self.line(
            f"The latest version is: <comment>{game_info.major.version}</comment>"
        )
        if not self.confirm("Do you want to update the game?"):
            self.line("<error>Update aborted.</error>")
            return
        self.line("Downloading update package...")
        update_game_url = update_diff.game_pkgs[0].url
        out_path = State.game.cache.joinpath(PurePath(update_game_url).name)
        try:
            download_result = utils.download(
                update_game_url, out_path, file_len=update_diff.game_pkgs[0].size
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
                f"<error>Couldn't apply update: {e} \n{traceback.format_exc()}</error>"
            )
            return
        progress.finish("<comment>Update applied for base game.</comment>")
        # Get installed voicepacks
        installed_voicepacks = State.game.get_installed_voicepacks()
        # Voicepack update
        for remote_voicepack in update_diff.audio_pkgs:
            if remote_voicepack.language not in installed_voicepacks:
                continue
            # Voicepack is installed, update it
            archive_file = State.game.cache.joinpath(
                PurePath(remote_voicepack.url).name
            )
            self.line(
                f"Downloading update package for voicepack language '{remote_voicepack.language.name}'..."
            )
            try:
                download_result = utils.download(
                    remote_voicepack.url, archive_file, file_len=remote_voicepack.size
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
                State.game.apply_update_archive(
                    archive_file=archive_file, auto_repair=auto_repair
                )
            except Exception as e:
                progress.finish(
                    f"<error>Couldn't apply update: {e} \n{traceback.format_exc()}</error>"
                )
                return
            progress.finish(
                f"<comment>Update applied for language {remote_voicepack.language.name}.</comment>"
            )
        self.line("Setting version config... ")
        State.game.version_override = game_info.major.version
        set_version_config()
        State.game.version_override = None
        self.line(
            f"The game has been updated to version: <comment>{State.game.get_version_str()}</comment>"
        )


class RepairCommand(Command):
    name = "genshin repair"
    description = "Tries to repair the local game"
    options = default_options

    def handle(self):
        callback(command=self)
        self.line(
            "This command will try to repair the game by downloading missing/broken files."
        )
        self.line(
            "There will be no progress available, so please be patient and just wait."
        )
        if not self.confirm(
            "Do you want to repair the game (this will take a long time!)?"
        ):
            self.line("<error>Repairation aborted.</error>")
            return
        progress = utils.ProgressIndicator(self)
        progress.start("Repairing game files (no progress available)... ")
        try:
            State.game.repair_game()
        except Exception as e:
            progress.finish(
                f"<error>Repairation failed with following error: {e} \n{traceback.format_exc()}</error>"
            )
            return
        progress.finish("<comment>Repairation completed.</comment>")


class InstallDownloadCommand(Command):
    name = "genshin install download"
    description = (
        "Downloads the latest version of the game. "
        + "Note that this will not download the default voicepack (English), you need to download it manually."
    )
    options = default_options + [
        option("pre-download", description="Pre-download the game if available"),
    ]

    def handle(self):
        callback(command=self)
        pre_download = self.option("pre-download")
        progress = utils.ProgressIndicator(self)
        progress.start("Fetching install package information... ")
        try:
            game_info = State.game.get_remote_game(pre_download=pre_download)
        except Exception as e:
            progress.finish(
                f"<error>Fetching failed with following error: {e} \n{traceback.format_exc()}</error>"
            )
            return
        progress.finish(
            "<comment>Installation information fetched successfully.</comment>"
        )
        if not self.confirm("Do you want to download the game?"):
            self.line("<error>Download aborted.</error>")
            return
        self.line("Downloading install package...")
        first_pkg_out_path = None
        for game_pkg in game_info.major.game_pkgs:
            out_path = State.game.cache.joinpath(PurePath(game_pkg.url).name)
            if not first_pkg_out_path:
                first_pkg_out_path = out_path
            try:
                download_result = utils.download(
                    game_pkg.url, out_path, file_len=game_pkg.size
                )
            except Exception as e:
                self.line_error(
                    f"<error>Couldn't download install package: {e}</error>"
                )
                return
            if not download_result:
                self.line_error("<error>Download failed.</error>")
                return
        self.line("Download completed.")


class UpdateDownloadCommand(Command):
    name = "genshin update download"
    description = "Download the update for the local game if available"
    options = default_options + [
        option(
            "auto-repair", "R", description="Automatically repair the game if needed"
        ),
        option("pre-download", description="Pre-download the game if available"),
        option(
            "from-version", description="Update from a specific version", flag=False
        ),
    ]

    def handle(self):
        callback(command=self)
        auto_repair = self.option("auto-repair")
        pre_download = self.option("pre-download")
        from_version = self.option("from-version")
        if auto_repair:
            self.line("<comment>Auto-repair is enabled.</comment>")
        if from_version:
            self.line(f"Updating from version: <comment>{from_version}</comment>")
            State.game.version_override = from_version
        progress = utils.ProgressIndicator(self)
        progress.start("Checking for updates... ")
        try:
            update_diff = State.game.get_update(pre_download=pre_download)
            game_info = State.game.get_remote_game(pre_download=pre_download)
        except Exception as e:
            progress.finish(
                f"<error>Update checking failed with following error: {e} \n{traceback.format_exc()}</error>"
            )
            return
        if update_diff is None or isinstance(game_info.major, str | None):
            progress.finish("<comment>Game is already updated.</comment>")
            return
        progress.finish("<comment>Update available.</comment>")
        self.line(
            f"The current version is: <comment>{State.game.get_version_str()}</comment>"
        )
        self.line(
            f"The latest version is: <comment>{game_info.major.version}</comment>"
        )
        if not self.confirm("Do you want to download the update?"):
            self.line("<error>Download aborted.</error>")
            return
        self.line("Downloading update package...")
        update_game_url = update_diff.game_pkgs[0].url
        out_path = State.game.cache.joinpath(PurePath(update_game_url).name)
        try:
            download_result = utils.download(
                update_game_url, out_path, file_len=update_diff.game_pkgs[0].size
            )
        except Exception as e:
            self.line_error(
                f"<error>Couldn't download update: {e} \n{traceback.format_exc()}</error>"
            )
            return

        if not download_result:
            self.line_error("<error>Download failed.</error>")
            return
        self.line("Download completed.")
        # Get installed voicepacks
        installed_voicepacks = State.game.get_installed_voicepacks()
        # Voicepack update
        for remote_voicepack in update_diff.audio_pkgs:
            if remote_voicepack.language not in installed_voicepacks:
                continue
            # Voicepack is installed, update it
            archive_file = State.game.cache.joinpath(
                PurePath(remote_voicepack.url).name
            )
            self.line(
                f"Downloading update package for voicepack language '{remote_voicepack.language.name}'..."
            )
            try:
                download_result = utils.download(
                    remote_voicepack.url, archive_file, file_len=remote_voicepack.size
                )
            except Exception as e:
                self.line_error(f"<error>Couldn't download update: {e}</error>")
                return
            if not download_result:
                self.line_error("<error>Download failed.</error>")
                return
            self.line("Download completed.")


class ApplyInstallArchive(Command):
    name = "genshin install apply-archive"
    description = "Applies the install archive"
    arguments = [argument("path", description="Path to the install archive")]
    options = default_options

    def handle(self):
        callback(command=self)
        install_archive = self.argument("path")
        progress = utils.ProgressIndicator(self)
        progress.start("Applying install package...")
        try:
            State.game.install_archive(install_archive)
        except Exception as e:
            progress.finish(
                f"<error>Couldn't apply package: {e} \n{traceback.format_exc()}</error>"
            )
            return
        progress.finish("<comment>Package applied.</comment>")
        set_version_config(self=self)


class ApplyUpdateArchive(Command):
    name = "genshin update apply-archive"
    description = "Applies the update archive to the local game"
    arguments = [argument("path", description="Path to the update archive")]
    options = default_options + [
        option(
            "auto-repair", "R", description="Automatically repair the game if needed"
        ),
    ]

    def handle(self):
        callback(command=self)
        update_archive = self.argument("path")
        auto_repair = self.option("auto-repair")
        progress = utils.ProgressIndicator(self)
        progress.start("Applying update package...")
        try:
            State.game.apply_update_archive(update_archive, auto_repair=auto_repair)
        except Exception as e:
            progress.finish(
                f"<error>Couldn't apply update: {e} \n{traceback.format_exc()}</error>"
            )
            return
        progress.finish("<comment>Update applied.</comment>")
        set_version_config()


commands = [
    ApplyInstallArchive,
    ApplyUpdateArchive,
    GetVersionCommand,
    InstallCommand,
    InstallDownloadCommand,
    RepairCommand,
    UpdateCommand,
    UpdateDownloadCommand,
    VoicepackInstall,
    VoicepackList,
    VoicepackListInstalled,
    VoicepackUpdate,
]
