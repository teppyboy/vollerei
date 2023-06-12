import subprocess
from pathlib import Path
from shutil import which
from vollerei.utils.git.exceptions import GitCloneError, GitNotInstalled


class Git:
    """
    Quick wrapper around git binary
    """

    def __init__(self) -> None:
        pass

    @staticmethod
    def check_git():
        """
        Check for git installation, if not found raise GitNotInstalled
        """
        if not which("git"):
            raise GitNotInstalled("git is not installed")

    def pull_or_clone(self, url: str, path: str = None) -> None:
        self.check_git()
        """
        Pulls or clones a git repository
        
        If the repository already exists and the url matches, it'll be pulled.
        """
        if path is None:
            path = Path.cwd().joinpath(Path(url).stem)
        try:
            origin_url = subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"], cwd=path
            ).decode()
            if origin_url != url:
                raise subprocess.CalledProcessError
            subprocess.check_call(["git", "pull"], cwd=path)
        except subprocess.CalledProcessError:
            try:
                subprocess.check_call(["git", "clone", url, path])
            except subprocess.CalledProcessError as e:
                raise GitCloneError(
                    f"Failed to clone or update repository {url} to {path}"
                ) from e
