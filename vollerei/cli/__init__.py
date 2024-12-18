from cleo.application import Application
from vollerei.cli import commands

application = Application()
for command in commands.exports:
    application.add(command)


def run():
    application.run()
