from copy import deepcopy

import pytest

from syncify.utils.helpers import limit_value, to_collection, flatten_nested, merge_maps, get_most_common_values
from syncify.utils.helpers import strip_ignore_words, safe_format_map, get_max_width, align_and_truncate


###########################################################################
## String
###########################################################################
def test_strip_ignore_words():
    # marks as not special
    assert strip_ignore_words("Hello", None) == (True, "Hello")
    assert strip_ignore_words("I am a string", ["A"]) == (True, "I am a string")
    assert strip_ignore_words("special end??", ["A"]) == (True, "special end??")

    # marks as special
    assert strip_ignore_words("!special1", ["special"]) == (False, "special1")
    assert strip_ignore_words("*%2I am very special!", ["very", "i"]) == (False, "2I am very special!")

    # marks as special as needed and strips words
    assert strip_ignore_words("I am a string", ["i"]) == (True, "am a string")
    assert strip_ignore_words("*%I   am very special!", ["am", "i"]) == (False, "am very special!")


def test_safe_format_map():
    test = {
        "a": "please {replace_me}",
        "b": {"nested1": "{replace_me}", "nested2": "no {replacement}"},
        "c": {"nested1": {"nested2a": "{replace_me} too", "nested2b": "don't replace_me"}},
        "d": "{don't fail}"
    }
    replacements = {"replace_me": "new value"}
    safe_format_map(test, format_map=replacements)

    assert test == {
        "a": "please new value",
        "b": {"nested1": "new value", "nested2": "no {replacement}"},
        "c": {"nested1": {"nested2a": "new value too", "nested2b": "don't replace_me"}},
        "d": "{don't fail}"
    }


def test_get_max_width():
    values = ["a" * 10, "b" * 15, "c" * 20, "d" * 25, "e" * 30]

    assert get_max_width(values, min_width=5, max_width=8) == 8
    assert get_max_width(values, min_width=5, max_width=22) == 22
    assert get_max_width(values, min_width=5, max_width=50) == 31  # +1 for trailing space
    assert get_max_width(values, min_width=50, max_width=100) == 50

    assert get_max_width([]) == 0


def test_align_and_truncate():
    assert align_and_truncate("a" * 10, max_width=19, right_align=False) == "a" * 10 + " " * 9
    assert align_and_truncate("b" * 15, max_width=19, right_align=False) == "b" * 15 + " " * 4
    assert align_and_truncate("c" * 20, max_width=19, right_align=False) == "c" * 16 + "..."
    assert align_and_truncate("d" * 25, max_width=19, right_align=False) == "d" * 16 + "..."
    assert align_and_truncate("e" * 25, max_width=19, right_align=True) == "..." + "e" * 16


###########################################################################
## Number
###########################################################################
def test_limit_value():
    assert limit_value(6, 0, 20) == 6
    assert limit_value(-5, 10, 20) == 10
    assert limit_value(-5, -20, 20) == -5
    assert limit_value(-5, -2, 20) == -2
    assert limit_value(30, -2, 20) == 20

    assert limit_value(0.12, 0.5, 1) == 0.5
    assert limit_value(2, 0.5, 1.8) == 1.8
    assert limit_value(1, 0.5, 1.8) == 1


###########################################################################
## Collection
###########################################################################
# noinspection PyTypeChecker
def test_to_collection():
    # None input always returns None
    assert to_collection(None) is None
    assert to_collection(None, list) is None
    assert to_collection(None, set) is None
    assert to_collection(None, tuple) is None
    assert to_collection(None, dict) is None
    assert to_collection(None, str) is None

    # input always equals output on equal types
    assert to_collection("123", str) == "123"
    assert to_collection(123, int) == 123
    assert to_collection({1: "a", 2: "b", 3: "c"}, dict) == {1: "a", 2: "b", 3: "c"}

    # converts to tuple (default)
    assert to_collection("123") == ("123",)
    assert to_collection(1) == (1,)
    assert to_collection([1, 2, 3]) == (1, 2, 3)
    assert to_collection({1, 2, 3, 4}) == (1, 2, 3, 4)
    assert to_collection({1: "a", 2: "b", 3: "c"}) == ({1: "a", 2: "b", 3: "c"},)

    # converts to set
    assert to_collection("123", set) == {"123"}
    assert to_collection(1, set) == {1}
    assert to_collection([1, 2, 3], set) == {1, 2, 3}
    assert to_collection({1, 2, 3, 4}, set) == {1, 2, 3, 4}

    # converts to list
    assert to_collection("123", list) == ["123"]
    assert to_collection(1, list) == [1]
    assert to_collection([1, 2, 3], list) == [1, 2, 3]
    assert to_collection({1, 2, 3, 4}, list) == [1, 2, 3, 4]
    assert to_collection({1: "a", 2: "b", 3: "c"}, list) == [{1: "a", 2: "b", 3: "c"}]

    # fails on unrecognised type
    with pytest.raises(TypeError):
        to_collection("123", dict)
        to_collection(1, str)
        to_collection([1, 2, 3], bool)
        to_collection({1, 2, 3, 4}, float)


###########################################################################
## Mapping
###########################################################################
def test_flatten_nested():
    # flattens non-nested
    assert flatten_nested({"a": 1, "b": 2, "c": 3}) == [1, 2, 3]
    assert flatten_nested({"a": 1, "b": [2, 3, 4], "c": 5}) == [1, 2, 3, 4, 5]

    # flattens nested
    nested_map = {"a": 1, "b": [2, 3, 4], "c": {"sub1": 5, "sub2": [6], "sub3": {"deep": [7, 8]}}}
    assert flatten_nested(nested_map) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert flatten_nested(nested_map, ["a", "b"]) == ["a", "b", 1, 2, 3, 4, 5, 6, 7, 8]


def tests_merge_maps():
    source = {
        1: "value",
        2: {"a": "val a", "b": "val b", "c": {"nested1": "nested val"}},
        3: {"nested1": {"nested2": {"nested3": "old value"}}},
        4: {"a": [1, 2, 3]}
    }
    new = {
        2: {"b": "new value b", "c": {"nested1": "modified nested val"}},
        3: {"nested1": {"nested2": {"nested3": "new value", "new key": "new val"}}},
        4: {"a": [4, 5]}
    }

    test = deepcopy(source)
    merge_maps(source=test, new=new, extend=False, overwrite=False)
    assert test == {
        1: "value",
        2: {"a": "val a", "b": "val b", "c": {"nested1": "nested val"}},
        3: {"nested1": {"nested2": {"nested3": "old value", "new key": "new val"}}},
        4: {"a": [1, 2, 3]}
    }

    test = deepcopy(source)
    merge_maps(source=test, new=new, extend=False, overwrite=True)
    assert test == {
        1: "value",
        2: {"a": "val a", "b": "new value b", "c": {"nested1": "modified nested val"}},
        3: {"nested1": {"nested2": {"nested3": "new value", "new key": "new val"}}},
        4: {"a": [4, 5]}
    }

    test = deepcopy(source)
    merge_maps(source=test, new=new, extend=True, overwrite=False)
    assert test == {
        1: "value",
        2: {"a": "val a", "b": "val b", "c": {"nested1": "nested val"}},
        3: {"nested1": {"nested2": {"nested3": "old value", "new key": "new val"}}},
        4: {"a": [1, 2, 3, 4, 5]}
    }


###########################################################################
## Misc
###########################################################################
def test_get_most_common_values():
    assert get_most_common_values([1, 1, 2, 3, 3, 3, 4]) == [3, 1, 2, 4]
    assert get_most_common_values(["asd", 6, "five", "asd", "five", "asd"]) == ["asd", "five", 6]
