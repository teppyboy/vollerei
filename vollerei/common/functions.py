import concurrent.futures
from io import IOBase
import json
from pathlib import Path
import zipfile
from vollerei.abc.launcher.game import GameABC
from vollerei.utils import HDiffPatch, HPatchZPatchError


_hdiff = HDiffPatch()


def apply_update_archive(
    game: GameABC, archive_file: Path | IOBase, auto_repair: bool = True
) -> None:
    """
    Applies an update archive to the game, it can be the game update or a
    voicepack update.

    Because this function is shared for all games, you should use the game's
    `apply_update_archive()` method instead.
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
        patchpath = game._cache.joinpath(patch_file)
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
