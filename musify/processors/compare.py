"""
Processor making comparisons between objects and data types.
"""
import re
from collections.abc import Sequence
from datetime import datetime, date
from functools import reduce
from operator import mul
from typing import Any

from musify.base import MusifyItem
from musify.field import Field
from musify.processors.base import DynamicProcessor, dynamicprocessormethod
from musify.processors.exception import ComparerError
from musify.processors.time import TimeMapper
from musify.types import UnitSequence
from musify.utils import to_collection


class Comparer(DynamicProcessor):
    """
    Compares an item or object with another item, object or a given set of expected values to find a match.

    :param condition: The condition to match on e.g. Is, LessThan, InRange, Contains.
    :param expected: Optional list of expected values to match on.
        Types of the values in this list are automatically converted to the type of the item field's value.
    :param field: The field to match on.
    :param reference_required: When True, a reference object of type ``T`` must be passed to the ``compare`` method.
        An exception will be raised if this is True and reference object is not passed.
    """

    __slots__ = ("_expected", "_converted", "field", "reference_required")

    @classmethod
    def _processor_method_fmt(cls, name: str) -> str:
        return "_" + cls._pascal_to_snake(name)

    @property
    def condition(self) -> str:
        """String representation of the current condition name of this object"""
        return self._processor_name.lstrip("_")

    @property
    def expected(self) -> list[Any] | None:
        """A list of expected values used for most conditions"""
        return self._expected

    @expected.setter
    def expected(self, value: Sequence[Any] | None):
        """Set the list of expected values and reset the ``_converted`` attribute to False"""
        self._converted = False
        self._expected = to_collection(value, list)

    def __init__(
            self,
            condition: str,
            expected: UnitSequence[Any] | None = None,
            field: Field | None = None,
            reference_required: bool = False,
    ):
        super().__init__()
        self._expected: list[Any] | None = None
        self._converted = False

        self.expected: list[Any] | None = to_collection(expected, list)
        #: The :py:class:`Field` representing the property to extract the comparison value from
        #: when an :py:class:`MusifyItem` is given
        self.field: Field | None = field.map(field)[0] if field else None
        #: Whether to raise an exception when :py:meth:`compare` is called and a reference object is not provided.
        self.reference_required = reference_required

        self._set_processor_name(condition)

    def __call__(self, *args, **kwargs) -> bool:
        return self.compare(*args, **kwargs)

    def compare[T: Any](self, item: T, reference: T | None = None) -> bool:
        """
        Compare a ``item`` to a ``reference`` or,
        if no ``reference`` is given, to this object's list of ``expected`` values

        :return: True if a match is found, False otherwise.
        :raise LocalProcessorError: If no reference given and no expected values set for this comparer.
        """
        if self.condition is None:
            return False

        if reference is None and self.reference_required:
            raise ComparerError("A reference is required for this instance of Comparer")
        if reference is None and not self.expected:
            raise ComparerError("No comparative item given and no expected values set")

        tag_name = None
        if self.field and isinstance(item, MusifyItem):
            tag_name = self.field.name.lower()
            actual = item[tag_name]
        else:
            actual = item

        if reference is None:
            # convert the expected values to the same type as the actual value if not yet converted
            if not self._converted:
                self._convert_expected(actual)
            expected = self.expected
        else:  # use the values from the reference as the expected values
            expected = to_collection(reference[tag_name], list)

        if expected:  # special on-the-fly conversions for datetime values
            if isinstance(actual, datetime) and not isinstance(expected[0], datetime):
                actual = actual.date()
            elif not isinstance(actual, datetime) and isinstance(expected[0], datetime):
                expected = [exp.date() for exp in expected]

        return super().__call__(actual, expected)

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
        elif isinstance(value, datetime):
            self._convert_expected_to_datetime()
            self._converted = True
        elif isinstance(value, bool):
            self._expected.clear()
            self._converted = True
        elif isinstance(value, str):
            self._converted = True

    def _convert_expected_to_int(self) -> None:
        """Convert expected values to integers"""
        converted: list[int] = []
        for exp in self.expected:
            if isinstance(exp, str) and ":" in exp:
                # value is a string representation of time
                exp = self._get_seconds(exp)
            converted.append(int(exp))
        self._expected = converted

    def _convert_expected_to_float(self) -> None:
        """Convert expected values to floats"""
        converted: list[float] = []
        for exp in self.expected:
            if isinstance(exp, str) and ":" in exp:
                # value is a string representation of time
                exp = self._get_seconds(exp)
            converted.append(float(exp))
        self._expected = converted

    def _convert_expected_to_datetime(self) -> None:
        """Convert expected values to :py:class:`datetime` objects"""
        converted: list[date] = []

        for exp in self.expected:
            if isinstance(exp, datetime):
                converted.append(exp.date())
            elif re.match(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", exp):
                # value is a string representation of datetime
                digits: list[int] = list(map(int, exp.split("/")[::-1]))

                if len(str(digits[-1])) < 4:  # year is not fully qualified, add millennium part
                    this_millennium = str(date.today().year)[:2]
                    last_millennium = str(int(this_millennium) - 1)

                    if digits[0] % 1000 > date.today().year % 1000:
                        digits[0] = int(last_millennium + str(digits[0])[-2:].zfill(2))
                    else:
                        digits[0] = int(this_millennium + str(digits[0])[-2:].zfill(2))

                converted.append(date(*digits))
            else:  # value is durational difference, calculate datetime using the current time
                digit = int(re.sub(r"\D+", "", exp))
                mapper_key = re.sub(r"\d+", "", exp)
                converted.append(datetime.now() - TimeMapper(mapper_key)(digit))

        self._expected = converted

    @staticmethod
    def _get_seconds(time_str: str) -> float:
        """Convert string representation of time to seconds e.g. 4:30 -> 270s"""
        factors = (24, 60, 60, 1)
        digits_split = time_str.split(":")
        digits = tuple(int(n.split(",")[0]) for n in digits_split)

        seconds = 0
        if "," in digits_split[-1]:  # add milliseconds if present
            seconds += int(digits_split[-1].split(",")[1]) / 1000

        for i, digit in enumerate(reversed(digits), 1):  # convert to seconds
            seconds += digit * reduce(mul, factors[-i:], 1)

        return seconds

    @dynamicprocessormethod
    def _is(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return value == expected[0]

    @dynamicprocessormethod
    def _is_not(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return not self._is(value=value, expected=expected)

    @dynamicprocessormethod("greater_than", "in_the_last")
    def _is_after(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return value > expected[0] if value is not None and expected[0] is not None else False

    @dynamicprocessormethod("less_than", "not_in_the_last")
    def _is_before(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return value < expected[0] if value is not None and expected[0] is not None else False

    @dynamicprocessormethod
    def _is_in(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return value in expected

    @dynamicprocessormethod
    def _is_not_in(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return not self._is_in(value=value, expected=expected)

    @dynamicprocessormethod
    def _in_range(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return expected[0] <= value <= expected[1] if value is not None and expected[0] is not None else False

    @dynamicprocessormethod
    def _not_in_range(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return not self._in_range(value=value, expected=expected)

    @dynamicprocessormethod
    def _is_not_null(self, value: Any | None, _: Sequence[Any] | None = None) -> bool:
        return value is not None or value is True

    @dynamicprocessormethod
    def _is_null(self, value: Any | None, _: Sequence[Any] | None = None) -> bool:
        return value is None or value is False

    @dynamicprocessormethod
    def _starts_with(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return value.startswith(str(expected[0])) if value is not None and expected[0] is not None else False

    @dynamicprocessormethod
    def _ends_with(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return value.endswith(str(expected[0])) if value is not None and expected[0] is not None else False

    @dynamicprocessormethod
    def _contains(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return str(expected[0]) in value if value is not None and expected[0] is not None else False

    @dynamicprocessormethod
    def _does_not_contain(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return not self._contains(value=value, expected=expected)

    @dynamicprocessormethod
    def _matches_reg_ex(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return bool(re.search(str(expected[0]), value)) if value is not None and expected[0] is not None else False

    @dynamicprocessormethod
    def _matches_reg_ex_ignore_case(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        if value is not None and expected[0] is not None:
            return False
        return bool(re.search(str(expected[0]), str(value), flags=re.I))

    def as_dict(self):
        return {
            "condition": self.condition,
            "expected": self.expected,
            "field": self.field.name if self.field else None,
            "reference_required": self.reference_required,
        }
