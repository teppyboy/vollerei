"""
Class wrapper for API endpoint /resource
"""


from vollerei.common.enums import VoicePackLanguage


class Segment:
    """
    A segment of the game archive.

    Attributes:
        path (str): Segment download path.
        md5 (str): Segment md5 checksum.
        package_size (int | None): Segment package size.
    """

    path: str
    md5: str
    # str -> int and checked if int is 0 then None
    package_size: int | None

    def __init__(self, path: str, md5: str, package_size: int | None) -> None:
        self.path = path
        self.md5 = md5
        self.package_size = package_size

    @staticmethod
    def from_dict(data: dict) -> "Segment":
        return Segment(
            data["path"],
            data["md5"],
            int(data["package_size"])
            if data["package_size"] and data["package_size"] != "0"
            else None,
        )


class VoicePack:
    """
    Voice pack information

    `name` maybe converted from `path` if the server returns empty string.

    Attributes:
        language (VoicePackLanguage): Language of the voice pack.
        name (str): Voice pack archive name.
        path (str): Voice pack download path.
        size (int): Voice pack size.
        md5 (str): Voice pack md5 checksum.
        package_size (int): Voice pack package size.
    """

    language: VoicePackLanguage
    name: str
    path: str
    # str -> int
    size: int
    md5: str
    # str -> int
    package_size: int

    def __init__(
        self,
        language: VoicePackLanguage,
        name: str,
        path: str,
        size: int,
        md5: str,
        package_size: int,
    ) -> None:
        self.language = language
        self.name = name
        self.path = path
        self.size = size
        self.md5 = md5
        self.package_size = package_size

    @staticmethod
    def from_dict(data: dict) -> "VoicePack":
        return VoicePack(
            VoicePackLanguage.from_remote_str(data["language"]),
            data["name"],
            data["path"],
            int(data["size"]),
            data["md5"],
            int(data["package_size"]),
        )


class Diff:
    """
    Game resource diff from a version to latest information

    Attributes:
        TODO
    """

    name: str
    version: str
    path: str
    # str -> int
    size: int
    md5: str
    is_recommended_update: bool
    voice_packs: list[VoicePack]
    # str -> int
    package_size: int

    def __init__(
        self,
        name: str,
        version: str,
        path: str,
        size: int,
        md5: str,
        is_recommended_update: bool,
        voice_packs: list[VoicePack],
        package_size: int,
    ) -> None:
        self.name = name
        self.version = version
        self.path = path
        self.size = size
        self.md5 = md5
        self.is_recommended_update = is_recommended_update
        self.voice_packs = voice_packs
        self.package_size = package_size

    @staticmethod
    def from_dict(data: dict) -> "Diff":
        return Diff(
            data["name"],
            data["version"],
            data["path"],
            int(data["size"]),
            data["md5"],
            data["is_recommended_update"],
            [VoicePack.from_dict(i) for i in data["voice_packs"]],
            int(data["package_size"]),
        )


class Latest:
    """
    Latest game resource information

    `name` maybe converted from `path` if the server returns empty string,
    and if `path` is empty too then it'll convert the name from the first
    segment of `segments` list.

    `path` maybe None if the server returns empty string, in that case
    you'll have to download the game using `segments` list and merge them.

    `voice_packs` will be empty for Star Rail, they force you to download
    in-game instead.

    `decompressed_path` is useful for repairing game files by only having
    to re-download the corrupted files.

    `segments` is a list of game archive segments, you'll have to download
    them and merge them together to get the full game archive. Not available
    on Star Rail.

    Attributes:
        name (str): Game archive name.
        version (str): Game version in the archive.
        path (str | None): Game archive download path.
        size (int): Game archive size in bytes.
        md5 (str): Game archive MD5 checksum.
        entry (str): Game entry file (e.g. GenshinImpact.exe).
        voice_packs (list[VoicePack]): Game voice packs.
        decompressed_path (str | None): Game archive decompressed path.
        segments (list[Segment]): Game archive segments.
        package_size (int): Game archive package size in bytes.
    """

    name: str
    version: str
    path: str | None
    # str -> int
    size: int
    md5: str
    entry: str
    voice_packs: list[VoicePack]
    # str but checked for empty string
    decompressed_path: str | None
    segments: list[Segment]
    # str -> int
    package_size: int

    def __init__(
        self,
        name: str,
        version: str,
        path: str,
        size: int,
        md5: str,
        entry: str,
        voice_packs: list[VoicePack],
        decompressed_path: str | None,
        segments: list[Segment],
        package_size: int,
    ) -> None:
        self.name = name
        self.version = version
        self.path = path
        self.size = size
        self.md5 = md5
        self.entry = entry
        self.voice_packs = voice_packs
        self.decompressed_path = decompressed_path
        self.segments = segments
        self.package_size = package_size

    @staticmethod
    def from_dict(data: dict) -> "Latest":
        if data["name"] == "":
            if data["path"] == "":
                data["name"] = data["segments"][0]["path"].split("/")[-1]
            else:
                data["name"] = data["path"].split("/")[-1]
        return Latest(
            data["name"],
            data["version"],
            data["path"] if data["path"] != "" else None,
            int(data["size"]),
            data["md5"],
            data["entry"],
            [VoicePack.from_dict(i) for i in data["voice_packs"]],
            data["decompressed_path"] if data["decompressed_path"] != "" else None,
            [Segment.from_dict(i) for i in data["segments"]],
            int(data["package_size"]),
        )


class Game:
    latest: Latest
    diffs: list[Diff]

    def __init__(self, latest: Latest, diffs: list[Diff]) -> None:
        self.latest = latest
        self.diffs = diffs

    @staticmethod
    def from_dict(data: dict) -> "Game":
        return Game(
            Latest.from_dict(data["latest"]), [Diff.from_dict(i) for i in data["diffs"]]
        )


class Plugin:
    name: str
    # str but checked for empty string
    version: str | None
    path: str
    # str -> int
    size: int
    md5: str
    # str but checked for empty string
    entry: str | None
    # str -> int
    package_size: int

    def __init__(
        self,
        name: str,
        version: str | None,
        path: str,
        size: int,
        md5: str,
        entry: str | None,
        package_size: int,
    ) -> None:
        self.name = name
        self.version = version
        self.path = path
        self.size = size
        self.md5 = md5
        self.entry = entry
        self.package_size = package_size

    @staticmethod
    def from_dict(data: dict) -> "Plugin":
        return Plugin(
            data["name"],
            data["version"] if data["version"] != "" else None,
            data["path"],
            int(data["size"]),
            data["md5"],
            data["entry"] if data["entry"] != "" else None,
            int(data["package_size"]),
        )


class LauncherPlugin:
    plugins: list[Plugin]
    # str -> int
    version: int

    def __init__(self, plugins: list[Plugin], version: int) -> None:
        self.plugins = plugins
        self.version = version

    @staticmethod
    def from_dict(data: dict) -> "LauncherPlugin":
        return LauncherPlugin(
            [Plugin.from_dict(i) for i in data["plugins"]], int(data["version"])
        )


class DeprecatedPackage:
    name: str
    md5: str

    def __init__(self, name: str, md5: str) -> None:
        self.name = name
        self.md5 = md5

    @staticmethod
    def from_dict(data: dict) -> "DeprecatedPackage":
        return DeprecatedPackage(data["name"], data["md5"])


class DeprecatedFile:
    path: str
    # str but checked for empty string
    md5: str | None

    def __init__(self, path: str, md5: str | None) -> None:
        self.path = path
        self.md5 = md5

    @staticmethod
    def from_dict(data: dict) -> "DeprecatedFile":
        return DeprecatedFile(data["path"], data["md5"] if data["md5"] != "" else None)


class Resource:
    """
    Data class for /resource endpoint

    I'm still unclear about `force_update` and `sdk` attributes, so I'll
    leave them as None for now.

    Attributes:
        game (Game): Game resource information.
        plugin (LauncherPlugin): Launcher plugin information.
        web_url (str): Game official launcher web URL.
        force_update (None): Not used by official launcher I guess?
        pre_download_game (Game | None): Pre-download game resource information.
        deprecated_packages (list[DeprecatedPackage]): Deprecated game packages.
        sdk (None): Maybe for Bilibili version of Genshin?
        deprecated_files (list[DeprecatedFile]): Deprecated game files.
    """

    # I'm generous enough to convert the string into int
    # for you guys, wtf Mihoyo?
    game: Game
    # ?? Mihoyo for plugin["plugins"] which is a list of Plugin objects
    plugin: LauncherPlugin
    web_url: str
    # ?? Mihoyo
    force_update: None
    # Will be a Game object if a pre-download is available.
    pre_download_game: Game | None
    deprecated_packages: list[DeprecatedPackage]
    # Maybe a SDK for Bilibili version in Genshin?
    sdk: None
    deprecated_files: list[DeprecatedFile]

    def __init__(
        self,
        game: Game,
        plugin: Plugin,
        web_url: str,
        force_update: None,
        pre_download_game: Game | None,
        deprecated_packages: list[DeprecatedPackage],
        sdk: None,
        deprecated_files: list[DeprecatedFile],
    ) -> None:
        self.game = game
        self.plugin = plugin
        self.web_url = web_url
        self.force_update = force_update
        self.pre_download_game = pre_download_game
        self.deprecated_packages = deprecated_packages
        self.sdk = sdk
        self.deprecated_files = deprecated_files

    @staticmethod
    def from_dict(json: dict) -> "Resource":
        return Resource(
            Game.from_dict(json["game"]),
            LauncherPlugin.from_dict(json["plugin"]),
            json["web_url"],
            json["force_update"],
            Game.from_dict(json["pre_download_game"])
            if json["pre_download_game"]
            else None,
            [DeprecatedPackage.from_dict(x) for x in json["deprecated_packages"]],
            json["sdk"],
            [DeprecatedFile.from_dict(x) for x in json["deprecated_files"]],
        )
