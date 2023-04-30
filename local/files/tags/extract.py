import re
from abc import ABCMeta
from datetime import datetime
from os.path import basename, dirname, getmtime, splitext, getsize
from typing import Optional, List, Tuple

from local.files.tags.helpers import TagBase, TagEnums
from spotify.utils import check_valid_spotify_type, SpotifyTypes


class TagExtractor(TagBase, metaclass=ABCMeta):

    def _extract_metadata(self) -> None:
        """Driver for extracting metadata from a loaded file"""

        self.title = self.extract_title()
        self.artist = self.extract_artist()
        self.album = self.extract_album()
        self.album_artist = self.extract_album_artist()
        self.track_number = self.extract_track_number()
        self.track_total = self.extract_track_total()
        self.genres = self.extract_genres()
        self.year = self.extract_year()
        self.bpm = self.extract_bpm()
        self.key = self.extract_key()
        self.disc_number = self.extract_disc_number()
        self.disc_total = self.extract_disc_total()
        self.compilation = self.extract_compilation()
        self.has_image = self.extract_images() is not None
        self.comments = self.extract_comments()
        self.uri, self.has_uri, self.comments = self.extract_uri(TagEnums.COMMENTS)

        self.folder = basename(dirname(self.path))
        self.filename = basename(self.path)
        self.ext = splitext(self.path)[1].lower()
        self.size = getsize(self.path)
        self.length = self.file.info.length
        self.date_modified = datetime.fromtimestamp(getmtime(self.path))

    def _get_tag_values(self, tag_names: List[str]) -> Optional[list]:
        """Extract all tag values for a given list of tag IDs"""
        values = []
        for tag_name in tag_names:
            value = self.file.get(tag_name)
            if value is None or (isinstance(value, str) and len(value.strip()) == 0):
                # skip null or empty/blank strings
                continue

            values.extend(value) if isinstance(value, list) else values.append(value)

        return values if len(values) > 0 else None

    def extract_title(self) -> Optional[str]:
        """Extract metadata from file for track title"""
        values = self._get_tag_values(self.tag_map.title)
        return str(values[0]) if values is not None else None

    def extract_artist(self) -> Optional[str]:
        """Extract metadata from file for artist"""
        values = self._get_tag_values(self.tag_map.artist)
        return str(values[0]) if values is not None else None

    def extract_album(self) -> Optional[str]:
        """Extract metadata from file for album"""
        values = self._get_tag_values(self.tag_map.album)
        return str(values[0]) if values is not None else None

    def extract_album_artist(self) -> Optional[str]:
        """Extract metadata from file for album artist"""
        values = self._get_tag_values(self.tag_map.album_artist)
        return str(values[0]) if values is not None else None

    def extract_track_number(self) -> Optional[int]:
        """Extract metadata from file for track number"""
        values = self._get_tag_values(self.tag_map.track_number)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[0]) if self._num_sep in value else int(value)

    def extract_track_total(self) -> Optional[int]:
        """Extract metadata from file for total track count"""
        values = self._get_tag_values(self.tag_map.track_total)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[1]) if self._num_sep in value else int(value)

    def extract_genres(self) -> Optional[List[str]]:
        """Extract metadata from file for genre"""
        values = self._get_tag_values(self.tag_map.genres)
        return [str(value) for value in values] if values is not None else None

    def extract_year(self) -> Optional[int]:
        """Extract metadata from file for year"""
        values = self._get_tag_values(self.tag_map.year)
        if values is None:
            return

        try:
            return int(re.sub("\D+", "", str(values[0]))[:4])
        except (ValueError, TypeError):
            return

    def extract_bpm(self) -> Optional[float]:
        """Extract metadata from file for bpm"""
        values = self._get_tag_values(self.tag_map.bpm)
        return float(values[0]) if values is not None else None

    def extract_key(self) -> Optional[str]:
        """Extract metadata from file for key"""
        values = self._get_tag_values(self.tag_map.key)
        return str(values[0]) if values is not None else None

    def extract_disc_number(self) -> Optional[int]:
        """Extract metadata from file for disc number"""
        values = self._get_tag_values(self.tag_map.disc_number)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[0]) if self._num_sep in value else int(value)

    def extract_disc_total(self) -> Optional[int]:
        """Extract metadata from file for total disc count"""
        values = self._get_tag_values(self.tag_map.disc_total)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[1]) if self._num_sep in value else int(value)

    def extract_compilation(self) -> bool:
        """Extract metadata from file for compilation"""
        values = self._get_tag_values(self.tag_map.compilation)
        return bool(values[0]) if values is not None else None

    def extract_images(self) -> Optional[List[bytes]]:
        """Extract image from file"""
        values = self._get_tag_values(self.tag_map.image)
        return [bytes(value) for value in values] if values is not None else None

    def extract_comments(self) -> Optional[List[str]]:
        """Extract metadata from file for comment"""
        values = self._get_tag_values(self.tag_map.comments)
        return list(set(str(value) for value in values)) if values is not None else None

    def extract_uri(self, tag_name: TagEnums) -> Tuple[str, bool, Optional[List[str]]]:
        """
        Set properties relating to Spotify URI

        :param tag_name: name of the tag that contains possible values.
        :return: URI, if the track is available on remote server i.e. has_uri on remote server,
                and remaining values from given tag name.
        """
        has_uri = False
        uri = None
        possible_values: List[str] = getattr(self, tag_name.name.lower())

        if possible_values is not None and len(possible_values) > 0:
            for uri in possible_values:
                if uri == self._unavailable_uri_value:
                    possible_values.remove(uri)
                    has_uri = False
                    uri = None
                    break
                elif check_valid_spotify_type(uri, types=SpotifyTypes.URI):
                    possible_values.remove(uri)
                    has_uri = True
                    break

        return uri, has_uri, possible_values if len(possible_values) > 0 else None
