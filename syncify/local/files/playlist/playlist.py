from abc import ABCMeta, abstractmethod
from os.path import basename, splitext
from typing import List, MutableMapping, Optional, Set

from local.files.track.collection.collection import TrackCollection
from syncify.local.files.track.track import Track


class Playlist(TrackCollection, metaclass=ABCMeta):
    """
    Generic class for CRUD operations on playlists.

    :param path: Full path of the playlist.
    :param tracks: Available Tracks to search through for matches.
    :param library_folder: Full path of folder containing tracks.
    :param other_folders: Full paths of other possible library paths.
        Use to replace path stems from other libraries for the paths in loaded playlists.
        Useful when managing similar libraries on multiple platforms.
    """

    @property
    @abstractmethod
    def playlist_ext(self) -> List[str]:
        """Allowed extensions in lowercase"""
        raise NotImplementedError

    def __init__(
            self,
            path: str,
            tracks: Optional[List[Track]] = None,
            library_folder: Optional[str] = None,
            other_folders: Optional[Set[str]] = None,
    ):
        TrackCollection.__init__(self)

        self.name, self.ext = splitext(basename(path))
        self.path: str = path
        self.tracks: Optional[List[Track]] = None
        self.description: Optional[str] = None

        self._library_folder: str = library_folder.rstrip("\\/") if library_folder is not None else None
        self._original_folder: Optional[str] = None
        self._other_folders: Optional[Set[str]] = None
        if other_folders is not None:
            self._other_folders = set(folder.rstrip("\\/") for folder in other_folders)

        self.load(tracks=tracks)

    @abstractmethod
    def load(self, tracks: Optional[List[Track]] = None) -> Optional[List[Track]]:
        """
        Read the playlist file

        :param tracks: Available Tracks to search through for matches.
        :return: Ordered list of tracks in this playlist
        """
        raise NotImplementedError

    @abstractmethod
    def write(self, tracks: List[Track]) -> int:
        """
        Write the given Tracks to the playlist file
        Sanitise a file path by:
            - replacing path stems found in other_folders
            - sanitising path separators to match current os separator
            - replacing path with case-sensitive path if appropriate

        :param tracks: Available Tracks to search through for matches.
        :return: Number of paths written to the file
        """

    def as_dict(self) -> MutableMapping[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "tracks": [track.as_json() for track in self.tracks]
        }

    def as_json(self) -> MutableMapping[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "tracks": [track.as_dict() for track in self.tracks]
        }
