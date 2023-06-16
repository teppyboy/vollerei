import requests
from zipfile import ZipFile
from io import BytesIO
from pathlib import Path

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
