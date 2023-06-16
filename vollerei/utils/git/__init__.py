import subprocess
import requests
import json
from pathlib import Path
from shutil import which, rmtree
from urllib.parse import urlparse
from vollerei.constants import utils_cache_path
from vollerei.utils.git.exceptions import GitCloneError
from vollerei.utils import download_and_extract


class Git:
    """
    Quick wrapper around git binary (or simulate git if git is not installed)

    Simulate git because Windows users may not have git installed.
    """

    def __init__(self) -> None:
        self._cache = utils_cache_path.joinpath("git")
        self._cache.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def is_installed() -> bool:
        """
        Check for git installation

        Returns:
            bool: True if git is installed, False otherwise
        """
        if not which("git"):
            return False
        return True

    def _is_gitea(self, netloc: str) -> bool:
        """
        Check if the url is a Gitea server
        """
        rsp = requests.get(f"https://{netloc}/api/v1/meta")
        try:
            data: dict = rsp.json()
        except json.JSONDecodeError:
            return False
        if not data.get("version"):
            return False
        return True

    def _gitea_get_latest_commit(self, netloc: str, path: str) -> str:
        """
        Get latest commit from a Gitea repository
        """
        # Params to speed up request
        rsp = requests.get(
            f"https://{netloc}/api/v1/repos/{path}/commits",
            params={"limit": 1, "stat": False, "verification": False, "files": False},
        )
        try:
            data: list = rsp.json()
        except json.JSONDecodeError:
            return None
        return data[0]["sha"]

    def _download_and_extract_zip(self, url: str, path: Path) -> None:
        download_and_extract(url, path)
        path.joinpath(".git/PLEASE_INSTALL_GIT").touch()

    def _clone(self, url: str, path: str = None) -> None:
        """
        "Clone" a git repository without git
        """
        if Path(url).suffix == ".git":
            url = url[:-4]
        url_info = urlparse(url)
        netloc = url_info.netloc
        if path is None:
            path = Path.cwd().joinpath(Path(url).stem)
        path: Path = Path(path)
        if self._is_gitea(netloc):
            commit = self._gitea_get_latest_commit(netloc, url_info.path)
            self._download_and_extract_zip(
                f"https://{netloc}/api/v1/repos/{url_info.path}/archive/{commit}.zip",
                path,
            )
        elif netloc == "notabug.org":
            # NotABug workaround
            # Still guessing the branch is master here...
            branch = "master"
            self._download_and_extract_zip(
                f"https://notabug.org/{url_info.path}/archive/{branch}.zip", path
            )
        else:
            raise NotImplementedError

    def get_latest_release_dl(self, url: str) -> list[str]:
        dl = []
        if Path(url).suffix == ".git":
            url = url[:-4]
        url_info = urlparse(url)
        netloc = url_info.netloc
        if self._is_gitea(netloc):
            rsp = requests.get(
                f"https://{netloc}/api/v1/repos/{url_info.path}/releases/latest",
            )
            rsp.raise_for_status()
            data = rsp.json()
            for asset in data["assets"]:
                dl.append(asset["browser_download_url"])
        else:
            raise NotImplementedError

    def pull_or_clone(self, url: str, path: str = None) -> None:
        """
        Pulls or clones a git repository

        If the repository already exists and the url matches, it'll be pulled.
        """
        if not self.is_installed():
            # Git is not installed, we need to simulate it
            self._clone(url, path)
            return
        if path is None:
            if Path(url).suffix == ".git":
                path = Path.cwd().joinpath(Path(url).stem)
            else:
                path = Path.cwd().joinpath(Path(url).name)
        path_as_path = Path(path)
        if path_as_path.joinpath(".git/PLEASE_INSTALL_GIT").exists():
            # This is a fake .git directory we created.
            # We need to clone the repository
            rmtree(path)
        try:
            if not path_as_path.exists():
                raise subprocess.CalledProcessError
            origin_url = subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"], cwd=path
            ).decode()
            if origin_url != url:
                raise subprocess.CalledProcessError
            subprocess.check_call(["git", "pull"], cwd=path)
        except subprocess.CalledProcessError:
            if path_as_path.exists():
                rmtree(path)
            try:
                subprocess.check_call(["git", "clone", url, path])
            except subprocess.CalledProcessError as e:
                raise GitCloneError(
                    f"Failed to clone or update repository {url} to {path}"
                ) from e
