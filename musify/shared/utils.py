import re
from collections import Counter
from collections.abc import Iterable, Collection, MutableSequence, Mapping, MutableMapping
from typing import Any

from musify.shared.exception import MusifyTypeError, SafeDict
from musify.shared.types import Number


###########################################################################
## String
###########################################################################
def strip_ignore_words(value: str, words: Iterable[str] | None = frozenset(["The", "A"])) -> tuple[bool, str]:
    """
    Remove ignorable words from the beginning of a string.
    Useful for sorting collections strings with ignorable start words and/or special characters.
    Only removes the first word it finds at the start of the string.

    :return: Tuple of (True if the string starts with some special character, the formatted string)
    """
    if not value:
        return False, value

    special_chars = list('!"£$%^&*()_+-=…')
    special_start = any(value.startswith(c) for c in special_chars)
    value = re.sub(r"^\W+", "", value).strip()

    if not words:
        return not special_start, value

    new_value = value
    for word in words:
        new_value = re.sub(rf"^{word}\s+", "", value, flags=re.I)
        if new_value != value:
            break

    return not special_start, new_value


def safe_format_map[T](value: T, format_map: Mapping[str, Any]) -> T:
    """
    Apply a ``format_map`` to a given ``value`` ignoring missing keys.
    If ``value`` is a map, apply the ``format_map`` recursively.
    """
    if not isinstance(format_map, SafeDict):
        format_map = SafeDict(**format_map)

    if isinstance(value, MutableMapping):
        for k, v in value.items():
            value[k] = safe_format_map(v, format_map)
    elif isinstance(value, str) and '{' in value and '}' in value:
        value = value.format_map(format_map)
    return value


def get_max_width(values: Collection[Any], min_width: int = 15, max_width: int = 50) -> int:
    """Get max width of given list of ``values`` for column-aligned logging"""
    if len(values) == 0:
        return 0
    max_len = len(max(map(str, values), key=len))
    return limit_value(value=max_len + 1, floor=min_width, ceil=max_width)


def align_and_truncate(value: Any, max_width: int = 0, right_align: bool = False) -> str:
    """Align string with space padding. Truncate any string longer than max width with ..."""
    if max_width == 0:
        return value
    truncated = str(value)[:(max_width - 3)] + "..." if not right_align else "..." + str(value)[-(max_width - 3):]
    return f"{value if len(str(value)) < max_width else truncated:<{max_width}}"


###########################################################################
## Number
###########################################################################
def limit_value(value: Number, floor: Number = 1, ceil: Number = 50) -> Number:
    """Limit a given ``value`` to always be between some ``floor`` and ``ceil``"""
    return max(min(value, ceil), floor)


###########################################################################
## Collection
###########################################################################
def to_collection[T: (list, set, tuple)](data: Any, cls: type[T] = tuple) -> T | None:
    """
    Safely turn any object into a collection of a given type ``T``.
    Strings are converted to collections of size 1 where the first element is the string.
    Returns None if value is None.
    """
    if data is None or isinstance(data, cls):
        return data
    elif isinstance(data, Iterable) and not isinstance(data, str) and not isinstance(data, Mapping):
        return cls(data)
    elif cls is tuple:
        return (data,)
    elif cls is set:
        return {data}
    elif cls is list:
        return [data]
    raise MusifyTypeError(f"Unable to convert data to {cls.__name__} (data={data})")


def unique_list(value: Iterable[Any]) -> list[Any]:
    """
    Returns a copy of the given ``value`` that contains only unique elements.
    Useful for producing unique lists whilst preserving order.
    """
    unique = []
    for item in value:
        if item not in unique:
            unique.append(item)
    return unique


###########################################################################
## Mapping
###########################################################################
def flatten_nested[T: Any](nested: MutableMapping, previous: MutableSequence[T] | None = None) -> list[T]:
    """Flatten the final layers of the values of a nested map to a single list"""
    if previous is None:
        previous = []

    if isinstance(nested, MutableMapping):
        for key, value in nested.items():
            flatten_nested(value, previous=previous)
    elif isinstance(nested, (list, set, tuple)):
        previous.extend(nested)
    else:
        previous.append(nested)

    return previous


def merge_maps[T: MutableMapping](source: T, new: Mapping, extend: bool = True, overwrite: bool = False) -> T:
    """
    Recursively update a given ``source`` map in place with a ``new`` map.

    :param source: The source map.
    :param new: The new map with values to update for the source map.
    :param extend: When a value is a list and a list is already present in the source map, extend the list when True.
        When False, only replace the list if overwrite is True.
    :param overwrite: When True, overwrite any value in the source list destructively.
    :return: The updated dict.
    """
    def is_collection(value: Any) -> bool:
        """Return True if ``value`` is of type ``Collection`` and not a string or map"""
        return isinstance(value, Collection) and not isinstance(value, str) and not isinstance(value, Mapping)

    for k, v in new.items():
        if isinstance(v, Mapping) and isinstance(source.get(k, {}), Mapping):
            source[k] = merge_maps(source.get(k, {}), v, extend=extend, overwrite=overwrite)
        elif extend and is_collection(v) and is_collection(source.get(k, [])):
            source[k] = to_collection(source.get(k, []), list) + to_collection(v, list)
        elif overwrite or source.get(k) is None:
            source[k] = v
    return source


###########################################################################
## Misc
###########################################################################
def get_most_common_values(values: Iterable[Any]) -> list[Any]:
    """Get an ordered list of the most common values for a given collection of ``values``"""
    return [x[0] for x in Counter(values).most_common()]


def get_user_input(text: str | None = None) -> str:
    """Print formatted dialog with optional text and get the user's input."""
    return input(f"\33[93m{text}\33[0m | ").strip()
