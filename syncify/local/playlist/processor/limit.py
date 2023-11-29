from collections.abc import Callable, Collection, Mapping
from functools import reduce
from operator import mul
from random import shuffle
from typing import Any, Self

from syncify.enums import SyncifyEnum
from syncify.enums.tags import PropertyName
from syncify.local.exception import LimitError
from syncify.local.playlist.processor.base import TrackProcessor
from syncify.local.playlist.processor.sort import TrackSort
from syncify.local.track.base.track import LocalTrack


class LimitType(SyncifyEnum):
    """Represents the possible limit types to apply when filtering a playlist."""
    ITEMS = 0
    ALBUMS = 1

    SECONDS = 11
    MINUTES = 12
    HOURS = 13
    DAYS = 14
    WEEKS = 15

    BYTES = 20
    KILOBYTES = 21
    MEGABYTES = 22
    GIGABYTES = 23
    TERABYTES = 24


class TrackLimit(TrackProcessor):
    """
    Sort tracks inplace based on given conditions.

    :param limit: The number of tracks to limit to. A value of 0 applies no limiting.
    :param on: The type to limit on e.g. items, albums, minutes.
    :param sorted_by: When limiting, sort the collection of tracks by this function first.
    :param allowance: When limiting on bytes or length, add this extra allowance factor to
        the max size limit on comparison.
        e.g. say the limiter currently has 29 minutes worth of songs in its final list and the max limit is 30 minutes.
        The limiter has to now consider whether to include the next song it sees with length 3 minutes.
        With an allowance of 0, this song will not be added.
        However, with an allowance of say 1.33 it will as the max limit for this comparison becomes 30 * 1.33 = 40.
        Now, with 32 minutes worth of songs in the final playlist, the limit is >30 minutes and the limiter stops
        processing.
    """

    _valid_methods: Mapping[str, str] = {}

    @property
    def limit_sort(self) -> str | None:
        """String representation of the sorting method to use before limiting"""
        return self._limit_sort

    @limit_sort.setter
    def limit_sort(self, value: str | None):
        """Sets the sorting method name and stored function"""
        if value is None:
            self._limit_sort: str | None = None
            self._sort_method = lambda _: None
            return

        name = self._get_method_name(value, valid=self._valid_methods, prefix=self._sort_method_prefix)
        self._limit_sort = self._snake_to_camel(name, prefix=self._sort_method_prefix)
        self._sort_method = getattr(self, self._valid_methods[name])

    @classmethod
    def from_xml(cls, xml: Mapping[str, Any] | None = None) -> Self | None:
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
            on: LimitType = LimitType.ITEMS,
            sorted_by: str | None = None,
            allowance: float = 1.0,
    ):
        self.limit_max = limit
        self.kind = on
        self.allowance = allowance

        prefix = "_sort"
        self._sort_method_prefix = "_sort"
        self._valid_methods = {
            k if k.startswith(prefix) else prefix + k: v if v.startswith(prefix) else prefix + v
            for k, v in self._valid_methods.items()
        } | {
            name: name for name in dir(self) if name.startswith(self._sort_method_prefix)
        }
        self._sort_method: Callable[[list[LocalTrack]], None] = lambda _: None
        self.limit_sort = sorted_by

    def limit(self, tracks: list[LocalTrack], ignore: Collection[str | LocalTrack] | None = None) -> None:
        """
        Limit ``tracks`` inplace based on set conditions.

        :param tracks: The list of tracks to limit.
        :param ignore: list of tracks or paths of tracks to ignore when limiting.
            i.e. keep them in the list regardless.
        """
        if len(tracks) == 0 or self.limit_max == 0:
            return

        self._sort_method(tracks)  # sort the input tracks in-place if sort method given

        if ignore is not None and len(ignore) > 0:  # filter out the ignore tracks if given
            ignore = {track.path if isinstance(track, LocalTrack) else track for track in ignore}

            tracks_limit = [track for track in tracks if track.path not in ignore]
            tracks_ignore = [track for track in tracks if track.path in ignore]
            tracks.clear()
            tracks.extend(tracks_ignore)
        else:  # make a copy of the given tracks and clear the original list
            tracks_limit = [t for t in tracks]
            tracks.clear()

        if self.kind == LimitType.ITEMS:  # limit on items
            tracks.extend(tracks_limit[:self.limit_max])
        elif self.kind == LimitType.ALBUMS:  # limit on albums
            seen_albums = []
            for track in tracks_limit:
                if len(seen_albums) < self.limit_max and track.album not in seen_albums:
                    # album limit not yet reached
                    seen_albums.append(track.album)
                if track.album in seen_albums:
                    tracks.append(track)
        else:  # limit on duration or size
            count = 0
            for track in tracks_limit:
                value = self._convert(track)
                if count + value <= self.limit_max * self.allowance:  # limit not yet reached
                    tracks.append(track)
                    count += value
                if count > self.limit_max:  # limit reached
                    break

    @staticmethod
    def _sort_random(tracks: list[LocalTrack]) -> None:
        shuffle(tracks)

    @staticmethod
    def _sort_highest_rating(tracks: list[LocalTrack]) -> None:
        TrackSort.sort_by_field(tracks, PropertyName.RATING, reverse=True)

    @staticmethod
    def _sort_lowest_rating(tracks: list[LocalTrack]) -> None:
        TrackSort.sort_by_field(tracks, PropertyName.RATING)

    @staticmethod
    def _sort_most_recently_played(tracks: list[LocalTrack]) -> None:
        TrackSort.sort_by_field(tracks, PropertyName.LAST_PLAYED, reverse=True)

    @staticmethod
    def _sort_least_recently_played(tracks: list[LocalTrack]) -> None:
        TrackSort.sort_by_field(tracks, PropertyName.LAST_PLAYED)

    @staticmethod
    def _sort_most_often_played(tracks: list[LocalTrack]) -> None:
        TrackSort.sort_by_field(tracks, PropertyName.PLAY_COUNT, reverse=True)

    @staticmethod
    def _sort_least_often_played(tracks: list[LocalTrack]) -> None:
        TrackSort.sort_by_field(tracks, PropertyName.PLAY_COUNT)

    @staticmethod
    def _sort_most_recently_added(tracks: list[LocalTrack]) -> None:
        TrackSort.sort_by_field(tracks, PropertyName.DATE_ADDED, reverse=True)

    @staticmethod
    def _sort_least_recently_added(tracks: list[LocalTrack]) -> None:
        TrackSort.sort_by_field(tracks, PropertyName.DATE_ADDED)

    def _convert(self, track: LocalTrack) -> float:
        """
        Convert units for track length or size

        :raises LimitError: When the given limit type cannot be found
        """
        if 10 < self.kind.value < 20:
            factors = (1, 60, 60, 24, 7)[:self.kind.value % 10]
            return track.length / reduce(mul, factors, 1)
        elif 20 <= self.kind.value < 30:
            bytes_scale = 1000
            return track.size / (bytes_scale ** (self.kind.value % 10))
        else:
            raise LimitError(f"Unrecognised LimitType: {self.kind}")

    def as_dict(self):
        return {
            "on": self.kind,
            "limit": self.limit_max,
            "sorted_by": self.limit_sort,
            "allowance": self.allowance
        }
