from vollerei.exceptions import VollereiError


class PatcherError(VollereiError):
    """Base class for exceptions in related to the patcher."""

    pass


class VersionNotSupportedError(PatcherError):
    """Exception raised when the game version is not supported."""

    pass


class PatchingFailedError(PatcherError):
    """Exception raised when the patching failed."""

    pass


class PatchUpdateError(PatcherError):
    """Exception raised when the patch update failed."""

    pass


class UnpatchingFailedError(PatcherError):
    """Exception raised when the unpatching failed."""

    pass
