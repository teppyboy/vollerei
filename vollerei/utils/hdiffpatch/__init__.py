import platform
import subprocess
from zipfile import ZipFile
import requests
from io import BytesIO
from shutil import which
from vollerei.constants import HDIFFPATCH_GIT_URL
from vollerei.paths import tools_data_path


class HDiffPatch:
    def __init__(self):
        self._data = tools_data_path.joinpath("hdiffpatch")
        self._data.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _get_platform_arch():
        match platform.system():
            case "Windows":
                match platform.architecture()[0]:
                    case "32bit":
                        return "windows32"
                    case "64bit":
                        return "windows64"
            case "Linux":
                match platform.architecture()[0]:
                    case "32bit":
                        return "linux32"
                    case "64bit":
                        return "linux64"
            case "Darwin":
                return "macos"

        # Rip BSD they need to use Linux compatibility layer to run this
        # (or use Wine if they prefer that)
        raise RuntimeError("Only Windows, Linux and macOS are supported by HDiffPatch")

    def _get_exec(self, exec_name) -> str | None:
        if which(exec_name):
            return exec_name
        if not self.data_path.exists():
            return None
        if not any(self.data_path.iterdir()):
            return None
        platform_arch_path = self.data_path.joinpath(self._get_platform_arch())
        file = platform_arch_path.joinpath(exec_name)
        if file.exists():
            file.chmod(0o755)
            return str(file)

    def hpatchz(self) -> str | None:
        hpatchz_name = "hpatchz" + (".exe" if platform.system() == "Windows" else "")
        return self._get_exec(hpatchz_name)

    def patch_file(self, in_file, out_file, patch_file):
        hpatchz = self.hpatchz()
        if not hpatchz:
            raise RuntimeError("hpatchz executable not found")
        subprocess.check_call([hpatchz, "-f", in_file, patch_file, out_file])

    async def _get_latest_release_info(self) -> dict:
        split = HDIFFPATCH_GIT_URL.split("/")
        repo = split[-1]
        owner = split[-2]
        rsp = requests.get(
            "https://api.github.com/repos/{}/{}/releases/latest".format(owner, repo),
            params={"Headers": "Accept: application/vnd.github.v3+json"},
        )
        rsp.raise_for_status()
        for asset in (await rsp.json())["assets"]:
            if not asset["name"].endswith(".zip"):
                continue
            if "linux" in asset["name"]:
                continue
            if "windows" in asset["name"]:
                continue
            if "macos" in asset["name"]:
                continue
            if "android" in asset["name"]:
                continue
            return asset

    async def get_latest_release_url(self):
        asset = await self._get_latest_release_info()
        return asset["browser_download_url"]

    async def get_latest_release_name(self):
        asset = await self._get_latest_release_info()
        return asset["name"]

    async def download(self):
        """
        Download the latest release of HDiffPatch.
        """
        url = await self.get_latest_release_url()
        if not url:
            raise RuntimeError("Unable to find latest release")
        file = BytesIO()
        with requests.get(url, stream=True) as r:
            with open(file, "wb") as f:
                for chunk in r.iter_content(chunk_size=32768):
                    f.write(chunk)
        with ZipFile(file) as z:
            z.extractall(self._data)
