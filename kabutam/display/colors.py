from kabutam.config import get_color_scheme

RED = "\033[31m"
GREEN = "\033[32m"
BOLD = "\033[1m"
RESET = "\033[0m"


def colorise_profit(value: float, text: str) -> str:
    scheme = get_color_scheme()

    if scheme == "none" or value == 0:
        return text

    if scheme == "japan":
        color = RED if value > 0 else GREEN
    else:
        color = GREEN if value > 0 else RED

    return f"{BOLD}{color}{text}{RESET}"
