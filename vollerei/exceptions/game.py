from vollerei.exceptions import VollereiError


class GameError(VollereiError):
    """Base class for exceptions in related to the game installation."""

    pass


class GameNotInstalledError(GameError):
    """Game is not installed."""

    pass


class GameAlreadyUpdatedError(GameError):
    """Game is already updated."""

    pass


class GameAlreadyInstalledError(GameError):
    """Game is already installed."""

    pass


class ScatteredFilesNotAvailableError(GameError):
    """Scattered files are not available."""

    pass


class GameNotUpdatedError(GameError):
    """Game is not updated."""

    pass


class PreDownloadNotAvailable(GameError):
    """Pre-download version is not available."""

    pass
