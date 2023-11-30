import re
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta, date
from functools import reduce
from operator import mul
from typing import Any, Self

from dateutil.relativedelta import relativedelta

from syncify.enums.tags import Name, TagName, PropertyName
from syncify.local.exception import FieldError, LocalProcessorError
from syncify.local.track.base.track import LocalTrack
from syncify.utils import UnitSequence
from syncify.utils.helpers import to_collection
from .base import TrackProcessor

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


class TrackComparer(TrackProcessor):
    """
    Compares a track with another track or a given set of expected values to find a match.

    :param field: The field to match on.
    :param condition: The condition to match on e.g. Is, LessThan, InRange, Contains.
    :param expected: Optional list of expected values to match on.
        Types of the values in this list are automatically converted to the type of the track field's value.
    """

    # map of time character representation to it unit conversion from seconds
    _td_str_mapper = {
        "h": lambda x: timedelta(hours=int(x)),
        "d": lambda x: timedelta(days=int(x)),
        "w": lambda x: timedelta(weeks=int(x)),
        "m": lambda x: relativedelta(months=int(x))
    }

    # map of conditions and their equivalent functions
    _valid_methods: Mapping[str, str] = {
        "_greater_than": "_is_after",
        "_less_than": "_is_before",
        "_cond_is_in_the_last": "_is_after",
        "_cond_is_not_in_the_last": "_is_before",
    }

    @property
    def condition(self) -> str:
        """String representation of the current condition name of this object"""
        return self._condition

    @condition.setter
    def condition(self, value: str):
        """Sets the condition name and stored method"""
        if value is None:
            self._condition: str | None = None
            self._method: Callable[[Any | None, Sequence[Any] | None], bool] = lambda _, __: False
            return

        name = self._get_method_name(value=value, valid=self._valid_methods, prefix=self._cond_method_prefix)
        self._condition = self._snake_to_camel(name, prefix=self._cond_method_prefix)
        self._method = getattr(self, self._valid_methods[name])

    @property
    def expected(self) -> Sequence[Any] | None:
        """A list of expected values used for most conditions"""
        return self._expected

    @expected.setter
    def expected(self, value: Sequence[Any] | None = None):
        """Set the list of expected values and reset the ``_converted`` attribute to False"""
        self._converted = False
        self._expected = value

    @classmethod
    def from_xml(cls, xml: Mapping[str, Any] | None = None) -> list[Self] | None:
        if xml is None:
            return

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
        self._converted = False
        self._expected: list[Any] | None = None

        self.field: Name = field
        self.expected: list[Any] | None = to_collection(expected, list)

        prefix = "_cond"
        self._cond_method_prefix = "_cond"
        self._valid_methods = {
            k if k.startswith(prefix) else prefix + k: v if v.startswith(prefix) else prefix + v
            for k, v in self._valid_methods.items()
        } | {
            name: name for name in dir(self) if name.startswith(self._cond_method_prefix)
        }
        self.condition = condition

    def compare(self, track: LocalTrack, reference: UnitSequence[LocalTrack] | None = None) -> bool:
        """
        Compare a ``track`` to a ``reference`` or,
        if no ``reference`` is given, to this object's list of ``expected`` values

        :raises LocalProcessorError: If no reference given and no expected values set for this comparator.
        """
        if reference is None and self.expected is None:
            raise LocalProcessorError("No comparative track given and no expected values set")

        tag_name = self._get_tag(self.field)
        actual = track[tag_name]

        if reference is None:
            # convert the expected values to the same type as the actual value if not yet converted
            if not self._converted:
                self._convert_expected(actual)
            expected = self.expected
        else:  # use the values from the reference as the expected values
            expected = to_collection(reference[tag_name], list)

        if expected is not None:  # special on-the-fly conversions for datetime values
            if isinstance(actual, datetime) and not isinstance(expected[0], datetime):
                actual = actual.date()
            elif not isinstance(actual, datetime) and isinstance(expected[0], datetime):
                expected = [exp.date() for exp in expected]

        try:  # do the comparison
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
                converted.append(datetime.now() - self._td_str_mapper[mapper_key](digit))

        self._expected = converted

    @staticmethod
    def _cond_is(value: Any | None, expected: Sequence[Any] | None) -> bool:
        return value == expected[0]

    @classmethod
    def _cond_is_not(cls, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return not cls._cond_is(value=value, expected=expected)

    @staticmethod
    def _cond_is_after(value: Any | None, expected: Sequence[Any] | None) -> bool:
        return value > expected[0] if value is not None and expected[0] is not None else False

    @staticmethod
    def _cond_is_before(value: Any | None, expected: Sequence[Any] | None) -> bool:
        return value < expected[0] if value is not None and expected[0] is not None else False

    @staticmethod
    def _cond_is_in(value: Any | None, expected: Sequence[Any] | None) -> bool:
        return value in expected

    @classmethod
    def _cond_is_not_in(cls, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return not cls._cond_is_in(value=value, expected=expected)

    @staticmethod
    def _cond_in_range(value: Any | None, expected: Sequence[Any] | None) -> bool:
        return expected[0] < value < expected[1] if value is not None and expected[0] is not None else False

    @classmethod
    def _cond_not_in_range(cls, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return not cls._cond_in_range(value=value, expected=expected)

    @staticmethod
    def _cond_is_not_null(value: Any | None, _: Sequence[Any] | None = None) -> bool:
        return value is not None or value is True

    @staticmethod
    def _cond_is_null(value: Any | None, _: Sequence[Any] | None = None) -> bool:
        return value is None or value is False

    @staticmethod
    def _cond_starts_with(value: Any | None, expected: Sequence[Any] | None) -> bool:
        return value.startswith(expected[0]) if value is not None and expected[0] is not None else False

    @staticmethod
    def _cond_ends_with(value: Any | None, expected: Sequence[Any] | None) -> bool:
        return value.endswith(expected[0]) if value is not None and expected[0] is not None else False

    @staticmethod
    def _cond_contains(value: Any | None, expected: Sequence[Any] | None) -> bool:
        return expected[0] in value if value is not None and expected[0] is not None else False

    @classmethod
    def _cond_does_not_contain(cls, value: Any | None, expected: Sequence[Any] | None) -> bool:
        return not cls._cond_contains(value=value, expected=expected)

    @staticmethod
    def _cond_in_tag_hierarchy(value: Any | None, expected: Sequence[Any] | None) -> bool:
        # TODO: what does this even mean
        raise NotImplementedError

    @staticmethod
    def _cond_matches_reg_ex(value: Any | None, expected: Sequence[Any] | None) -> bool:
        return bool(re.search(expected[0], value)) if value is not None and expected[0] is not None else False

    @staticmethod
    def _cond_matches_reg_ex_ignore_case(value: Any | None, expected: Sequence[Any] | None) -> bool:
        if value is not None and expected[0] is not None:
            return False
        return bool(re.search(expected[0], value, flags=re.IGNORECASE))

    def as_dict(self):
        return {"field": self.field.name, "condition": self.condition, "expected": self.expected}
