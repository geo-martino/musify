import re
from abc import ABCMeta, abstractmethod
from os.path import basename, splitext, dirname, join
from typing import List, MutableMapping, Optional, Collection, Any, Union

from syncify.local.files.file import File
from syncify.local.files.track import LocalTrack
from syncify.local.files.track.collection import TrackCollection
from syncify.local.files.track.collection import TrackMatch, TrackLimit, TrackSort
from syncify.utils_new.generic import PrettyPrinter, UpdateResult


class Playlist(PrettyPrinter, TrackCollection, File, metaclass=ABCMeta):
    """
    Generic class for CRUD operations on playlists.

    :param path: Full path of the playlist.
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
        self.tracks: Optional[List[LocalTrack]] = None
        self.description: Optional[str] = None

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
    def save(self) -> UpdateResult:
        """
        Write the tracks in this Playlist and its settings (if applicable) to file.

        :return: UpdateResult object with stats on the changes to the playlist.
        """

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "processors": [p for p in [self.matcher, self.limiter, self.sorter] if p is not None],
            "track_count": len(self.tracks) if self.tracks is not None else 0
            # "tracks": self.tracks
        }


if __name__ == "__main__":
    from os.path import join
    from glob import glob

    from syncify.local.files.track import FLAC
    from syncify.local.files.track import MP3
    from syncify.local.files.track import M4A
    from syncify.local.files.track import WMA
    from syncify.local.files import load_track
    from syncify.local.files.playlist.xautopf import XAutoPF
    from syncify.local.files.playlist.m3u import M3U

    playlist_folder = join("MusicBee", "Playlists")
    library_folder = "D:\\Music\\"
    other_folder = "/mnt/d/Music/"

    print("Setting file paths")
    FLAC.set_file_paths(library_folder=library_folder)
    MP3.set_file_paths(library_folder=library_folder)
    M4A.set_file_paths(library_folder=library_folder)
    WMA.set_file_paths(library_folder=library_folder)

    print("Loading tracks")
    tracks = []
    tracks.extend(load_track(path=path) for path in FLAC.available_track_paths)
    tracks.extend(load_track(path=path) for path in MP3.available_track_paths)
    tracks.extend(load_track(path=path) for path in M4A.available_track_paths)
    tracks.extend(load_track(path=path) for path in WMA.available_track_paths)

    for path in glob(join(library_folder, playlist_folder, "**", f"*.xautopf"), recursive=True):
        pl = XAutoPF(path=path, tracks=tracks, library_folder=library_folder, other_folders={other_folder})
        print(pl.name, len(pl))
        # # [print(str(i).zfill(3), track.album, track.title, sep=" = ") for i, track in enumerate(pl.tracks, 1)]
        # print(json.dumps(pl.xml, indent=2))

    for path in glob(join(library_folder, playlist_folder, "**", f"*.m3u"), recursive=True):
        pl = M3U(path=path, tracks=tracks, library_folder=library_folder, other_folders={other_folder})
        print(pl.name, len(pl))
        # [print(str(i).zfill(3), track.album, track.title, sep=" = ") for i, track in enumerate(pl.tracks, 1)]
