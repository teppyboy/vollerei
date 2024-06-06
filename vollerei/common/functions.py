import concurrent.futures
from io import IOBase
import json
import hashlib
from pathlib import Path
import zipfile
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
    archive = zipfile.ZipFile(archive_file, "r")
    # Get files list (we don't want to extract all of them)
    files = archive.namelist()
    # Don't extract these files (they're useless and if the game isn't patched then
    # it'll raise 31-4xxx error in Genshin)
    for file in ["deletefiles.txt", "hdifffiles.txt"]:
        try:
            files.remove(file)
        except ValueError:
            pass
    try:
        # miHoYo loves CRLF
        deletefiles = archive.read("deletefiles.txt").decode().split("\r\n")
    except IOError:
        pass
    else:
        for file_str in deletefiles:
            file = game.path.joinpath(file)
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
    for x in archive.read("hdifffiles.txt").decode().split("\r\n"):
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
        archive.extract(patch_file, game.temppath)
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

    def extract_or_repair(file):
        # Extract file
        try:
            archive.extract(file, game.path)
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
    # Using ThreadPoolExecutor instead of archive.extractall() because
    # archive.extractall() can crash with large archives, and it doesn't
    # handle broken files.
    extract_executor = concurrent.futures.ThreadPoolExecutor()
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
    pkg_version = []
    if not pkg_version_file.is_file():
        try:
            game.repair_file(game.path.joinpath("pkg_version"), game_info=game_info)
        except Exception as e:
            raise RepairError(
                "pkg_version file not found, most likely you need to download the full game again."
            ) from e
    else:
        with pkg_version_file.open("r") as f:
            for line in f.readlines():
                line = line.strip()
                if not line:
                    continue
                pkg_version.append(json.loads(line))
    repair_executor = concurrent.futures.ThreadPoolExecutor()
    for file in pkg_version:

        def repair(target_file, game_info):
            try:
                game.repair_file(target_file, game_info=game_info)
            except Exception as e:
                print(f"Failed to repair {target_file['remoteName']}: {e}")

        def verify_and_repair(target_file, game_info):
            file_path = game.path.joinpath(target_file["remoteName"])
            if not file_path.is_file():
                print(f"File {target_file['remoteName']} not found, repairing...")
                repair(file_path, game_info)
                return
            with file_path.open("rb", buffering=0) as f:
                file_hash = hashlib.file_digest(f, "md5").hexdigest()
            if file_hash != target_file["md5"]:
                print(
                    f"Hash mismatch for {target_file['remoteName']} ({file_hash}; expected {target_file['md5']})"
                )
                repair(file_path, game_info)

        # Single-threaded for now
        # verify_and_repair(file, game_info)
        repair_executor.submit(verify_and_repair, file, game_info)
    repair_executor.shutdown(wait=True)
