from glob import glob
from os.path import basename, splitext, join
from typing import Optional, List, Set, MutableMapping, Mapping

from local.files.track.file import __ACCEPTED_FILETYPES__, __TRACK_CLASSES__
from syncify.local.files.utils.exception import IllegalFileTypeError


class PlaylistManager:

    def __init__(
            self,
            playlist_folder: Optional[str] = None,
            library_folder: Optional[str] = None,
            other_folders: Optional[Set[str]] = None,
    ):

        self.playlist_folder: str = playlist_folder.rstrip("\\/") if playlist_folder is not None else None
        self.library_folder: str = library_folder.rstrip("\\/") if library_folder is not None else None

        self.other_folders: Optional[Set[str]] = None
        if other_folders is not None:
            self.other_folders = {folder.rstrip("\\/") for folder in other_folders}

        # all playlist lowercase names mapped to their filepaths with accepted filetypes in playlist folder
        self.playlist_paths: Optional[MutableMapping[str, str]] = None

        self.track_paths: Optional[Set[str]] = None
        self._track_paths_lower_map: Optional[Mapping[str, str]] = None

        self.set_file_paths(load_from_track_obj=True)

    def set_file_paths(self, load_from_track_obj: bool = False) -> None:
        """
        Set instance property for all available file paths. Necessary for loading with case-sensitive logic.

        :param load_from_track_obj: Quickly load available track paths from track objs instead of searching library.
        """
        if self.playlist_folder is not None:
            self.playlist_paths = {}
            for filetype in self.filetypes:
                paths = glob(join(self.playlist_folder, "**", f"*.{filetype}"), recursive=True)
                self.playlist_paths.update({splitext(basename(path))[0]: path for path in paths})

        if load_from_track_obj:
            self.track_paths = {
                path
                for track_obj in __TRACK_CLASSES__
                for path in track_obj.available_track_paths if track_obj.available_track_paths is not None
            }
        else:
            self.track_paths = set()
            for ext in __ACCEPTED_FILETYPES__:
                # first glob doesn't get filenames that start with a period
                self.track_paths.update(glob(join(self.library_folder, "**", f"*{ext}"), recursive=True))
                # second glob only picks up filenames that start with a period
                self.track_paths.update(glob(join(self.library_folder, "*", "**", f".*{ext}"), recursive=True))

        self._track_paths_lower_map = {path.lower(): path for path in self.filepaths}


    def _get_playlist_path(
            self, name: Optional[str] = None, path: Optional[str] = None, ext: Optional[str] = None
    ) -> str:
        """
        General method for loading paths of a given playlist. Playlist path must include an extension.
        When both name and path are defined, the name is used as a priority if playlist_folder has been defined.
        If not, the function will use the path.

        :param name: Relative playlist path to process.
            Function will look for this relative path in the playlist_folder.
        :param path: Full playlist path to process.
        :param ext: Extension to append if missing.
        :return: The full playlist path.
        :exception ValueError: If the input values are invalid.
        :exception FileNotFoundError: If the playlist cannot be found.
        """
        if path is None:
            if name is not None:
                if self.playlist_folder is None:
                    raise ValueError("No playlist folder defined for this loader instance")
                path = join(self.playlist_folder, name)
            else:
                raise ValueError("Must define either a playlist name or path")

        # add extension if missing
        if ext is not None:
            ext = ext.strip(".")
            path += f".{ext}" if not path.endswith(f".{ext}") else ""

        if not exists(path):
            raise FileNotFoundError(f"Could not find playlist at path: {path}")

        return path

    def load(self, name: Optional[str] = None, path: Optional[str] = None) -> Optional[List[str]]:
        """
        General method for loading paths of a given playlist.
        When both name and path are defined, the name is used as a priority if playlist_folder has been defined.
        If not, the function will use the path.

        :param name: Relative playlist path to process with extension.
            Function will look for this relative path in the playlist_folder.
        :param path: Full playlist path to process with extension.
        :return: Paths of the tracks in this playlist.
        :exception ValueError: If the input values are invalid.
        :exception FileNotFoundError: If the playlist cannot be found.
        """
        path = self._get_playlist_path(name=name, path=path, ext=None)

        splitpath = splitext(basename(path))
        if name is None:
            name = splitpath[0]

        ext = splitpath[1].lower()
        if len(ext) == 0:
            path_ext = self.playlist_paths.get(name.lower())
            if path_ext is None:
                raise ValueError(f"No extension given and playlist not found in playlist folder: {path}")

        if ext == ".m3u":
            return self.get_track_paths_m3u(path=path)
        elif ext == ".xautopf":
            return self.get_track_paths_xautopf(path=path)
        else:
            raise IllegalFileTypeError(ext)

if __name__ == "__main__":
    playlist_folder = "MusicBee/Playlists"
    library_folder = "/mnt/d/Music/"
    other_folder = "D:\\Music\\"

    loader = PlaylistLoader(
        library_folder=library_folder, playlist_folder=playlist_folder, other_folders={other_folder}
    )

    name = "2sing.m3u"
    print(loader.get_track_paths_m3u(path=join(library_folder, playlist_folder, "B A S S")))