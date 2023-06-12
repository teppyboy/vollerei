class Xdelta3Error(Exception):
    """Base class for xdelta3 errors"""

    pass


class Xdelta3NotInstalledError(Xdelta3Error):
    """Raised when xdelta3 is not installed"""

    pass


class Xdelta3PatchError(Xdelta3Error):
    """Raised when xdelta3 patch fails"""

    pass
