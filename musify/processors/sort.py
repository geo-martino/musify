"""
Processor that sorts the given collection of items based on given configuration.
"""

from collections.abc import Callable, Mapping, MutableMapping, Sequence, MutableSequence, Iterable
from copy import copy
from datetime import datetime
from random import shuffle
from typing import Any, Self

from musify.processors.base import MusicBeeProcessor
from musify.shared.core.base import Item
from musify.shared.core.enum import MusifyEnum, Field, Fields
from musify.shared.types import UnitSequence, UnitIterable
from musify.shared.utils import flatten_nested, strip_ignore_words, to_collection, limit_value


class ShuffleMode(MusifyEnum):
    """Represents the possible shuffle modes to use when shuffling items in a playlist."""
    NONE = 0
    RANDOM = 1
    HIGHER_RATING = 2
    RECENT_ADDED = 3
    DIFFERENT_ARTIST = 3


class ShuffleBy(MusifyEnum):
    """Represents the possible items/properties to shuffle by when shuffling items in a playlist."""
    TRACK = 0
    ALBUM = 1
    ARTIST = 2


class ItemSorter(MusicBeeProcessor):
    """
    Sort items in-place based on given conditions.

    :param fields:
        * When None and ShuffleMode is RANDOM, shuffle the items. Otherwise, do nothing.
        * List of tags/properties to sort by.
        * Map of ``{<tag/property>: <reversed>}``. If reversed is true, sort the ``tag/property`` in reverse.
    :param shuffle_mode: The mode to use for shuffling.
    :param shuffle_by: The field to shuffle by when shuffling.
    :param shuffle_weight: The weights (between -1 and 1) to apply to shuffling modes that can use it.
        This value will automatically be limited to within the accepted range 0 and 1.
    """

    __slots__ = ("sort_fields", "shuffle_mode", "shuffle_by", "shuffle_weight")

    #: Settings for custom sort codes.
    _custom_sort: dict[int, Mapping[Field, bool]] = {
        6: {
            Fields.ALBUM: False,
            Fields.DISC_NUMBER: False,
            Fields.TRACK_NUMBER: False,
            Fields.FILENAME: False
        }
    }
    # TODO: implement field_code 78 - manual order according to MusicBee library file.
    #  This is a workaround
    _custom_sort[78] = _custom_sort[6]

    @classmethod
    def sort_by_field(cls, items: list[Item], field: Field | None = None, reverse: bool = False) -> None:
        """
        Sort items by the values of a given field.

        :param items: List of items to sort
        :param field: Tag or property to sort on. If None and reverse is True, reverse the order of the list.
        :param reverse: If true, reverse the order of the sort.
        """
        if field is None:
            if reverse:
                items.reverse()
            return

        tag_name = field.map(field)[0].name.lower()

        # attempt to find an example value to determine the value type for this sort
        example_value = None
        for item in items:
            example_value = item[tag_name]
            if example_value is not None:
                break
        if example_value is None:
            # if no example value found, all values are None and so no sort can happen safely. Skip
            return

        # get sort key based on value type
        if isinstance(example_value, datetime):  # key converts datetime to floats
            def sort_key(t: Item) -> float:
                """Get the sort key for timestamp tags from the given ``t``"""
                value = t[tag_name]
                return value.timestamp() if value is not None else 0.0
        elif isinstance(example_value, str):  # key strips ignore words from string
            sort_key: Callable[[Item], (bool, str)] = lambda t: strip_ignore_words(t[tag_name])
        else:
            sort_key: Callable[[Item], object] = lambda t: t[tag_name] if t[tag_name] else 0

        items.sort(key=sort_key, reverse=reverse)

    @classmethod
    def group_by_field[T: Item](cls, items: UnitIterable[T], field: Field | None = None) -> dict[Any, list[T]]:
        """
        Group items by the values of a given field.

        :param items: List of items to sort.
        :param field: Tag or property to group by. None returns map of ``{None: <items>}``.
        :return: Map of grouped items.
        """
        if field is None:  # group by None
            return {None: to_collection(items, list)}

        tag_name = field.map(field)[0].name.lower()

        def group(v: Any) -> None:
            """Group items by the given value ``v``"""
            if grouped.get(v) is None:
                grouped[v] = []
            grouped[v].append(item)

        grouped: dict[Any | None, list[T]] = {}
        for item in items:  # produce map of grouped values
            value = to_collection(item[tag_name])
            if isinstance(value, Iterable):
                for val in value:
                    group(val)
            else:
                group(value)

        return grouped

    @classmethod
    def from_xml(cls, xml: Mapping[str, Any], **__) -> Self:
        fields: Sequence[Field] | Mapping[Field | bool]
        source = xml["SmartPlaylist"]["Source"]

        if "SortBy" in source:
            field_code = int(source["SortBy"].get("@Field", 0))
        elif "DefinedSort" in source:
            field_code = int(source["DefinedSort"]["@Id"])
        else:
            return

        if field_code in cls._custom_sort:
            fields = cls._custom_sort[field_code]
            return cls(fields=fields)
        else:
            field = Fields.from_value(field_code)[0]

        if field is None:
            return cls()
        elif "SortBy" in source:
            fields = {field: source["SortBy"]["@Order"] == "Descending"}
        elif "DefinedSort" in source:
            fields = [field]
        else:
            raise NotImplementedError("Sort type in XML not recognised")

        shuffle_mode = ShuffleMode.from_name(cls._pascal_to_snake(xml["SmartPlaylist"]["@ShuffleMode"]))[0]
        shuffle_by = ShuffleBy.from_name(cls._pascal_to_snake(xml["SmartPlaylist"]["@GroupBy"]))[0]
        shuffle_weight = float(xml["SmartPlaylist"].get("@ShuffleSameArtistWeight", 1))

        return cls(fields=fields, shuffle_mode=shuffle_mode, shuffle_by=shuffle_by, shuffle_weight=shuffle_weight)

    def to_xml(self, **kwargs) -> Mapping[str, Any]:
        raise NotImplementedError

    def __init__(
            self,
            fields: UnitSequence[Field | None] | Mapping[Field | None, bool] = (),
            shuffle_mode: ShuffleMode = ShuffleMode.NONE,
            shuffle_by: ShuffleBy = ShuffleBy.TRACK,
            shuffle_weight: float = 1.0
    ):
        super().__init__()
        fields = to_collection(fields, list) if isinstance(fields, Field) else fields
        self.sort_fields: Mapping[Field | None, bool]
        self.sort_fields = {field: False for field in fields} if isinstance(fields, Sequence) else fields

        self.shuffle_mode: ShuffleMode | None
        self.shuffle_mode = shuffle_mode if shuffle_mode in [ShuffleMode.NONE, ShuffleMode.RANDOM] else ShuffleMode.NONE
        self.shuffle_by: ShuffleBy | None = shuffle_by
        self.shuffle_weight = limit_value(shuffle_weight, floor=-1, ceil=1)

    def __call__(self, items: MutableSequence[Item]) -> None:
        return self.sort(items=items)

    def sort(self, items: MutableSequence[Item]) -> None:
        """Sorts a list of ``items`` in-place."""
        if len(items) == 0:
            return

        if self.shuffle_mode == ShuffleMode.RANDOM:  # random
            shuffle(items)
        elif self.shuffle_mode == ShuffleMode.NONE and self.sort_fields:  # sort by fields
            items_nested = self._sort_by_fields({None: items}, fields=self.sort_fields)
            items.clear()
            items.extend(flatten_nested(items_nested))
        elif not self.sort_fields:  # no sort
            return
        else:
            # TODO: implement all shuffle modes
            raise NotImplementedError(f"Shuffle mode not yet implemented: {self.shuffle_mode}")

    @classmethod
    def _sort_by_fields(cls, items_grouped: MutableMapping, fields: MutableMapping[Field, bool]) -> MutableMapping:
        """
        Sort items by the given fields recursively in the order given.

        :param items_grouped: Map of items grouped by the last sort value.
        :param fields: Map of ``{<tag/property>: <reversed>}``.
            If reversed is True, sort the ``tag/property`` in reverse.
        :return: Map of grouped and sorted items.
        """
        field, reverse = next(iter(fields.items()), (None, None))
        if field is None:  # sorting complete
            return items_grouped

        fields = copy(fields)
        fields.pop(field)

        # sort each group and recurse through each field for each group
        for i, (key, items) in enumerate(items_grouped.items(), 1):
            cls.sort_by_field(items=items, field=field, reverse=reverse)
            items_grouped[key] = cls._sort_by_fields(cls.group_by_field(items, field=field), fields=fields)

        return items_grouped

    def as_dict(self):
        fields = None
        if isinstance(self.sort_fields, Mapping):
            fields = {field.name: "desc" if r else "asc" for field, r in self.sort_fields.items()}

        return {
            "sort_fields": fields,
            "shuffle_mode": self.shuffle_mode,
            "shuffle_by": self.shuffle_by
        }
