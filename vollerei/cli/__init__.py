from cleo.application import Application
from vollerei.cli import hsr

application = Application()
for command in hsr.commands:
    application.add(command)


def run():
    application.run()
