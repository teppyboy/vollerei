from vollerei.exceptions import VollereiError


class GameError(VollereiError):
    """Base class for exceptions in related to the game installation."""

    pass


class GameNotInstalledError(GameError):
    """Game is not installed."""

    pass


class PreDownloadNotAvailable(GameError):
    """Pre-download version is not available."""

    pass
