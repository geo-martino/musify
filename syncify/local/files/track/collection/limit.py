import re
from enum import IntEnum
from random import shuffle
from typing import Any, Callable, List, Mapping, Optional, Self

from syncify.local.files.track.collection.processor import TrackProcessor
from syncify.local.files.utils.exception import EnumNotFoundError
from syncify.local.files.track.collection.sort import TrackSort
from syncify.local.files.track.tags import PropertyNames
from syncify.local.files.track.track import Track


class LimitType(IntEnum):
    ITEMS = 0
    ALBUMS = 1

    SECONDS = 11
    MINUTES = 12
    HOURS = 13
    DAYS = 14
    WEEKS = 15

    BYTES = 21
    KILOBYTES = 22
    MEGABYTES = 23
    GIGABYTES = 24
    TERABYTES = 25

    @classmethod
    def from_name(cls, name: str) -> Self:
        """
        Returns the first enum that matches the given name

        :exception EnumNotFoundError: If a corresponding enum cannot be found.
        """
        for enum in cls:
            if enum.name.startswith(name.split("_")[0].upper()):
                return enum
        raise EnumNotFoundError(name)


class TrackLimit(TrackProcessor):
    """
    Sort tracks inplace based on given conditions.

    :param limit: The number of tracks to limit to.
    :param on: The type to limit on e.g. items, albums, minutes.
    :param sorted_by: When limiting, sort the collection of tracks by this function first.
    :param allowance: When limit on bytes or length, add this extra allowance to the max size limit.
    """

    @property
    def limit_sort(self) -> str:
        return self._limit_sort

    @limit_sort.getter
    def limit_sort(self) -> str:
        return self._limit_sort

    @limit_sort.setter
    def limit_sort(self, value: str):
        sort_sanitised = self._sort_method_prefix + re.sub('([A-Z])', lambda m: f"_{m.group(0).lower()}", value)

        if sort_sanitised not in self._valid_conditions:
            valid_methods_str = ", ".join([c.replace(self._sort_method_prefix, "") for c in self._valid_conditions])
            raise ValueError(
                f"Unrecognised sort method: {value} | " 
                f"Valid sort methods: {valid_methods_str}"
            )

        self._limit_sort = sort_sanitised.replace("_", " ").strip()
        self._sort_method = getattr(self, sort_sanitised)

    def __init__(
            self,
            limit: int = 0,
            on: Optional[LimitType] = LimitType.ITEMS,
            sorted_by: Optional[str] = None,
            allowance: float = 1.25
    ):
        self._sort_method: Callable[[List[Track]], None] = lambda _: None

        self.limit = limit
        self.kind = on
        self.allowance = allowance

        self._sort_method_prefix = "_sort_"
        self._valid_conditions = [cond for cond in self.__annotations__ if cond.startswith(self._sort_method_prefix)]
        self.limit_sort = sorted_by

    @classmethod
    def from_xml(cls, xml: Optional[Mapping[str, Any]] = None) -> Optional[Self]:
        if xml is None:
            return cls()

        conditions: Mapping[str, str] = xml["SmartPlaylist"]["Source"]["Limit"]
        if conditions["Enabled"] != "True":
            return
        # filter_duplicates = conditions["@FilterDuplicates"] == "True"

        # MusicBee appears to have some extra allowance on time and byte limits of ~1.25
        return cls(
            limit=int(conditions["@Count"]),
            on=LimitType.from_name(conditions["@Type"]),
            sorted_by=conditions["@SelectedBy"],
            allowance=1.25
        )

    def limit(self, tracks: List[Track]) -> None:
        """Limit tracks inplace based on set conditions"""
        self._sort_method(tracks)

        tracks_limit = tracks.copy()
        tracks.clear()

        if self.kind == LimitType.ITEMS:
            tracks.extend(tracks_limit[:self.limit])
        elif self.kind == LimitType.ALBUMS:
            seen_albums = []
            for track in tracks_limit:
                tracks.append(track)
                if track.album not in seen_albums:
                    seen_albums.append(track.album)

                if len(seen_albums) >= self.limit:
                    break
        else:
            count = 0
            for track in tracks_limit:
                value = self._convert(track)

                if count + value <= self.limit * self.allowance:
                    tracks.append(track)
                    count += value

                if count > self.limit:
                    break

    @staticmethod
    def _sort_random(tracks: List[Track]) -> None:
        shuffle(tracks)

    @staticmethod
    def _sort_highest_rating(tracks: List[Track]) -> None:
        TrackSort.sort_by_field(tracks, PropertyNames.RATING, reverse=True)

    @staticmethod
    def _sort_lowest_rating(tracks: List[Track]) -> None:
        TrackSort.sort_by_field(tracks, PropertyNames.RATING, reverse=False)

    @staticmethod
    def _sort_most_recently_played(tracks: List[Track]) -> None:
        TrackSort.sort_by_field(tracks, PropertyNames.LAST_PLAYED, reverse=True)

    @staticmethod
    def _sort_least_recently_played(tracks: List[Track]) -> None:
        TrackSort.sort_by_field(tracks, PropertyNames.LAST_PLAYED, reverse=False)

    @staticmethod
    def _sort_most_often_played(tracks: List[Track]) -> None:
        TrackSort.sort_by_field(tracks, PropertyNames.PLAY_COUNT, reverse=True)

    @staticmethod
    def _sort_least_often_played(tracks: List[Track]) -> None:
        TrackSort.sort_by_field(tracks, PropertyNames.PLAY_COUNT, reverse=False)

    @staticmethod
    def _sort_most_recently_added(tracks: List[Track]) -> None:
        TrackSort.sort_by_field(tracks, PropertyNames.DATE_ADDED, reverse=True)

    @staticmethod
    def _sort_least_recently_added(tracks: List[Track]) -> None:
        TrackSort.sort_by_field(tracks, PropertyNames.DATE_ADDED, reverse=False)

    def _convert(self, track: Track) -> float:
        """Convert units for track length or size"""
        if self.kind == LimitType.SECONDS:
            return track.length
        elif self.kind == LimitType.MINUTES:
            return track.length / 60
        elif self.kind == LimitType.HOURS:
            return track.length / (60 * 60)
        elif self.kind == LimitType.DAYS:
            return track.length / (60 * 60 * 24)
        elif self.kind == LimitType.WEEKS:
            return track.length / (60 * 60 * 24 * 7)
        else:
            bytes_scale = 1000
            return track.size / (self.kind.value % 10 * bytes_scale)
