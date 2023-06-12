from vollerei.exceptions import VollereiError


class PatcherError(VollereiError):
    """Base class for exceptions in related to the patcher."""

    pass


class VersionNotSupportedError(PatcherError):
    """Exception raised when the game version is not supported."""

    pass
