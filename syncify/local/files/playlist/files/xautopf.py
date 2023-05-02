import re
from datetime import datetime, timedelta
from functools import reduce
from operator import mul
from random import shuffle
from typing import Optional, List, Mapping, Any, Set, Callable, Union, MutableMapping, Tuple, Self, Literal

import xmltodict
from dateutil.relativedelta import relativedelta

from syncify.local.files.track.tags import Name, PropertyNames, TagNames
from syncify.local.files.track.track import Track
from syncify.local.files.playlist.playlist import Playlist
from syncify.utils.helpers import make_list
from syncify.utils_new.generic import strip_ignore_words, flatten_nested


# Map of MusicBee field name to Tag or Property
_field_name_map = {
    "None": None,
    "Title": TagNames.TITLE,
    "ArtistPeople": TagNames.ARTIST,
    "Album": TagNames.ALBUM,  # album ignoring articles like 'the' and 'a' etc.
    "TrackNo": TagNames.TRACK,
    "GenreSplits": TagNames.GENRES,
    "Year": TagNames.YEAR,
    "Tempo": TagNames.BPM,
    "DiscNo": TagNames.DISC,
    "AlbumArtist": TagNames.ALBUM_ARTIST,
    "Comment": TagNames.COMMENTS,
    "FileDuration": PropertyNames.LENGTH,
    "FolderName": PropertyNames.FOLDER,
    "FilePath": PropertyNames.PATH,
    "FileName": PropertyNames.FILENAME,
    "FileExtension": PropertyNames.EXT,
    "FileDateAdded": PropertyNames.DATE_ADDED,
    "FilePlayCount": PropertyNames.PLAY_COUNT,
}


def _get_field_from_code(field_code: int) -> Optional[Name]:
    """Get the Tag or Property for a given MusicBee field code"""
    if field_code == 0:
        return
    elif field_code in [e.value for e in TagNames.all()]:
        return TagNames.from_value(field_code)
    elif field_code in [e.value for e in PropertyNames.all()]:
        return PropertyNames.from_value(field_code)
    elif field_code == 78:  # album including articles like 'the' and 'a' etc.
        return TagNames.ALBUM  # album ignoring articles like 'the' and 'a' etc.
    else:
        raise ValueError(f"Field code not recognised: {field_code}")


class ValueCompare:

    _td_str_mapper = {
        "h": lambda x: timedelta(hours=int(x)),
        "d": lambda x: timedelta(days=int(x)),
        "w": lambda x: timedelta(weeks=int(x)),
        "m": lambda x: relativedelta(months=int(x))
    }

    def __init__(self, value: Any, expected: List[Any]) -> None:
        self._value: Any = value
        self._expected: List[Any] = expected
        self.convert_types()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value: Any):
        self._value = value
        self.convert_types()

    @property
    def expected(self) -> List[Any]:
        return self._expected

    @expected.setter
    def expected(self, expected: List[Any]):
        self._expected = expected
        self.convert_types()

    @classmethod
    def from_xml(
            cls, condition: Mapping[str, str], last_played: Track = None
    ) -> Tuple[Self, Callable[[], bool]]:

        field = _field_name_map.get(condition.get("@Field", "None"))
        expected: List[str] = [val for k, val in condition.items() if k.startswith("@Value")]
        if expected[0] == '[playing track]':
            if last_played is not None and field is not None:
                expected = [getattr(last_played, field.name.lower(), None)]
            else:
                expected.clear()

        compare_str = condition["@Comparison"]
        compare_str = re.sub('([A-Z])', lambda m: f"_{m.group(0).lower()}", compare_str)

        obj = cls(None, expected)
        return obj, getattr(obj, compare_str)

    def set_value_from_track(self, track: Track, field: Optional[Name]) -> None:
        self.value = getattr(track, field.name.lower(), None)

    def convert_types(self) -> None:
        if isinstance(self.value, int):
            self.convert_expected_to_int()
        elif isinstance(self.value, float):
            self.convert_expected_to_float()
        elif isinstance(self.value, datetime):
            self.convert_expected_to_dt()
        elif isinstance(self.value, bool):
            self._expected = None

    def convert_expected_to_int(self) -> None:
        converted: List[int] = []
        for exp in self.expected:
            if not isinstance(exp, int) or not isinstance(exp, float) and ":" in exp:
                exp = self._get_seconds(exp)
            converted.append(int(exp))
        self._expected = converted

    def convert_expected_to_float(self) -> None:
        converted: List[float] = []
        for exp in self.expected:
            if not isinstance(exp, int) or not isinstance(exp, float) and ":" in exp:
                exp = self._get_seconds(exp)
            converted.append(float(exp))
        self._expected = converted

    def convert_expected_to_dt(self) -> None:
        converted: List[datetime | Any] = []

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
    def _get_seconds(time_str: str) -> float:
        factors = [24, 60, 60, 1]
        digits_split = time_str.split(":")
        digits = [int(n.split(",")[0]) for n in digits_split]
        seconds = int(digits_split[-1].split(",")[1]) / 1000

        for i, digit in enumerate(digits, 1):
            seconds += digit * reduce(mul, factors[-i:], 1)

        return seconds

    def _is(self) -> bool:
        return self.value == self._expected[0]

    def _is_not(self) -> bool:
        return not self._is()

    def _is_after(self) -> bool:
        return self.value > self._expected[0]

    def _is_before(self) -> bool:
        return self.value < self._expected[0]

    def _is_in_the_last(self) -> bool:
        return self._is_after()

    def _is_not_in_the_last(self) -> bool:
        return self._is_before()

    def _is_in(self) -> bool:
        return self.value in self._expected

    def _is_not_in(self) -> bool:
        return not self._is_in()

    def _greater_than(self) -> bool:
        return self.value > self._expected[0]

    def _less_than(self) -> bool:
        return self.value < self._expected[0]

    def _in_range(self) -> bool:
        return self._expected[0] < self.value < self._expected[1]

    def _not_in_range(self) -> bool:
        return not self._in_range()

    def _is_not_null(self) -> bool:
        return self.value is not None or self.value is True

    def _is_null(self) -> bool:
        return self.value is None or self.value is False

    def _starts_with(self) -> bool:
        return self.value.startswith(self._expected[0])

    def _ends_with(self) -> bool:
        return self.value.endswith(self._expected[0])

    def _contains(self) -> bool:
        return self._expected[0] in self.value

    def _does_not_contain(self) -> bool:
        return not self._contains()

    def _in_tag_hierarchy(self) -> bool:
        # TODO: what even is this
        raise NotImplementedError

    def _matches_reg_ex(self) -> bool:
        return bool(re.search(self._expected[0], self.value))

    def _matches_reg_ex_ignore_case(self) -> bool:
        return bool(re.search(self._expected[0], self.value, flags=re.IGNORECASE))


class TrackSort:
    """
    Sort tracks inplace.

    :param fields:
        * List of tags/properties to sort by.
        * Map of {``tag/property``: ``reversed``}. If reversed is true, sort the ``tag/property`` in reverse.
    :param shuffle_mode: String representation of the shuffle mode to use
    """

    _custom_sort: Mapping[int, Mapping[Name, bool]] = {
        6: {
            TagNames.ALBUM: False,
            TagNames.DISC: False,
            TagNames.TRACK: False,
            PropertyNames.FILENAME: False
        }
    }

    def __init__(
            self,
            fields: Optional[Union[List[Name], Mapping[Name, bool]]] = None,
            shuffle_mode: Optional[Literal['None']] = None
    ):
        self.fields: Union[List[Name], Mapping[Name, bool]] = fields
        self.shuffle_mode: Optional[str] = shuffle_mode

    @classmethod
    def from_xml(cls, xml: Optional[Mapping[str, Any]] = None) -> Self:
        """
        Initialise Sort object from XML playlist.

        :param xml: The loaded XML object for this playlist.
            If None, sorter will shuffle randomly when calling ``sort``.
        """
        fields: Union[List[Name], Mapping[Name, bool]]
        if xml is None:
            return cls()

        source = xml["SmartPlaylist"]["Source"]
        shuffle_mode = xml["SmartPlaylist"]["@ShuffleMode"]

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
            field = _get_field_from_code(field_code)

        if field is None:
            return cls(shuffle_mode=shuffle_mode)
        elif "SortBy" in source:
            fields = {field: source["SortBy"]["@Order"] == "Descending"}
        elif "DefinedSort" in source:
            fields = [field]
        else:
            raise ValueError("Sort type in XML not recognised")

        return cls(fields=fields, shuffle_mode=shuffle_mode)

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
            sort_value: Callable[[Track], float] = lambda track: getattr(track, tag_name, default).timestamp()
        elif isinstance(example_value, str):
            sort_value: Callable[[Track], Tuple[bool, str]] = \
                lambda track: strip_ignore_words(getattr(track, tag_name, ""))
        else:
            sort_value: Callable[[Track], object] = lambda track: getattr(track, tag_name, 0)

        sorted(tracks, key=sort_value, reverse=reverse)

    def sort(self, tracks: List[Track]) -> None:
        """Sorts a list of tracks inplace."""
        if self.shuffle_mode == "None":
            tracks_grouped = self.group_by_field(tracks, field=next(iter(self.fields), None))
            tracks_nested = self._sort_by_fields(tracks_grouped, fields=self.fields)

            tracks.clear()
            tracks.extend(flatten_nested(tracks_nested))
        else:  # only random sort supported
            # TODO: implement other shuffle modes
            shuffle(tracks)

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


class TrackLimit:

    # TODO: split these to individual methods
    _limit_sort_func = {
        "Random": lambda tracks: shuffle(tracks),
        "HighestRating":
            lambda tracks: TrackSort.sort_by_field(tracks, PropertyNames.RATING, reverse=True),
        "LowestRating":
            lambda tracks: TrackSort.sort_by_field(tracks, PropertyNames.RATING, reverse=False),
        "MostRecentlyPlayed":
            lambda tracks: TrackSort.sort_by_field(tracks, PropertyNames.LAST_PLAYED, reverse=True),
        "LeastRecentlyPlayed":
            lambda tracks: TrackSort.sort_by_field(tracks, PropertyNames.LAST_PLAYED, reverse=False),
        "MostOftenPlayed":
            lambda tracks: TrackSort.sort_by_field(tracks, PropertyNames.PLAY_COUNT, reverse=True),
        "LeastOftenPlayed":
            lambda tracks: TrackSort.sort_by_field(tracks, PropertyNames.PLAY_COUNT, reverse=False),
        "MostRecentlyAdded":
            lambda tracks: TrackSort.sort_by_field(tracks, PropertyNames.DATE_ADDED, reverse=True),
        "LeastRecentlyAdded":
            lambda tracks: TrackSort.sort_by_field(tracks, PropertyNames.DATE_ADDED, reverse=False),
    }
    _limit_unit_conversion_func = {
        "Minutes": lambda track: track.length / 60,
        "Hours": lambda track: track.length / (60 * 60),
        "Megabytes": lambda track: track.size / (1000 ** 2),
        "Gigabytes": lambda track: track.size / (1000 ** 3),
    }

    def __init__(self, conditions: Optional[Mapping[str, str]] = None):
        self.conditions: Optional[Mapping[str, str]] = conditions

    @classmethod
    def from_xml(cls, xml: Optional[Mapping[str, Any]] = None):
        if xml is None:
            return cls()

        conditions: Mapping[str, str] = xml["SmartPlaylist"]["Source"]["Limit"]
        return cls(conditions)

    def limit(self, tracks: List[Track]) -> None:
        """
        Limit tracks inplace based on set conditions
        """
        if self.conditions["Enabled"] != "True":
            return

        tracks_sorted = self._limit_sort_func[self.conditions["@SelectedBy"]](tracks)
        limit = int(self.conditions["@Count"])
        kind = self.conditions["@Type"]
        # filter_duplicates = conditions["@FilterDuplicates"] == "True"

        tracks.clear()

        if kind == "Items":
            tracks.extend(tracks_sorted[:limit])
        elif kind == "Albums":
            seen_albums = []
            for track in tracks_sorted:
                tracks.append(track)
                if track.album not in seen_albums:
                    seen_albums.append(track['album'])

                if len(seen_albums) >= limit:
                    break
        else:
            count = 0
            for track in tracks_sorted:
                # MusicBee appears to have some extra allowance on this limit of ~1.25
                if count + self._limit_unit_conversion_func[kind](track) <= limit * 1.25:
                    tracks.append(track)
                    count += self._limit_unit_conversion_func[kind](track)
                if count > limit:
                    break


class XAutoPF(Playlist):
    """
    For reading and writing data from MusicBee's auto-playlist format.

    **Note**: You must provide a list of tracks to search on initialisation for this playlist type.

    :param path: Full path of the playlist.
    :param tracks: Available Tracks to search through for matches. Required.
    :param library_folder: Full path of folder containing tracks.
    :param other_folders: Full paths of other possible library paths.
        Use to replace path stems from other libraries for the paths in loaded playlists.
        Useful when managing similar libraries on multiple platforms.
    """

    playlist_ext = [".xautopf"]

    def __init__(
            self,
            path: str,
            tracks: List[Track],
            library_folder: Optional[str] = None,
            other_folders: Optional[Set[str]] = None
    ):
        self.xml: Optional[Mapping[str, Any]] = None
        Playlist.__init__(self, path=path, tracks=tracks, library_folder=library_folder, other_folders=other_folders)

    def load(self, tracks: Optional[List[Track]] = None) -> Optional[List[Track]]:
        """
        Read the playlist file.

        **Note**: You must provide a list of tracks for this playlist type.

        :param tracks: Available Tracks to search through for matches.
        :return: Ordered list of tracks in this playlist
        """
        if tracks is None:
            raise ValueError("This playlist type requires that you provide a list of loaded tracks")

        with open(self.path, "r", encoding='utf-8') as f:
            self.xml: Mapping[str, Any] = xmltodict.parse(f.read())

        source = self.xml["SmartPlaylist"]["Source"]
        self.description = source["Description"]

        conditions: List[Mapping[str, str]] = make_list(source["Conditions"]["Condition"])  # match conditions
        combine_str: str = source["Conditions"]["@CombineMethod"]  # how to combine match conditions
        combine: Callable[[List[bool]], bool] = lambda x: any(x) if combine_str == "Any" else all(x)

        include_str: str = source.get("ExceptionsInclude")  # tracks to include even if they don't meet match conditions
        include: Optional[List[str]] = include_str.split("|") if isinstance(include_str, str) else None
        exclude_str: str = source.get("Exceptions")  # tracks to exclude even if they do meet match conditions
        exclude: Optional[List[str]] = exclude_str.split("|") if isinstance(exclude_str, str) else None

        if include is not None:
            self._check_for_other_folder_stem(include)
            include = [self._sanitise_file_path(path) for path in include]
            include = [path for path in include if path is not None]
        if exclude is not None:
            if self._original_folder is None:
                self._check_for_other_folder_stem(include)
            include = [self._sanitise_file_path(path) for path in include]
            include = [path for path in include if path is not None]

        tracks = self._match(tracks=tracks, conditions=conditions, combine=combine, include=include, exclude=exclude)
        self._limit(tracks)
        self._sort(tracks)

        return tracks

    @staticmethod
    def _match(
            tracks: List[Track],
            conditions: List[Mapping[str, str]],
            combine: Callable[[List[bool]], bool],
            include: Optional[List[str]] = None,
            exclude: List[str] = None
    ) -> List[Track]:
        """
        Return a new list of tracks from input tracks that match the given conditions.

        :param tracks: List of tracks to search through for matches.
        :param conditions: Main match conditions.
        :param combine: Function for combining match conditions.
        :param include: Tracks to include even if they don't meet match conditions.
        :param exclude: Tracks to exclude even if they do meet match conditions.
        :return: Ordered list of tracks that match the conditions.
        """
        matches = []
        TrackSort.sort_by_field(tracks, field=PropertyNames.LAST_PLAYED, reverse=True)
        last_played = tracks[0]

        for condition in conditions:
            comparer, match = ValueCompare.from_xml(condition, last_played=last_played)
            field = _field_name_map.get(condition.get("@Field", "None"))

            for track in tracks:
                if include and track.path in include:
                    matches.append(track)
                    continue
                elif exclude and track.path in exclude:
                    continue

                match_results = []
                comparer.set_value_from_track(track, field)
                match_results.append(match())

                if combine(match_results):
                    matches.append(track)

        return matches

    def _sort(self, tracks: List[Track]) -> None:
        """Sort tracks inplace"""
        TrackSort.from_xml(xml=self.xml).sort(tracks=tracks)

    def _limit(self, tracks: List[Track]) -> None:
        """Limit tracks inplace"""
        TrackLimit.from_xml(xml=self.xml).limit(tracks=tracks)

    def write(self, tracks: List[Track]) -> int:
        raise NotImplementedError
