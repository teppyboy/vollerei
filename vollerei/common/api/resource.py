from vollerei.common.enums import VoicePackLanguage
from typing import Union


class Game:
    def __init__(self, id: str, biz: str):
        self.id = id
        self.biz = biz

    @staticmethod
    def from_dict(data: dict) -> "Game":
        return Game(id=data["id"], biz=data["biz"])


class GamePackage:
    def __init__(self, url: str, md5: str, size: int, decompressed_size: int):
        self.url = url
        self.md5 = md5
        self.size = size
        self.decompressed_size = decompressed_size

    @staticmethod
    def from_dict(data: list[dict]) -> list["GamePackage"]:
        game_pkgs = []
        for pkg in data:
            game_pkgs.append(
                GamePackage(
                    url=pkg["url"],
                    md5=pkg["md5"],
                    size=int(pkg["size"]),
                    decompressed_size=int(pkg["decompressed_size"]),
                )
            )
        return game_pkgs


class AudioPackage:
    def __init__(
        self,
        language: VoicePackLanguage,
        url: str,
        md5: str,
        size: int,
        decompressed_size: int,
    ):
        self.language = language
        self.url = url
        self.md5 = md5
        self.size = size
        self.decompressed_size = decompressed_size

    @staticmethod
    def from_dict(data: list[dict]) -> "AudioPackage":
        audio_pkgs = []
        for pkg in data:
            audio_pkgs.append(
                AudioPackage(
                    language=VoicePackLanguage.from_remote_str(pkg["language"]),
                    url=pkg["url"],
                    md5=pkg["md5"],
                    size=int(pkg["size"]),
                    decompressed_size=int(pkg["decompressed_size"]),
                )
            )
        return audio_pkgs


class Major:
    def __init__(
        self,
        version: str,
        game_pkgs: list[GamePackage],
        audio_pkgs: list[AudioPackage],
        res_list_url: str,
    ):
        self.version = version
        self.game_pkgs = game_pkgs
        self.audio_pkgs = audio_pkgs
        self.res_list_url = res_list_url

    @staticmethod
    def from_dict(data: dict) -> "Major":
        return Major(
            version=data["version"],
            game_pkgs=GamePackage.from_dict(data["game_pkgs"]),
            audio_pkgs=AudioPackage.from_dict(data["audio_pkgs"]),
            res_list_url=data["res_list_url"],
        )


# Currently patch has the same fields as major
Patch = Major


class Main:
    def __init__(self, major: Major, patches: list[Patch]):
        self.major = major
        self.patches = patches

    @staticmethod
    def from_dict(data: dict) -> "Main":
        return Main(
            major=Major.from_dict(data["major"]),
            patches=[Patch.from_dict(x) for x in data["patches"]],
        )


class PreDownload:
    def __init__(self, major: Major | str | None, patches: list[Patch]):
        self.major = major
        self.patches = patches

    # Union to fix the typing issue.
    @staticmethod
    def from_dict(data: dict | None) -> Union["PreDownload", None]:
        # pre_download can be null in the server for certain games
        # e.g. HI3:
        # "pre_download": null
        # while in GI it is the following:
        # "pre_download": {
        #   "major": null,
        #   "patches": []
        # }
        if data is None:
            return None
        return PreDownload(
            major=(
                data["major"]
                if isinstance(data["major"], str | None)
                else Major.from_dict(data["major"])
            ),
            patches=[Patch.from_dict(x) for x in data["patches"]],
        )


# Why miHoYo uses the same name "game_packages" for this big field and smol field
class GameInfo:
    def __init__(self, game: Game, main: Main, pre_download: PreDownload):
        self.game = game
        self.main = main
        self.pre_download = pre_download

    @staticmethod
    def from_dict(data: dict) -> "GameInfo":
        return GameInfo(
            game=Game.from_dict(data["game"]),
            main=Main.from_dict(data["main"]),
            pre_download=PreDownload.from_dict(data["pre_download"]),
        )


def from_dict(data: dict) -> list[GameInfo]:
    game_pkgs = []
    for pkg in data["game_packages"]:
        game_pkgs.append(GameInfo.from_dict(pkg))
    return game_pkgs
