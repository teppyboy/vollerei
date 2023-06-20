import subprocess
from pathlib import Path


__all__ = ["exec_su", "write_text", "append_text"]


def exec_su(args, stdin: str = None):
    """Execute a command using pkexec (friendly gui)"""
    if not Path("/usr/bin/pkexec").exists():
        raise FileNotFoundError("pkexec not found.")
    proc = subprocess.Popen(
        args, shell=True, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL
    )
    if stdin:
        proc.stdin.write(stdin.encode())
        proc.stdin.close()
    proc.wait()
    match proc.returncode:
        case 127:
            raise OSError("Authentication failed.")
        case 128:
            raise RuntimeError("User cancelled the authentication.")

    return proc


def write_text(text, path: str | Path):
    """Write text to a file using pkexec (friendly gui)"""
    if isinstance(path, Path):
        path = str(path)
    exec_su(f'pkexec tee "{path}"', stdin=text)


def append_text(text, path: str | Path):
    """Append text to a file using pkexec (friendly gui)"""
    if isinstance(path, Path):
        path = str(path)
    exec_su(f'pkexec tee -a "{path}"', stdin=text)
