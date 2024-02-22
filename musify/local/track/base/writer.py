"""
Implements all functionality pertaining to writing and deleting metadata/tags/properties of a :py:class:`LocalTrack`.
"""

from abc import ABCMeta, abstractmethod
from collections.abc import Mapping, Collection
from copy import copy
from dataclasses import dataclass
from typing import Any

import mutagen

from musify.local.track.base.reader import TagReader
from musify.local.track.field import LocalTrackField as Tags
from musify.shared.core.misc import Result
from musify.shared.types import UnitIterable
from musify.shared.utils import to_collection


@dataclass(frozen=True)
class SyncResultTrack(Result):
    """Stores the results of a sync with local track"""
    #: Were changes to the file on the disk made.
    saved: bool
    #: Map of the tag updated and the index of the condition it satisfied to be updated.
    updated: Mapping[Tags, int]


class TagWriter(TagReader, metaclass=ABCMeta):
    """Functionality for updating and removing tags/metadata/properties from a loaded audio file."""

    #: The date format to use when saving string representations of dates to tag values
    date_format = "%Y-%m-%d"

    def delete_tags(self, tags: UnitIterable[Tags] = (), dry_run: bool = True) -> SyncResultTrack:
        """
        Remove tags from file.

        :param tags: Tags to remove.
        :param dry_run: Run function, but do not modify file at all.
        :return: List of tags that have been removed.
        """
        if tags is None or (isinstance(tags, Collection) and len(tags) == 0):
            return SyncResultTrack(saved=False, updated={})

        tag_names = set(Tags.to_tags(tags))
        removed = set()
        for tag_name in tag_names:
            if self.delete_tag(tag_name, dry_run):
                removed.update(Tags.from_name(tag_name))

        if Tags.IMAGES in removed:
            self.has_image = False

        save = not dry_run and len(removed) > 0
        if save:
            self.file.save()

        removed = sorted(removed, key=lambda x: Tags.all().index(x))
        return SyncResultTrack(saved=save, updated={u: 0 for u in removed})

    def delete_tag(self, tag_name: str, dry_run: bool = True) -> bool:
        """
        Remove a tag by its tag name.

        :param tag_name: Tag name as found in :py:class:`TagMap` to remove.
        :param dry_run: Run function, but do not modify file at all.
        :return: True if tag has been remove, False otherwise.
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

    def save(self, tags: UnitIterable[Tags] = Tags.ALL, replace: bool = False, dry_run: bool = True) -> SyncResultTrack:
        """
        Update file's tags from given dictionary of tags.

        :param tags: Tags to be updated.
        :param replace: Destructively replace tags in each file.
        :param dry_run: Run function, but do not modify file at all.
        :return: List of tags that have been updated.
        """
        # noinspection PyAttributeOutsideInit
        self._file = self.load()
        file = copy(self)
        updated: dict[Tags, int] = {}

        tags: list[Tags] = to_collection(tags, list)
        if Tags.ALL in tags:
            tags = Tags.all(only_tags=True)

        # all chunks below follow the same basic structure
        # - check if any of the conditionals for this tag type are met
        # - if met, proceed to writing the tag data
        # - if data has been written (or would have been if not a dry run),
        #   append the tag name to a list of updated tags

        if Tags.TITLE in tags:
            conditionals = {
                file.title is None and self.title is not None,
                replace and self.title != file.title
            }
            if any(conditionals) and self._write_title(dry_run):
                updated |= {Tags.TITLE: [i for i, c in enumerate(conditionals) if c][0]}

        if Tags.ARTIST in tags:
            conditionals = {
                file.artist is None and self.artist is not None,
                replace and self.artist != file.artist
            }
            if any(conditionals) and self._write_artist(dry_run):
                updated |= {Tags.ARTIST: [i for i, c in enumerate(conditionals) if c][0]}

        if Tags.ALBUM in tags:
            conditionals = {
                file.album is None and self.album is not None,
                replace and self.album != file.album
            }
            if any(conditionals) and self._write_album(dry_run):
                updated |= {Tags.ALBUM: [i for i, c in enumerate(conditionals) if c][0]}

        if Tags.ALBUM_ARTIST in tags:
            conditionals = {
                file.album_artist is None and self.album_artist is not None,
                replace and self.album_artist != file.album_artist
            }
            if any(conditionals) and self._write_album_artist(dry_run):
                updated |= {Tags.ALBUM_ARTIST: [i for i, c in enumerate(conditionals) if c][0]}

        if any(f in tags for f in {Tags.TRACK, Tags.TRACK_NUMBER, Tags.TRACK_TOTAL}):
            conditionals = {
                file.track_number is None and file.track_total is None and
                (self.track_number is not None or self.track_total is not None),
                replace and (self.track_number != file.track_number or self.track_total != file.track_total)
            }
            if any(conditionals) and self._write_track(dry_run):
                updated |= {Tags.TRACK: [i for i, c in enumerate(conditionals) if c][0]}

        if Tags.GENRES in tags:
            conditionals = {file.genres is None and bool(self.genres), replace and self.genres != file.genres}
            if any(conditionals) and self._write_genres(dry_run):
                updated |= {Tags.GENRES: [i for i, c in enumerate(conditionals) if c][0]}

        if any(f in tags for f in {Tags.DATE, Tags.YEAR, Tags.MONTH, Tags.DAY}):
            # date is just a composite of year + month + day, can safely ignore this in the conditionals
            values_exist = any({self.year is not None, self.month is not None, self.day is not None})
            conditionals = {
                file.year is None and file.month is None and file.day is None and values_exist,
                replace and (self.year != file.year or self.month != file.month or self.day != file.day)
            }

            if any(conditionals):
                date, year, month, day = self._write_date(dry_run)
                condition = [i for i, c in enumerate(conditionals) if c][0]
                if date:
                    updated |= {Tags.DATE: condition}
                if year:
                    updated |= {Tags.YEAR: condition}
                if month:
                    updated |= {Tags.MONTH: condition}
                if day:
                    updated |= {Tags.DAY: condition}

        if Tags.BPM in tags:
            self_bpm = int(self["bpm"] if self["bpm"] is not None else 0)
            file_bpm = int(file["bpm"] if file["bpm"] is not None else 0)
            conditionals = {
                file.bpm is None and self.bpm is not None and self.bpm > 30,
                file_bpm < 30 < self_bpm,
                replace and self_bpm != file_bpm
            }
            if any(conditionals) and self._write_bpm(dry_run):
                updated |= {Tags.BPM: [i for i, c in enumerate(conditionals) if c][0]}

        if Tags.KEY in tags:
            conditionals = {file.key is None and self.key is not None, replace and self.key != file.key}
            if any(conditionals) and self._write_key(dry_run):
                updated |= {Tags.KEY: [i for i, c in enumerate(conditionals) if c][0]}

        if any(f in tags for f in {Tags.DISC, Tags.DISC_NUMBER, Tags.DISC_TOTAL}):
            conditionals = {
                file.disc_number is None and file.disc_total is None and
                (self.disc_number is not None or self.disc_total is not None),
                replace and (self.disc_number != file.disc_number or self.disc_total != file.disc_total)
            }
            if any(conditionals) and self._write_disc(dry_run):
                updated |= {Tags.DISC: [i for i, c in enumerate(conditionals) if c][0]}

        if Tags.COMPILATION in tags:
            conditionals = {
                file.compilation is None and self.compilation is not None,
                replace and self.compilation != file.compilation
            }
            if any(conditionals) and self._write_compilation(dry_run):
                updated |= {Tags.COMPILATION: [i for i, c in enumerate(conditionals) if c][0]}

        if Tags.COMMENTS in tags:
            conditionals = {file.comments is None and bool(self.comments), replace and self.comments != file.comments}
            if any(conditionals) and self._write_comments(dry_run):
                updated |= {Tags.COMMENTS: [i for i, c in enumerate(conditionals) if c][0]}

        if Tags.URI in tags:
            conditionals = {self.uri != file.uri or self.has_uri != file.has_uri}
            if any(conditionals) and self._write_uri(dry_run):
                updated |= {Tags.URI: [i for i, c in enumerate(conditionals) if c][0]}

        if Tags.IMAGES in tags:
            conditionals = {file.has_image is False, replace}
            if any(conditionals) and self.image_links and self._write_images(dry_run):
                updated |= {Tags.IMAGES: [i for i, c in enumerate(conditionals) if c][0]}

        save = not dry_run and len(updated) > 0
        if save:
            try:
                self.file.save()
            except mutagen.MutagenError as ex:
                raise ex

        return SyncResultTrack(saved=save, updated=updated)

    @abstractmethod
    def _write_tag(self, tag_id: str | None, tag_value: Any, dry_run: bool = True) -> bool | None:
        """
        Generic method for updating a tag value in the file.

        :param tag_id: ID of the tag for this file type.
        :param tag_value: New value to assign.
        :param dry_run: Run function, but do not modify file at all.
        :return: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        if tag_id is None:
            return False

        if tag_value is None:
            remove = not dry_run and tag_id in self.file and self.file[tag_id]
            if remove:
                del self.file[tag_id]
            return remove

    def _write_title(self, dry_run: bool = True) -> bool:
        """
        Write track title tags to file

        :param dry_run: Run function, but do not modify file at all.
        :return: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.title), None), self.title, dry_run)

    def _write_artist(self, dry_run: bool = True) -> bool:
        """
        Write artist tags to file

        :param dry_run: Run function, but do not modify file at all.
        :return: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.artist), None), self.artist, dry_run)

    def _write_album(self, dry_run: bool = True) -> bool:
        """
        Write album tags to file

        :param dry_run: Run function, but do not modify file at all.
        :return: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.album), None), self.album, dry_run)

    def _write_album_artist(self, dry_run: bool = True) -> bool:
        """
        Write album artist tags to file

        :param dry_run: Run function, but do not modify file at all.
        :return: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.album_artist), None), self.album_artist, dry_run)

    def _write_track(self, dry_run: bool = True) -> bool:
        """
        Write track number tags to file

        :param dry_run: Run function, but do not modify file at all.
        :return: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        tag_id_number = next(iter(self.tag_map.track_number), None)
        tag_id_total = next(iter(self.tag_map.track_total), None)

        if tag_id_number != tag_id_total and self.track_total is not None:
            number_updated = self._write_tag(tag_id_number, str(self.track_number).zfill(2), dry_run)
            total_updated = self._write_tag(tag_id_total, str(self.track_total).zfill(2), dry_run)
            return number_updated or total_updated
        elif self.track_total is not None:
            tag_value = self.num_sep.join([str(self.track_number).zfill(2), str(self.track_total).zfill(2)])
        else:
            tag_value = str(self.track_number).zfill(2)

        return self._write_tag(tag_id_number, tag_value, dry_run)

    def _write_genres(self, dry_run: bool = True) -> bool:
        """
        Write genre tags to file

        :param dry_run: Run function, but do not modify file at all.
        :return: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.genres), None), self.genres, dry_run)

    def _write_date(self, dry_run: bool = True) -> tuple[bool, bool, bool, bool]:
        """
        Write date (including year, month and day) tags to file

        :param dry_run: Run function, but do not modify file at all.
        :return: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        date_str = self.date.strftime(self.date_format) if self.date else None
        if not date_str:
            date_str = f"{self.year}-{str(self.month).zfill(2)}" if self.month else str(self.year)
        date = self._write_tag(next(iter(self.tag_map.date), None), date_str, dry_run)
        if date:
            return date, False, False, False

        year = self._write_tag(next(iter(self.tag_map.year), None), self.year, dry_run)
        month = self._write_tag(next(iter(self.tag_map.month), None), self.month, dry_run)
        day = self._write_tag(next(iter(self.tag_map.day), None), self.day, dry_run)

        return date, year, month, day

    def _write_bpm(self, dry_run: bool = True) -> bool:
        """
        Write BPM tags to file

        :param dry_run: Run function, but do not modify file at all.
        :return: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.bpm), None), self.bpm, dry_run)

    def _write_key(self, dry_run: bool = True) -> bool:
        """
        Write key tags to file

        :param dry_run: Run function, but do not modify file at all.
        :return: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.key), None), self.key, dry_run)

    def _write_disc(self, dry_run: bool = True) -> bool:
        """
        Write disc number tags to file

        :param dry_run: Run function, but do not modify file at all.
        :return: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        tag_id_number = next(iter(self.tag_map.disc_number), None)
        tag_id_total = next(iter(self.tag_map.disc_total), None)
        fill = len(str(self.disc_total)) if self.disc_total is not None else 1

        if tag_id_number != tag_id_total and self.disc_total is not None:
            number_updated = self._write_tag(tag_id_number, str(self.disc_number).zfill(fill), dry_run)
            total_updated = self._write_tag(tag_id_total, str(self.disc_total).zfill(fill), dry_run)
            return number_updated or total_updated
        elif self.disc_total is not None:
            tag_value = self.num_sep.join([str(self.disc_number).zfill(fill), str(self.disc_total).zfill(fill)])
        else:
            tag_value = str(self.disc_number).zfill(fill)

        return self._write_tag(tag_id_number, tag_value, dry_run)

    def _write_compilation(self, dry_run: bool = True) -> bool:
        """
        Write compilation tags to file

        :param dry_run: Run function, but do not modify file at all.
        :return: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.compilation), None), int(self.compilation), dry_run)

    def _write_comments(self, dry_run: bool = True) -> bool:
        """
        Write comment tags to file

        :param dry_run: Run function, but do not modify file at all.
        :return: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        return self._write_tag(next(iter(self.tag_map.comments), None), self.comments, dry_run)

    def _write_uri(self, dry_run: bool = True) -> bool:
        """
        Write URI tags to file

        :param dry_run: Run function, but do not modify file at all.
        :return: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
        if not self.remote_wrangler:
            return False

        tag_id = next(iter(self.tag_map[self.uri_tag.name.lower()]), None)
        tag_value = self.remote_wrangler.unavailable_uri_dummy if not self.has_uri else self.uri
        return self._write_tag(tag_id, tag_value, dry_run)

    @abstractmethod
    def _write_images(self, dry_run: bool = True) -> bool:
        """
        Write image to file

        :param dry_run: Run function, but do not modify file at all.
        :return: True if the file was updated or would have been when dry_run is True, False otherwise.
        """
