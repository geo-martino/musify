import re
from datetime import datetime, timedelta, date
from functools import reduce
from operator import mul
from typing import Any, Callable, List, Mapping, Optional, Self, MutableMapping

from dateutil.relativedelta import relativedelta

from syncify.local.files.track.base import Name, LocalTrack, TagName
from syncify.local.files.track.collection import TrackProcessor
from syncify.local.files.utils.musicbee import field_name_map
from syncify.utils.helpers import make_list
from utils_new.generic import UnionList


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

    _valid_methods: Mapping[str, str] = {
        "_greater_than": "_is_after",
        "_less_than": "_is_before",
        "_cond_is_in_the_last": "_is_after",
        "_cond_is_not_in_the_last": "_is_before",
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

        name = self._get_method_name(value=value, valid=self._valid_methods, prefix=self._cond_method_prefix)
        self._condition = self._snake_to_camel(name, prefix=self._cond_method_prefix)
        self._method = getattr(self, self._valid_methods[name])

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
            if len(expected) == 0 or expected[0] == '[playing track]':
                expected = None

            objs.append(cls(field=field, condition=condition["@Comparison"], expected=expected))

        return objs

    def __init__(self, field: Name, condition: str, expected: Optional[UnionList[Any]] = None) -> None:
        self._method: Callable[[Optional[Any], Optional[List[Any]]], bool] = lambda _, __: False
        self._converted = False
        self._expected: Optional[List[Any]] = None

        self.field: Name = field
        self.expected: Optional[List[Any]] = make_list(expected)

        prefix = "_cond"
        self._cond_method_prefix = "_cond"
        self._valid_methods = {
            k if k.startswith(prefix) else prefix + k: v if v.startswith(prefix) else prefix + v
            for k, v in self._valid_methods.items()
        } | {name: name for name in dir(self) if name.startswith(self._cond_method_prefix)}
        self.condition = condition

    def compare(self, track: LocalTrack, reference: Optional[UnionList[LocalTrack]] = None) -> bool:
        """
        Compare a track to another a track
        or, if no other track is given, to the instance's list of expected values
        """
        if reference is None and self.expected is None:
            raise ValueError("No comparative track given and no expected values set")

        field_name = TagName.to_tag(self.field)[0] if isinstance(self.field, TagName) else self.field.name.lower()

        actual = getattr(track, field_name, None)

        if reference is None:
            if not self._converted:
                self._convert_expected(actual)
            expected = self.expected
        else:
            expected = make_list(getattr(reference, self.field.name.lower(), None))

        if expected is not None:
            if isinstance(actual, datetime) and not isinstance(expected[0], datetime):
                actual = actual.date()
            elif not isinstance(actual, datetime) and isinstance(expected[0], datetime):
                expected = [exp.date() for exp in expected]

        try:
            return self._method(actual, expected)
        except TypeError:
            return False

    def _convert_expected(self, value: Any) -> None:
        """Driver for converting expected values to the same type as given value"""
        if self._converted:
            return

        if isinstance(value, int):
            self._convert_expected_to_int()
            self._converted = True
        elif isinstance(value, float):
            self._convert_expected_to_float()
            self._converted = True
        elif isinstance(value, date):
            self._convert_expected_to_datetime()
            self._converted = True
        elif isinstance(value, bool):
            self._expected.clear()
            self._converted = True

    @staticmethod
    def _get_seconds(time_str: str) -> float:
        """Convert string representation of time to seconds"""
        factors = [24, 60, 60, 1]
        digits_split = time_str.split(":")
        digits = [int(n.split(",")[0]) for n in digits_split]

        seconds = 0
        if "," in digits_split[-1]:
            seconds += int(digits_split[-1].split(",")[1]) / 1000

        for i, digit in enumerate(reversed(digits), 1):
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

    def _convert_expected_to_datetime(self) -> None:
        """Convert expected values to datetime objects"""
        converted: List[date] = []

        for exp in self.expected:
            if isinstance(exp, datetime):
                converted.append(exp.date())
            elif re.match(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", exp):
                digits = [int(d) for d in reversed(exp.split("/"))]

                if len(str(digits[-1])) < 4:  # year is not fully qualified, add millennium part
                    this_millennium = str(date.today().year)[:2]
                    last_millennium = str(int(this_millennium) - 1)

                    if digits[0] % 1000 > date.today().year % 1000:
                        digits[0] = int(last_millennium + str(digits[0])[-2:].zfill(2))
                    else:
                        digits[0] = int(this_millennium + str(digits[0])[-2:].zfill(2))

                converted.append(date(*digits))
            else:
                digit = int(re.sub(r"\D+", "", exp))
                mapper_key = re.sub(r"\d+", "", exp)
                converted.append(datetime.now() - self._td_str_mapper[mapper_key](digit))

        self._expected = converted

    @staticmethod
    def _cond_is(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return value == expected[0]

    @classmethod
    def _cond_is_not(cls, value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return not cls._cond_is(value=value, expected=expected)

    @staticmethod
    def _cond_is_after(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return value > expected[0]

    @staticmethod
    def _cond_is_before(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return value < expected[0]

    @staticmethod
    def _cond_is_in(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return value in expected

    @classmethod
    def _cond_is_not_in(cls, value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return not cls._cond_is_in(value=value, expected=expected)

    @staticmethod
    def _cond_in_range(value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return expected[0] < value < expected[1]

    @classmethod
    def _cond_not_in_range(cls, value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return not cls._cond_in_range(value=value, expected=expected)

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

    @classmethod
    def _cond_does_not_contain(cls, value: Optional[Any], expected: Optional[List[Any]]) -> bool:
        return not cls._cond_contains(value=value, expected=expected)

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

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "field": self.field.name,
            "condition": self.condition,
            "expected": self.expected
        }
