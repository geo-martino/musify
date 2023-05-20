import re
from collections import Counter
from typing import Any, Optional, Iterable, Collection
from typing import Tuple, Mapping, List, TypeVar, Union

from .logger import Logger

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
