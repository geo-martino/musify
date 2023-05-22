import re
from abc import ABCMeta, abstractmethod
from datetime import datetime
from os.path import dirname, join, getmtime, getctime
from typing import List, Optional, Union, Collection

from syncify.abstract.collection import Playlist
from syncify.abstract.misc import Result
from syncify.local.file import File
from syncify.local.library.collection import LocalCollection
from syncify.local.playlist.processor import TrackMatch, TrackLimit, TrackSort
from syncify.local.track import LocalTrack
from syncify.utils.logger import Logger


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
        """The name of this playlist, taken to always be the filename."""
        return self.filename

    @name.setter
    def name(self, value: str):
        self._path = join(dirname(self._path), value + self.ext)

    @property
    def items(self) -> List[LocalTrack]:
        return self._tracks

    @property
    def tracks(self) -> List[LocalTrack]:
        return self._tracks

    @tracks.setter
    def tracks(self, value: List[LocalTrack]):
        self._tracks = value

    @property
    def path(self) -> str:
        return self._path

    @property
    def date_modified(self) -> Optional[datetime]:
        if self.path:
            return datetime.fromtimestamp(getmtime(self.path))

    @property
    def date_created(self) -> Optional[datetime]:
        if self.path:
            return datetime.fromtimestamp(getctime(self.path))

    def __init__(
            self,
            path: str,
            matcher: Optional[TrackMatch] = None,
            limiter: Optional[TrackLimit] = None,
            sorter: Optional[TrackSort] = None,
    ):
        Logger.__init__(self)
        self._path: str = path
        self._tracks: Optional[List[LocalTrack]] = None
        self._tracks_original: Optional[List[LocalTrack]] = None

        self.matcher = matcher
        self.limiter = limiter
        self.sorter = sorter

    def _match(self, tracks: Optional[List[LocalTrack]] = None, reference: Optional[LocalTrack] = None):
        """Wrapper for matcher"""
        m = self.matcher
        if m is not None and tracks is not None:
            if m.include_paths is None and m.exclude_paths is None and m.comparators is None:
                # just return the tracks given if matcher has no settings applied
                self.tracks: List[LocalTrack] = tracks.copy()
            else:  # run matcher
                self.tracks: List[LocalTrack] = m.match(tracks=tracks, reference=reference)

    def _limit(self, ignore: Optional[Union[Collection[str], Collection[LocalTrack]]] = None):
        """Wrapper for limiter"""
        if self.limiter is not None and self.tracks is not None:
            self.limiter.limit(tracks=self.tracks, ignore=ignore)

    def _sort(self):
        """Wrapper for sorter"""
        if self.sorter is not None and self.tracks is not None:
            self.sorter.sort(tracks=self.tracks)

    def _prepare_paths_for_output(self, paths: Collection[str]) -> Collection[str]:
        """Add the original library folder back to a list of paths for output"""
        library_folder = self.matcher.library_folder
        original_folder = self.matcher.original_folder

        if len(paths) > 0 and library_folder is not None and original_folder is not None:
            pattern = re.compile(library_folder.replace("\\", "\\\\"), re.IGNORECASE)
            paths = [pattern.sub(original_folder, p) for p in paths]

        return paths

    @abstractmethod
    def load(self, tracks: Optional[List[LocalTrack]] = None) -> Optional[List[LocalTrack]]:
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
