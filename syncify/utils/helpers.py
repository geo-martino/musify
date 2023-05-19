import re
from collections import Counter
from typing import Any, Optional, Iterable
from typing import Tuple, Mapping, List, TypeVar, Union

sort_ignore_words = ["The", "A"]

T = TypeVar('T')
UnionList = Union[T, List[T]]


def make_list(data: Any) -> Optional[List]:
    if isinstance(data, list):
        return data
    elif isinstance(data, set):
        return list(data)

    return [data] if data is not None else None


def strip_ignore_words(value: str) -> Tuple[bool, str]:
    if not value:
        return False, value

    new_value = value
    not_special = not any(value.startswith(c) for c in list('!"£$%^&*()_+-=…'))

    for word in sort_ignore_words:
        new_value = re.sub(f"^{word} ", "", value)
        if new_value != value:
            break

    return not_special, new_value


def flatten_nested(nested: Mapping, previous: List = None) -> List:
    if previous is None:
        previous = []

    if isinstance(nested, dict):
        for key, value in nested.items():
            flatten_nested(value, previous=previous)
    elif isinstance(nested, list):
        previous.extend(nested)

    return previous


def get_most_common_values(values: Iterable[Any]) -> List[Any]:
    """Get an ordered list of the most common values for a given collection of ``values``"""
    return [x[0] for x in Counter(values).most_common()]


def get_user_input(text: Optional[str] = None) -> str:
    """Print dialog with optional text and get the user's input."""
    return input(f"\33[93m{text}\33[0m | ").strip()
