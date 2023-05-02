from abc import ABC, abstractmethod
from os.path import exists, basename, splitext
from typing import Optional, List, Set

from syncify.local.files.track.track import Track


class Playlist(ABC):
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

    def _check_for_other_folder_stem(self, paths: List[str]) -> None:
        """
        Checks for the presence of some other folder as the stem of the paths in this playlist.
        Useful when managing similar libraries across multiple operating systems

        :param paths: Paths to search through for a match.
        """
        self._original_folder = None

        for path in paths:
            results = [folder for folder in self._other_folders if path.startswith(folder)]
            if len(results) != 0:
                self._original_folder = results[0]
                break

    def _sanitise_file_path(self, path: str) -> Optional[str]:
        """
        Sanitise a file path by:
            - replacing path stems found in other_folders
            - sanitising path separators to match current os separator
            - checking the track exists and replacing path with case-sensitive path if found

        :param path: Path to sanitise.
        :return: Sanitised path if path exists, None if not.
        """
        if not path:
            return

        if self._library_folder is not None:
            # check if replacement of filepath stem is necessary
            if self._original_folder is not None:
                path = path.replace(self._original_folder, self._library_folder)

            # sanitise path separators
            path = path.replace("\\", "/") if "/" in self._library_folder else path.replace("/", "\\")

        if exists(path):
            return path

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
