from copy import copy
from datetime import datetime
from random import shuffle
from typing import Any, Callable, List, Mapping, MutableMapping, Optional, Self, Tuple, Union

from syncify.abstract import SyncifyEnum
from syncify.local.files.track.base import Name, PropertyName, TagName, LocalTrack
from syncify.local.files.track.collection.processor import TrackProcessor
from syncify.utils_new.helpers import UnionList, flatten_nested, strip_ignore_words, make_list


def get_field_from_code(field_code: int) -> Optional[Name]:
    """Get the Tag or Property for a given MusicBee field code"""
    if field_code == 0:
        return
    elif field_code in [e.value for e in TagName.all()]:
        return TagName.from_value(field_code)
    elif field_code in [e.value for e in PropertyName.all()]:
        return PropertyName.from_value(field_code)
    elif field_code == 78:  # album including articles like 'the' and 'a' etc.
        return TagName.ALBUM  # album ignoring articles like 'the' and 'a' etc.
    else:
        raise ValueError(f"Field code not recognised: {field_code}")


class ShuffleMode(SyncifyEnum):
    NONE = 0
    RANDOM = 1
    HIGHER_RATING = 2
    RECENT_ADDED = 3
    DIFFERENT_ARTIST = 3


class ShuffleBy(SyncifyEnum):
    TRACK = 0
    ALBUM = 1
    ARTIST = 2


class TrackSort(TrackProcessor):
    """
    Sort tracks inplace based on given conditions.

    :param fields:
        * When None and ShuffleMode is RANDOM, shuffle the tracks. Otherwise, do nothing.
        * List of tags/properties to sort by.
        * Map of {``tag/property``: ``reversed``}. If reversed is true, sort the ``tag/property`` in reverse.
    :param shuffle_mode: The mode to use for shuffling.
    :param shuffle_by: The field to shuffle by when shuffling.
    :param shuffle_weight: The weights (between 0 and 1) to apply to shuffling modes that can use it.
        This value will automatically be limited to within the accepted range 0 and 1.
    """

    _custom_sort: Mapping[int, Mapping[Name, bool]] = {
        6: {
            TagName.ALBUM: False,
            TagName.DISC: False,
            TagName.TRACK: False,
            PropertyName.FILENAME: False
        }
    }

    @staticmethod
    def sort_by_field(tracks: List[LocalTrack], field: Optional[Name] = None, reverse: bool = False) -> None:
        """
        Sort tracks by the values of a given field.

        :param tracks: List of tracks to sort
        :param field: Tag or property to sort on. If None and reverse is True, reverse the order of the list.
        :param reverse: If true, reverse the order of the sort.
        """
        if field is None:
            if reverse:
                tracks.reverse()
            return

        tag_name = field.to_tag(field)[0] if isinstance(field, TagName) else field.name.lower()
        example_value = None
        for track in tracks:
            example_value = getattr(track, tag_name)
            if example_value is not None:
                break

        if example_value is None:
            return

        if isinstance(example_value, datetime):
            def sort_key(t: LocalTrack) -> float:
                value = getattr(t, tag_name)
                return value.timestamp() if value is not None else 0.0
        elif isinstance(example_value, str):
            sort_key: Callable[[LocalTrack], Tuple[bool, str]] = lambda t: strip_ignore_words(getattr(t, tag_name, ""))
        else:
            sort_key: Callable[[LocalTrack], object] = lambda t: getattr(t, tag_name, 0)

        tracks.sort(key=sort_key, reverse=reverse)

    @classmethod
    def group_by_field(
            cls, tracks: List[LocalTrack], field: Optional[Name] = None
    ) -> MutableMapping[Any, List[LocalTrack]]:
        """
        Group tracks by the values of a given field.

        :param tracks: List of tracks to sort.
        :param field: Tag or property to group by. None returns map of {``None``: ``tracks``}.
        :return: Map of grouped tracks.
        """
        if field is None:
            return {None: tracks}

        grouped: MutableMapping[Optional[Any], List[LocalTrack]] = {}

        for track in tracks:
            tag_name = field.to_tag(field)[0] if isinstance(field, TagName) else field.name.lower()
            value = getattr(track, tag_name, None)
            if grouped.get(value) is None:
                grouped[value] = []

            grouped[value].append(track)

        return grouped

    @classmethod
    def from_xml(cls, xml: Optional[Mapping[str, Any]] = None) -> Self:
        """
        Initialise object from XML playlist.

        :param xml: The loaded XML object for this playlist.
            If None, sorter will shuffle randomly when calling ``sort``.
        """
        fields: Union[List[Name], Mapping[Name, bool]]
        if xml is None:
            return cls()

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
            field = get_field_from_code(field_code)

        if field is None:
            return cls()
        elif "SortBy" in source:
            fields = {field: source["SortBy"]["@Order"] == "Descending"}
        elif "DefinedSort" in source:
            fields = [field]
        else:
            raise NotImplementedError("Sort type in XML not recognised")

        shuffle_mode = ShuffleMode.from_name(cls._camel_to_snake(xml["SmartPlaylist"]["@ShuffleMode"]))
        shuffle_by = ShuffleBy.from_name(cls._camel_to_snake(xml["SmartPlaylist"]["@GroupBy"]))
        shuffle_weight = float(xml["SmartPlaylist"].get("@ShuffleSameArtistWeight", 1))

        return cls(fields=fields, shuffle_mode=shuffle_mode, shuffle_by=shuffle_by, shuffle_weight=shuffle_weight)

    def __init__(
            self,
            fields: Optional[Union[UnionList[Optional[Name]], MutableMapping[Optional[Name], bool]]] = None,
            shuffle_mode: ShuffleMode = ShuffleMode.NONE,
            shuffle_by: ShuffleBy = ShuffleBy.TRACK,
            shuffle_weight: float = 1.0
    ):
        fields = make_list(fields) if isinstance(fields, Name) else fields
        if isinstance(fields, list):
            self.sort_fields: MutableMapping[Name, bool] = {field: False for field in fields}
        else:
            self.sort_fields: MutableMapping[Name, bool] = fields

        self.shuffle_mode: Optional[ShuffleMode] = \
            shuffle_mode if shuffle_mode in [ShuffleMode.NONE, ShuffleMode.RANDOM] else ShuffleMode.NONE
        self.shuffle_by: Optional[ShuffleBy] = shuffle_by
        self.shuffle_weight = max(min(shuffle_weight, 1.0), 0.0)

    def sort(self, tracks: List[LocalTrack]) -> None:
        """Sorts a list of tracks inplace."""
        if len(tracks) == 0:
            return

        if self.shuffle_mode == ShuffleMode.RANDOM:
            shuffle(tracks)
        elif self.shuffle_mode == ShuffleMode.NONE and self.sort_fields is not None:
            tracks_nested = self._sort_by_fields({None: tracks}, fields=self.sort_fields)
            tracks.clear()
            tracks.extend(flatten_nested(tracks_nested))
        elif self.sort_fields is None:
            return
        else:
            raise NotImplementedError(f"Shuffle mode not yet implemented: {self.shuffle_mode}")

    @classmethod
    def _sort_by_fields(cls, tracks_grouped: MutableMapping, fields: MutableMapping[Name, bool]) -> MutableMapping:
        """
        Sort tracks by the given fields recursively in the order given.

        :param tracks_grouped: Map of tracks grouped by the last sort value.
        :param fields: Map of {``tag/property``: ``reversed``}.
            If reversed is True, sort the ``tag/property`` in reverse.
        :return: Map of grouped and sorted tracks.
        """
        field, reverse = next(iter(fields.items()), (None, None))
        if field is None:
            return tracks_grouped

        fields = copy(fields)
        fields.pop(field)
        tag_name = field.to_tag(field)[0] if isinstance(field, TagName) else field.name.lower()

        for i, (key, tracks) in enumerate(tracks_grouped.items(), 1):
            tracks.sort(key=lambda t: (getattr(t, tag_name) is None, getattr(t, tag_name)), reverse=reverse)
            tracks_grouped[key] = cls._sort_by_fields(cls.group_by_field(tracks, field=field), fields=fields)

        return tracks_grouped

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "sort_fields": {field.name: "desc" if r else "asc" for field, r in self.sort_fields.items()},
            "shuffle_mode": self.shuffle_mode,
            "shuffle_by": self.shuffle_by
        }
