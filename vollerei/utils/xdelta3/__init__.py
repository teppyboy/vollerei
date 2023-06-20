import platform
import subprocess
import requests
from os import PathLike
from zipfile import ZipFile
from shutil import which
from vollerei.paths import tools_cache_path
from vollerei.utils.xdelta3.exceptions import (
    Xdelta3NotInstalledError,
    Xdelta3PatchError,
)


class Xdelta3:
    """
    Quick wrapper around xdelta3 binary
    """

    def __init__(self) -> None:
        self._xdelta3_path = tools_cache_path.joinpath("xdelta3")
        self._xdelta3_path.mkdir(parents=True, exist_ok=True)

    def _get_binary(self, recurse=None) -> str:
        if which("xdelta3"):
            return "xdelta3"
        if platform.system() == "Windows":
            for path in self._xdelta3_path.glob("*.exe"):
                return path
            if recurse is None:
                recurse = 3
            elif recurse == 0:
                raise Xdelta3NotInstalledError(
                    "xdelta3 is not installed and can't be automatically installed"
                )
            else:
                recurse -= 1
            self.download()
            return self.get_binary(recurse=recurse)
        raise Xdelta3NotInstalledError("xdelta3 is not installed")

    def get_binary(self) -> str:
        """
        Get xdelta3 binary
        """
        return self._get_binary()

    def download(self):
        """
        Download xdelta3 binary
        """
        url = None
        if platform.system() != "Windows":
            raise NotImplementedError(
                "xdelta3 binary is not available for this platform, please install it manually"  # noqa: E501
            )
        match platform.machine():
            case "AMD64":
                url = "https://github.com/jmacd/xdelta-gpl/releases/download/v3.1.0/xdelta3-3.1.0-x86_64.exe.zip"
            case "i386":
                url = "https://github.com/jmacd/xdelta-gpl/releases/download/v3.1.0/xdelta3-3.1.0-i686.exe.zip"
            case "i686":
                url = "https://github.com/jmacd/xdelta-gpl/releases/download/v3.1.0/xdelta3-3.1.0-i686.exe.zip"
        file = self._xdelta3_path.joinpath("xdelta3.zip")
        with requests.get(url, stream=True) as r:
            with open(file, "wb") as f:
                for chunk in r.iter_content(chunk_size=32768):
                    f.write(chunk)
        with ZipFile(file) as z:
            z.extractall(self._xdelta3_path)
        file.unlink()

    def patch_file(self, patch: PathLike, target: PathLike, output: PathLike):
        """
        Patch a file
        """
        try:
            subprocess.check_call(
                [self.get_binary(), "-d", "-s", patch, target, output]
            )
        except subprocess.CalledProcessError as e:
            raise Xdelta3PatchError(
                f"xdelta3 failed with exit code {e.returncode}"
            ) from e
