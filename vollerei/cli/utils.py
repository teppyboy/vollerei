import requests
from cleo.commands.command import Command
from pathlib import Path
from threading import Thread
from time import sleep
from tqdm import tqdm


no_confirm = False
silent_message = False


def args_to_kwargs(args: list):
    """
    Convert a list of arguments to a dict of keyword arguments.
    """
    kwargs = {}
    cur_key = None
    for arg in args:
        if "--" == arg[:2]:
            arg_key = arg[2:].replace("-", "_")
            kwargs[arg_key] = True
            cur_key = arg_key
        elif cur_key:
            kwargs[cur_key] = arg
    return kwargs


class ProgressIndicator:
    def auto_advance(self):
        """
        Automatically advance the progress indicator.
        """
        while self.progress._started:
            self.progress.advance()
            sleep(self.progress._interval / 1000)

    def __init__(
        self, command: Command, interval: int = None, values: list[str] = None
    ):
        self.command = command
        if not interval:
            interval = 100
        if not values:
            values = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.progress = self.command.progress_indicator(
            interval=interval, values=values
        )
        self.thread = Thread(target=self.auto_advance)
        self.thread.daemon = True

    def start(self, message: str):
        """
        Start the progress indicator.
        """
        self.progress.start(message)
        self.thread.start()

    def finish(self, message: str, reset_indicator=False):
        """
        Finish the progress indicator.
        """
        self.progress.finish(message=message, reset_indicator=reset_indicator)


def download(url, out: Path, file_len: int = None, overwrite: bool = False) -> bool:
    if overwrite:
        out.unlink(missing_ok=True)
    headers = {}
    if out.exists():
        cur_len = (out.stat()).st_size
        headers |= {"Range": f"bytes={cur_len}-{file_len if file_len else ''}"}
    else:
        out.touch()
    # Streaming, so we can iterate over the response.
    response = requests.get(url=url, headers=headers, stream=True)
    if response.status_code == 416:
        return True
    response.raise_for_status()
    # Sizes in bytes.
    total_size = int(response.headers.get("content-length", 0))
    block_size = 32768

    with tqdm(total=total_size, unit="KB", unit_scale=True) as progress_bar:
        with out.open("ab") as file:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                file.write(data)

    if total_size != 0 and progress_bar.n != total_size:
        return False
    return True


def msg(*args, **kwargs):
    """
    Print but silentable
    """
    if silent_message:
        return
    print(*args, **kwargs)
