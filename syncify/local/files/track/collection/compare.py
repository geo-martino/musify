import re
from datetime import datetime, timedelta
from functools import reduce
from operator import mul
from typing import Any, Callable, List, Mapping, Optional, Self, MutableMapping

from dateutil.relativedelta import relativedelta

from syncify.local.files.track.base import Name, Track, TagName
from syncify.local.files.track.collection import TrackProcessor
from syncify.local.files.utils.musicbee import field_name_map
from syncify.utils.helpers import make_list


class TrackCompare(TrackProcessor):
    """
    Compares a track with another track or a given set of expected values to find a match.

    :param field: The field to match on.
    :param condition: The condition to match on e.g. Is, LessThan, InRange, Contains.
    :param expected: Optional list of expected values to match on.
        Types of the values in this list are automatically converted to the type of the track field's value.
    """

    _td_str_mapper = {
        "h": lambda x: timedelta(hours=int(x)),
        "d": lambda x: timedelta(days=int(x)),
        "w": lambda x: timedelta(weeks=int(x)),
        "m": lambda x: relativedelta(months=int(x))
    }

    @property
    def condition(self) -> str:
        return self._condition

    @condition.getter
    def condition(self) -> str:
        return self._condition

    @condition.setter
    def condition(self, value: str):
        if value is None:
            return

        condition_sanitised = re.sub('([A-Z])', lambda m: f"_{m.group(0).lower()}", value.strip()).replace(" ", "_")
        if not condition_sanitised.startswith("_"):
            condition_sanitised = "_" + condition_sanitised
        if not condition_sanitised.startswith(self._cond_method_prefix):
            condition_sanitised = self._cond_method_prefix + condition_sanitised

        if condition_sanitised not in self._valid_methods:
            valid_methods_str = ", ".join([c.replace(self._cond_method_prefix, "") for c in self._valid_methods])
            raise ValueError(
                f"Unrecognised condition: {value} | " 
                f"Valid conditions: {valid_methods_str}"
            )

        self._condition = condition_sanitised.replace(self._cond_method_prefix, "").replace("_", " ").strip()
        self._method = getattr(self, condition_sanitised)

    @property
    def expected(self) -> Optional[List[Any]]:
        return self._expected

    @expected.getter
    def expected(self) -> Optional[List[Any]]:
        return self._expected

    @expected.setter
    def expected(self, value: Optional[List[Any]] = None):
        self._converted = False
        self._expected = value

    def __init__(self, field: Name, condition: str, expected: Optional[List[Any]] = None) -> None:
        self._method: Callable[[Any, Optional[List[Any]]], bool] = lambda _, __: False
        self._converted = False
        self._expected: Optional[List[Any]] = None

        self.field: Any = field
        self.expected: Optional[List[Any]] = expected

        self._cond_method_prefix = "_cond"
        self._valid_methods = [name for name in dir(self) if name.startswith(self._cond_method_prefix)]
        self.condition = condition

    @classmethod
    def from_xml(cls, xml: Optional[Mapping[str, Any]] = None) -> Optional[List[Self]]:
        if xml is None:
            return

        conditions: List[Mapping[str, str]] = make_list(xml["SmartPlaylist"]["Source"]["Conditions"]["Condition"])

        objs = []
        for condition in conditions:
            field_str = condition.get("@Field", "None")
            field: Name = field_name_map.get(field_str)
            if field is None:
                raise ValueError(f"Unrecognised field name: {field_str}")

            expected: Optional[List[str]] = [val for k, val in condition.items() if k.startswith("@Value")]
            if expected[0] == '[playing track]':
                expected = None

            compare_str = condition["@Comparison"]
            compare_str = re.sub('([A-Z])', lambda m: f"_{m.group(0).lower()}", compare_str)

            objs.append(cls(field=field, condition=compare_str, expected=expected))

        return objs

    def compare(self, track_1: Track, track_2: Optional[List[Track]] = None) -> bool:
        """
        Compare a track to another a track
        or, if no other track is given, to the instance's list of expected values
        """
        if track_2 is None and self.expected is None:
            raise ValueError("No comparative track given and no expected values set")

        field_name = TagName.to_tag(self.field)[0] if isinstance(self.field, TagName) else self.field.name.lower()

        actual = getattr(track_1, field_name, None)
        if track_2 is None:
            if not self._converted:
                self._convert_expected(actual)
            expected = self.expected
        else:
            expected = make_list(getattr(track_2, self.field.name.lower(), None))

        try:
            return self._method(actual, expected)
        except TypeError:
            return False

    def _convert_expected(self, value: Any) -> None:
        """Driver for converting expected values to the same type as given value"""
        if isinstance(value, int):
            self._convert_expected_to_int()
        elif isinstance(value, float):
            self._convert_expected_to_float()
        elif isinstance(value, datetime):
            self._convert_expected_to_dt()
        elif isinstance(value, bool):
            self._expected.clear()

    @staticmethod
    def _get_seconds(time_str: str) -> float:
        """Convert string representation of time to seconds"""
        factors = [24, 60, 60, 1]
        digits_split = time_str.split(":")
        digits = [int(n.split(",")[0]) for n in digits_split]
        seconds = int(digits_split[-1].split(",")[1]) / 1000

        for i, digit in enumerate(digits, 1):
            seconds += digit * reduce(mul, factors[-i:], 1)

        return seconds

    def _convert_expected_to_int(self) -> None:
        """Convert expected values to integers"""
        converted: List[int] = []
        for exp in self.expected:
            if isinstance(exp, str) and ":" in exp:
                exp = self._get_seconds(exp)
            converted.append(int(exp))
        self._expected = converted

    def _convert_expected_to_float(self) -> None:
        """Convert expected values to floats"""
        converted: List[float] = []
        for exp in self.expected:
            if isinstance(exp, str) and ":" in exp:
                exp = self._get_seconds(exp)
            converted.append(float(exp))
        self._expected = converted

    def _convert_expected_to_dt(self) -> None:
        """Convert expected values to datetime objects"""
        converted: List[datetime] = []

        for exp in self.expected:
            if isinstance(exp, datetime):
                converted.append(exp)
            elif re.match("\d{1,2}/\d{1,2}/\d{4}", exp):
                converted.append(datetime.strptime(exp, "%d/%m/%Y"))
            elif re.match("\d{1,2}/\d{1,2}/\d{2}", exp):
                converted.append(datetime.strptime(exp, "%d/%m/%y"))
            else:
                digit = int(re.sub("\D+", "", exp))
                mapper_key = re.sub("\W+", "", exp)
                converted.append(datetime.now() - self._td_str_mapper[mapper_key](digit))

        self._expected = converted

    @staticmethod
    def _cond_is(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return value == expected[0]

    def _cond_is_not(self, value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return not self._cond_is(value=value, expected=expected)

    @staticmethod
    def _cond_is_after(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return value > expected[0]

    @staticmethod
    def _cond_is_before(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return value < expected[0]

    def _cond_is_in_the_last(self, value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return self._cond_is_after(value=value, expected=expected)

    def _cond_is_not_in_the_last(self, value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return self._cond_is_before(value=value, expected=expected)

    @staticmethod
    def _cond_is_in(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return value in expected

    def _cond_is_not_in(self, value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return not self._cond_is_in(value=value, expected=expected)

    @staticmethod
    def _cond_greater_than(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return value > expected[0]

    @staticmethod
    def _cond_less_than(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return value < expected[0]

    @staticmethod
    def _cond_in_range(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return expected[0] < value < expected[1]

    def _cond_not_in_range(self, value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return not self._cond_in_range(value=value, expected=expected)

    @staticmethod
    def _cond_is_not_null(value: Optional[Any], _: Optional[List[Any]] = None) -> bool:
        return value is not None or value is True

    @staticmethod
    def _cond_is_null(value: Optional[Any], _: Optional[List[Any]] = None) -> bool:
        return value is None or value is False

    @staticmethod
    def _cond_starts_with(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return value.startswith(expected[0])

    @staticmethod
    def _cond_ends_with(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return value.endswith(expected[0])

    @staticmethod
    def _cond_contains(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return expected[0] in value

    def _cond_does_not_contain(self, value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return not self._cond_contains(value=value, expected=expected)

    @staticmethod
    def _cond_in_tag_hierarchy(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        # TODO: what does this even mean
        raise NotImplementedError

    @staticmethod
    def _cond_matches_reg_ex(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return bool(re.search(expected[0], value))

    @staticmethod
    def _cond_matches_reg_ex_ignore_case(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return bool(re.search(expected[0], value, flags=re.IGNORECASE))

    def as_dict(self) -> MutableMapping[str, object]:
        return {
            "field": self.field.name,
            "condition": self.condition,
            "expected": self.expected
        }
