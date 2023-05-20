import re
from abc import ABCMeta, abstractmethod
from typing import Optional, List, Tuple, Set

from PIL import Image

from syncify.local.file import File
from syncify.local.track.base.processor import TagProcessor
from syncify.spotify import check_spotify_type, IDType, __UNAVAILABLE_URI_VALUE__


class TagReader(File, TagProcessor, metaclass=ABCMeta):
    """Contains methods for extracting tags from a loaded file"""

    def _read_metadata(self):
        """Driver for extracting metadata from a loaded file"""

        self.title = self._read_title()
        self.artist = self._read_artist()
        self.album = self._read_album()
        self.album_artist = self._read_album_artist()
        self.track_number = self._read_track_number()
        self.track_total = self._read_track_total()
        self.genres = self._read_genres()
        self.year = self._read_year()
        self.bpm = self._read_bpm()
        self.key = self._read_key()
        self.disc_number = self._read_disc_number()
        self.disc_total = self._read_disc_total()
        self.compilation = self._read_compilation()
        self.comments = self._read_comments()

        self._uri, self._has_uri = self._read_uri()
        self.has_image = self._check_for_images()

    def _read_tag(self, tag_ids: List[str]) -> Optional[list]:
        """Extract all tag values from file for a given list of tag IDs"""
        values = []
        for tag_id in tag_ids:
            value = self.file.get(tag_id)
            if value is None or (isinstance(value, str) and len(value.strip()) == 0):
                # skip null or empty/blank strings
                continue

            values.extend(value) if isinstance(value, list) else values.append(value)

        return values if len(values) > 0 else None

    def _read_title(self) -> Optional[str]:
        """Extract track title tags from file"""
        values = self._read_tag(self.tag_map.title)
        return str(values[0]) if values is not None else None

    def _read_artist(self) -> Optional[str]:
        """Extract artist tags from file"""
        values = self._read_tag(self.tag_map.artist)
        return str(values[0]) if values is not None else None

    def _read_album(self) -> Optional[str]:
        """Extract album tags from file"""
        values = self._read_tag(self.tag_map.album)
        return str(values[0]) if values is not None else None

    def _read_album_artist(self) -> Optional[str]:
        """Extract album artist tags from file"""
        values = self._read_tag(self.tag_map.album_artist)
        return str(values[0]) if values is not None else None

    def _read_track_number(self) -> Optional[int]:
        """Extract track number tags from file"""
        values = self._read_tag(self.tag_map.track_number)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[0]) if self._num_sep in value else int(value)

    def _read_track_total(self) -> Optional[int]:
        """Extract total track count tags from file"""
        values = self._read_tag(self.tag_map.track_total)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[1]) if self._num_sep in value else int(value)

    def _read_genres(self) -> Optional[List[str]]:
        """Extract genre tags from file"""
        values = self._read_tag(self.tag_map.genres)
        return [str(value) for value in values] if values is not None else None

    def _read_year(self) -> Optional[int]:
        """Extract year tags from file"""
        values = self._read_tag(self.tag_map.year)
        if values is None:
            return

        try:
            year = int(re.sub(r"\D+", "", str(values[0]))[:4])
            return year if year > 1000 else None
        except (ValueError, TypeError):
            return

    def _read_bpm(self) -> Optional[float]:
        """Extract bpm tags from file"""
        values = self._read_tag(self.tag_map.bpm)
        return float(values[0]) if values is not None else None

    def _read_key(self) -> Optional[str]:
        """Extract key tags from file"""
        values = self._read_tag(self.tag_map.key)
        return str(values[0]) if values is not None else None

    def _read_disc_number(self) -> Optional[int]:
        """Extract disc number tags from file"""
        values = self._read_tag(self.tag_map.disc_number)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[0]) if self._num_sep in value else int(value)

    def _read_disc_total(self) -> Optional[int]:
        """Extract total disc count tags from file"""
        values = self._read_tag(self.tag_map.disc_total)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[1]) if self._num_sep in value else int(value)

    def _read_compilation(self) -> Optional[bool]:
        """Extract compilation tags from file"""
        values = self._read_tag(self.tag_map.compilation)
        return bool(int(values[0])) if values is not None else None

    def _read_comments(self) -> Optional[Set[str]]:
        """Extract comment tags from file"""
        values = self._read_tag(self.tag_map.comments)
        return list({str(value) for value in values}) if values is not None else None

    def _read_uri(self) -> Tuple[Optional[str], Optional[bool]]:
        """
        Extract data relating to Spotify URI from file

        :return: Tuple of URI, plus:
            * True if the track contains a URI and is available on remote server
            * False if the track has no URI and is not available on remote server
            * None if the track has no URI, and it is not known whether it is available on remote server
        """
        has_uri = None
        uri = None
        possible_values: Optional[List[str]] = self[self.uri_tag.name.casefold()]
        if possible_values is None or len(possible_values) == 0:
            return uri, has_uri

        for uri in possible_values:
            if uri == __UNAVAILABLE_URI_VALUE__:
                has_uri = False
                uri = None
                break
            elif check_spotify_type(uri, types=IDType.URI):
                has_uri = True
                break

        return uri, has_uri

    @abstractmethod
    def _read_images(self) -> Optional[List[Image.Image]]:
        """Extract image from file"""

    def _check_for_images(self) -> bool:
        """Check if file has embedded images"""
        return self._read_tag(self.tag_map.images) is not None
