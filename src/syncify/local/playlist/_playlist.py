import re
from abc import ABCMeta, abstractmethod
from collections.abc import Collection, Iterable
from datetime import datetime
from os.path import dirname, join, getmtime, getctime, exists

from syncify.abstract.object import Playlist
from syncify.abstract.misc import Result
from syncify.local import File
from syncify.local.collection import LocalCollection
from syncify.local.playlist._match import LocalMatcher
from syncify.local.track import LocalTrack, load_track
from syncify.processors.limit import ItemLimiter
from syncify.processors.sort import ItemSorter
from syncify.remote.processors.wrangle import RemoteDataWrangler


class LocalPlaylist(LocalCollection[LocalTrack], Playlist[LocalTrack], File, metaclass=ABCMeta):
    """
    Generic class for loading and manipulating local playlists.

    :param path: Absolute path of the playlist.
    :param matcher: :py:class:`TrackMatch` object to use for matching tracks.
    :param limiter: :py:class:`TrackLimit` object to use for limiting the number of tracks matched.
    :param sorter: :py:class:`TrackSort` object to use for sorting the final track list.
    :param available_track_paths: A list of available track paths that are known to exist
        and are valid for the track types supported by this program.
        Useful for case-insensitive path loading and correcting paths to case-sensitive.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on tracks.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
        The wrangler is also used when loading tracks to allow them to process URI tags.
        For more info on this, see :py:class:`LocalTrack`.
    """

    __slots__ = ("_path", "_tracks", "_tracks_original", "matcher", "limiter", "sorter", "available_track_paths")

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
            matcher: LocalMatcher | None = None,
            limiter: ItemLimiter | None = None,
            sorter: ItemSorter | None = None,
            available_track_paths: Iterable[str] = (),
            remote_wrangler: RemoteDataWrangler = None,
    ):
        super().__init__(remote_wrangler=remote_wrangler)

        self._path: str = path
        self._tracks: list[LocalTrack] | None = None
        self._tracks_original: list[LocalTrack] | None = None

        self.matcher = matcher
        self.limiter = limiter
        self.sorter = sorter

        self.available_track_paths: Iterable[str] = available_track_paths

    def _load_track(self, path: str) -> LocalTrack:
        """Wrapper for LocalTrack loader. Returns the loaded track."""
        return load_track(path=path, available=self.available_track_paths, remote_wrangler=self.remote_wrangler)

    def _match(self, tracks: Collection[LocalTrack] = (), reference: LocalTrack | None = None) -> None:
        """Wrapper for matcher"""
        matcher = self.matcher
        if matcher is None or not tracks:
            return

        if matcher.include_paths is None and matcher.exclude_paths is None and matcher.comparers is None:
            # just return the tracks given if matcher has no settings applied
            self.tracks: list[LocalTrack] = [t for t in tracks]
        else:  # run matcher
            self.tracks: list[LocalTrack] = matcher(tracks=tracks, reference=reference)

    def _limit(self, ignore: Collection[str | LocalTrack]) -> None:
        """Wrapper for limiter"""
        if self.limiter is not None and self.tracks is not None:
            track_path_map = {track.path: track for track in self.tracks}
            ignore: set[LocalTrack] = {i if isinstance(i, LocalTrack) else track_path_map.get(i) for i in ignore}
            self.limiter(items=self.tracks, ignore=ignore)

    def _sort(self) -> None:
        """Wrapper for sorter"""
        if self.sorter is not None and self.tracks is not None:
            self.sorter(items=self.tracks)

    def _prepare_paths_for_output(self, paths: Collection[str]) -> list[str]:
        """
        Reconfigure the given list of paths by adding back the original library folder.
        Used to ensure saving of correct and valid paths back to playlists.
        """
        library_folder = self.matcher.library_folder
        original_folder = self.matcher.original_folder

        if len(paths) > 0 and library_folder is not None and original_folder is not None:
            pattern = re.compile(library_folder.replace("\\", "\\\\"), re.I)
            paths = [pattern.sub(original_folder, p) for p in paths]

        return paths

    @abstractmethod
    def load(self, tracks: Collection[LocalTrack] | None = None) -> list[LocalTrack] | None:
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

    def merge(self, playlist: Playlist) -> None:
        raise NotImplementedError

    def as_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "processors": [p for p in [self.matcher, self.limiter, self.sorter] if p is not None],
            "track_total": self.track_total,
            "length": self.length,
            "date_created": self.date_created,
            "date_modified": self.date_modified,
            "last_played": self.last_played,
            "remote_source": self.remote_wrangler.remote_source if self.remote_wrangler else None,
        }
