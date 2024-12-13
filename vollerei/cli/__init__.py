from cleo.application import Application
from vollerei.cli import hsr, genshin

application = Application()
for command in hsr.commands + genshin.commands:
    application.add(command())


def run():
    application.run()
