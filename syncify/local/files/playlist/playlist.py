from dataclasses import dataclass
from abc import ABCMeta, abstractmethod, ABC
from os.path import basename, splitext
from typing import List, MutableMapping, Optional, Set, Collection

from syncify.local.files.file import File
from syncify.local.files import Track
from syncify.local.files.track.collection import TrackMatch, TrackLimit, TrackSort
from syncify.utils_new.generic import PrettyPrinter


@dataclass
class UpdateResult(ABC):
    pass


class Playlist(PrettyPrinter, File, metaclass=ABCMeta):
    """
    Generic class for CRUD operations on playlists.

    :param path: Full path of the playlist.
    :param library_folder: Full path of folder containing tracks.
    :param other_folders: Full paths of other possible library paths.
        Use to replace path stems from other libraries for the paths in loaded playlists.
        Useful when managing similar libraries on multiple platforms.
    """

    def __init__(
            self,
            path: str,
            library_folder: Optional[str] = None,
            other_folders: Optional[Set[str]] = None,
            matcher: Optional[TrackMatch] = None,
            limiter: Optional[TrackLimit] = None,
            sorter: Optional[TrackSort] = None,
    ):
        self.name, self.ext = splitext(basename(path))
        self.path: str = path
        self.tracks: Optional[List[Track]] = None
        self.description: Optional[str] = None

        self._library_folder: str = library_folder.rstrip("\\/") if library_folder is not None else None
        self._original_folder: Optional[str] = None
        self._other_folders: Optional[Set[str]] = None
        if other_folders is not None:
            self._other_folders = {folder.rstrip("\\/") for folder in other_folders}

        self.matcher = matcher
        self.limiter = limiter
        self.sorter = sorter

    def _match(self, tracks: Optional[List[Track]] = None, reference: Optional[Track] = None) -> None:
        """Wrapper for matcher"""
        if self.matcher is not None and tracks is not None:
            self.tracks: List[Track] = self.matcher.match(tracks=tracks, reference=reference, combine=True)

    def _limit(self, ignore: Optional[Set[str]] = None) -> None:
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
            paths = [p.lower().replace(library_folder.lower(), original_folder.lower()) for p in paths]

        return paths

    @abstractmethod
    def load(self, tracks: Optional[List[Track]] = None) -> Optional[List[Track]]:
        """
        Read the playlist file and update the tracks in this playlist instance.

        :param tracks: Available Tracks to search through for matches.
        :return: Ordered list of tracks in this playlist
        """
        raise NotImplementedError

    @abstractmethod
    def write(self) -> UpdateResult:
        """
        Write the tracks in this Playlist to file.

        :return: UpdateResult object with stats on the changes to the playlist.
        """

    def as_dict(self) -> MutableMapping[str, object]:
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
    import json

    from syncify.local.files.track import FLAC
    from syncify.local.files.track import MP3
    from syncify.local.files.track import M4A
    from syncify.local.files.track import WMA
    from syncify.local.files import load_track
    from syncify.local.files.playlist.xautopf import XAutoPF
    from syncify.local.files.playlist.m3u import M3U

    from timeit import timeit
    from time import time

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
        print(pl)
        # # [print(str(i).zfill(3), track.album, track.title, sep=" = ") for i, track in enumerate(pl.tracks, 1)]
        # print(json.dumps(pl.xml, indent=2))

    for path in glob(join(library_folder, playlist_folder, "**", f"*.m3u"), recursive=True):
        pl = M3U(path=path, tracks=tracks, library_folder=library_folder, other_folders={other_folder})
        print(pl)
        print(len(pl.tracks))
        [print(str(i).zfill(3), track.album, track.title, sep=" = ") for i, track in enumerate(pl.tracks, 1)]
