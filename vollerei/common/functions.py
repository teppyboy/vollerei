import concurrent.futures
import json
import hashlib
import py7zr
from io import IOBase
from pathlib import Path
from vollerei.abc.launcher.game import GameABC
from vollerei.exceptions.game import RepairError
from vollerei.utils import HDiffPatch, HPatchZPatchError


_hdiff = HDiffPatch()


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
    # archive = zipfile.ZipFile(archive_file, "r")
    archive = py7zr.SevenZipFile(archive_file, "r")
    # Get files list (we don't want to extract all of them)
    files = archive.namelist()
    # Don't extract these files (they're useless and if the game isn't patched then
    # it'll raise 31-4xxx error in Genshin)
    for file in ["deletefiles.txt", "hdifffiles.txt"]:
        try:
            files.remove(file)
        except ValueError:
            pass
    # Think for me a better name for this variable
    txtfiles = archive.read(["deletefiles.txt", "hdifffiles.txt"])
    try:
        # miHoYo loves CRLF
        deletebytes = txtfiles["deletefiles.txt"].read()
        if deletebytes is bytes:
            deletebytes = deletebytes.decode()
        deletefiles = deletebytes.split("\r\n")
    except IOError:
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
    hdifffiles = []
    hdiffbytes = txtfiles["hdifffiles.txt"].read()
    if hdiffbytes is bytes:
        hdiffbytes = hdiffbytes.decode()
    for x in hdiffbytes.split("\r\n"):
        try:
            hdifffiles.append(json.loads(x.strip())["remoteName"])
        except json.JSONDecodeError:
            pass

    # Patch function
    def extract_and_patch(file, patch_file):
        patchpath = game.cache.joinpath(patch_file)
        # Delete old patch file if exists
        patchpath.unlink(missing_ok=True)
        # Extract patch file
        # Spaghetti code :(, fuck my eyes.
        archive.extract(game.temppath, [patch_file])
        file = file.rename(file.with_suffix(file.suffix + ".bak"))
        try:
            _hdiff.patch_file(file, file.with_suffix(""), patchpath)
        except HPatchZPatchError:
            if auto_repair:
                try:
                    game.repair_file(game.path.joinpath(file.with_suffix("")))
                except Exception:
                    # Let the game download the file.
                    file.rename(file.with_suffix(""))
                else:
                    file.unlink()
            else:
                # Let the game download the file.
                file.rename(file.with_suffix(""))
            return
        finally:
            patchpath.unlink()
        # Remove old file, since we don't need it anymore.
        file.unlink()

    def extract_or_repair(file: str):
        # Extract file
        try:
            archive.extract(game.path, [file])
        except Exception as e:
            # Repair file
            if not auto_repair:
                raise e
            game.repair_file(game.path.joinpath(file))

    # Multi-threaded patching
    patch_jobs = []
    for file_str in hdifffiles:
        file = game.path.joinpath(file_str)
        if not file.exists():
            # Not patching since we don't have the file
            continue
        patch_file: str = file_str + ".hdiff"
        # Remove hdiff files from files list to extract
        files.remove(patch_file)
        patch_jobs.append([extract_and_patch, [file, patch_file]])

    # Create new ThreadPoolExecutor for patching
    patch_executor = concurrent.futures.ThreadPoolExecutor()
    for job in patch_jobs:
        patch_executor.submit(job[0], *job[1])
    patch_executor.shutdown(wait=True)

    # Extract files from archive after we have filtered out the patch files
    # Using ProcessPoolExecutor instead of archive.extractall() because
    # archive.extractall() can crash with large archives, and it doesn't
    # handle broken files.
    # ProcessPoolExecutor is faster than ThreadPoolExecutor, and it shouldn't 
    # cause any problems here.
    extract_executor = concurrent.futures.ProcessPoolExecutor()
    for file in files:
        extract_executor.submit(extract_or_repair, file)
    extract_executor.shutdown(wait=True)

    # Close the archive
    archive.close()


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
