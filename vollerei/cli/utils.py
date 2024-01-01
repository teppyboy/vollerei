from cleo.commands.command import Command
from threading import Thread
from time import sleep


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


def msg(*args, **kwargs):
    """
    Print but silentable
    """
    if silent_message:
        return
    print(*args, **kwargs)
