from configparser import ConfigParser
from pathlib import Path


class ConfigFile(ConfigParser):
    path: Path

    def __init__(self, path, **kwargs):
        super().__init__(**kwargs)
        self.path = Path(path)
        self.read(self.path)

    def save(self):
        with self.path.open("w") as f:
            self.write(f)
