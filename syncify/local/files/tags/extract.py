import os
import re
from abc import ABCMeta
from datetime import datetime
from os.path import basename, dirname, getmtime, splitext, getsize, join, exists
from typing import Optional, List, Tuple

from PIL import Image

from syncify.local.files.tags.helpers import TrackBase
from syncify.spotify.helpers import check_spotify_type, SpotifyType, __UNAVAILABLE_URI_VALUE__


class TagExtractor(TrackBase, metaclass=ABCMeta):

    def _extract_metadata(self, position: Optional[int] = None) -> None:
        """
        Driver for extracting metadata from a loaded file

        :param position: A position to assign to this track e.g. for playlist order.
        """

        self.position = position
        self.title = self._extract_title()
        self.artist = self._extract_artist()
        self.album = self._extract_album()
        self.album_artist = self._extract_album_artist()
        self.track_number = self._extract_track_number()
        self.track_total = self._extract_track_total()
        self.genres = self._extract_genres()
        self.year = self._extract_year()
        self.bpm = self._extract_bpm()
        self.key = self._extract_key()
        self.disc_number = self._extract_disc_number()
        self.disc_total = self._extract_disc_total()
        self.compilation = self._extract_compilation()
        self.comments = self._extract_comments()

        self.uri, self.has_uri = self._extract_uri()

        self.image_links = None
        self.has_image = self._check_for_images()

        self.folder = basename(dirname(self.path))
        self.filename = basename(self.path)
        self.ext = splitext(self.path)[1].lower()
        self.size = getsize(self.path)
        self.length = self.file.info.length
        self.date_modified = datetime.fromtimestamp(getmtime(self.path))

    def _get_tag_values(self, tag_ids: List[str]) -> Optional[list]:
        """Extract all tag values for a given list of tag IDs"""
        values = []
        for tag_id in tag_ids:
            value = self.file.get(tag_id)
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

    def _extract_genres(self) -> Optional[List[str]]:
        """Extract metadata from file for genre"""
        values = self._get_tag_values(self.tag_map.genres)
        return [str(value) for value in values] if values is not None else None

    def _extract_year(self) -> Optional[int]:
        """Extract metadata from file for year"""
        values = self._get_tag_values(self.tag_map.year)
        if values is None:
            return

        try:
            year = int(re.sub("\D+", "", str(values[0]))[:4])
            return year if year > 1000 else None
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
        return bool(int(values[0])) if values is not None else None

    def _extract_comments(self) -> Optional[List[str]]:
        """Extract metadata from file for comment"""
        values = self._get_tag_values(self.tag_map.comments)
        return list(set(str(value) for value in values)) if values is not None else None

    def _extract_uri(self) -> Tuple[Optional[str], bool]:
        """
        Extract metadata relating to Spotify URI from current object metadata

        :return: URI, if the track is available on remote server i.e. has_uri on remote server.
        """
        has_uri = False
        uri = None
        possible_values: Optional[List[str]] = getattr(self, self.uri_tag.name.lower())
        if possible_values is None or len(possible_values) == 0:
            return uri, has_uri

        for uri in possible_values:
            if uri == __UNAVAILABLE_URI_VALUE__:
                has_uri = False
                uri = None
                break
            elif check_spotify_type(uri, types=SpotifyType.URI):
                has_uri = True
                break

        return uri, has_uri

    def _extract_images(self) -> Optional[List[Image.Image]]:
        """Extract image from file"""
        values = self._get_tag_values(self.tag_map.images)
        return [Image.open(bytes(value)) for value in values] if values is not None else None

    def _check_for_images(self) -> bool:
        """Check if file has embedded images"""
        return self._get_tag_values(self.tag_map.images) is not None

    def save_images_to_file(self, output_folder: str) -> int:
        """
        Extract and save all embedded images from file

        :returns: Number of images extracted.
        """
        images = self._extract_images()
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
