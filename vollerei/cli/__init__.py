from vollerei.cli import hsr
from vollerei.cli import utils
import typer


app = typer.Typer()
app.add_typer(hsr.app, name="hsr")

app.callback()


def callback(noconfirm: bool = False, silent: bool = False):
    """
    An open-source launcher for anime games.
    """
    utils.silent_message = silent
    if noconfirm:
        utils.no_confirm = noconfirm
