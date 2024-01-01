class HDiffPatchError(Exception):
    """Base class for HDiffPatch errors"""

    pass


class HPatchZError(HDiffPatchError):
    """Raised when hpatchz fails"""

    pass


class HPatchZPatchError(HPatchZError):
    """Raised when hpatchz patch fails"""

    pass


class NotInstalledError(HPatchZError):
    """Raised when HDiffPatch is not installed"""

    pass


class PlatformNotSupportedError(HPatchZError):
    """Raised when HDiffPatch is not available for your platform"""

    pass
