import hashlib
import urllib.parse
from collections.abc import Iterable
from datetime import datetime
from os.path import join, exists, normpath
from typing import Any

import xmltodict

from syncify.local.exception import MusicBeeIDError
from syncify.local.file import File
from syncify.local.library.library import LocalLibrary
from syncify.local.playlist import LocalPlaylist
from syncify.local.track.base.track import LocalTrack
from syncify.remote.processors.wrangle import RemoteDataWrangler
from syncify.utils import UnitCollection, Number


class MusicBee(LocalLibrary, File):
    """
    Represents a local MusicBee library, providing various methods for manipulating
    tracks and playlists across an entire local library collection.

    :ivar valid_extensions: Extensions of library files that can be loaded by this class.
    :ivar musicbee_library_filename: The filename of the MusicBee library folder.

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
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on tracks.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
        The wrangler is also used when loading tracks to allow them to process URI tags.
        For more info on this, see :py:class:`LocalTrack`.
    """

    valid_extensions = frozenset({".xml"})
    musicbee_library_filename = "iTunes Music Library.xml"

    _xml_timestamp_fmt = "%Y-%m-%dT%H:%M:%S%z"

    @property
    def path(self) -> str:
        return self._path

    def __init__(
            self,
            library_folder: str | None = None,
            musicbee_folder: str = "MusicBee",
            other_folders: UnitCollection[str] = (),
            include: Iterable[str] = (),
            exclude: Iterable[str] = (),
            load: bool = True,
            remote_wrangler: RemoteDataWrangler = None,
    ):
        if not exists(musicbee_folder):
            in_library = join(library_folder.rstrip("\\/"), musicbee_folder.lstrip("\\/"))
            if not exists(in_library):
                raise FileNotFoundError(
                    f"Cannot find MusicBee library at given path: {musicbee_folder} OR {in_library}"
                )
            musicbee_folder = in_library

        self._path: str = join(musicbee_folder, self.musicbee_library_filename)
        with open(self._path, "r", encoding="utf-8") as f:
            self.xml: dict[str, Any] = xmltodict.parse(f.read())

        super().__init__(
            library_folder=library_folder,
            playlist_folder=join(musicbee_folder, "Playlists"),
            other_folders=other_folders,
            include=include,
            exclude=exclude,
            load=load,
            remote_wrangler=remote_wrangler,
        )

    @classmethod
    def _xml_dt_to_ts(cls, timestamp: datetime | None) -> str | None:
        """Convert timestamp string as found in the MusicBee XML library file to a ``datetime`` object"""
        if timestamp:
            return timestamp.strftime(cls._xml_timestamp_fmt)

    @classmethod
    def _xml_ts_to_dt(cls, timestamp_str: str | None) -> datetime | None:
        """Convert timestamp string as found in the MusicBee XML library file to a ``datetime`` object"""
        if timestamp_str:
            return datetime.strptime(timestamp_str, cls._xml_timestamp_fmt)

    @staticmethod
    def _clean_xml_filepath(path: str) -> str:
        """Clean the file paths as found in the MusicBee XML library file to a standard system path"""
        return normpath(urllib.parse.unquote(path.replace("file://localhost/", "")))

    def load(self, *args, **kwargs) -> list[LocalTrack]:
        """Alias for load_tracks method"""
        return self.load_tracks()

    def load_tracks(self) -> list[LocalTrack]:
        tracks_paths = {track.path.casefold(): track for track in self._load_tracks()}
        self.logger.debug("Enrich local tracks: START")

        for track_xml in self.xml["Tracks"].values():
            if not track_xml["Location"].startswith("file://localhost/"):
                continue

            track = tracks_paths.get(self._clean_xml_filepath(track_xml["Location"]).casefold())
            if track is None:
                continue

            track.date_added = self._xml_ts_to_dt(track_xml.get("Date Added"))
            track.last_played = self._xml_ts_to_dt(track_xml.get("Play Date UTC"))
            track.play_count = int(track_xml.get("Play Count", 0))
            track.rating = int(track_xml.get("Rating")) if track_xml.get("Rating") is not None else None

        self.logger.debug("Enrich local tracks: DONE\n")
        return list(tracks_paths.values())

    def save(self, dry_run: bool = True, *args, **kwargs) -> Any:
        """Generate and save the XML library file for this MusicBee library"""
        # TODO: implement me
        raise NotImplementedError

    @staticmethod
    def generate_persistent_id(id_: str | None = None, value: str | None = None) -> str:
        """
        Validates a given persistent ID as given by ``id_``,
        or generates a valid persistent ID from a given ``value``.

        :param id_: A persistent ID to validate
        :param value: A value to generate a persistent ID from.
        :return: The valid persistent ID.
        :raise MusicBeeIDError: When no ``id_`` and no ``value`` is given, or the given ``id_`` is invalid.
        """
        if not value and not id_:
            raise MusicBeeIDError(
                "You must provide either a persistent ID to validate or a value to generate a persistent ID from."
            )

        id_ = id_ if id_ else hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
        if len(id_) != 16:
            raise MusicBeeIDError(f"Persistent ID is not 16-characters in length (length={len(id_)}): {id_}")
        return id_

    @classmethod
    def track_to_xml(
            cls, track: LocalTrack, track_id: int, persistent_id: str | None = None
    ) -> dict[str, str | Number]:
        """
        Convert a local track into a dict representation of XML data for a MusicBee library file

        :param track: The track to convert.
        :param track_id: An incremental ID to assign to the track.
        :param persistent_id: An 16-character unique ID to assign to the track.
        :return: A dict representation of XML data for the given track.
        :raise MusicBeeIDError: When the given ``persistent_id`` is invalid.
        """
        data = {
            "Track ID": track_id,
            # "Encoder": ,
            "Comments": track.comments,
            "BPM": track.bpm,
            "Disc Count": track.disc_total,
            "Track Count": track.track_total,
            "Disc Number": track.disc_number,
            "Track Number": track.track_number,
            "Compilation": track.compilation,
            "Name": track.title,
            "Artist": track.artist,
            "Album Artist": track.album_artist,
            "Album": track.album,
            "Year": track.year,
            "Genre": track.genres,
            "Kind": track.kind,
            "Size": track.size,
            "Total Time": track.length,
            "Date Modified": cls._xml_dt_to_ts(track.date_modified),
            "Date Added": cls._xml_dt_to_ts(track.date_added),
            "Bit Rate": track.bit_rate,
            "Sample Rate": track.sample_rate,
            "Play Count": track.play_count,
            "Play Date UTC": cls._xml_dt_to_ts(track.last_played),
            "Persistent ID": cls.generate_persistent_id(id_=persistent_id, value=track.path),
            "Track Type": "File",
            "Location": f"file://localhost/{urllib.parse.quote(track.path.replace('\\', '/'), safe=':/')}",
        }

        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def playlist_to_xml(
            cls,
            playlist: LocalPlaylist,
            playlist_id: int,
            persistent_id: str | None = None,
            tracks: list[LocalTrack] = None,
    ) -> dict[str, str | Number]:
        """
        Convert a local playlist into a dict representation of XML data for a MusicBee library file.

        :param playlist: The playlist to convert.
        :param playlist_id: An incremental ID to assign to the playlist.
        :param persistent_id: An 16-character unique ID to assign to the playlist.
        :param tracks: A list of all available tracks in the library.
            The function will use this as an index to get a list of Track IDs for this playlist.
        :return: A dict representation of XML data for the given playlist.
        :raise MusicBeeIDError: When the given ``persistent_id`` is invalid.
        """
        data = {
            "Playlist ID": playlist_id,
            "Playlist Persistent ID": cls.generate_persistent_id(id_=persistent_id, value=playlist.path),
            "All Items": True,
            "Name": playlist.name,
            "Description": playlist.description,
            "Playlist Items": {"Track ID": tracks.index(track) for track in playlist},
        }

        return {k: v for k, v in data.items() if v is not None}
