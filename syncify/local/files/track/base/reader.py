import os
import re
from abc import ABCMeta, abstractmethod
from datetime import datetime
from os.path import basename, dirname, getmtime, splitext, getsize, join, exists
from typing import Optional, List, Tuple, Set

from PIL import Image

from syncify.local.files.track.base.tags import TagProcessor
from syncify.spotify import check_spotify_type, IDType, __UNAVAILABLE_URI_VALUE__


class TagReader(TagProcessor, metaclass=ABCMeta):
    """Contains methods for extracting tags from a loaded file"""

    def _read_metadata(self) -> None:
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

        self.folder = basename(dirname(self.path))
        self.filename = basename(self.path)
        self.ext = splitext(self.path)[1].lower()
        self.size = getsize(self.path)
        self.length = self.file.info.length
        self.date_modified = datetime.fromtimestamp(getmtime(self.path))

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
        """Extract metadata from file for track title"""
        values = self._read_tag(self.tag_map.title)
        return str(values[0]) if values is not None else None

    def _read_artist(self) -> Optional[str]:
        """Extract metadata from file for artist"""
        values = self._read_tag(self.tag_map.artist)
        return str(values[0]) if values is not None else None

    def _read_album(self) -> Optional[str]:
        """Extract metadata from file for album"""
        values = self._read_tag(self.tag_map.album)
        return str(values[0]) if values is not None else None

    def _read_album_artist(self) -> Optional[str]:
        """Extract metadata from file for album artist"""
        values = self._read_tag(self.tag_map.album_artist)
        return str(values[0]) if values is not None else None

    def _read_track_number(self) -> Optional[int]:
        """Extract metadata from file for track number"""
        values = self._read_tag(self.tag_map.track_number)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[0]) if self._num_sep in value else int(value)

    def _read_track_total(self) -> Optional[int]:
        """Extract metadata from file for total track count"""
        values = self._read_tag(self.tag_map.track_total)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[1]) if self._num_sep in value else int(value)

    def _read_genres(self) -> Optional[List[str]]:
        """Extract metadata from file for genre"""
        values = self._read_tag(self.tag_map.genres)
        return [str(value) for value in values] if values is not None else None

    def _read_year(self) -> Optional[int]:
        """Extract metadata from file for year"""
        values = self._read_tag(self.tag_map.year)
        if values is None:
            return

        try:
            year = int(re.sub(r"\D+", "", str(values[0]))[:4])
            return year if year > 1000 else None
        except (ValueError, TypeError):
            return

    def _read_bpm(self) -> Optional[float]:
        """Extract metadata from file for bpm"""
        values = self._read_tag(self.tag_map.bpm)
        return float(values[0]) if values is not None else None

    def _read_key(self) -> Optional[str]:
        """Extract metadata from file for key"""
        values = self._read_tag(self.tag_map.key)
        return str(values[0]) if values is not None else None

    def _read_disc_number(self) -> Optional[int]:
        """Extract metadata from file for disc number"""
        values = self._read_tag(self.tag_map.disc_number)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[0]) if self._num_sep in value else int(value)

    def _read_disc_total(self) -> Optional[int]:
        """Extract metadata from file for total disc count"""
        values = self._read_tag(self.tag_map.disc_total)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[1]) if self._num_sep in value else int(value)

    def _read_compilation(self) -> Optional[bool]:
        """Extract metadata from file for compilation"""
        values = self._read_tag(self.tag_map.compilation)
        return bool(int(values[0])) if values is not None else None

    def _read_comments(self) -> Optional[Set[str]]:
        """Extract metadata from file for comment"""
        values = self._read_tag(self.tag_map.comments)
        return list({str(value) for value in values}) if values is not None else None

    def _read_uri(self) -> Tuple[Optional[str], Optional[bool]]:
        """
        Extract metadata relating to Spotify URI from current object metadata

        :return: URI, if the track is available on remote server i.e. has_uri on remote server.
        """
        has_uri = None
        uri = None
        possible_values: Optional[List[str]] = getattr(self, self.uri_tag.name.lower())
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

    def extract_images_to_file(self, output_folder: str) -> int:
        """
        Extract and save all embedded images from file

        :returns: Number of images extracted.
        """
        images = self._read_images()
        if images is None:
            return False
        count = 0

        for i, image in enumerate(images):
            output_path = join(output_folder, self.filename + f"_{str(i).zfill(2)}" + image.format.lower())
            if not exists(dirname(output_path)):
                os.makedirs(dirname(output_path))

            image.save(output_path)
            count += 1

        return count
