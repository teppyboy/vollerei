from enum import Enum


class VoicePackLanguage(Enum):
    Japanese = "ja-jp"
    Chinese = "zh-cn"
    Taiwanese = "zh-tw"
    Korean = "ko-kr"
    English = "en-us"

    @staticmethod
    def from_remote_str(s: str) -> "VoicePackLanguage":
        """
        Converts a language string from remote server to a VoicePackLanguage enum.
        """
        if s == "ja-jp":
            return VoicePackLanguage.Japanese
        elif s == "zh-cn":
            return VoicePackLanguage.Chinese
        elif s == "zh-tw":
            return VoicePackLanguage.Taiwanese
        elif s == "ko-kr":
            return VoicePackLanguage.Korean
        elif s == "en-us":
            return VoicePackLanguage.English
        else:
            raise ValueError(f"Invalid language string: {s}")
