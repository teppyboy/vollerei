# Vollerei

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

An open-source launcher for anime games

## Installation

Assumming you have `pipx` installed, execute the following command:
```bash
pipx install git+https://git.tretrauit.me/tretrauit/vollerei --preinstall tqdm
```

## Why?

I've done [worthless-launcher](https://tretrauit.gitlab.io/worthless-launcher) for an open-world anime game, 
since I want to support other anime games and the launcher code is very messy, this launcher was made.

## Features

### Turn-based game
- [x] Cross-platform support
    > Tested on Windows and Linux myself, although should work on most major OSes where `HDiffPatch` is supported.
- [x] Does *not* require administrator/root privileges
    > Though if issues occur during installation/upgrading process, you can always try running the program with elevated privileges to fix them.
- [x] Download the game update (including pre-downloads if available)
- [x] Get the game version
- [x] Get installed voicepacks
- [x] Installation
- [x] Patch the game for unsupported platforms (with telemetry checking)
- [x] Repair the game (Smarter than the official launcher!)
- [x] Update the game
- [x] Update voicepacks 
- [ ] Uninstall the game (Just remove the game directory lol)
- [x] Voicepacks installation
#### Advanced features
- [x] Apply the update archives
- [x] Download the update archives
- [x] Easy to use API

### Other games
I haven't developed for them yet, but since most of the code is shared I'll do that when I have the motivation to do so.

~~Help me get motivated by going to https://paypal.me/tretrauit and send me a coffee lol~~

## Notes

This launcher tries to mimic the official launcher behaviour as much as possible but if a ban appears, I will
not be responsible for it. (*Turn-based game* have a ban wave already, see AAGL discord for more info)

## Alternatives

This launcher focuses on the API and CLI, for GUI-based launcher you may want to check out:

+ [An Anime Game Launcher](https://aagl.launcher.moe/) - That famous launcher for an open-world anime game.
+ [Yaagl](https://github.com/3Shain/yet-another-anime-game-launcher) - All in one launcher for MacOS.
+ [Honkers launcher](https://github.com/an-anime-team/honkers-launcher) - Another launcher for an anime game.
+ [Honkers Railway](https://github.com/an-anime-team/the-honkers-railway-launcher) - A launcher for a turn-based anime game.

## License

[MIT](./LICENSE)
