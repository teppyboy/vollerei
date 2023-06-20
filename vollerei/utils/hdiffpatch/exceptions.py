class HDiffPatchError(Exception):
    """Base class for HDiffPatch errors"""

    pass


class HPatchZError(HDiffPatchError):
    """Raised when hpatchz fails"""

    pass


class NotInstalledError(HPatchZError):
    """Raised when HDiffPatch is not installed"""

    pass


class HPatchZPatchError(HPatchZError):
    """Raised when hpatchz patch fails"""

    pass
