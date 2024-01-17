"""
Processor that limits the items in a given collection of items
"""

from collections.abc import Collection, Mapping
from functools import reduce
from operator import mul
from random import shuffle
from typing import Any, Self

from musify.local.file import File
from musify.processors.base import DynamicProcessor, MusicBeeProcessor, dynamicprocessormethod
from musify.processors.exception import ItemLimiterError
from musify.processors.sort import ItemSorter
from musify.shared.core.base import Item
from musify.shared.core.enum import MusifyEnum, Fields
from musify.shared.core.object import Track


class LimitType(MusifyEnum):
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


class ItemLimiter(MusicBeeProcessor, DynamicProcessor):
    """
    Sort items in-place based on given conditions.

    :param limit: The number of items to limit to. A value of 0 applies no limiting.
    :param on: The type to limit on e.g. items, albums, minutes.
    :param sorted_by: When limiting, sort the collection of items by this function first.
    :param allowance: When limiting on bytes or length, add this extra allowance factor to
        the max size limit on comparison.
        e.g. say the limiter currently has 29 minutes worth of songs in its final list and the max limit is 30 minutes.
        The limiter has to now consider whether to include the next song it sees with length 3 minutes.
        With an allowance of 0, this song will not be added.
        However, with an allowance of say 1.33 it will as the max limit for this comparison becomes 30 * 1.33 = 40.
        Now, with 32 minutes worth of songs in the final playlist, the limit is >30 minutes and the limiter stops
        processing.
    """

    __slots__ = ("limit_max", "kind", "allowance")

    @property
    def limit_sort(self) -> str | None:
        """String representation of the sorting method to use before limiting"""
        return self._processor_name.lstrip("_")

    @classmethod
    def from_xml(cls, xml: Mapping[str, Any], **__) -> Self | None:
        conditions: Mapping[str, str] = xml["SmartPlaylist"]["Source"]["Limit"]
        if conditions["@Enabled"] != "True":
            return
        # filter_duplicates = conditions["@FilterDuplicates"] == "True"

        # MusicBee appears to have some extra allowance on time and byte limits of ~1.25
        return cls(
            limit=int(conditions["@Count"]),
            on=LimitType.from_name(conditions["@Type"])[0],
            sorted_by=conditions["@SelectedBy"],
            allowance=1.25
        )

    def to_xml(self, **kwargs) -> Mapping[str, Any]:
        raise NotImplementedError

    def __init__(
            self,
            limit: int = 0,
            on: LimitType = LimitType.ITEMS,
            sorted_by: str | None = None,
            allowance: float = 1.0,
    ):
        super().__init__()

        #: The number of items to limit to.
        self.limit_max = limit
        #: The type to limit on e.g. items, albums, minutes.
        self.kind = on
        #: When limiting on bytes or length, add this extra allowance factor to
        #: the max size limit on comparison.
        self.allowance = allowance

        self._set_processor_name(sorted_by, fail_on_empty=False)

    def __call__[T: Item](self, items: list[T], ignore: Collection[T] = ()) -> None:
        return self.limit(items=items, ignore=ignore)

    def limit[T: Item](self, items: list[T], ignore: Collection[T] = ()) -> None:
        """
        Limit ``items`` in-place based on set conditions.

        :param items: The list of items to limit.
        :param ignore: list of items to ignore when limiting. i.e. keep them in the list regardless.
        """
        if len(items) == 0 or self.limit_max == 0:
            return

        if self._processor_name:  # sort the input items in-place if sort method given
            super().__call__(items)

        if ignore:  # filter out the ignore items if given
            items_limit = [item for item in items if item not in ignore]
            items_ignore = [item for item in items if item in ignore]
            items.clear()
            items.extend(items_ignore)
        else:  # make a copy of the given items and clear the original list
            items_limit = [t for t in items]
            items.clear()

        if self.kind == LimitType.ITEMS:  # limit on items
            items.extend(items_limit[:self.limit_max])
        elif self.kind == LimitType.ALBUMS:  # limit on albums
            seen_albums = []
            for item in items_limit:
                if not isinstance(item, Track):
                    ItemLimiterError("In order to limit on Album, all items must be of type 'Track'")

                if len(seen_albums) < self.limit_max and item.album not in seen_albums:
                    # album limit not yet reached
                    seen_albums.append(item.album)
                if item.album in seen_albums:
                    items.append(item)
        else:  # limit on duration or size
            count = 0
            for item in items_limit:
                value = self._convert(item)
                if count + value <= self.limit_max * self.allowance:  # limit not yet reached
                    items.append(item)
                    count += value
                if count > self.limit_max:  # limit reached
                    break

    def _convert(self, item: Item) -> float:
        """
        Convert units for item length or size and return the value.

        :raise ItemLimiterError: When the given limit type cannot be found
        """
        if 10 < self.kind.value < 20:
            if not hasattr(item, "length"):
                raise ItemLimiterError("The given item cannot be limited on length as it does not have a length.")

            factors = (1, 60, 60, 24, 7)[:self.kind.value % 10]
            # noinspection PyUnresolvedReferences
            return item.length / reduce(mul, factors, 1)

        elif 20 <= self.kind.value < 30:
            if not isinstance(item, File):
                raise ItemLimiterError("The given item cannot be limited on bytes as it is not a file.")

            bytes_scale = 1000
            return item.size / (bytes_scale ** (self.kind.value % 10))

        else:
            raise ItemLimiterError(f"Unrecognised LimitType: {self.kind}")

    @dynamicprocessormethod
    def _random(self, items: list[Item]) -> None:
        shuffle(items)

    @dynamicprocessormethod
    def _highest_rating(self, items: list[Item]) -> None:
        ItemSorter.sort_by_field(items, Fields.RATING, reverse=True)

    @dynamicprocessormethod
    def _lowest_rating(self, items: list[Item]) -> None:
        ItemSorter.sort_by_field(items, Fields.RATING)

    @dynamicprocessormethod
    def _most_recently_played(self, items: list[Item]) -> None:
        ItemSorter.sort_by_field(items, Fields.LAST_PLAYED, reverse=True)

    @dynamicprocessormethod
    def _least_recently_played(self, items: list[Item]) -> None:
        ItemSorter.sort_by_field(items, Fields.LAST_PLAYED)

    @dynamicprocessormethod
    def _most_often_played(self, items: list[Item]) -> None:
        ItemSorter.sort_by_field(items, Fields.PLAY_COUNT, reverse=True)

    @dynamicprocessormethod
    def _least_often_played(self, items: list[Item]) -> None:
        ItemSorter.sort_by_field(items, Fields.PLAY_COUNT)

    @dynamicprocessormethod
    def _most_recently_added(self, items: list[Item]) -> None:
        ItemSorter.sort_by_field(items, Fields.DATE_ADDED, reverse=True)

    @dynamicprocessormethod
    def _least_recently_added(self, items: list[Item]) -> None:
        ItemSorter.sort_by_field(items, Fields.DATE_ADDED)

    def as_dict(self):
        return {
            "on": self.kind,
            "limit": self.limit_max,
            "sorted_by": self.limit_sort,
            "allowance": self.allowance
        }
