no_confirm = False


def ask(question: str):
    if no_confirm:
        print(question + " [Y/n] Y")
        return True
    while True:
        answer = input(question + " [y/n] ")
        if answer.lower() in ["y", "yes"]:
            return True
        # Pacman way, treat all other answers as no
        else:
            return False
