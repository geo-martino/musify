import urllib.parse
from collections.abc import Iterable
from datetime import datetime
from os.path import join, exists, normpath
from typing import Any

import xmltodict

from syncify.local.file import File
from syncify.local.track.base.track import LocalTrack
from syncify.utils import UnitCollection
from syncify.utils.logger import Logger
from .library import LocalLibrary


class MusicBee(LocalLibrary, File):
    """
    Represents a local MusicBee library, providing various methods for manipulating
    tracks and playlists across an entire local library collection.

    :param library_folder: The absolute path of the library folder containing all tracks.
        The intialiser will check for the existence of this path and only store it if it exists.
    :param musicbee_folder: The absolute path of the playlist folder containing all playlists
        or the relative path within the given ``library_folder``.
        The intialiser will check for the existence of this path and only store the absolute path if it exists.
    :param other_folders: Absolute paths of other possible library paths.
        Use to replace path stems from other libraries for the paths in loaded playlists.
        Useful when managing similar libraries on multiple platforms.
    :param include: An optional list of playlist names to include when loading playlists.
    :param exclude: An optional list of playlist names to exclude when loading playlists.
    :param load: When True, load the library on intialisation.
    """

    @property
    def path(self) -> str:
        return self._path

    valid_extensions = frozenset({".xml"})

    def __init__(
            self,
            library_folder: str | None = None,
            musicbee_folder: str = "MusicBee",
            other_folders: UnitCollection[str] | None = None,
            include: Iterable[str] | None = None,
            exclude: Iterable[str] | None = None,
            load: bool = True
    ):
        Logger.__init__(self)
        self.logger.info(f"\33[1;95m ->\33[1;97m Loading MusicBee library \33[0m")

        if not exists(musicbee_folder):
            in_library = join(library_folder.rstrip("\\/"), musicbee_folder.lstrip("\\/"))
            if not exists(in_library):
                raise FileNotFoundError(
                    f"Cannot find MusicBee library at given path: {musicbee_folder} OR {in_library}"
                )
            musicbee_folder = in_library

        self._path: str = join(musicbee_folder, "iTunes Music Library.xml")
        with open(self._path, "r", encoding="utf-8") as f:
            self.xml: dict[str, Any] = xmltodict.parse(f.read())

        self.print_line()
        LocalLibrary.__init__(
            self,
            library_folder=library_folder,
            playlist_folder=join(musicbee_folder, "Playlists"),
            other_folders=other_folders,
            include=include,
            exclude=exclude,
            load=load
        )

    @staticmethod
    def _xml_ts_to_dt(timestamp_str: str | None) -> datetime | None:
        """Convert timestamp string as found in the MusicBee XML library file to a ``datetime`` object"""
        if timestamp_str:
            return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S%z")

    @staticmethod
    def _clean_xml_filepath(path: str) -> str:
        """Clean the file paths as found in the MusicBee XML library file to a standard system path"""
        return normpath(urllib.parse.unquote(path.replace("file://localhost/", "")))

    def load_tracks(self) -> list[LocalTrack]:
        tracks_paths = {track.path.lower(): track for track in self._load_tracks()}
        self.logger.debug("Enrich local tracks: START")

        for track_xml in self.xml["Tracks"].values():
            if not track_xml["Location"].startswith("file://localhost/"):
                continue

            track = tracks_paths.get(self._clean_xml_filepath(track_xml["Location"]).lower())
            if track is None:
                continue

            track.date_added = self._xml_ts_to_dt(track_xml.get("Date Added"))
            track.last_played = self._xml_ts_to_dt(track_xml.get("Play Date UTC"))
            track.play_count = int(track_xml.get("Play Count", 0))
            track.rating = int(track_xml.get("Rating")) if track_xml.get("Rating") is not None else None

        self.logger.debug("Enrich local tracks: DONE\n")
        return list(tracks_paths.values())
