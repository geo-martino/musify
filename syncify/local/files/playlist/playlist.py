import re
from abc import ABCMeta, abstractmethod
from datetime import datetime
from os.path import basename, splitext, dirname, join, getmtime, exists
from typing import List, MutableMapping, Optional, Collection, Any, Union, Callable, Tuple

from syncify.local.files.file import File
from syncify.local.files.track import LocalTrack
from syncify.local.files.track.collection import LocalTrackCollection
from syncify.local.files.track.collection import TrackMatch, TrackLimit, TrackSort
from syncify.utils_new.generic import UpdateResult


class LocalPlaylist(LocalTrackCollection, File, metaclass=ABCMeta):
    """
    Generic class for manipulating local playlists.

    :param path: Absolute path of the playlist.
    :param matcher: :class:`TrackMatch` object to use for matching tracks.
    :param limiter: :class:`TrackLimit` object to use for limiting the number of tracks matched.
    :param sorter: :class:`TrackSort` object to use for sorting the final track list.
    """

    @property
    def tracks(self) -> List[LocalTrack]:
        return self._tracks

    @tracks.getter
    def tracks(self) -> List[LocalTrack]:
        return self._tracks

    @tracks.setter
    def tracks(self, value: List[LocalTrack]):
        if len(value) > 0:
            key_type = Callable[[LocalTrack], Tuple[bool, datetime]]
            key: key_type = lambda t: (t.last_played is None, t.last_played)
            self.last_played = sorted(value, key=key, reverse=True)[0].last_played
        self._tracks = value

    @property
    def path(self) -> str:
        return self._path

    @path.getter
    def path(self) -> str:
        return self._path

    @property
    def name(self) -> str:
        return self._name

    @name.getter
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._path = join(dirname(self._path), value + self.ext)
        self._name = value

    def __init__(
            self,
            path: str,
            matcher: Optional[TrackMatch] = None,
            limiter: Optional[TrackLimit] = None,
            sorter: Optional[TrackSort] = None,
    ):
        self._name, self.ext = splitext(basename(path))
        self._path: str = path
        self._tracks: Optional[List[LocalTrack]] = None
        self.description: Optional[str] = None
        self.last_played: Optional[datetime] = None
        self.date_modified: Optional[datetime] = None

        if exists(self._path):
            self.date_modified = datetime.fromtimestamp(getmtime(self._path))

        self.matcher = matcher
        self.limiter = limiter
        self.sorter = sorter

        self._tracks_original: Optional[List[LocalTrack]] = None

    def _match(self, tracks: Optional[List[LocalTrack]] = None, reference: Optional[LocalTrack] = None) -> None:
        """Wrapper for matcher"""
        m = self.matcher
        if m is not None and tracks is not None:
            if m.include_paths is None and m.exclude_paths is None and m.comparators is None:
                self.tracks: List[LocalTrack] = tracks.copy()
            else:
                self.tracks: List[LocalTrack] = m.match(tracks=tracks, reference=reference, combine=True)

    def _limit(self, ignore: Optional[Union[Collection[str], Collection[LocalTrack]]] = None) -> None:
        """Wrapper for limiter"""
        if self.limiter is not None and self.tracks is not None:
            self.limiter.limit(tracks=self.tracks, ignore=ignore)

    def _sort(self) -> None:
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
    def save(self, dry_run: bool = True) -> UpdateResult:
        """
        Write the tracks in this Playlist and its settings (if applicable) to file.

        :param dry_run: Run function, but do not modify file at all.
        :return: UpdateResult object with stats on the changes to the playlist.
        """

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "processors": [p for p in [self.matcher, self.limiter, self.sorter] if p is not None],
            "track_count": len(self.tracks) if self.tracks is not None else 0,
            "date_modified": self.date_modified,
            "last_played": self.last_played,
        }
