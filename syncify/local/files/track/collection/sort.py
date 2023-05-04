from datetime import datetime
from random import shuffle
from typing import Any, Callable, List, Mapping, MutableMapping, Optional, Self, Tuple, Union

from syncify.local.files.track.base import Name, PropertyName, TagName, Track
from syncify.local.files.track.collection.processor import TrackProcessor, Mode
from syncify.local.files.utils.musicbee import get_field_from_code
from syncify.utils_new.generic import flatten_nested, strip_ignore_words


class ShuffleMode(Mode):
    NONE = 0
    RANDOM = 1
    HIGHER_RATING = 2
    RECENT_ADDED = 3
    DIFFERENT_ARTIST = 3


class ShuffleBy(Mode):
    TRACK = 0
    ALBUM = 1
    ARTIST = 2


class TrackSort(TrackProcessor):
    """
    Sort tracks inplace based on given conditions.

    :param fields:
        * List of tags/properties to sort by.
        * Map of {``tag/property``: ``reversed``}. If reversed is true, sort the ``tag/property`` in reverse.
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
    def sort_by_field(tracks: List[Track], field: Optional[Name], reverse: bool = False) -> None:
        """
        Sort tracks by the values of a given field.

        :param tracks: List of tracks to sort
        :param field: Tag or property to sort on. None just shuffles the tracks. If None, shuffle randomly.
        :param reverse: If true, reverse the order of the sort.
        """
        if field is None:
            shuffle(tracks)
            return

        tag_name = field.name.lower()
        example_value = None
        for track in tracks:
            example_value = getattr(track, tag_name)
            if example_value is not None:
                break

        if example_value is None:
            return

        if isinstance(example_value, datetime):
            default = datetime.fromtimestamp(0)
            sort_value: Callable[[Track], float] = lambda t: getattr(t, tag_name, default).timestamp()
        elif isinstance(example_value, str):
            sort_value: Callable[[Track], Tuple[bool, str]] = lambda t: strip_ignore_words(getattr(t, tag_name, ""))
        else:
            sort_value: Callable[[Track], object] = lambda t: getattr(t, tag_name, 0)

        sorted(tracks, key=sort_value, reverse=reverse)

    @classmethod
    def group_by_field(cls, tracks: List[Track], field: Optional[Name]) -> MutableMapping[Any, List[Track]]:
        """
        Group tracks by the values of a given field.

        :param tracks: List of tracks to sort.
        :param field: Tag or property to group by. None returns map of {``None``: ``tracks``}.
        :return: Map of grouped tracks.
        """
        if field is None:
            return {None: tracks}

        grouped: MutableMapping[Optional[Any], List[Track]] = {}

        for track in tracks:
            value = getattr(track, field.name.lower(), None)
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
            raise ValueError("Sort type in XML not recognised")

        shuffle_mode = ShuffleMode.from_name(cls._camel_to_snake(xml["SmartPlaylist"]["@ShuffleMode"]))
        shuffle_by = ShuffleBy.from_name(cls._camel_to_snake(xml["SmartPlaylist"]["@GroupBy"]))
        shuffle_weight = float(xml["SmartPlaylist"].get("@ShuffleSameArtistWeight", 1))

        return cls(fields=fields, shuffle_mode=shuffle_mode, shuffle_by=shuffle_by, shuffle_weight=shuffle_weight)

    def __init__(
            self,
            fields: Optional[Union[List[Name], Mapping[Name, bool]]] = None,
            shuffle_mode: Optional[ShuffleMode] = None,
            shuffle_by: Optional[ShuffleBy] = None,
            shuffle_weight: float = 1.0
    ):
        self.sort_fields: Union[List[Name], Mapping[Name, bool]] = fields
        self.shuffle_mode: Optional[ShuffleMode] = shuffle_mode
        self.shuffle_by: Optional[ShuffleBy] = shuffle_by
        self.shuffle_weight = shuffle_weight

    def sort(self, tracks: List[Track]) -> None:
        """Sorts a list of tracks inplace."""
        if self.sort_fields is None:
            return

        if self.shuffle_mode == ShuffleMode.NONE:
            tracks_grouped = self.group_by_field(tracks, field=next(iter(self.sort_fields), None))
            tracks_nested = self._sort_by_fields(tracks_grouped, fields=self.sort_fields)

            tracks.clear()
            tracks.extend(flatten_nested(tracks_nested, sort_keys=True, sort_ignore=True))
        elif self.shuffle_mode == ShuffleMode.RANDOM:
            shuffle(tracks)
        else:
            NotImplementedError(f"Shuffle mode not yet implemented: {self.shuffle_mode}")

    @classmethod
    def _sort_by_fields(
            cls, tracks_grouped: MutableMapping, fields: Optional[Union[List[Name], Mapping[Name, bool]]]
    ) -> MutableMapping:
        """
        Sort tracks by the given fields recursively in the order given.

        :param tracks_grouped: Map of tracks grouped by the last sort value.
        :param fields:
            * List of tags or properties to sort by.
            * Map of {``tag/property``: ``reversed``}. If reversed is true, sort the ``tag/property`` in reverse.
            * None just shuffles the tracks.
        :return: Map of grouped and sorted tracks.
        """
        if isinstance(fields, list):
            fields = {field: False for field in fields}

        field = next(iter(fields), None)

        if field is None:
            return tracks_grouped
        elif len(fields) == 1:
            for tracks in tracks_grouped.values():
                cls.sort_by_field(tracks, field=field, reverse=fields[field])
        else:
            fields = fields.copy()
            fields.pop(field)
            field = next(iter(fields))
            for key, tracks in tracks_grouped.items():
                tracks_grouped[key] = cls.group_by_field(tracks, field=field)

        return tracks_grouped

    def as_dict(self) -> MutableMapping[str, object]:
        return {
            "sort_fields": {field.name: "desc" if r else "asc" for field, r in self.sort_fields.items()},
            "shuffle_mode": self.shuffle_mode,
            "shuffle_by": self.shuffle_by
        }
