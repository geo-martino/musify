import os
import pyfiglet
import random
import re
from collections import Counter
from typing import Any, Optional, Iterable, Collection, Tuple, Mapping, List, TypeVar, Union


sort_ignore_words = frozenset(["The", "A"])

T = TypeVar('T')
UnionList = Union[T, List[T]]
Number = Union[int, float]


def make_list(data: Any) -> Optional[List]:
    """Safely turn any object into a list unless None"""
    if isinstance(data, list):
        return data
    elif isinstance(data, set):
        return list(data)

    return [data] if data is not None else None


def strip_ignore_words(value: str, words: Collection[str] = sort_ignore_words) -> Tuple[bool, str]:
    """
    Remove ignorable words from a string.

    :returns: Tuple (True if the string starts with some special character, the formatted string)
    """
    if not value:
        return False, value

    new_value = value
    not_special = not any(value.startswith(c) for c in list('!"£$%^&*()_+-=…'))

    for word in words:
        new_value = re.sub(f"^{word} ", "", value)
        if new_value != value:
            break

    return not_special, new_value


def flatten_nested(nested: Mapping, previous: List = None) -> List:
    """Flatten a nested set of maps to a single list"""
    if previous is None:
        previous = []

    if isinstance(nested, dict):
        for key, value in nested.items():
            flatten_nested(value, previous=previous)
    elif isinstance(nested, list):
        previous.extend(nested)
    else:
        previous.append(nested)

    return previous


def limit_value(value: Number, floor: Number = 1, ceil: Number = 50) -> Number:
    """Limit a given ``value`` to always be between some ``floor`` and ``ceil``"""
    return max(min(value, ceil), floor)


def chunk(values: List[Any], size: int) -> List[List[Any]]:
    """Chunk a list of ``values`` into a list of lists of equal ``size``"""
    chunked = [values[i: i + size] for i in range(0, len(values), size)]
    return [c for c in chunked if c]


def get_most_common_values(values: Iterable[Any]) -> List[Any]:
    """Get an ordered list of the most common values for a given collection of ``values``"""
    return [x[0] for x in Counter(values).most_common()]


def get_user_input(text: Optional[str] = None) -> str:
    """Print formatted dialog with optional text and get the user's input."""
    return input(f"\33[93m{text}\33[0m | ").strip()


###########################################################################
## Syncify branding
###########################################################################
# noinspection SpellCheckingInspection
def print_logo():
    """Pretty print the Syncify logo in the centre of the terminal"""
    fonts = ["basic", "broadway", "chunky", "doom", "drpepper", "epic", "hollywood", "isometric1", "isometric2",
             "isometric3", "isometric4", "larry3d", "shadow", "slant", "speed", "standard", "univers", "whimsy"]
    colours = [91, 93, 92, 94, 96, 95]
    if bool(random.getrandbits(1)):
        colours.reverse()

    cols = os.get_terminal_size().columns
    figlet = pyfiglet.Figlet(font=random.choice(fonts), direction=0, justify="left", width=cols)

    text = figlet.renderText("SYNCIFY").rstrip().split("\n")
    text_width = max(len(line) for line in text)
    indent = int((cols - text_width) / 2)

    for i, line in enumerate(text, random.randint(0, len(colours))):
        print(f"{' ' * indent}\33[1;{colours[i % len(colours)]}m{line}\33[0m")
    print()


def print_line(text: str = "", line_char: str = "-"):
    """Print an aligned line with the given text in the centre of the terminal"""
    text = text.replace("_", " ").title()
    cols = os.get_terminal_size().columns

    text = f" {text} " if text else ""
    amount_left = (cols - len(text)) // 2
    output_len = amount_left * 2 + len(text)
    amount_right = amount_left + (1 if output_len < cols else 0)
    print(f"\33[1;96m{line_char * amount_left}\33[95m{text}\33[1;96m{line_char * amount_right}\33[0m\n")


def print_time(seconds: float):
    """Print the time in minutes and seconds in the centre of the terminal"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    text = f"{mins} mins {secs} secs"

    cols = os.get_terminal_size().columns
    indent = int((cols - len(text)) / 2)

    print(f"\33[1;95m{' ' * indent}{text}\33[0m")
