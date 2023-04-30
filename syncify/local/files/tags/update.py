from abc import ABCMeta, abstractmethod
from copy import copy
from http.client import HTTPResponse
from typing import List, Optional, Union
from urllib.error import URLError
from urllib.request import urlopen

from helpers import TagEnums
from helpers import TrackBase
from syncify.utils.helpers import make_list


class TagUpdater(TrackBase, metaclass=ABCMeta):

    def _open_image_url(self, image_url: Optional[str]) -> Optional[HTTPResponse]:
        """Open HTTPResponse object from a given URL for downloading images"""
        if image_url is None:
            return

        try:  # open image from link
            return urlopen(image_url)
        except URLError:
            self._logger.error(f"{image_url} | Failed to open image")
            return
    
    def update_file_tags(
            self, 
            tags: Optional[Union[TagEnums, List[TagEnums]]] = None, 
            replace: bool = False, 
            dry_run: bool = True
    ) -> List[TagEnums]:
        """
        Update file's tags from given dictionary of tags.

        :param tags: Tags to be updated.
        :param replace: Destructively replace tags in each file.
        :param dry_run: Run function, but do not modify file at all.
        :returns: List of tags that have been updated.
        """
        self.load_file()
        file = copy(self)
        
        tags: List[TagEnums] = make_list(tags)
        updated: List[TagEnums] = []

        if TagEnums.TITLE in tags:
            conditionals = [file.title is None, replace and self.title != file.title]
            if any(conditionals) and self.update_title(dry_run):
                updated.append(TagEnums.TITLE)
                    
        if TagEnums.ARTIST in tags:
            conditionals = [file.artist is None, replace and self.artist != file.artist]
            if any(conditionals) and self.update_artist(dry_run):
                updated.append(TagEnums.ARTIST)

        if TagEnums.ALBUM in tags:
            conditionals = [file.album is None, replace and self.album != file.album]
            if any(conditionals) and self.update_album(dry_run):
                updated.append(TagEnums.ALBUM)

        if TagEnums.ALBUM_ARTIST in tags:
            conditionals = [file.album_artist is None, replace and self.album_artist != file.album_artist]
            if any(conditionals) and self.update_album_artist(dry_run):
                updated.append(TagEnums.ALBUM_ARTIST)

        if TagEnums.TRACK in tags:
            conditionals = [
                file.track_number is None and file.track_total is None,
                replace and (self.track_number != file.track_number or self.track_total != file.track_total)
            ]
            if any(conditionals) and self.update_track(dry_run):
                updated.append(TagEnums.TRACK)

        if TagEnums.GENRES in tags:
            conditionals = [file.genres is None, replace and self.genres != file.genres]
            if any(conditionals) and self.update_genres(dry_run):
                updated.append(TagEnums.GENRES)

        if TagEnums.YEAR in tags:
            conditionals = [file.year is None, replace and self.year != file.year]
            if any(conditionals) and self.update_year(dry_run):
                updated.append(TagEnums.YEAR)

        if TagEnums.BPM in tags:
            conditionals = [
                file.bpm is None,
                int(getattr(file, "bpm", 0)) < 30,
                replace and int(getattr(self, "bpm", 0)) != int(getattr(file, "bpm", 0))
            ]
            if any(conditionals) and self.update_bpm(dry_run):
                updated.append(TagEnums.BPM)

        if TagEnums.KEY in tags:
            conditionals = [file.key is None, replace and self.key != file.key]
            if any(conditionals) and self.update_key(dry_run):
                updated.append(TagEnums.KEY)

        if TagEnums.DISC in tags:
            conditionals = [
                file.disc_number is None and file.disc_number is None,
                replace and (self.disc_number != file.disc_number or self.disc_total != file.disc_total)
            ]
            if any(conditionals) and self.update_disc(dry_run):
                updated.append(TagEnums.DISC)

        if TagEnums.COMPILATION in tags:
            conditionals = [file.compilation is None, replace and self.compilation != file.compilation]
            if any(conditionals) and self.update_compilation(dry_run):
                updated.append(TagEnums.COMPILATION)

        if TagEnums.IMAGE in tags:  # needs deeper comparison
            conditionals = [file.has_image is None, replace and self.has_image != file.has_image]
            if any(conditionals) and self.update_images(dry_run):
                updated.append(TagEnums.IMAGE)

        if TagEnums.COMMENTS in tags:
            conditionals = [file.comments is None, replace and self.comments != file.comments]
            if any(conditionals) and self.update_comments(dry_run):
                updated.append(TagEnums.COMMENTS)

        if TagEnums.URI in tags:  # needs deeper comparison
            conditionals = [file.uri is None, self.has_uri is False, replace and self.uri != file.uri]
            if any(conditionals) and self.update_uri(dry_run):
                updated.append(TagEnums.URI)
        
        return updated
                    
    @abstractmethod
    def _update_tag_value(self, tag_id: Optional[str], tag_value: object, dry_run: bool = True) -> bool:
        """
        Generic method for updating a give tag value in the file.
        
        :param tag_id: ID of the tag for this file type.
        :param tag_value: New value to assign.
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
    
    def update_title(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for track title
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.title), None), self.title, dry_run)

    def update_artist(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for artist
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.artist), None), self.artist, dry_run)

    def update_album(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for album
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.album), None), self.album, dry_run)

    def update_album_artist(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for album artist
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.album_artist), None), self.album_artist, dry_run)

    def update_track(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for track number
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        tag_id_number = next(iter(self.tag_map.track_number), None)
        tag_id_total = next(iter(self.tag_map.track_total), None)
        
        if tag_id_number != tag_id_total and self.track_total is not None:
            number_updated = self._update_tag_value(tag_id_number, str(self.track_number).zfill(2), dry_run)
            total_updated = self._update_tag_value(tag_id_total, str(self.track_total).zfill(2), dry_run)
            return number_updated or total_updated
        elif self.track_total is not None:
            tag_value = self._num_sep.join([str(self.track_number).zfill(2), str(self.track_total).zfill(2)])
        else:
            tag_value = str(self.track_number).zfill(2)

        return self._update_tag_value(tag_id_number, tag_value, dry_run)

    def update_genres(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for genre
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.genres), None), self.genres, dry_run)

    def update_year(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for year
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.year), None), self.year, dry_run)

    def update_bpm(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for bpm
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.bpm), None), self.bpm, dry_run)

    def update_key(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for key
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.key), None), self.key, dry_run)

    def update_disc(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for disc number
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        tag_id_number = next(iter(self.tag_map.disc_number), None)
        tag_id_total = next(iter(self.tag_map.disc_total), None)

        if tag_id_number != tag_id_total and self.disc_total is not None:
            number_updated = self._update_tag_value(tag_id_number, str(self.disc_number).zfill(2), dry_run)
            total_updated = self._update_tag_value(tag_id_total, str(self.disc_total).zfill(2), dry_run)
            return number_updated or total_updated
        elif self.disc_total is not None:
            tag_value = self._num_sep.join([str(self.disc_number).zfill(2), str(self.disc_total).zfill(2)])
        else:
            tag_value = str(self.disc_number).zfill(2)

        return self._update_tag_value(tag_id_number, tag_value, dry_run)

    def update_compilation(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for compilation
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.compilation), None), self.compilation, dry_run)

    @abstractmethod
    def update_images(self, dry_run: bool = True) -> bool:
        """
        Update image in file
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """

    def update_comments(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for comment
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.comments), None), self.comments, dry_run)

    def update_uri(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for URI
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(self.uri_tag.name.lower(), self.uri, dry_run)
    