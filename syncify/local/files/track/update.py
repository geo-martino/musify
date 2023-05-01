from abc import ABCMeta, abstractmethod
from copy import copy
from typing import List, Optional, Union, Set

from syncify.local.files.track.processor import TagProcessor
from syncify.local.files.utils.tags import TagEnums
from syncify.spotify.helpers import __UNAVAILABLE_URI_VALUE__
from syncify.utils.helpers import make_list


class TagUpdater(TagProcessor, metaclass=ABCMeta):

    def update_file_tags(
            self, 
            tags: Optional[Union[TagEnums, List[TagEnums]]] = None, 
            replace: bool = False, 
            dry_run: bool = True
    ) -> Set[TagEnums]:
        """
        Update file's tags from given dictionary of tags.

        :param tags: Tags to be updated.
        :param replace: Destructively replace tags in each file.
        :param dry_run: Run function, but do not modify file at all.
        :returns: List of tags that have been updated.
        """
        self.load_file()
        file = copy(self)
        updated: Set[TagEnums] = set()

        tags: Set[TagEnums] = set(make_list(tags))
        if TagEnums.ALL in tags:
            tags = TagEnums.all()

        if TagEnums.TITLE in tags:
            conditionals = [file.title is None, replace and self.title != file.title]
            if any(conditionals) and self._update_title(dry_run):
                updated.add(TagEnums.TITLE)
                    
        if TagEnums.ARTIST in tags:
            conditionals = [file.artist is None, replace and self.artist != file.artist]
            if any(conditionals) and self._update_artist(dry_run):
                updated.add(TagEnums.ARTIST)

        if TagEnums.ALBUM in tags:
            conditionals = [file.album is None, replace and self.album != file.album]
            if any(conditionals) and self._update_album(dry_run):
                updated.add(TagEnums.ALBUM)

        if TagEnums.ALBUM_ARTIST in tags:
            conditionals = [file.album_artist is None, replace and self.album_artist != file.album_artist]
            if any(conditionals) and self._update_album_artist(dry_run):
                updated.add(TagEnums.ALBUM_ARTIST)

        if TagEnums.TRACK in tags:
            conditionals = [
                file.track_number is None and file.track_total is None,
                replace and (self.track_number != file.track_number or self.track_total != file.track_total)
            ]
            if any(conditionals) and self._update_track(dry_run):
                updated.add(TagEnums.TRACK)

        if TagEnums.GENRES in tags:
            conditionals = [file.genres is None, replace and self.genres != file.genres]
            if any(conditionals) and self._update_genres(dry_run):
                updated.add(TagEnums.GENRES)

        if TagEnums.YEAR in tags:
            conditionals = [file.year is None, replace and self.year != file.year]
            if any(conditionals) and self._update_year(dry_run):
                updated.add(TagEnums.YEAR)

        if TagEnums.BPM in tags:
            conditionals = [
                file.bpm is None,
                int(getattr(file, "bpm", 0)) < 30,
                replace and int(getattr(self, "bpm", 0)) != int(getattr(file, "bpm", 0))
            ]
            if any(conditionals) and self._update_bpm(dry_run):
                updated.add(TagEnums.BPM)

        if TagEnums.KEY in tags:
            conditionals = [file.key is None, replace and self.key != file.key]
            if any(conditionals) and self._update_key(dry_run):
                updated.add(TagEnums.KEY)

        if TagEnums.DISC in tags:
            conditionals = [
                file.disc_number is None and file.disc_number is None,
                replace and (self.disc_number != file.disc_number or self.disc_total != file.disc_total)
            ]
            if any(conditionals) and self._update_disc(dry_run):
                updated.add(TagEnums.DISC)

        if TagEnums.COMPILATION in tags:
            conditionals = [file.compilation is None, replace and self.compilation != file.compilation]
            if any(conditionals) and self._update_compilation(dry_run):
                updated.add(TagEnums.COMPILATION)

        if TagEnums.COMMENTS in tags:
            conditionals = [file.comments is None, replace and self.comments != file.comments]
            if any(conditionals) and self._update_comments(dry_run):
                updated.add(TagEnums.COMMENTS)

        if TagEnums.URI in tags:  # needs deeper comparison
            conditionals = [file.uri is None, self.has_uri is False, replace and self.uri != file.uri]
            if any(conditionals) and self._update_uri(dry_run):
                updated.add(TagEnums.URI)

        if TagEnums.IMAGES in tags:  # needs deeper comparison
            conditionals = [file.has_image is False, replace and self.has_image != file.has_image]
            if any(conditionals) and self._update_images(dry_run):
                updated.add(TagEnums.IMAGES)

        if not dry_run and len(updated) > 0:
            self.file.save()

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
    
    def _update_title(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for track title
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.title), None), self.title, dry_run)

    def _update_artist(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for artist
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.artist), None), self.artist, dry_run)

    def _update_album(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for album
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.album), None), self.album, dry_run)

    def _update_album_artist(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for album artist
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.album_artist), None), self.album_artist, dry_run)

    def _update_track(self, dry_run: bool = True) -> bool:
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

    def _update_genres(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for genre
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.genres), None), self.genres, dry_run)

    def _update_year(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for year
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.year), None), self.year, dry_run)

    def _update_bpm(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for bpm
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.bpm), None), self.bpm, dry_run)

    def _update_key(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for key
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.key), None), self.key, dry_run)

    def _update_disc(self, dry_run: bool = True) -> bool:
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

    def _update_compilation(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for compilation
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.compilation), None), int(self.compilation), dry_run)

    def _update_comments(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for comment
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        return self._update_tag_value(next(iter(self.tag_map.comments), None), self.comments, dry_run)

    def _update_uri(self, dry_run: bool = True) -> bool:
        """
        Update metadata in file for URI
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """
        tag_id = next(iter(getattr(self.tag_map, self.uri_tag.name.lower(), [])), None)
        tag_value = __UNAVAILABLE_URI_VALUE__ if not self.has_uri else self.uri
        return self._update_tag_value(tag_id, tag_value, dry_run)

    @abstractmethod
    def _update_images(self, dry_run: bool = True) -> bool:
        """
        Update image in file

        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been if dry_run is True, False otherwise.
        """

    def clear_tags(self, tags: Optional[Union[TagEnums, List[TagEnums]]] = None, dry_run: bool = True) -> Set[TagEnums]:
        """
        Remove tags from file.

        :param tags: Tags to remove.
        :param dry_run: Run function, but do not modify file at all.
        :returns: List of tags that have been removed.
        """
        tags: Set[TagEnums] = set(make_list(tags))
        if TagEnums.ALL in tags:
            tags = TagEnums.all()

        tag_names = set(tag_name for tag in tags for tag_name in TagEnums.to_tag(tag))
        removed = set(TagEnums.to_enum(tag_name) for tag_name in tag_names if self._clear_tag(tag_name, dry_run))

        if TagEnums.IMAGES in removed:
            self.has_image = False

        if not dry_run and len(removed) > 0:
            self.file.save()

        return removed

    def _clear_tag(self, tag_name: str, dry_run: bool = True) -> bool:
        """
        Remove a tag by its tag name.

        :param tag_name: Tag ID to remove.
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if tag has been remove, False otherwise.
        """
        removed = False

        tag_ids = getattr(self.tag_map, tag_name, None)
        if tag_ids is None or len(tag_ids) is None:
            return removed

        for tag_id in tag_ids:
            if tag_id in self.file:
                if not dry_run:
                    del self.file[tag_id]
                removed = True

        return removed
    