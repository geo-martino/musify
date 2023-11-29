import pytest

from syncify.utils.helpers import to_collection, strip_ignore_words, flatten_nested, limit_value, get_most_common_values


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


def test_flatten_nested():
    # flattens non-nested
    assert flatten_nested({"a": 1, "b": 2, "c": 3}) == [1, 2, 3]
    assert flatten_nested({"a": 1, "b": [2, 3, 4], "c": 5}) == [1, 2, 3, 4, 5]

    # flattens nested
    nested_map = {"a": 1, "b": [2, 3, 4], "c": {"sub1": 5, "sub2": [6], "sub3": {"deep": [7, 8]}}}
    assert flatten_nested(nested_map) == [1, 2, 3, 4, 5, 6, 7, 8]
    assert flatten_nested(nested_map, ["a", "b"]) == ["a", "b", 1, 2, 3, 4, 5, 6, 7, 8]


def test_limit_value():
    assert limit_value(6, 0, 20) == 6
    assert limit_value(-5, 10, 20) == 10
    assert limit_value(-5, -20, 20) == -5
    assert limit_value(-5, -2, 20) == -2
    assert limit_value(30, -2, 20) == 20

    assert limit_value(0.12, 0.5, 1) == 0.5
    assert limit_value(2, 0.5, 1.8) == 1.8
    assert limit_value(1, 0.5, 1.8) == 1


def test_get_most_common_values():
    assert get_most_common_values([1, 1, 2, 3, 3, 3, 4]) == [3, 1, 2, 4]
    assert get_most_common_values(["asd", 6, "five", "asd", "five", "asd"]) == ["asd", "five", 6]
