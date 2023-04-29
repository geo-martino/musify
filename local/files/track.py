import re
from dataclasses import dataclass
from datetime import datetime
from glob import glob
from os.path import basename, dirname, getmtime, getsize, join, splitext
from typing import Optional

import mutagen
from spotify.utils import check_valid_spotify_type, SpotifyTypes
from utils.logger import Logger


@dataclass
class TagMap:
    title: list[str]
    artist: list[str]
    album: list[str]
    track_number: list[str]
    track_total: list[str]
    genre: list[str]
    year: list[str]
    bpm: list[str]
    key: list[str]
    disc_number: list[str]
    disc_total: list[str]
    compilation: list[str]
    album_artist: list[str]
    comment: list[str]
    image: list[str]


@dataclass
class TagMetadata:
    # metadata
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    album_artist: Optional[str] = None
    track_number: Optional[int] = None
    track_total: Optional[int] = None
    genres: Optional[list[str]] = None
    year: Optional[int] = None
    bpm: Optional[float] = None
    key: Optional[str] = None
    disc_number: Optional[int] = None
    disc_total: Optional[int] = None
    compilation: bool = False
    comments: Optional[list[str]] = None
    has_image: bool = False

    # file properties
    path: Optional[str] = None
    folder: Optional[str] = None
    filename: Optional[str] = None
    ext: Optional[str] = None
    size: Optional[int] = None
    length: Optional[float] = None
    date_modified: Optional[datetime] = None

    # spotify properties
    uri: Optional[str] = None
    has_uri: bool = False

    # library properties
    date_added: Optional[datetime] = None
    last_played: Optional[datetime] = None
    play_count: Optional[int] = None
    rating: Optional[int] = None


class Track(Logger, TagMetadata):

    # placeholder URI tag for tracks which aren't on Spotify
    _unavailable_uri_value = "spotify:track:unavailable"

    # some number values come as a combined string i.e. track number/track total
    # determine the separator to use when representing both values as a combined string
    _num_sep = "/"

    _filetypes: list[str] = None  # allowed extensions in lowercase
    _filepaths: list[str] = None  # all file paths in library
    _filepaths_lower: list[str] = None  # all file paths in library in lowercase

    def __init__(self, path: str, position: Optional[int] = None):
        Logger.__init__(self)

        self.path: Optional[str] = path
        self.position: Optional[int] = position
        self.valid: bool = False

        self._file: Optional[mutagen.File] = self._load_file()
        if self._file is not None:
            self._extract_metadata()
            self.valid = True

    @property
    def tag_map(self) -> TagMap:
        raise NotImplementedError

    @classmethod
    def set_file_paths(cls, music_folder: str):
        """
        Set class property for all available file paths. Necessary for loading with case-sensitive logic.
        """
        for ext in cls._filetypes:
            # first glob doesn't get filenames that start with a period
            cls._filepaths += glob(join(music_folder, "**", f"*{ext}"), recursive=True)
            # second glob only picks up filenames that start with a period
            cls._filepaths += glob(join(music_folder, "*", "**", f".*{ext}"), recursive=True)
        cls._filepaths.sort()
        cls._filepaths_lower = [path.lower() for path in cls._filepaths]

    def _load_file(self) -> Optional[mutagen.File]:
        """
        Load local file using mutagen and set object file path and extension properties.

        :returns: Mutagen file object or None if load error.
        """
        # extract file extension and confirm file type is listed in accepted file types list
        ext = splitext(self.path)[1].lower()
        if ext not in self._filetypes:
            self._logger.warning(
                f"{ext} not an accepted {self.__class__.__qualname__} file extension. "
                f"Use only: {', '.join(self._filetypes)}")
            return

        try:  # load path as given
            file = mutagen.File(self.path)
        except mutagen.MutagenError:
            try:  # load case-sensitive path and adjust object path reference if found
                path = self._get_case_sensitive_path(self.path)
                file = mutagen.File(path)
                self.path = path
            except (mutagen.MutagenError, FileNotFoundError):  # give up
                self._logger.error(f"File not found | {self.path}")
                return

        self.ext = ext
        return file

    def _get_case_sensitive_path(self, path: str) -> str:
        """
        Try to find a case-sensitive path from the list of available paths.

        :returns: Case-sensitive path if found
        :raises: FileNotFoundError. If there are no available file paths or a case-sensitive path cannot be found.
        """
        if len(self._filepaths) != len(self._filepaths_lower):
            raise AssertionError("Number of paths in file path lists does not match")

        try:
            return self._filepaths[self._filepaths_lower.index(path.lower())]
        except (ValueError, TypeError):
            raise FileNotFoundError(f"Path not found in library: {path}")

    def _extract_metadata(self) -> None:
        """Driver for extracting metadata from a loaded file"""

        self.title = self._extract_title()
        self.artist = self._extract_artist()
        self.album = self._extract_album()
        self.album_artist = self._extract_album_artist()
        self.track_number = self._extract_track_number()
        self.track_total = self._extract_track_total()
        self.genre = self._extract_genres()
        self.year = self._extract_year()
        self.bpm = self._extract_bpm()
        self.key = self._extract_key()
        self.disc_number = self._extract_disc_number()
        self.disc_total = self._extract_disc_total()
        self.compilation = self._extract_compilation()
        self.has_image = self._extract_images() is not None

        comments = self._extract_comments()
        comments = self._set_uri(comments)
        self.comment = comments[0] if len(comments) > 0 else None

        self.folder = basename(dirname(self.path))
        self.filename = basename(self.path)
        self.ext = splitext(self.path)[1].lower()
        self.size = getsize(self.path)
        self.length = self._file.length
        self.date_modified = datetime.fromtimestamp(getmtime(self.path))

    # noinspection PyTypeChecker
    def _set_uri(self, possible_values: Optional[set[str]]) -> list[str]:
        """
        Set properties relating to Spotify URI

        :param possible_values: a list of possible URIs to search through to find a valid URI.
        :return: Input list minus the URI if found.
        """
        if possible_values is not None and len(possible_values) > 0:
            for uri in possible_values:
                if uri == self._unavailable_uri_value:
                    self.has_uri = False

                    possible_values.remove(uri)
                    break
                elif check_valid_spotify_type(uri, types=SpotifyTypes.URI):
                    self.has_uri = True
                    self.uri = uri

                    possible_values.remove(uri)
                    break

        return possible_values

    def _get_tag_values(self, tag_ids: list[str]) -> Optional[list]:
        """Extract all tag values for a given list of tag IDs"""
        values = []
        for tag_id in tag_ids:
            value = self._file.get(tag_id)
            if value is None or (isinstance(value, str) and len(value.strip()) == 0):
                # skip null or empty/blank strings
                continue

            values.extend(value) if isinstance(value, list) else values.append(value)

        return values if len(values) > 0 else None
    
    def _extract_title(self) -> Optional[str]:
        """Extract metadata from file for track title"""
        values = self._get_tag_values(self.tag_map.title)
        return str(values[0]) if values is not None else None
    
    def _extract_artist(self) -> Optional[str]:
        """Extract metadata from file for artist"""
        values = self._get_tag_values(self.tag_map.artist)
        return str(values[0]) if values is not None else None
    
    def _extract_album(self) -> Optional[str]:
        """Extract metadata from file for album"""
        values = self._get_tag_values(self.tag_map.album)
        return str(values[0]) if values is not None else None
    
    def _extract_album_artist(self) -> Optional[str]:
        """Extract metadata from file for album artist"""
        values = self._get_tag_values(self.tag_map.album_artist)
        return str(values[0]) if values is not None else None
    
    def _extract_track_number(self) -> Optional[int]:
        """Extract metadata from file for track number"""
        values = self._get_tag_values(self.tag_map.track_number)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[0]) if self._num_sep in value else int(value)

    def _extract_track_total(self) -> Optional[int]:
        """Extract metadata from file for total track count"""
        values = self._get_tag_values(self.tag_map.track_total)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[1]) if self._num_sep in value else int(value)
    
    def _extract_genres(self) -> Optional[list[str]]:
        """Extract metadata from file for genre"""
        values = self._get_tag_values(self.tag_map.genre)
        return [str(value) for value in values] if values is not None else None
    
    def _extract_year(self) -> Optional[int]:
        """Extract metadata from file for year"""
        values = self._get_tag_values(self.tag_map.year)
        if values is None:
            return

        try:
            return int(re.sub("\D+", "", str(values[0]))[:4])
        except (ValueError, TypeError):
            return
    
    def _extract_bpm(self) -> Optional[float]:
        """Extract metadata from file for bpm"""
        values = self._get_tag_values(self.tag_map.bpm)
        return float(values[0]) if values is not None else None
    
    def _extract_key(self) -> Optional[str]:
        """Extract metadata from file for key"""
        values = self._get_tag_values(self.tag_map.key)
        return str(values[0]) if values is not None else None
    
    def _extract_disc_number(self) -> Optional[int]:
        """Extract metadata from file for disc number"""
        values = self._get_tag_values(self.tag_map.disc_number)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[0]) if self._num_sep in value else int(value)

    def _extract_disc_total(self) -> Optional[int]:
        """Extract metadata from file for total disc count"""
        values = self._get_tag_values(self.tag_map.disc_total)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[1]) if self._num_sep in value else int(value)
    
    def _extract_compilation(self) -> bool:
        """Extract metadata from file for compilation"""
        values = self._get_tag_values(self.tag_map.compilation)
        return bool(values[0]) if values is not None else None
    
    def _extract_comments(self) -> Optional[list[str]]:
        """Extract metadata from file for comment"""
        values = self._get_tag_values(self.tag_map.comment)
        return [str(value) for value in values] if values is not None else None
    
    def _extract_images(self) -> Optional[list[bytes]]:
        """Extract image from file"""
        values = self._get_tag_values(self.tag_map.image)
        return [bytes(value) for value in values] if values is not None else None
        
