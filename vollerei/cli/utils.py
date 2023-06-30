no_confirm = False
silent_message = False


def ask(question: str):
    if no_confirm:
        print(question + " [Y/n]: Y")
        return True
    while True:
        answer = input(question + " [Y/n]: ")
        if answer.lower().strip() in ["y", "yes", ""]:
            return True
        # Pacman way, treat all other answers as no
        else:
            return False


def msg(*args, **kwargs):
    """
    Print but silentable
    """
    if silent_message:
        return
    print(*args, **kwargs)
