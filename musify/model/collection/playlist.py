from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import ClassVar

from pydantic import Field, validate_call

from musify._types import StrippedString
from musify.model import MusifyMutableMapping, MusifyMapping
from musify.model._base import _CollectionModel
from musify.model.item.track import Track, HasTracks, HasMutableTracks
from musify.model.properties import HasName, HasURI, HasLength, HasImages, SparseDate


class Playlist[TK, TV: Track](HasMutableTracks[TK, TV], HasName, HasURI, HasLength, HasImages):
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

    def merge(self, other: HasTracks[TK, TV], reference: HasTracks[TK, TV] | None = None) -> None:
        """
        Merge two playlists together.

        See :py:meth:`.MusifyMutableSequence.merge` for more information.
        """
        self.tracks.merge(other.tracks, reference=reference.tracks if reference else None)


type MergePlaylistsType[K, V] = V | Iterable[V] | Mapping[K, V]


class HasPlaylists[TK, TV: Playlist](_CollectionModel):
    """A mixin class to add a `playlists` property to a MusifyCollection."""
    playlists: MusifyMapping[TK, TV] = Field(
        description="The playlists in this collection",
        default_factory=MusifyMapping[TK, TV],
        frozen=True,
    )


class HasMutablePlaylists[TK, TV: Playlist](HasPlaylists[TK, TV]):
    playlists: MusifyMutableMapping[TK, TV] = Field(
        description="The playlists in this collection",
        default_factory=MusifyMutableMapping[TK, TV],
        frozen=True,
    )

    @staticmethod
    def _get_playlists_map_from_merge_input(
            playlists: MergePlaylistsType[TK, TV] | None
    ) -> MusifyMutableMapping[TK, TV] | None:
        match playlists:
            case None:
                return
            case MusifyMutableMapping():
                return playlists
            case HasPlaylists():
                return playlists.playlists
            case _:
                return MusifyMutableMapping(playlists)

    @validate_call
    def merge_playlists(
            self, other: MergePlaylistsType[TK, TV], reference: MergePlaylistsType[TK, TV] = None
    ) -> None:
        """
        Merge playlists from given list/map/library to this library.

        If a matching playlist is found in the current model, :py:meth:`.Playlist.merge` is called on the
        current playlist with the other playlist.
        If a reference is provided and a match is found, this will be passed to :py:meth:`.Playlist.merge` too.
        If a playlist is not found in the current model, it will be added to the model.

        :param other: The playlists to merge into the current playlists.
        :param reference: The reference playlists to refer to when merging.
        """
        other = self._get_playlists_map_from_merge_input(other)
        reference = self._get_playlists_map_from_merge_input(reference)

        for name, playlist in other.items():
            if playlist not in self.playlists:
                self.playlists.add(deepcopy(playlist))
                continue

            self.playlists[playlist].merge(playlist, reference=reference[playlist] if reference else None)
