class GitError(Exception):
    """Base class for git errors"""

    pass


class GitCloneError(GitError):
    """Raised when git clone fails"""

    pass


class GitPullError(GitError):
    """Raised when git pull fails"""

    pass


class GitNotInstalled(GitError):
    """Raised when git is not installed"""

    pass
