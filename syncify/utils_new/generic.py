import re
from datetime import datetime
from typing import Tuple, Mapping, List

sort_ignore_words = ["The", "A"]


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


def flatten_nested(nested: Mapping, previous: list = None) -> List:
    if previous is None:
        previous = []

    if isinstance(nested, dict):
        for value in nested.values():
            flatten_nested(value, previous)
    elif isinstance(nested, list):
        previous.extend(nested)

    return previous
