import platform
import subprocess
from zipfile import ZipFile
import requests
from io import BytesIO
from shutil import which
from vollerei.constants import HDIFFPATCH_GIT_URL
from vollerei.paths import tools_data_path
from vollerei.utils.hdiffpatch.exceptions import (
    HPatchZPatchError,
    NotInstalledError,
    PlatformNotSupportedError,
)


class HDiffPatch:
    """
    Quick wrapper around HDiffPatch binaries

    Mostly copied from worthless-launcher
    """

    def __init__(self):
        self._hdiff = tools_data_path.joinpath("hdiffpatch")
        self._hdiff.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _get_platform_arch():
        processor = platform.machine()
        match platform.system():
            case "Windows":
                match processor:
                    case "i386":
                        return "windows32"
                    case "x86_64":
                        return "windows64"
                    case "AMD64":
                        return "windows64"
                    case "arm":
                        return "windows_arm32"
                    case "arm64":
                        return "windows_arm64"
            case "Linux":
                match processor:
                    case "i386":
                        return "linux32"
                    case "x86_64":
                        return "linux64"
                    case "arm":
                        return "linux_arm32"
                    case "arm64":
                        return "linux_arm64"
            case "Darwin":
                return "macos"

        # TODO: Add support for Android & other architectures

        # Rip BSD they need to use Linux compatibility layer to run this
        # (or use Wine if they prefer that)
        raise PlatformNotSupportedError(
            "Only Windows, Linux and macOS are supported by HDiffPatch"
        )

    def _get_binary(self, exec_name: str, recurse=None) -> str:
        if which(exec_name):
            return exec_name
        if platform.system() == "Windows" and not exec_name.endswith(".exe"):
            exec_name += ".exe"
        if self._hdiff.exists() and any(self._hdiff.iterdir()):
            file = self._hdiff.joinpath(self._get_platform_arch(), exec_name)
            if file.exists():
                if platform.system() != "Windows":
                    file.chmod(0o755)
                return str(file)
        if recurse is None:
            recurse = 3
        elif recurse == 0:
            raise NotInstalledError(
                "HDiffPatch is not installed and can't be automatically installed"
            )
        else:
            recurse -= 1
        self.download()
        return self._get_binary(exec_name=exec_name, recurse=recurse)

    def hpatchz(self) -> str | None:
        return self._get_binary("hpatchz")

    def patch_file(self, in_file, out_file, patch_file):
        try:
            subprocess.check_call([self.hpatchz(), "-f", in_file, patch_file, out_file])
        except subprocess.CalledProcessError as e:
            raise HPatchZPatchError("Patch error") from e

    def _get_latest_release_info(self) -> dict:
        split = HDIFFPATCH_GIT_URL.split("/")
        repo = split[-1]
        owner = split[-2]
        rsp = requests.get(
            "https://api.github.com/repos/{}/{}/releases/latest".format(owner, repo),
            params={"Headers": "Accept: application/vnd.github.v3+json"},
        )
        rsp.raise_for_status()
        archive_processor = self._get_platform_arch()
        for asset in rsp.json()["assets"]:
            if not asset["name"].endswith(".zip"):
                continue
            if archive_processor not in asset["name"]:
                continue
            return asset

    def get_latest_release_url(self):
        asset = self._get_latest_release_info()
        return asset["browser_download_url"]

    def get_latest_release_name(self):
        asset = self._get_latest_release_info()
        return asset["name"]

    def download(self):
        """
        Download the latest release of HDiffPatch.
        """
        url = self.get_latest_release_url()
        if not url:
            raise RuntimeError("Unable to find latest release")
        file = BytesIO()
        with requests.get(url, stream=True) as r:
            for chunk in r.iter_content(chunk_size=32768):
                file.write(chunk)
        with ZipFile(file) as z:
            z.extractall(self._hdiff)
