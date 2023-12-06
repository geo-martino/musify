import hashlib
import urllib.parse
from collections.abc import Iterable, Mapping, Sequence, Generator
from datetime import datetime
from os.path import join, exists, normpath
from typing import Any

from lxml import etree

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
        self._xml_parser = XMLLibraryParser(self._path)
        self.xml: dict[str, Any] = self._xml_parser.parse()

        super().__init__(
            library_folder=library_folder,
            playlist_folder=join(musicbee_folder, "Playlists"),
            other_folders=other_folders,
            include=include,
            exclude=exclude,
            load=load,
            remote_wrangler=remote_wrangler,
        )

    def load_tracks(self) -> list[LocalTrack]:
        tracks_paths = {track.path.casefold(): track for track in self._load_tracks()}
        self.logger.debug("Enrich local tracks: START")

        for track_xml in self.xml["Tracks"].values():
            if track_xml["Track Type"] != "File":
                continue

            track = tracks_paths.get(track_xml["Location"].casefold())
            if track is None:
                continue

            track.date_added = track_xml.get("Date Added")
            track.last_played = track_xml.get("Play Date UTC")
            track.play_count = track_xml.get("Play Count", 0)
            track.rating = int(track_xml.get("Rating")) if track_xml.get("Rating") is not None else None

        self.logger.debug("Enrich local tracks: DONE\n")
        return list(tracks_paths.values())

    def save(self, dry_run: bool = True, *args, **kwargs) -> Any:
        """
        Generate and save the XML library file for this MusicBee library.

        :param dry_run: Run function, but do not modify file at all.
        """
        tracks_paths = {track.path.casefold(): track for track in self.tracks}
        track_id_map: dict[LocalTrack, tuple[int, str]] = {}
        for track_xml in self.xml["Tracks"].values():
            if track_xml["Track Type"] != "File":
                continue

            track = tracks_paths.get(track_xml["Location"].casefold())
            if not track:
                continue

            track_id_map[track] = (track_xml["Track ID"], track_xml["Persistent ID"])

        tracks = {}
        max_track_id = max(id_ for id_, _ in track_id_map.values()) if track_id_map else 0
        for i, track in enumerate(self.tracks, max_track_id):
            track_id, persistent_id = track_id_map.get(track, [i, None])
            tracks[track_id] = self.track_to_xml(track, track_id=track_id, persistent_id=persistent_id)

        playlist_id_map = {
            playlist_xml["Name"]: (playlist_xml["Playlist ID"], playlist_xml["Playlist Persistent ID"])
            for playlist_xml in self.xml["Playlists"]
        }

        playlists = {}
        max_playlist_id = max(id_ for id_, _ in playlist_id_map.values()) if playlist_id_map else 0
        for i, (name, playlist) in enumerate(self.playlists.items(), max_playlist_id):
            playlist_id, persistent_id = track_id_map.get(name, [i, None])
            playlists[playlist_id] = self.playlist_to_xml(
                playlist, tracks=track_id_map, playlist_id=playlist_id, persistent_id=persistent_id
            )

        xml = {
            "Major Version": self.xml.get("Major Version", "1"),
            "Minor Version": self.xml.get("Minor Version", "1"),
            "Application Version": self.xml.get("Application Version", "1"),
            "Music Folder": XMLLibraryParser.to_xml_path(self.library_folder),
            "Library Persistent ID":
                self.xml.get("Library Persistent ID", self.generate_persistent_id(self.library_folder)),
            "Tracks": tracks,
            "Playlists": playlists,
        }

        return xml

    @staticmethod
    def generate_persistent_id(value: str | None = None, id_: str | None = None) -> str:
        """
        Generates a valid persistent ID from a given ``value``
        or validates a given persistent ID as given by ``id_``,

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
        if len(id_) > 16:
            raise MusicBeeIDError(f"Persistent ID is >16-characters in length (length={len(id_)}): {id_}")
        return id_.upper()

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
        genres = {}
        if track.genres and len(track.genres) == 1:
            genres = {"Genre": track.genres}
        elif track.genres:
            genres = {f"Genre{i}": genre for i, genre in enumerate(track.genres, 1)}

        data = {
            "Track ID": track_id,
            "Persistent ID": cls.generate_persistent_id(id_=persistent_id, value=track.path),
            "Name": track.title,
            "Artist": track.artist,
            "Album": track.album,
            "Album Artist": track.album_artist,
            "Track Number": str(track.track_number).zfill(len(str(track.track_total)) if track.track_total else 0),
            "Track Count": track.track_total,
        } | genres | {
            "Year": track.year,
            "BPM": track.bpm,
            "Disc Number": track.disc_number,
            "Disc Count": track.disc_total,
            "Compilation": track.compilation,
            "Comments": track.comments,
            "Total Time": int(track.length * 1000),  # in milliseconds
            "Rating": track.rating,
            # "Composer": track.composer,  # currently not supported by this program
            # "Conductor": track.conductor,  # currently not supported by this program
            # "Publisher": track.publisher,  # currently not supported by this program
            # "Encoder": track.encoder,  # currently not supported by this program
            "Size": track.size,
            "Kind": track.kind,
            # "": track.channels,  # unknown MusicBee mapping
            "Bit Rate": int(track.bit_rate),
            # "": track.bit_depth,  # unknown MusicBee mapping
            "Sample Rate": int(track.sample_rate * 1000),  # in Hz
            "Date Modified": XMLLibraryParser.to_xml_timestamp(track.date_modified),
            "Date Added": XMLLibraryParser.to_xml_timestamp(track.date_added),
            "Play Date UTC": XMLLibraryParser.to_xml_timestamp(track.last_played),
            "Play Count": track.play_count,
            "Track Type": "File",  # can also be 'URL' for streams
            "Location": XMLLibraryParser.to_xml_path(track.path),
        }

        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def playlist_to_xml(
            cls,
            playlist: LocalPlaylist,
            tracks: Mapping[LocalTrack, int | Sequence[int, str]] | list[LocalTrack],
            playlist_id: int,
            persistent_id: str | None = None,
    ) -> dict[str, str | Number]:
        """
        Convert a local playlist into a dict representation of XML data for a MusicBee library file.

        :param playlist: The playlist to convert.
        :param tracks: A map of all available tracks in the library to their track IDs, or a simple list of tracks.
            If a map is given and the values are :py:class:`Sequence`, take the first index as the Track ID.
            If a list is given, the function will use the track's index as the Track ID.
        :param playlist_id: An incremental ID to assign to the playlist.
        :param persistent_id: An 16-character unique ID to assign to the playlist.
        :return: A dict representation of XML data for the given playlist.
        :raise MusicBeeIDError: When the given ``persistent_id`` is invalid.
        """
        items: list[dict[str, int]] = []
        for track in playlist:
            if isinstance(tracks, dict):
                result = tracks[track]
                items.append({"Track ID": result if isinstance(result, int) else result[0]})
            else:
                items.append({"Track ID":  tracks.index(track)})

        data = {
            "Playlist ID": playlist_id,
            "Playlist Persistent ID": cls.generate_persistent_id(id_=persistent_id, value=playlist.path),
            "All Items": True,  # unknown what this does, what happens if 'False'?
            "Name": playlist.name,
            "Description": playlist.description,
            "Playlist Items": items,
        }

        return {k: v for k, v in data.items() if v is not None}


# noinspection PyProtectedMember
class XMLLibraryParser:
    """
    Parses the MusicBee library to and from iTunes style XML

    :param path: Path to the XML file.
    """

    _xml_timestamp_fmt = "%Y-%m-%dT%H:%M:%SZ"
    _xml_path_keys = frozenset({"Location", "Music Folder"})

    def __init__(self, path: str):
        self.path = path
        self.iterparse = None

    @classmethod
    def to_xml_timestamp(cls, timestamp: datetime | None) -> str | None:
        """Convert timestamp string as found in the MusicBee XML library file to a ``datetime`` object"""
        if timestamp:
            return timestamp.strftime(cls._xml_timestamp_fmt)

    @classmethod
    def from_xml_timestamp(cls, timestamp_str: str | None) -> datetime | None:
        """Convert timestamp string as found in the MusicBee XML library file to a ``datetime`` object"""
        if timestamp_str:
            return datetime.strptime(timestamp_str, cls._xml_timestamp_fmt)

    @staticmethod
    def to_xml_path(path: str) -> str:
        """Convert a standard system path to a file path as found in the MusicBee XML library file"""
        return f"file://localhost/{urllib.parse.quote(path.replace('\\', '/'), safe=':/')}"

    @staticmethod
    def from_xml_path(path: str) -> str:
        """Clean the file paths as found in the MusicBee XML library file to a standard system path"""
        return normpath(urllib.parse.unquote(path.replace("file://localhost/", "")))

    def _iter_elements(self) -> Generator[etree._Element, [], []]:
        for event, element in self.iterparse:
            yield element

    def _parse_value(self, value: Any, tag: str, parent: str | None = None):
        if tag == 'string':
            if parent in self._xml_path_keys:
                return self.from_xml_path(value)
            else:
                return value
        elif tag == 'integer':
            try:
                return int(value) if "." not in value else float(value)
            except ValueError:
                return value
        elif tag == 'date':
            return self.from_xml_timestamp(value)
        elif tag in ['true', 'false']:
            return tag == 'true'

    def _parse_element(self, element: etree._Element | None = None) -> Any:
        elem = next(self._iter_elements())
        peek = element.getnext() if element is not None else None

        if elem.tag in ['string', 'integer', 'date', 'true', 'false']:
            return self._parse_value(
                value=elem.text, tag=elem.tag, parent=element.text if element is not None else None
            )
        elif peek is not None and peek.tag == "dict":
            next_elem = next(self._iter_elements())
            value = self._parse_value(value=next_elem.text, tag=next_elem.tag, parent=elem.text)
            return {elem.text: value} | self._parse_dict()
        elif peek is not None and peek.tag == "array":
            return self._parse_array(elem)
        elif peek is not None:
            raise Exception(f"Unrecognised element: {element.tag}, {element.text}, {peek.tag}, {peek.text}")
        else:
            raise Exception(f"Unrecognised element: {element.tag}, {element.text}")

    def _parse_array(self, element: etree._Element | None = None) -> list[Any]:
        array = []

        for elem in self._iter_elements():
            if elem is None or elem.tag == "array":
                break

            peek = elem.getnext()
            if elem is not None and elem.tag == "key":
                next_elem = next(self._iter_elements())
                value = self._parse_value(value=next_elem.text, tag=next_elem.tag, parent=elem.text)
                array.append({elem.text: value} | self._parse_dict())
            elif peek is None and element is not None:
                value = self._parse_value(value=elem.text, tag=elem.tag, parent=element.text)
                array.append({element.text: value} | self._parse_dict())
            else:
                array.append(self._parse_element())

        return array

    def _parse_dict(self) -> dict[str, Any]:
        record = {}

        for elem in self._iter_elements():
            if elem is None or elem.tag == "dict":
                break

            peek = elem.getnext()

            if elem.text == "Playlist ID":
                print(elem.text, peek.text)
            if peek is not None and peek.tag == "dict":
                record[elem.text] = self._parse_dict()
            else:
                record[elem.text] = self._parse_element(elem)

        return record

    def parse(self) -> dict[str, Any]:
        """Parse the XML file from the currently stored ``path`` to a dictionary"""
        self.iterparse = etree.iterparse(self.path)
        results = {}

        for element in self._iter_elements():
            peek = element.getnext()
            if peek is None:
                break

            if element.tag == "plist":
                continue
            elif element.tag == "key":
                key = element.text
                if peek.tag == "dict":
                    results[key] = self._parse_dict()
                elif peek.tag == "array":
                    results[key] = self._parse_array()
                else:
                    results[key] = self._parse_element(element)
            else:
                raise NotImplementedError

        return results
