from __future__ import annotations

from collections.abc import Collection, Iterable
from copy import deepcopy
from typing import Self, ClassVar

from pydantic import Field

from musify._types import StrippedString
from musify.exception import MusifyTypeError
from musify.model import MusifyMutableMapping
from musify.model._base import _CollectionModel
from musify.model.item.track import Track, HasTracks
from musify.model.properties import HasName, HasLength, HasImages, SparseDate


class Playlist[TK, TV: Track](HasTracks[TK, TV], HasName, HasLength, HasImages):
    """Represents a playlist collection and its properties."""
    type: ClassVar[str] = "playlist"

    description: StrippedString | None = Field(
        description="The description of this playlist.",
        default=None,
    )
    created: SparseDate | None = Field(
        description="The date this playlist was created.",
        default=None,
    )
    modified: SparseDate | None = Field(
        description="The date this playlist was modifed.",
        default=None,
    )

    def merge(self, other: Collection[TV], reference: Self | None = None) -> None:
        """
        Merge tracks in this playlist with another collection, synchronising tracks between the two.
        Only modifies this playlist.

        Sort order is not preserved when merging.
        Any items that need to be added to this playlist will be added at the end of the playlist.
        Duplicates that are present in the ``other`` collection are filtered out by default.

        :param other: The collection of items to merge onto this playlist.
        :param reference: Optionally, provide a reference playlist to compare both the current playlist
            and the ``other`` items to. The function will determine tracks to remove from
            this playlist based on the reference. Useful for using this function as a synchronizer
            where the reference refers to the playlist at the previous sync.
        """
        if not self._validate_item_type(other):
            raise MusifyTypeError([type(i).__name__ for i in other])

        if reference is None:
            self.extend(self.outer_difference(other), allow_duplicates=False)
            return

        for item in reference:
            if item not in other and item in self:
                self.remove(item)

        self.extend(reference.outer_difference(other), allow_duplicates=False)

    def __or__(self, other: Iterable[TV]) -> Self:
        return deepcopy(self).merge(other)

    def __ior__(self, other: Iterable[TV]) -> Self:
        self.merge(other)
        return self


class HasPlaylists[TK, TV: Playlist](_CollectionModel):
    """A mixin class to add a `playlists` property to a MusifyCollection."""
    playlists: MusifyMutableMapping[TK, TV] = Field(
        description="The playlists in this collection",
        default_factory=list,
        frozen=True,
    )
