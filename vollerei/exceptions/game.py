from vollerei.exceptions import VollereiError


class GameError(VollereiError):
    """Base class for exceptions in related to the game installation."""

    pass


class GameNotInstalledError(GameError):
    """Exception raised when the game is not installed."""

    pass
