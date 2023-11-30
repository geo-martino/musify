from abc import ABCMeta, abstractmethod
from collections.abc import Mapping, Collection
from copy import copy
from dataclasses import dataclass
from typing import Any

import mutagen

from syncify.abstract.misc import Result
from syncify.local.track.base.processor import TagName
from syncify.local.track.base.reader import TagReader
from syncify.spotify import __UNAVAILABLE_URI_VALUE__
from syncify.utils import UnitIterable
from syncify.utils.helpers import to_collection


@dataclass(frozen=True)
class SyncResultTrack(Result):
    """Stores the results of a sync with local track"""
    saved: bool  # if changes to the file on the disk were made
    updated: Mapping[TagName, int]  # The tag updated and the condition index it satisfied to be updated


class TagWriter(TagReader, metaclass=ABCMeta):
    """Contains methods for updating and removing tags from a loaded file"""

    def save(
            self, tags: UnitIterable[TagName] = TagName.ALL, replace: bool = False, dry_run: bool = True
    ) -> SyncResultTrack:
        """
        Update file's tags from given dictionary of tags.

        :param tags: Tags to be updated.
        :param replace: Destructively replace tags in each file.
        :param dry_run: Run function, but do not modify file at all.
        :returns: List of tags that have been updated.
        """
        self.get_file()
        file = copy(self)
        updated: dict[TagName, int] = {}

        tags: list[TagName] = to_collection(tags, list)
        if TagName.ALL in tags:
            tags = TagName.all()

        # all chunks below follow the same basic structure
        # - check if any of the conditionals for this tag type are met
        # - if met, proceed to writing the tag data
        # - if data has been written (or would have been if not a dry run),
        #   append the tag name to a list of updated tags

        if TagName.TITLE in tags:
            conditionals = {
                file.title is None and self.title is not None,
                replace and self.title != file.title
            }
            if any(conditionals) and self._write_title(dry_run):
                updated |= {TagName.TITLE: [i for i, c in enumerate(conditionals) if c][0]}
                    
        if TagName.ARTIST in tags:
            conditionals = {
                file.artist is None and self.artist is not None,
                replace and self.artist != file.artist
            }
            if any(conditionals) and self._write_artist(dry_run):
                updated |= {TagName.ARTIST: [i for i, c in enumerate(conditionals) if c][0]}

        if TagName.ALBUM in tags:
            conditionals = {
                file.album is None and self.album is not None,
                replace and self.album != file.album
            }
            if any(conditionals) and self._write_album(dry_run):
                updated |= {TagName.ALBUM: [i for i, c in enumerate(conditionals) if c][0]}

        if TagName.ALBUM_ARTIST in tags:
            conditionals = {
                file.album_artist is None and self.album_artist is not None,
                replace and self.album_artist != file.album_artist
            }
            if any(conditionals) and self._write_album_artist(dry_run):
                updated |= {TagName.ALBUM_ARTIST: [i for i, c in enumerate(conditionals) if c][0]}

        if TagName.TRACK in tags:
            conditionals = {
                file.track_number is None and file.track_total is None and
                (self.track_number is not None or self.track_total is not None),
                replace and (self.track_number != file.track_number or self.track_total != file.track_total)
            }
            if any(conditionals) and self._write_track(dry_run):
                updated |= {TagName.TRACK: [i for i, c in enumerate(conditionals) if c][0]}

        if TagName.GENRES in tags:
            conditionals = {file.genres is None and self.genres, replace and self.genres != file.genres}
            if any(conditionals) and self._write_genres(dry_run):
                updated |= {TagName.GENRES: [i for i, c in enumerate(conditionals) if c][0]}

        if TagName.YEAR in tags:
            conditionals = {file.year is None and self.year is not None, replace and self.year != file.year}
            if any(conditionals) and self._write_year(dry_run):
                updated |= {TagName.YEAR: [i for i, c in enumerate(conditionals) if c][0]}

        if TagName.BPM in tags:
            self_bpm = int(self["bpm"] if self["bpm"] is not None else 0)
            file_bpm = int(file["bpm"] if file["bpm"] is not None else 0)
            conditionals = {
                file.bpm is None and self.bpm is not None and self.bpm > 30,
                file_bpm < 30 < self_bpm,
                replace and self_bpm != file_bpm
            }
            if any(conditionals) and self._write_bpm(dry_run):
                updated |= {TagName.BPM: [i for i, c in enumerate(conditionals) if c][0]}

        if TagName.KEY in tags:
            conditionals = {file.key is None and self.key is not None, replace and self.key != file.key}
            if any(conditionals) and self._write_key(dry_run):
                updated |= {TagName.KEY: [i for i, c in enumerate(conditionals) if c][0]}

        if TagName.DISC in tags:
            conditionals = {
                file.disc_number is None and file.disc_total is None and
                (self.disc_number is not None or self.disc_total is not None),
                replace and (self.disc_number != file.disc_number or self.disc_total != file.disc_total)
            }
            if any(conditionals) and self._write_disc(dry_run):
                updated |= {TagName.DISC: [i for i, c in enumerate(conditionals) if c][0]}

        if TagName.COMPILATION in tags:
            conditionals = {
                file.compilation is None and self.compilation is not None,
                replace and self.compilation != file.compilation
            }
            if any(conditionals) and self._write_compilation(dry_run):
                updated |= {TagName.COMPILATION: [i for i, c in enumerate(conditionals) if c][0]}

        if TagName.COMMENTS in tags:
            conditionals = {file.comments is None and self.comments, replace and self.comments != file.comments}
            if any(conditionals) and self._write_comments(dry_run):
                updated |= {TagName.COMMENTS: [i for i, c in enumerate(conditionals) if c][0]}

        if TagName.URI in tags:
            conditionals = {self.uri != file.uri or self.has_uri != file.has_uri}
            if any(conditionals) and self._write_uri(dry_run):
                updated |= {TagName.URI: [i for i, c in enumerate(conditionals) if c][0]}

        if TagName.IMAGES in tags:
            conditionals = {file.has_image is False, replace}
            if any(conditionals) and self.image_links and self._write_images(dry_run):
                updated |= {TagName.IMAGES: [i for i, c in enumerate(conditionals) if c][0]}
        
        save = not dry_run and len(updated) > 0
        if save:
            try:
                self.file.save()
            except mutagen.MutagenError as ex:
                raise ex

        return SyncResultTrack(saved=save, updated=updated)
                    
    @abstractmethod
    def _write_tag(self, tag_id: str | None, tag_value: Any, dry_run: bool = True) -> bool:
        """
        Generic method for updating a tag value in the file.
        
        :param tag_id: ID of the tag for this file type.
        :param tag_value: New value to assign.
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
    
    def _write_title(self, dry_run: bool = True) -> bool:
        """
        Write track title tags to file
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.title), None), self.title, dry_run)

    def _write_artist(self, dry_run: bool = True) -> bool:
        """
        Write artist tags to file
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.artist), None), self.artist, dry_run)

    def _write_album(self, dry_run: bool = True) -> bool:
        """
        Write album tags to file
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.album), None), self.album, dry_run)

    def _write_album_artist(self, dry_run: bool = True) -> bool:
        """
        Write album artist tags to file
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.album_artist), None), self.album_artist, dry_run)

    def _write_track(self, dry_run: bool = True) -> bool:
        """
        Write track number tags to file
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        tag_id_number = next(iter(self.tag_map.track_number), None)
        tag_id_total = next(iter(self.tag_map.track_total), None)
        
        if tag_id_number != tag_id_total and self.track_total is not None:
            number_updated = self._write_tag(tag_id_number, str(self.track_number).zfill(2), dry_run)
            total_updated = self._write_tag(tag_id_total, str(self.track_total).zfill(2), dry_run)
            return number_updated or total_updated
        elif self.track_total is not None:
            tag_value = self._num_sep.join([str(self.track_number).zfill(2), str(self.track_total).zfill(2)])
        else:
            tag_value = str(self.track_number).zfill(2)

        return self._write_tag(tag_id_number, tag_value, dry_run)

    def _write_genres(self, dry_run: bool = True) -> bool:
        """
        Write genre tags to file
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.genres), None), self.genres, dry_run)

    def _write_year(self, dry_run: bool = True) -> bool:
        """
        Write year tags to file
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.year), None), self.year, dry_run)

    def _write_bpm(self, dry_run: bool = True) -> bool:
        """
        Write bpm tags to file
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.bpm), None), self.bpm, dry_run)

    def _write_key(self, dry_run: bool = True) -> bool:
        """
        Write key tags to file
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.key), None), self.key, dry_run)

    def _write_disc(self, dry_run: bool = True) -> bool:
        """
        Write disc number tags to file
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        tag_id_number = next(iter(self.tag_map.disc_number), None)
        tag_id_total = next(iter(self.tag_map.disc_total), None)
        fill = len(str(self.disc_total)) if self.disc_total is not None else 1

        if tag_id_number != tag_id_total and self.disc_total is not None:
            number_updated = self._write_tag(tag_id_number, str(self.disc_number).zfill(fill), dry_run)
            total_updated = self._write_tag(tag_id_total, str(self.disc_total).zfill(fill), dry_run)
            return number_updated or total_updated
        elif self.disc_total is not None:
            tag_value = self._num_sep.join([str(self.disc_number).zfill(fill), str(self.disc_total).zfill(fill)])
        else:
            tag_value = str(self.disc_number).zfill(fill)

        return self._write_tag(tag_id_number, tag_value, dry_run)

    def _write_compilation(self, dry_run: bool = True) -> bool:
        """
        Write compilation tags to file
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.compilation), None), int(self.compilation), dry_run)

    def _write_comments(self, dry_run: bool = True) -> bool:
        """
        Write comment tags to file
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.comments), None), self.comments, dry_run)

    def _write_uri(self, dry_run: bool = True) -> bool:
        """
        Write URI tags to file
        
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        tag_id = next(iter(self.tag_map[self.uri_tag.name.casefold()]), None)
        tag_value = __UNAVAILABLE_URI_VALUE__ if not self.has_uri else self.uri
        return self._write_tag(tag_id, tag_value, dry_run)

    @abstractmethod
    def _write_images(self, dry_run: bool = True) -> bool:
        """
        Write image to file

        :param dry_run: Run function, but do not modify file at all.
        :returns: True if the file was updated or would have been when dry_run is True, False otherwise.
        """

    def delete_tags(self, tags: UnitIterable[TagName] | None = None, dry_run: bool = True) -> SyncResultTrack:
        """
        Remove tags from file.

        :param tags: Tags to remove.
        :param dry_run: Run function, but do not modify file at all.
        :returns: List of tags that have been removed.
        """
        if tags is None or (isinstance(tags, Collection) and len(tags) == 0):
            return SyncResultTrack(saved=False, updated={})

        # noinspection PyTypeChecker
        tag_names = set(TagName.to_tags(tags))
        removed = {TagName.from_name(tag_name) for tag_name in tag_names if self.delete_tag(tag_name, dry_run)}

        if TagName.IMAGES in removed:
            self.has_image = False

        save = not dry_run and len(removed) > 0
        if save:
            self.file.save()

        removed = sorted(removed, key=lambda x: TagName.all().index(x))
        return SyncResultTrack(saved=save, updated={u: 0 for u in removed})

    def delete_tag(self, tag_name: str, dry_run: bool = True) -> bool:
        """
        Remove a tag by its tag name.

        :param tag_name: Tag ID to remove.
        :param dry_run: Run function, but do not modify file at all.
        :returns: True if tag has been remove, False otherwise.
        """
        removed = False

        tag_ids = self.tag_map[tag_name]
        if tag_ids is None or len(tag_ids) is None:
            return removed

        for tag_id in tag_ids:
            if tag_id in self.file and self.file[tag_id]:
                if not dry_run:
                    del self.file[tag_id]
                removed = True

        return removed
    