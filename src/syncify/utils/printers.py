import os
import random
from collections.abc import Sequence, Collection

import pyfiglet

from syncify import PROGRAM_NAME

# noinspection SpellCheckingInspection
LOGO_FONTS = (
    "basic", "broadway", "chunky", "doom", "drpepper", "epic", "hollywood", "isometric1", "isometric2",
    "isometric3", "isometric4", "larry3d", "shadow", "slant", "speed", "standard", "univers", "whimsy"
)
LOGO_COLOURS = (91, 93, 92, 94, 96, 95)


def print_logo(fonts: Sequence[str] = LOGO_FONTS, colours: Collection[int] = LOGO_COLOURS) -> None:
    """Pretty print the Syncify logo in the centre of the terminal"""
    colours = list(colours)
    if bool(random.getrandbits(1)):
        colours.reverse()

    cols = os.get_terminal_size().columns
    # noinspection SpellCheckingInspection
    figlet = pyfiglet.Figlet(font=random.choice(fonts), direction=0, justify="left", width=cols)

    text = figlet.renderText(PROGRAM_NAME.upper()).rstrip().split("\n")
    text_width = max(len(line) for line in text)
    indent = int((cols - text_width) / 2)

    for i, line in enumerate(text, random.randint(0, len(colours))):
        print(f"{' ' * indent}\33[1;{colours[i % len(colours)]}m{line}\33[0m")
    print()


def print_line(text: str = "", line_char: str = "-") -> None:
    """Print an aligned line with the given text in the centre of the terminal"""
    text = text.replace("_", " ").title()
    cols = os.get_terminal_size().columns

    text = f" {text} " if text else ""
    amount_left = (cols - len(text)) // 2
    output_len = amount_left * 2 + len(text)
    amount_right = amount_left + (1 if output_len < cols else 0)
    print(f"\33[1;96m{line_char * amount_left}\33[95m{text}\33[1;96m{line_char * amount_right}\33[0m\n")


def print_time(seconds: float) -> None:
    """Print the time in minutes and seconds in the centre of the terminal"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    text = f"{mins} mins {secs} secs"

    cols = os.get_terminal_size().columns
    indent = int((cols - len(text)) / 2)

    print(f"\33[1;95m{' ' * indent}{text}\33[0m")
