import re
from collections.abc import Mapping, Sequence
from datetime import datetime, date
from functools import reduce
from operator import mul
from typing import Any, Self

from syncify.abstract.item import Item
from syncify.abstract.processor import MusicBeeProcessor, DynamicProcessor
from syncify.enums.tags import Name, TagName, PropertyName
from syncify.local.exception import FieldError
from syncify.processors.decorators import dynamicprocessormethod
from syncify.processors.exception import ItemComparerError
from syncify.processors.time import TimeMapper
from syncify.utils import UnitSequence
from syncify.utils.helpers import to_collection

# Map of MusicBee field name to Tag or Property
field_name_map = {
    "None": None,
    "Title": TagName.TITLE,
    "ArtistPeople": TagName.ARTIST,
    "Album": TagName.ALBUM,  # album ignoring articles like 'the' and 'a' etc.
    "TrackNo": TagName.TRACK,
    "GenreSplits": TagName.GENRES,
    "Year": TagName.YEAR,
    "Tempo": TagName.BPM,
    "DiscNo": TagName.DISC,
    "AlbumArtist": TagName.ALBUM_ARTIST,
    "Comment": TagName.COMMENTS,
    "FileDuration": PropertyName.LENGTH,
    "FolderName": PropertyName.FOLDER,
    "FilePath": PropertyName.PATH,
    "FileName": PropertyName.FILENAME,
    "FileExtension": PropertyName.EXT,
    "FileDateAdded": PropertyName.DATE_ADDED,
    "FilePlayCount": PropertyName.PLAY_COUNT,
}


class ItemComparer(MusicBeeProcessor, DynamicProcessor):
    """
    Compares an item with another item or a given set of expected values to find a match.

    :param field: The field to match on.
    :param condition: The condition to match on e.g. Is, LessThan, InRange, Contains.
    :param expected: Optional list of expected values to match on.
        Types of the values in this list are automatically converted to the type of the track field's value.
    """

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

    @classmethod
    def from_xml(cls, xml: Mapping[str, Any], **kwargs) -> list[Self] | None:
        conditions: tuple[Mapping[str, str]] = to_collection(xml["SmartPlaylist"]["Source"]["Conditions"]["Condition"])

        objs = []
        for condition in conditions:
            field_str = condition.get("@Field", "None")
            field: Name = field_name_map.get(field_str)
            if field is None:
                raise FieldError(f"Unrecognised field name", field=field_str)

            expected: tuple[str] | None = tuple(val for k, val in condition.items() if k.startswith("@Value"))
            if len(expected) == 0 or expected[0] == "[playing track]":
                expected = None

            objs.append(cls(field=field, condition=condition["@Comparison"], expected=expected))

        return objs

    def __init__(self, field: Name, condition: str, expected: UnitSequence[Any] | None = None):
        DynamicProcessor.__init__(self)
        self._expected: list[Any] | None = None
        self._converted = False

        self.field: Name = field
        self.expected: list[Any] | None = expected

        self._set_processor_name(condition)

    def compare[T: Item](self, track: T, reference: UnitSequence[T] | None = None) -> bool:
        """
        Compare a ``track`` to a ``reference`` or,
        if no ``reference`` is given, to this object's list of ``expected`` values

        :return: True if a match is found, False otherwise.
        :raise LocalProcessorError: If no reference given and no expected values set for this comparer.
        """
        if self.condition is None:
            return False

        if reference is None and not self.expected:
            raise ItemComparerError("No comparative track given and no expected values set")

        tag_name = self._get_tag(self.field)
        actual = track[tag_name]

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

        return self._process(actual, expected)

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
        """Convert expected values to datetime objects"""
        converted: list[date] = []

        for exp in self.expected:
            if isinstance(exp, datetime):
                converted.append(exp.date())
            elif re.match(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", exp):
                # value is a string representation of datetime
                digits: list[int] = list(map(int, reversed(exp.split("/"))))

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

    @dynamicprocessormethod("greater_than", "_is_in_the_last")
    def _is_after(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return value > expected[0] if value is not None and expected[0] is not None else False

    @dynamicprocessormethod("less_than", "_is_not_in_the_last")
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
        return expected[0] < value < expected[1] if value is not None and expected[0] is not None else False

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
        return value.startswith(expected[0]) if value is not None and expected[0] is not None else False

    @dynamicprocessormethod
    def _ends_with(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return value.endswith(expected[0]) if value is not None and expected[0] is not None else False

    @dynamicprocessormethod
    def _contains(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return expected[0] in value if value is not None and expected[0] is not None else False

    @dynamicprocessormethod
    def _does_not_contain(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return not self._contains(value=value, expected=expected)

    @dynamicprocessormethod
    def _in_tag_hierarchy(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        # TODO: what does this even mean
        raise NotImplementedError

    @dynamicprocessormethod
    def _matches_reg_ex(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return bool(re.search(expected[0], value)) if value is not None and expected[0] is not None else False

    @dynamicprocessormethod
    def _matches_reg_ex_ignore_case(self, value: Any | None, expected: Sequence[Any] | None) -> bool:
        if value is not None and expected[0] is not None:
            return False
        return bool(re.search(expected[0], value, flags=re.IGNORECASE))

    def to_xml(self, **kwargs) -> Mapping[str, Any]:
        raise NotImplementedError

    def as_dict(self):
        return {"field": self.field.name, "condition": self.condition, "expected": self.expected}
