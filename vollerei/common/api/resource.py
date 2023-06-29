"""
Class wrapper for API endpoint /resource
"""


class Segment:
    path: str
    md5: str
    # str -> int and checked if int is 0 then None
    package_size: int | None


class VoicePack:
    """
    Voice pack information

    `name` maybe converted from `path` if the server returns empty string.

    Attributes:
        TODO
    """

    language: str
    name: str
    path: str
    # str -> int
    size: int
    md5: str
    # str -> int
    package_size: int


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


class Latest:
    """
    Latest game resource information

    `name` maybe converted from `path` if the server returns empty string,
    and if `path` is empty too then it'll convert the name from the first
    segment of `segments` list.

    Attributes:
        TODO
    """

    name: str
    version: str
    path: str
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


class Game:
    latest: Latest
    diffs: list[Diff]


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


class LauncherPlugin:
    plugins: list[Plugin]
    # str -> int
    version: int


class DeprecatedPackage:
    name: str
    md5: str


class DeprecatedFile:
    path: str
    # str but checked for empty string
    md5: str | None


class Data:
    """
    Data class for /resource endpoint
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
