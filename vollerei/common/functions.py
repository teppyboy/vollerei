import concurrent.futures
import json
import hashlib
import py7zr
import zipfile
from io import IOBase
from os import PathLike
from pathlib import Path
from shutil import move
from vollerei.abc.launcher.game import GameABC
from vollerei.common.api import resource
from vollerei.exceptions.game import (
    RepairError,
    GameAlreadyInstalledError,
    GameNotInstalledError,
    ScatteredFilesNotAvailableError,
)
from vollerei.utils import HDiffPatch, HPatchZPatchError, download


_hdiff = HDiffPatch()


def _extract_files(
    archive: py7zr.SevenZipFile | zipfile.ZipFile, files, path: PathLike
):
    if isinstance(archive, py7zr.SevenZipFile):
        # .7z archive
        archive.extract(path, files)
    else:
        # .zip archive
        archive.extractall(path, files)


def _open_archive(file: Path | IOBase) -> py7zr.SevenZipFile | zipfile.ZipFile:
    archive: py7zr.SevenZipFile | zipfile.ZipFile = None
    try:
        archive = py7zr.SevenZipFile(file, "r")
    except py7zr.exceptions.Bad7zFile:
        # Try to open it as a zip file
        try:
            archive = zipfile.ZipFile(file, "r")
        except zipfile.BadZipFile:
            raise ValueError("Archive is not a valid 7z or zip file.")
    return archive


def apply_update_archive(
    game: GameABC, archive_file: Path | IOBase, auto_repair: bool = True
) -> None:
    """
    Applies an update archive to the game, it can be the game update or a
    voicepack update.

    Because this function is shared for all games, you should use the game's
    `apply_update_archive()` method instead, which additionally applies required
    methods for that game.
    """
    # Most code here are copied from worthless-launcher.
    # worthless-launcher uses asyncio for multithreading while this one uses
    # ThreadPoolExecutor, probably better for this use case.

    # We need `game` for the path and `auto_repair` for the auto repair option.

    # Install HDiffPatch
    _hdiff.hpatchz()

    # Open archive
    def reset_if_py7zr(archive):
        if isinstance(archive, py7zr.SevenZipFile):
            archive.reset()

    archive = _open_archive(archive_file)

    # Get files list (we don't want to extract all of them)
    files = archive.namelist()
    # Don't extract these files (they're useless and if the game isn't patched then
    # it'll raise 31-4xxx error in Genshin)
    for file in ["deletefiles.txt", "hdifffiles.txt", "hdiffmap.json"]:
        try:
            files.remove(file)
        except ValueError:
            pass
    # Think for me a better name for this variable
    txtfiles = None
    if isinstance(archive, py7zr.SevenZipFile):
        txtfiles = archive.read(["deletefiles.txt", "hdifffiles.txt", "hdiffmap.json"])
        # Reset archive to extract files
        archive.reset()
    try:
        # miHoYo loves CRLF
        if txtfiles is not None:
            deletebytes = txtfiles["deletefiles.txt"].read()
        else:
            deletebytes = archive.read("deletefiles.txt")
        if deletebytes is not str:
            # Typing
            deletebytes: bytes
            deletebytes = deletebytes.decode()
        deletefiles = deletebytes.split("\r\n")
    except (IOError, KeyError):
        pass
    else:
        for file_str in deletefiles:
            file = game.path.joinpath(file_str)
            if file == game.path:
                # Don't delete the game folder
                continue
            if not file.relative_to(game.path):
                # File is not in the game folder
                continue
            # Delete the file
            file.unlink(missing_ok=True)

    # hdiffpatch implementation
    # Read hdifffiles.txt to get the files to patch
    # Hdifffile format is [(source file, target file)]
    # While the patch file is named as target file + ".hdiff"
    hdifffiles: list[tuple[str, str]] = []
    new_hdiff_map = False
    if txtfiles is not None:
        old_hdiff_map = txtfiles.get("hdifffiles.txt")
        if old_hdiff_map is not None:
            hdiffbytes = old_hdiff_map.read()
        else:
            new_hdiff_map = True
            hdiffbytes = txtfiles["hdiffmap.json"].read()
    else:
        # Archive file must be a zip file
        if zipfile.Path(archive).joinpath("hdifffiles.txt").is_file():
            hdiffbytes = archive.read("hdifffiles.txt")
        else:
            new_hdiff_map = True
            hdiffbytes = archive.read("hdiffmap.json")
    if hdiffbytes is not str:
        # Typing
        hdiffbytes: bytes
        hdiffbytes = hdiffbytes.decode()
    if new_hdiff_map:
        mapping = json.loads(hdiffbytes)
        for diff in mapping["diff_map"]:
            hdifffiles.append((diff["source_file_name"], diff["target_file_name"]))
    else:
        for x in hdiffbytes.split("\r\n"):
            try:
                name = json.loads(x.strip())["remoteName"]
                hdifffiles.append((name, name))
            except json.JSONDecodeError:
                pass

    # Patch function
    def patch(source_file: Path, target_file: Path, patch_file: str):
        patch_path = game.cache.joinpath(patch_file)
        # Spaghetti code :(, fuck my eyes.
        bak_src_file = source_file.rename(
            source_file.with_suffix(source_file.suffix + ".bak")
        )
        try:
            _hdiff.patch_file(bak_src_file, target_file, patch_path)
        except HPatchZPatchError:
            if auto_repair:
                try:
                    # The game repairs file by downloading the latest file, in this case we want the target file
                    # instead of source file. Honestly I haven't tested this but I hope it works.
                    game.repair_file(target_file)
                except Exception:
                    # Let the game download the file.
                    bak_src_file.rename(file.with_suffix(""))
                else:
                    bak_src_file.unlink()
            else:
                # Let the game download the file.
                bak_src_file.rename(file.with_suffix(""))
            return
        else:
            # Remove old file, since we don't need it anymore.
            bak_src_file.unlink()
        finally:
            patch_path.unlink()

    # Multi-threaded patching
    patch_jobs = []
    patch_files = []
    for source_file, target_file in hdifffiles:
        source_path = game.path.joinpath(source_file)
        if not source_path.exists():
            # Not patching since we don't have the file
            continue
        target_path = game.path.joinpath(target_file)
        patch_file: str = target_file + ".hdiff"
        # Remove hdiff files from files list to extract
        files.remove(patch_file)
        # Add file to extract list
        patch_files.append(patch_file)
        patch_jobs.append([patch, [source_path, target_path, patch_file]])

    # Extract patch files to temporary dir
    _extract_files(archive, patch_files, game.cache)
    reset_if_py7zr(archive)  # For the next extraction
    # Create new ThreadPoolExecutor for patching
    patch_executor = concurrent.futures.ThreadPoolExecutor()
    for job in patch_jobs:
        patch_executor.submit(job[0], *job[1])
    patch_executor.shutdown(wait=True)

    # Extract files from archive after we have filtered out the patch files
    _extract_files(archive, files, game.path)

    # Close the archive
    archive.close()


def install_archive(game: GameABC, archive_file: Path | IOBase) -> None:
    """
    Applies an install archive to the game, it can be the game itself or a
    voicepack one.

    Because this function is shared for all games, you should use the game's
    `install_archive()` method instead, which additionally applies required
    methods for that game.
    """
    archive = _open_archive(archive_file)
    archive.extractall(game.path)
    archive.close()


def _repair_file(game: GameABC, file: PathLike, game_info: resource.Main) -> None:
    # .replace("\\", "/") is needed because Windows uses backslashes :)
    relative_file = file.relative_to(game.path)
    url = game_info.major.res_list_url + "/" + str(relative_file).replace("\\", "/")
    # Backup the file
    if file.exists():
        backup_file = file.with_suffix(file.suffix + ".bak")
        if backup_file.exists():
            backup_file.unlink()
        file.rename(backup_file)
        dest_file = file.with_suffix("")
    else:
        dest_file = file
    try:
        # Download the file
        temp_file = game.cache.joinpath(relative_file)
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading repair file {url} to {temp_file}")
        download(url, temp_file, overwrite=True, stream=True)
        # Move the file
        move(temp_file, dest_file)
        print("OK")
    except Exception as e:
        # Restore the backup
        print("Failed", e)
        if file.exists():
            file.rename(file.with_suffix(""))
        raise e
    # Delete the backup
    if file.exists():
        file.unlink(missing_ok=True)


def repair_files(
    game: GameABC,
    files: list[PathLike],
    pre_download: bool = False,
    game_info: resource.Game = None,
) -> None:
    """
    Repairs multiple game files.

    This will automatically handle backup and restore the file if the repair
    fails.

    Args:
        game (GameABC): The game to repair the files for.
        files (PathLike): The files to repair.
        pre_download (bool): Whether to get the pre-download version.
            Defaults to False.
    """
    if not game.is_installed():
        raise GameNotInstalledError("Game is not installed.")
    files_path = [Path(file) for file in files]
    for file in files_path:
        if not file.is_relative_to(game.path):
            raise ValueError("File is not in the game folder.")
    if not game_info:
        game_info = game.get_remote_game(pre_download=pre_download)
    if game_info.latest.decompressed_path is None:
        raise ScatteredFilesNotAvailableError("Scattered files are not available.")
    executor = concurrent.futures.ThreadPoolExecutor()
    for file in files_path:
        executor.submit(_repair_file, file, game=game_info)
        # self._repair_file(file, game=game)
    executor.shutdown(wait=True)


def repair_game(
    game: GameABC,
    pre_download: bool = False,
) -> None:
    """
    Tries to repair the game by reading "pkg_version" file and downloading the
    mismatched files from the server.

    Because this function is shared for all games, you should use the game's
    `repair_game()` method instead, which additionally applies required
    methods for that game.
    """
    # Most code here are copied from worthless-launcher.
    # worthless-launcher uses asyncio for multithreading while this one uses
    # ThreadPoolExecutor, probably better for this use case.
    if not game.is_installed():
        raise GameNotInstalledError("Game is not installed.")
    game_info = game.get_remote_game(pre_download=pre_download)
    pkg_version_file = game.path.joinpath("pkg_version")
    pkg_version: dict[str, dict[str, str]] = {}
    if not pkg_version_file.is_file():
        try:
            game.repair_file(game.path.joinpath("pkg_version"), game_info=game_info)
        except Exception as e:
            raise RepairError(
                "pkg_version file not found, most likely you need to download the full game again."
            ) from e
    with pkg_version_file.open("r") as f:
        for line in f.readlines():
            line = line.strip()
            if not line:
                continue
            line_json = json.loads(line)
            pkg_version[line_json["remoteName"]] = {
                "md5": line_json["md5"],
                "fileSize": line_json["fileSize"],
            }
    read_needed_files: list[Path] = []
    target_files: list[Path] = []
    repair_executor = concurrent.futures.ThreadPoolExecutor()
    for file in game.path.rglob("*"):
        # Ignore webCaches folder (because it's user data)
        if file.is_dir():
            continue
        if "webCaches" in str(file):
            continue

        def verify(file_path: Path):
            nonlocal target_files
            nonlocal pkg_version
            relative_path = file_path.relative_to(game.path)
            relative_path_str = str(relative_path).replace("\\", "/")
            # print(relative_path_str)
            # Wtf mihoyo, you build this game for Windows and then use Unix path separator :moyai:
            try:
                target_file = pkg_version.pop(relative_path_str)
                if target_file:
                    with file_path.open("rb", buffering=0) as f:
                        file_hash = hashlib.file_digest(f, "md5").hexdigest()
                    if file_hash == target_file["md5"]:
                        return
                    print(
                        f"Hash mismatch for {target_file['remoteName']} ({file_hash}; expected {target_file['md5']})"
                    )
                    target_files.append(file_path)
            except KeyError:
                # File not found in pkg_version
                read_needed_files.append(file_path)

        repair_executor.submit(verify, file)
    repair_executor.shutdown(wait=True)
    for file in read_needed_files:
        try:
            with file.open("rb", buffering=0) as f:
                # We only need to read 4 bytes to see if the file is readable or not
                f.read(4)
        except Exception:
            print(f"File '{file}' is corrupted.")
            target_files.append(file)
    # value not used for now
    for key, _ in pkg_version.items():
        target_file = game.path.joinpath(key)
        if target_file.is_file():
            continue
        print(f"{key} not found.")
        target_files.append(target_file)
    if not target_files:
        return
    print("Begin repairing files...")
    game.repair_files(target_files, game_info=game_info)
