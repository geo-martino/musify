from random import shuffle
from typing import Any, Callable, List, Mapping, Optional, Self, MutableMapping, Set

from syncify.local.files.track.base import PropertyName, Track
from syncify.local.files.track.collection.processor import TrackProcessor, Mode
from syncify.local.files.track.collection.sort import TrackSort


class LimitType(Mode):
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


class TrackLimit(TrackProcessor):
    """
    Sort tracks inplace based on given conditions.

    :param limit: The number of tracks to limit to. A value of 0 applies no limiting.
    :param on: The type to limit on e.g. items, albums, minutes.
    :param sorted_by: When limiting, sort the collection of tracks by this function first.
    :param allowance: When limit on bytes or length, add this extra allowance to the max size limit.
    """

    @property
    def limit_sort(self) -> Optional[str]:
        return self._limit_sort

    @limit_sort.getter
    def limit_sort(self) -> Optional[str]:
        return self._limit_sort

    @limit_sort.setter
    def limit_sort(self, value: Optional[str]):
        if value is None:
            return

        name = self._get_method_name(value, valid=self._valid_methods, prefix=self._sort_method_prefix)
        self._limit_sort = self._snake_to_camel(name, prefix=self._sort_method_prefix)
        self._sort_method = getattr(self, name)

    @classmethod
    def from_xml(cls, xml: Optional[Mapping[str, Any]] = None) -> Optional[Self]:
        if xml is None:
            return cls()

        conditions: Mapping[str, str] = xml["SmartPlaylist"]["Source"]["Limit"]
        if conditions["@Enabled"] != "True":
            return
        # filter_duplicates = conditions["@FilterDuplicates"] == "True"

        # MusicBee appears to have some extra allowance on time and byte limits of ~1.25
        return cls(
            limit=int(conditions["@Count"]),
            on=LimitType.from_name(conditions["@Type"]),
            sorted_by=conditions["@SelectedBy"],
            allowance=1.25
        )

    def __init__(
            self,
            limit: int = 0,
            on: Optional[LimitType] = LimitType.ITEMS,
            sorted_by: Optional[str] = None,
            allowance: float = 1.25,
    ):
        self._sort_method: Callable[[List[Track]], None] = lambda _: None

        self.limit_max = limit
        self.kind = on
        self.allowance = allowance

        self._sort_method_prefix = "_sort"
        self._valid_methods = [name for name in dir(self) if name.startswith(self._sort_method_prefix)]
        self.limit_sort = sorted_by

    def limit(self, tracks: List[Track], ignore: Optional[Set[str]] = None) -> None:
        """
        Limit tracks inplace based on set conditions.
        Optionally set a list of paths of tracks to ignore when limiting i.e. keep them in the list regardless.
        """
        if len(tracks) == 0 or self.kind is None or self.limit_max == 0:
            return

        self._sort_method(tracks)

        if ignore is not None:
            tracks_limit = [track for track in tracks if track.path not in ignore]
            tracks_ignore = [track for track in tracks if track.path in ignore]
            tracks.clear()
            tracks.extend(tracks_ignore)
        else:
            tracks_limit = tracks.copy()
            tracks.clear()

        if self.kind == LimitType.ITEMS:
            tracks.extend(tracks_limit[:self.limit_max])
        elif self.kind == LimitType.ALBUMS:
            seen_albums = []
            for track in tracks_limit:
                tracks.append(track)
                if track.album not in seen_albums:
                    seen_albums.append(track.album)

                if len(seen_albums) >= self.limit_max:
                    break
        else:
            count = 0
            for track in tracks_limit:
                value = self._convert(track)

                if count + value <= self.limit_max * self.allowance:
                    tracks.append(track)
                    count += value

                if count > self.limit_max:
                    break

    @staticmethod
    def _sort_random(tracks: List[Track]) -> None:
        shuffle(tracks)

    @staticmethod
    def _sort_highest_rating(tracks: List[Track]) -> None:
        TrackSort.sort_by_field(tracks, PropertyName.RATING, reverse=True)

    @staticmethod
    def _sort_lowest_rating(tracks: List[Track]) -> None:
        TrackSort.sort_by_field(tracks, PropertyName.RATING, reverse=False)

    @staticmethod
    def _sort_most_recently_played(tracks: List[Track]) -> None:
        TrackSort.sort_by_field(tracks, PropertyName.LAST_PLAYED, reverse=True)

    @staticmethod
    def _sort_least_recently_played(tracks: List[Track]) -> None:
        TrackSort.sort_by_field(tracks, PropertyName.LAST_PLAYED, reverse=False)

    @staticmethod
    def _sort_most_often_played(tracks: List[Track]) -> None:
        TrackSort.sort_by_field(tracks, PropertyName.PLAY_COUNT, reverse=True)

    @staticmethod
    def _sort_least_often_played(tracks: List[Track]) -> None:
        TrackSort.sort_by_field(tracks, PropertyName.PLAY_COUNT, reverse=False)

    @staticmethod
    def _sort_most_recently_added(tracks: List[Track]) -> None:
        TrackSort.sort_by_field(tracks, PropertyName.DATE_ADDED, reverse=True)

    @staticmethod
    def _sort_least_recently_added(tracks: List[Track]) -> None:
        TrackSort.sort_by_field(tracks, PropertyName.DATE_ADDED, reverse=False)

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

    def as_dict(self) -> MutableMapping[str, object]:
        return {
            "on": self.kind,
            "limit": self.limit_max,
            "sorted_by": self.limit_sort,
            "allowance": self.allowance
        }
