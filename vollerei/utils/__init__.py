import requests
import platform
import shutil
from zipfile import ZipFile
from io import BytesIO
from pathlib import Path

match platform.system():
    case "Linux":
        from vollerei.utils.linux import append_text
    case _:

        def append_text(text: str, path: Path) -> None:
            # Fallback to our own implementation
            # Will NOT work if we don't have permission to write to the file
            try:
                with path.open("a") as f:
                    f.write(text)
            except FileNotFoundError:
                with path.open(path, "w") as f:
                    f.write(text)
            except (PermissionError, OSError) as e:
                raise PermissionError(
                    "You don't have permission to write to the file."
                ) from e


# Re-exports
from vollerei.utils.git import Git
from vollerei.utils.xdelta3 import Xdelta3, Xdelta3NotInstalledError, Xdelta3PatchError
from vollerei.utils.xdelta3.exceptions import Xdelta3Error
from vollerei.utils.hdiffpatch import (
    HDiffPatch,
    HPatchZPatchError,
    NotInstalledError,
    PlatformNotSupportedError as HPatchZPlatformNotSupportedError,
)


__all__ = [
    "Git",
    "Xdelta3",
    "download_and_extract",
    "HDiffPatch",
    "write_hosts",
    "append_text_to_file",
    "Xdelta3Error",
    "Xdelta3NotInstalledError",
    "Xdelta3PatchError",
    "HPatchZPatchError",
    "NotInstalledError",
    "HPatchZPlatformNotSupportedError",
]


def download(
    url: str,
    out: Path,
    file_len: int = None,
    overwrite: bool = False,
    stream: bool = True,
) -> None:
    """
    Download to a path.

    Args:
        url (str): URL to download from.
        path (Path): Path to download to.
    """
    if overwrite:
        out.unlink(missing_ok=True)
    headers = {}
    mode = "a+b"
    if out.exists():
        cur_len = (out.stat()).st_size
        headers |= {"Range": f"bytes={cur_len}-{file_len if file_len else ''}"}
    else:
        mode = "w+b"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.touch()
    # Streaming, so we can iterate over the response.
    response = requests.get(url=url, headers=headers, stream=stream)
    if response.status_code == 416:
        print(f"File already downloaded: {out}")
        return
    response.raise_for_status()
    with open(out, mode) as file:
        shutil.copyfileobj(response.raw, file)
    return True


def download_and_extract(url: str, path: Path) -> None:
    """
    Download and extract a zip file to a path.

    Args:
        url (str): URL to download from.
        path (Path): Path to extract to.
    """
    rsp = requests.get(url, stream=True)
    rsp.raise_for_status()
    with BytesIO() as f:
        for chunk in rsp.iter_content(chunk_size=32768):
            f.write(chunk)
        f.seek(0)
        with ZipFile(f) as z:
            z.extractall(path)


def append_text_to_file(path: Path, text: str) -> None:
    try:
        with open(path, "a") as f:
            f.write(text)
    except FileNotFoundError:
        with open(path, "w") as f:
            f.write(text)
    except (PermissionError, OSError):
        append_text(text, path)


def write_hosts(hosts: list[str]) -> None:
    hosts_str = ""
    for line in hosts:
        hosts_str += f"0.0.0.0 {line}\n"
    match platform.system():
        case "Linux":
            append_text_to_file(Path("/etc/hosts"), hosts_str)
        case "Windows":
            append_text_to_file(
                Path("C:/Windows/System32/drivers/etc/hosts"), hosts_str
            )
