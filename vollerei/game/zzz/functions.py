from vollerei.abc.launcher.game import GameABC


def get_version(game: GameABC) -> tuple[int, int, int]:
    """
    Gets the current installed game version.

    Credits to An Anime Team for the code that does the magic:
    https://github.com/an-anime-team/anime-game-core/blob/main/src/games/zzz/game.rs#L49

    If the above method fails, it'll fallback to read the config.ini file
    for the version, which is not recommended (as described in
    `get_version_config()` docs)

    This returns (0, 0, 0) if the version could not be found
    (usually indicates the game is not installed), and in fact `is_installed()` uses
    this method to check if the game is installed too.

    Returns:
        tuple[int, int, int]: The version as a tuple of integers.
    """

    data_file = game.data_folder().joinpath("globalgamemanagers")
    if not data_file.exists():
        return game.get_version_config()

    def bytes_to_int(byte_array: list[bytes]) -> int:
        bytes_as_int = int.from_bytes(byte_array, byteorder="big")
        actual_int = bytes_as_int - 48  # 48 is the ASCII code for 0
        return actual_int

    version_bytes: list[list[bytes]] = [[], [], []]
    version_ptr = 0
    correct = True
    try:
        with data_file.open("rb") as f:
            f.seek(4000)
            for byte in f.read(10000):
                match byte:
                    case 0:
                        if (
                            correct
                            and len(version_bytes[0]) > 0
                            and len(version_bytes[1]) > 0
                            and len(version_bytes[2]) > 0
                        ):
                            found_version = tuple(
                                bytes_to_int(i) for i in version_bytes
                            )
                            return found_version
                        version_bytes = [[], [], []]
                        version_ptr = 0
                        correct = True
                    case b".":
                        version_ptr += 1
                        if version_ptr > 2:
                            correct = False
                    case _:
                        if correct and byte in b"0123456789":
                            version_bytes[version_ptr].append(byte)
                        else:
                            correct = False
    except Exception:
        pass
    # Fallback to config.ini
    return game.get_version_config()
