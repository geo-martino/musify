from abc import ABCMeta
from typing import Optional, Set

import mutagen

from local.files.tags.helpers import TagBase


class TagUpdater(TagBase, metaclass=ABCMeta):
    
    def update_title(self) -> None:
        """Update metadata in file for track title"""
        values = self._get_tag_values(self.tag_map.title)
        return str(values[0]) if values is not None else None

    def update_artist(self) -> None:
        """Update metadata in file for artist"""
        values = self._get_tag_values(self.tag_map.artist)
        return str(values[0]) if values is not None else None

    def update_album(self) -> None:
        """Update metadata in file for album"""
        values = self._get_tag_values(self.tag_map.album)
        return str(values[0]) if values is not None else None

    def update_album_artist(self) -> None:
        """Update metadata in file for album artist"""
        values = self._get_tag_values(self.tag_map.album_artist)
        return str(values[0]) if values is not None else None

    def update_track(self) -> None:
        """Update metadata in file for track number"""
        values = self._get_tag_values(self.tag_map.track_number)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[0]) if self._num_sep in value else int(value)

    def update_genres(self) -> None:
        """Update metadata in file for genre"""
        values = self._get_tag_values(self.tag_map.genres)
        return [str(value) for value in values] if values is not None else None

    def update_year(self) -> None:
        """Update metadata in file for year"""
        values = self._get_tag_values(self.tag_map.year)
        if values is None:
            return

        try:
            return int(re.sub("\D+", "", str(values[0]))[:4])
        except (ValueError, TypeError):
            return

    def update_bpm(self) -> None:
        """Update metadata in file for bpm"""
        values = self._get_tag_values(self.tag_map.bpm)
        return float(values[0]) if values is not None else None

    def update_key(self) -> None:
        """Update metadata in file for key"""
        values = self._get_tag_values(self.tag_map.key)
        return str(values[0]) if values is not None else None

    def update_disc(self) -> None:
        """Update metadata in file for disc number"""
        values = self._get_tag_values(self.tag_map.disc_number)
        if values is None:
            return

        value = str(values[0])
        return int(value.split(self._num_sep)[0]) if self._num_sep in value else int(value)

    def update_compilation(self) -> None:
        """Update metadata in file for compilation"""
        values = self._get_tag_values(self.tag_map.compilation)
        return bool(values[0]) if values is not None else None

    def update_images(self) -> None:
        """Update image in file"""
        values = self._get_tag_values(self.tag_map.image)
        return [bytes(value) for value in values] if values is not None else None

    def update_comments(self) -> None:
        """Update metadata in file for comment"""
        values = self._get_tag_values(self.tag_map.comments)
        return set(str(value) for value in values) if values is not None else None

    def update_uri(self) -> None:
        """Update metadata in file for URI"""
        values = self._get_tag_values(self.tag_map.uri)
        return str(values[0]) if values is not None else None
    