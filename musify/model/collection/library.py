"""
The core abstract implementations of :py:class:`MusifyItem` and :py:class:`MusifyCollection` classes.
"""
from abc import ABCMeta, abstractmethod
from collections.abc import Collection, Mapping
from copy import deepcopy
from typing import ClassVar

from pydantic import Field

from musify._types import Source
from musify.exception import MusifyTypeError
from musify.model.collection.playlist import Playlist, HasPlaylists
from musify.model.item.track import Track, HasTracks

type LibraryMergeType[T] = Library[T] | Collection[Playlist[T]] | Mapping[str, Playlist[T]]


class Library[TK, TV: Track, KP, VP: Playlist](HasTracks[TK, TV], HasPlaylists[KP, VP], metaclass=ABCMeta):
    """A library of items and playlists and other object types."""
    type: ClassVar[str] = "library"

    source: ClassVar[Source] = Field(
        description="The name of the source of this library.",
    )

    @property
    def track_total(self) -> int:
        """The total number of tracks in this sequence"""
        tracks = self.tracks.copy()
        seen_keys = set(key for track in tracks for key in track.unique_keys)
        for pl in self.playlists.values():
            for track in pl:
                if not any(key in seen_keys for key in track.unique_keys):
                    tracks.append(track)
                seen_keys.update(track.unique_keys)

        return len(tracks)

    @property
    def tracks_in_playlists(self) -> list[TV]:
        """All unique tracks from all playlists in this library"""
        tracks = []
        seen_keys = set()
        for pl in self.playlists.values():
            for track in pl:
                if not any(key in seen_keys for key in track.unique_keys):
                    tracks.append(track)
                seen_keys.update(track.unique_keys)

        return tracks

    @abstractmethod
    async def load(self):
        """Implementations of this function should load all data for this library and log results."""
        raise NotImplementedError

    @abstractmethod
    async def load_tracks(self) -> None:
        """
        Implementations of this function should load all tracks for this library
        and store them within the library object to be retrieved with property ``tracks``.
        """
        raise NotImplementedError

    @abstractmethod
    def log_tracks(self) -> None:
        """Log stats on currently loaded tracks"""
        raise NotImplementedError

    @abstractmethod
    async def load_playlists(self) -> None:
        """
        Implementations of this function should load all playlists for this library
        and store them within the library object to be retrieved with property ``playlists``.
        """
        raise NotImplementedError

    @abstractmethod
    def log_playlists(self) -> None:
        """Log stats on currently loaded playlists"""
        raise NotImplementedError

    def merge_playlists(self, playlists: LibraryMergeType[TV], reference: LibraryMergeType[TV] | None = None) -> None:
        """
        Merge playlists from given list/map/library to this library.

        See :py:meth:`.Playlist.merge` for more info.

        :param playlists: The playlists to merge onto this library's playlists.
            If a given playlist is not found in this library, simply add the playlist to this library.
        :param reference: Optionally, provide a reference playlist to compare both the current playlist
            and the ``other`` items to. The function will determine tracks to remove from
            this playlist based on the reference. Useful for using this function as a synchronizer
            where the reference refers to the playlist at the previous sync.
        """
        def get_playlists_map(value: LibraryMergeType[TV]) -> Mapping[str, Playlist[T]]:
            """Reformat the input playlist values to map"""
            if isinstance(value, Mapping):
                return value
            elif isinstance(value, Library):
                return value.playlists
            elif isinstance(value, Collection):
                return {pl.name: pl for pl in value}
            raise MusifyTypeError(f"Unrecognised input type: {value.__class__.__name__}")

        playlists = get_playlists_map(playlists)
        reference = get_playlists_map(reference) if reference is not None else {}

        for name, playlist in playlists.items():
            if name not in self.playlists:
                self.playlists[name] = deepcopy(playlist)
                continue

            self.playlists[name].merge(playlist, reference=reference.get(name))
