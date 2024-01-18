"""
Base implementation for the functionality of a local playlist.
"""

from abc import ABCMeta, abstractmethod
from collections.abc import Collection
from datetime import datetime
from os.path import dirname, join, getmtime, getctime, exists

from musify.local.collection import LocalCollection
from musify.local.file import File, PathMapper
from musify.local.track import LocalTrack
from musify.processors.base import Filter
from musify.processors.limit import ItemLimiter
from musify.processors.sort import ItemSorter
from musify.shared.core.misc import Result
from musify.shared.core.object import Playlist
from musify.shared.remote.processors.wrangle import RemoteDataWrangler


class LocalPlaylist[T: Filter[LocalTrack]](LocalCollection[LocalTrack], Playlist[LocalTrack], File, metaclass=ABCMeta):
    """
    Generic class for loading and manipulating local playlists.

    :param path: Absolute path of the playlist.
    :param matcher: :py:class:`Filter` object to use for matching tracks.
    :param limiter: :py:class:`ItemLimiter` object to use for limiting the number of tracks matched.
    :param sorter: :py:class:`ItemSorter` object to use for sorting the final track list.
    :param path_mapper: Optionally, provide a :py:class:`PathMapper` for paths stored in the playlist file.
        Useful if the playlist file contains relative paths and/or paths for other systems that need to be
        mapped to absolute, system-specific paths to be loaded and back again when saved.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on tracks.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
        The wrangler is also used when loading tracks to allow them to process URI tags.
        For more info on this, see :py:class:`LocalTrack`.
    """

    __slots__ = (
        "_path",
        "matcher",
        "limiter",
        "sorter",
        "path_mapper",
        "_tracks",
        "_original",
    )
    __attributes_classes__ = (Playlist, LocalCollection, File)

    @property
    def name(self) -> str:
        """The name of this playlist, always the same as the filename."""
        return self.filename

    @name.setter
    def name(self, value: str):
        self._path = join(dirname(self._path), value + self.ext)

    @property
    def tracks(self) -> list[LocalTrack]:
        return self._tracks

    @tracks.setter
    def tracks(self, value: list[LocalTrack]):
        self._tracks = value

    @property
    def path(self):
        return self._path

    @property
    def date_modified(self):
        if self.path and exists(self.path):
            return datetime.fromtimestamp(getmtime(self.path))

    @property
    def date_created(self):
        if self.path and exists(self.path):
            return datetime.fromtimestamp(getctime(self.path))

    def __init__(
            self,
            path: str,
            matcher: T | None = None,
            limiter: ItemLimiter | None = None,
            sorter: ItemSorter | None = None,
            path_mapper: PathMapper = PathMapper(),
            remote_wrangler: RemoteDataWrangler = None,
    ):
        super().__init__(remote_wrangler=remote_wrangler)

        self._path: str = path

        #: :py:class:`Filter` object to use for matching tracks.
        self.matcher = matcher
        #: :py:class:`ItemLimiter` object to use for limiting the number of tracks matched.
        self.limiter = limiter
        #: :py:class:`ItemSorter` object to use for sorting the final track list.
        self.sorter = sorter
        #: Maps paths stored in the playlist file.
        self.path_mapper = path_mapper

        self._tracks: list[LocalTrack] = []
        self._original: list[LocalTrack] = []

    def _match(self, tracks: Collection[LocalTrack] = (), reference: LocalTrack | None = None) -> None:
        """Wrapper for matcher operations"""
        if self.matcher is None or not tracks:
            return

        if not self.matcher.ready:  # just return the tracks given if matcher has no settings applied
            self.tracks: list[LocalTrack] = list(tracks)
        else:  # run matcher
            self.tracks: list[LocalTrack] = list(self.matcher(values=tracks, reference=reference))

    def _limit(self, ignore: Collection[str | LocalTrack]) -> None:
        """Wrapper for limiter operations"""
        if self.limiter is not None and self.tracks is not None:
            track_path_map = {track.path: track for track in self.tracks}
            ignore: set[LocalTrack] = {i if isinstance(i, LocalTrack) else track_path_map.get(i) for i in ignore}
            self.limiter(items=self.tracks, ignore=ignore)

    def _sort(self) -> None:
        """Wrapper for sorter operations"""
        if self.sorter is not None and self.tracks is not None:
            self.sorter(items=self.tracks)

    @abstractmethod
    def load(self, tracks: Collection[LocalTrack] = ()) -> list[LocalTrack]:
        """
        Read the playlist file and update the tracks in this playlist instance.

        :param tracks: Available Tracks to search through for matches.
        :return: Ordered list of tracks in this playlist
        """
        raise NotImplementedError

    @abstractmethod
    def save(self, dry_run: bool = True, *args, **kwargs) -> Result:
        """
        Write the tracks in this Playlist and its settings (if applicable) to file.

        :param dry_run: Run function, but do not modify file at all.
        :return: :py:class:`Result` object with stats on the changes to the playlist.
        """
        raise NotImplementedError

    def merge(self, playlist: Playlist[LocalTrack]) -> None:
        raise NotImplementedError
