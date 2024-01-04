import hashlib
import re
import urllib.parse
from collections.abc import Iterable, Mapping, Sequence, Generator
from datetime import datetime
from os.path import join, exists, normpath
from typing import Any

from lxml import etree
from lxml.etree import iterparse

from syncify.local import File
from syncify.local.exception import MusicBeeIDError, XMLReaderError, MusicBeeError, FileDoesNotExistError
from syncify.local.library._library import LocalLibrary
from syncify.local.playlist import LocalPlaylist
from syncify.local.track import LocalTrack
from syncify.remote.processors.wrangle import RemoteDataWrangler
from syncify.utils import UnitCollection, Number
from syncify.utils.helpers import correct_platform_separators


class MusicBee(LocalLibrary, File):
    """
    Represents a local MusicBee library, providing various methods for manipulating
    tracks and playlists across an entire local library collection.

    :ivar valid_extensions: Extensions of library files that can be loaded by this class.
    :ivar xml_library_filename: The filename of the MusicBee library folder.
    :ivar xml_path_keys: A list of keys for the XML library that need to be processed as system paths

    :param library_folder: The absolute path of the library folder containing all tracks.
        The intialiser will check for the existence of this path and only store it if it exists.
    :param musicbee_folder: The absolute path of the playlist folder containing all playlists
        or the relative path within the given ``library_folder``.
        The intialiser will check for the existence of this path and only store the absolute path if it exists.
    :param playlist_folder: The absolute path of the playlist folder containing all playlists
        or the relative path within the given ``library_folder`` or ``library_folder``/``musicbee_folder``.
        The intialiser will check for the existence of this path and only store the absolute path if it exists.
    :param other_folders: Absolute paths of other possible library paths.
        Use to replace path stems from other libraries for the paths in loaded playlists.
        Useful when managing similar libraries on multiple platforms.
    :param include: An optional list of playlist names to include when loading playlists.
    :param exclude: An optional list of playlist names to exclude when loading playlists.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on tracks.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
        The wrangler is also used when loading tracks to allow them to process URI tags.
        For more info on this, see :py:class:`LocalTrack`.
    """

    __slots__ = ("_path", "_xml_parser", "xml")

    valid_extensions = frozenset({".xml"})
    xml_library_filename = "iTunes Music Library.xml"
    xml_path_keys = {"Location", "Music Folder"}

    @property
    def path(self) -> str:
        return self._path

    def __init__(
            self,
            library_folder: str | None = None,
            musicbee_folder: str | None = "MusicBee",
            playlist_folder: str | None = "Playlists",
            other_folders: UnitCollection[str] = (),
            include: Iterable[str] = (),
            exclude: Iterable[str] = (),
            remote_wrangler: RemoteDataWrangler = None,
    ):
        if library_folder is None and musicbee_folder is None:
            raise MusicBeeError("Must give either library_folder or musicbee_folder")

        library_folder = correct_platform_separators(library_folder)
        musicbee_folder = correct_platform_separators(musicbee_folder)
        playlist_folder = correct_platform_separators(playlist_folder)

        # try to resolve the musicbee folder if relative path to library_folder given
        if musicbee_folder and not exists(musicbee_folder):
            if not library_folder:
                raise FileDoesNotExistError(f"Cannot find MusicBee library at given path: {musicbee_folder}")

            in_library = join(library_folder.rstrip("\\/"), musicbee_folder.lstrip("\\/"))
            if not exists(in_library):
                raise FileDoesNotExistError(
                    f"Cannot find MusicBee library at given path: {musicbee_folder} OR {in_library}"
                )
            musicbee_folder = in_library
        elif library_folder and (not musicbee_folder or not exists(musicbee_folder)):
            musicbee_folder = library_folder

        # try to resolve the playlist folder if relative path to musicbee_folder given
        musicbee_playlist_folder = join(musicbee_folder, playlist_folder)
        if exists(musicbee_playlist_folder):
            playlist_folder = musicbee_playlist_folder

        self._path: str = join(musicbee_folder, self.xml_library_filename)
        if not exists(self._path):
            raise FileDoesNotExistError(f"Cannot find MusicBee library at given path: {self._path}")

        self._xml_parser = XMLLibraryParser(self._path, path_keys=self.xml_path_keys)
        self.xml: dict[str, Any] = self._xml_parser.parse()

        super().__init__(
            library_folder=library_folder,
            playlist_folder=playlist_folder,
            other_folders=other_folders,
            include=include,
            exclude=exclude,
            remote_wrangler=remote_wrangler,
        )

    def _get_track_from_xml_path(self, track_xml: dict[str, Any], tracks: dict[str, LocalTrack]) -> LocalTrack | None:
        if track_xml["Track Type"] != "File":
            return

        path = track_xml["Location"]
        prefixes = {
            self.library_folder,
            self.xml["Music Folder"],
            *{other.replace("\\", "/") for other in self.other_folders},
            *{other.replace("/", "\\") for other in self.other_folders}
        }

        for prefix in prefixes:
            track = tracks.get(path.removeprefix(prefix).casefold(), tracks.get(path.removeprefix(prefix)))
            if track is not None:
                return track

        self.errors.append(path)

    def load_tracks(self) -> list[LocalTrack]:
        # need to remove the library folder to make it os agnostic
        tracks = super().load_tracks()
        tracks_paths = {track.path.removeprefix(self.library_folder).casefold(): track for track in tracks}

        self.logger.debug(f"Enrich {self.name} tracks: START")

        for track_xml in self.xml["Tracks"].values():
            track = self._get_track_from_xml_path(track_xml, tracks_paths)
            if track is None:
                continue

            track.rating = int(track_xml.get("Rating")) if track_xml.get("Rating") is not None else None
            track.date_added = track_xml.get("Date Added")
            track.last_played = track_xml.get("Play Date UTC")
            track.play_count = track_xml.get("Play Count", 0)

        self._log_errors("Could not find a loaded track for these paths from the MusicBee library file")
        self.logger.debug(f"Enrich {self.name} tracks: DONE\n")
        return list(tracks_paths.values())

    def save(self, dry_run: bool = True, *_, **__) -> dict[str, Any]:
        """
        Generate and save the XML library file for this MusicBee library.

        :param dry_run: Run function, but do not modify file at all.
        :return: Map representation of the saved XML file.
        """
        tracks_paths = {track.path.removeprefix(self.library_folder).casefold(): track for track in self.tracks}
        track_id_map: dict[LocalTrack, tuple[int, str]] = {}

        for track_xml in self.xml["Tracks"].values():
            track = self._get_track_from_xml_path(track_xml, tracks_paths)
            if track is None:
                continue

            track_id_map[track] = (track_xml["Track ID"], track_xml["Persistent ID"])

        self._log_errors("Could not find a loaded track for these paths from the MusicBee library file")

        tracks: dict[int, dict[str, Any]] = {}
        max_track_id = max(id_ for id_, _ in track_id_map.values()) if track_id_map else 0
        for i, track in enumerate(self.tracks, max(1, max_track_id)):
            track_id, persistent_id = track_id_map.get(track, [i, None])
            tracks[track_id] = self.track_to_xml(track, track_id=track_id, persistent_id=persistent_id)
            track_id_map[track] = (tracks[track_id]["Track ID"], tracks[track_id]["Persistent ID"])

        playlist_id_map = {
            playlist_xml["Name"]: (playlist_xml["Playlist ID"], playlist_xml["Playlist Persistent ID"])
            for playlist_xml in self.xml["Playlists"]
        }

        playlists: list[dict[str, Any]] = []
        max_playlist_id = max(id_ for id_, _ in playlist_id_map.values()) if playlist_id_map else 0
        for i, (name, playlist) in enumerate(self.playlists.items(), max_playlist_id):
            playlist_id, persistent_id = playlist_id_map.get(name, [i, None])
            playlist = self.playlist_to_xml(
                playlist, tracks=track_id_map, playlist_id=playlist_id, persistent_id=persistent_id
            )
            playlists.append(playlist)

        xml = {
            "Major Version": self.xml.get("Major Version", "1"),
            "Minor Version": self.xml.get("Minor Version", "1"),
            "Application Version": self.xml.get("Application Version", "1"),
            "Music Folder": self.library_folder,
            "Library Persistent ID":
                self.xml.get("Library Persistent ID", self.generate_persistent_id(self.library_folder)),
            "Tracks": dict(sorted(((id_, track) for id_, track in tracks.items()), key=lambda x: x[0])),
            "Playlists": sorted(playlists, key=lambda x: x["Playlist ID"]),
        }

        self._xml_parser.unparse(data=xml, dry_run=dry_run)
        self.xml = xml
        return self.xml

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

        id_ = id_ or hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
        if len(id_) > 16:
            raise MusicBeeIDError(f"Persistent ID is >16-characters in length (length={len(id_)}): {id_}")
        return id_.upper()

    @classmethod
    def track_to_xml(cls, track: LocalTrack, track_id: int, persistent_id: str | None = None) -> dict[str, Any]:
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
            genres = {"Genre": track.genres[0]}
        elif track.genres:
            genres = {f"Genre{i}": genre for i, genre in enumerate(track.genres, 1)}

        data = {
            "Track ID": track_id,
            "Persistent ID": cls.generate_persistent_id(id_=persistent_id, value=track.path),
            "Name": track.title,
            "Artist": track.artist,
            "Album": track.album,
            "Album Artist": track.album_artist,
            "Track Number": track.track_number,
            "Track Count": track.track_total,
        } | genres | {
            "Year": track.year,
            "BPM": track.bpm,
            "Disc Number": track.disc_number,
            "Disc Count": track.disc_total,
            "Compilation": track.compilation,
            "Comments": track.tag_sep.join(track.comments) if track.comments else None,
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
            "Date Modified": track.date_modified,
            "Date Added": track.date_added,
            "Play Date UTC": track.last_played,
            "Play Count": track.play_count,
            "Track Type": "File",  # can also be 'URL' for streams
            "Location": track.path,
        }

        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def playlist_to_xml(
            cls,
            playlist: LocalPlaylist,
            tracks: Mapping[LocalTrack, int | Sequence[int, str]] | list[LocalTrack],
            playlist_id: int,
            persistent_id: str | None = None,
    ) -> dict[str, Any]:
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

    :ivar timestamp_format: The string representation of the timestamp format when parsing.
    :ivar doctype: The doctype to add to the XML file when exporting data to file.
    :ivar schema_version: The schema version to add to the XML file when exporting data to file.

    :param path: Path to the XML file.
    :param path_keys: A list of keys in the XML file that need to be processed as system paths.
    """

    __slots__ = ("path", "path_keys", "iterparse")

    timestamp_format = "%Y-%m-%dT%H:%M:%SZ"
    doctype = ('<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" '
               '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">')
    schema_version = 1.0

    def __init__(self, path: str, path_keys: Iterable[str] | None = None):
        self.path: str = path
        self.path_keys: frozenset[str] = frozenset(path_keys) if path_keys else frozenset()
        self.iterparse: iterparse | None = None

    @classmethod
    def to_xml_timestamp(cls, timestamp: datetime | None) -> str | None:
        """Convert timestamp string as found in the MusicBee XML library file to a ``datetime`` object"""
        if timestamp:
            return timestamp.strftime(cls.timestamp_format)

    @classmethod
    def from_xml_timestamp(cls, timestamp_str: str | None) -> datetime | None:
        """Convert timestamp string as found in the MusicBee XML library file to a ``datetime`` object"""
        if timestamp_str:
            return datetime.strptime(timestamp_str, cls.timestamp_format)

    @staticmethod
    def to_xml_path(path: str) -> str:
        """Convert a standard system path to a file path as found in the MusicBee XML library file"""
        return f"file://localhost/{urllib.parse.quote(path.replace('\\', '/'), safe=':/')}"

    @staticmethod
    def from_xml_path(path: str) -> str:
        """Clean the file paths as found in the MusicBee XML library file to a standard system path"""
        return normpath(urllib.parse.unquote(path.removeprefix("file://localhost/")))

    def _iter_elements(self) -> Generator[etree.Element, [], []]:
        for event, element in self.iterparse:
            yield element

    def _parse_value(self, value: Any, tag: str, parent: str | None = None):
        if tag == 'string':
            if parent in self.path_keys:
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
            raise XMLReaderError(f"Unrecognised element: {element.tag}, {element.text}, {peek.tag}, {peek.text}")
        else:
            raise XMLReaderError(f"Unrecognised element: {element.tag}, {element.text}")

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

        # close the iterator
        for _ in self.iterparse:
            pass
        self.iterparse = None

        return results

    def _unparse_dict(self, element: etree._Element, data: Mapping[str, Any]):

        sub_element: etree._Element = etree.SubElement(element, "dict")
        for key, value in data.items():
            etree.SubElement(sub_element, "key").text = str(key)

            if isinstance(value, bool):
                etree.SubElement(sub_element, str(value).lower())
            elif isinstance(value, str):
                if key in self.path_keys:
                    etree.SubElement(sub_element, "string").text = self.to_xml_path(value)
                else:
                    etree.SubElement(sub_element, "string").text = str(value)
            elif isinstance(value, Number):
                etree.SubElement(sub_element, "integer").text = str(value)
            elif isinstance(value, datetime):
                etree.SubElement(sub_element, "date").text = self.to_xml_timestamp(value)
            elif isinstance(value, Mapping):
                self._unparse_dict(element=sub_element, data=value)
            elif isinstance(value, Sequence):
                array_element: etree.Element = etree.SubElement(sub_element, "array")
                for item in value:
                    self._unparse_dict(element=array_element, data=item)
            else:
                raise XMLReaderError(f"Unexpected value type: {value} ({type(value)})")

    def unparse(self, data: Mapping[str, Any], dry_run: bool = True) -> None:
        """
        Un-parse a map of XML data to XML and save to file.

        :param data: Map of XML data to export.
        :param dry_run: Run function, but do not modify file at all.
        """
        root: etree.Element = etree.Element("plist")
        root.set("version", str(self.schema_version))

        self._unparse_dict(element=root, data=data)
        etree.indent(root, space="\t", level=0)

        # convert to string and apply formatting to ensure output string is expected format
        output: str = etree.tostring(root, xml_declaration=True, encoding="UTF-8", doctype=self.doctype).decode("utf-8")
        output = re.sub(r"</key>\n\s+<(string|integer|date|true|false)", r"</key><\1", output)
        output = re.sub("\n\t", "\n", output)
        output = output.replace("'", '"')

        if not dry_run:
            with open(self.path, "w", encoding="utf-8") as file:
                file.write(output.rstrip('\n') + '\n')
