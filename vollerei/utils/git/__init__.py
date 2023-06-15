import subprocess
import requests
import json
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from shutil import which, rmtree
from urllib.parse import urlparse
from vollerei.constants import utils_cache_path
from vollerei.utils.git.exceptions import GitCloneError


class Git:
    """
    Quick wrapper around git binary (or simulate git if git is not installed)

    Simulate git because Windows users may not have git installed.
    """

    def __init__(self) -> None:
        self._cache = utils_cache_path.joinpath("git")
        self._cache.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def is_installed():
        """
        Check for git installation, if not found raise GitNotInstalled
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
        if self._is_gitea(netloc):
            # Hardcoding the branch to master, because well :D
            file = BytesIO()
            rsp = requests.get(
                f"https://{netloc}/api/v1/repos/{url_info.path}/archive/master.zip",
                stream=True,
            )
            rsp.raise_for_status()
            with open(file, "wb") as f:
                for chunk in rsp.iter_content(chunk_size=32768):
                    f.write(chunk)
            zip_file = ZipFile(file)
            zip_file.extractall(path)
            with Path(path).joinpath(".git/PLEASE_INSTALL_GIT").open("w") as f:
                f.write(json.dumps({"type": "gitea", "netloc": netloc, "path": url_info.path}))
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
