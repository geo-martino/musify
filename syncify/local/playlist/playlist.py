import re
from abc import ABCMeta, abstractmethod
from collections.abc import Collection
from datetime import datetime
from os.path import dirname, join, getmtime, getctime

from syncify.abstract.collection import Playlist
from syncify.abstract.misc import Result
from syncify.local.file import File
from syncify.local.library.collection import LocalCollection
from syncify.local.playlist.processor.limit import TrackLimit
from syncify.local.playlist.processor.match import TrackMatch
from syncify.local.playlist.processor.sort import TrackSort
from syncify.local.track.base.track import LocalTrack


class LocalPlaylist(Playlist, LocalCollection, File, metaclass=ABCMeta):
    """
    Generic class for manipulating local playlists.

    :param path: Absolute path of the playlist.
    :param matcher: :class:`TrackMatch` object to use for matching tracks.
    :param limiter: :class:`TrackLimit` object to use for limiting the number of tracks matched.
    :param sorter: :class:`TrackSort` object to use for sorting the final track list.
    """

    @property
    def name(self) -> str:
        """The name of this playlist, always the same as the filename."""
        return self.filename

    @name.setter
    def name(self, value: str):
        self._path = join(dirname(self._path), value + self.ext)

    @property
    def items(self):
        return self._tracks

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
        if self.path:
            return datetime.fromtimestamp(getmtime(self.path))

    @property
    def date_created(self):
        if self.path:
            return datetime.fromtimestamp(getctime(self.path))

    def __init__(
            self,
            path: str,
            matcher: TrackMatch | None = None,
            limiter: TrackLimit | None = None,
            sorter: TrackSort | None = None,
    ):
        Playlist.__init__(self)

        self._path: str = path
        self._tracks: list[LocalTrack] | None = None
        self._tracks_original: list[LocalTrack] | None = None

        self.matcher = matcher
        self.limiter = limiter
        self.sorter = sorter

    def _match(self, tracks: Collection[LocalTrack] | None = None, reference: LocalTrack | None = None) -> None:
        """Wrapper for matcher"""
        m = self.matcher
        if m is not None and tracks is not None:
            if m.include_paths is None and m.exclude_paths is None and m.comparators is None:
                # just return the tracks given if matcher has no settings applied
                self.tracks: list[LocalTrack] = [t for t in tracks]
            else:  # run matcher
                self.tracks: list[LocalTrack] = m.match(tracks=tracks, reference=reference)

    def _limit(self, ignore: Collection[str | LocalTrack] | None = None) -> None:
        """Wrapper for limiter"""
        if self.limiter is not None and self.tracks is not None:
            self.limiter.limit(tracks=self.tracks, ignore=ignore)

    def _sort(self) -> None:
        """Wrapper for sorter"""
        if self.sorter is not None and self.tracks is not None:
            self.sorter.sort(tracks=self.tracks)

    def _prepare_paths_for_output(self, paths: Collection[str]) -> list[str]:
        """Add the original library folder back to a list of paths for output"""
        library_folder = self.matcher.library_folder
        original_folder = self.matcher.original_folder

        if len(paths) > 0 and library_folder is not None and original_folder is not None:
            pattern = re.compile(library_folder.replace("\\", "\\\\"), re.IGNORECASE)
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
    def save(self, dry_run: bool = True) -> Result:
        """
        Write the tracks in this Playlist and its settings (if applicable) to file.

        :param dry_run: Run function, but do not modify file at all.
        :return: UpdateResult object with stats on the changes to the playlist.
        """

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
        }
