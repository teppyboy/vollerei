import requests
import platform
from zipfile import ZipFile
from io import BytesIO
from pathlib import Path

match platform.system():
    case "Linux":
        from vollerei.utils.linux import append_text
    case _:

        def append_text(text: str, path: Path) -> None:
            raise NotImplementedError(
                "append_text is not implemented for this platform"
            )


# Re-exports
from vollerei.utils.git import Git
from vollerei.utils.xdelta3 import Xdelta3


__all__ = ["Git", "Xdelta3", "download_and_extract"]


def download_and_extract(url: str, path: Path) -> None:
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
