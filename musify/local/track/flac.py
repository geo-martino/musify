"""
The FLAC implementation of a :py:class:`LocalTrack`.
"""

from io import BytesIO
from typing import Any

import mutagen
import mutagen.flac
import mutagen.id3
from PIL import Image

from musify.local.file import open_image, get_image_bytes
from musify.local.track.base.track import LocalTrack
from musify.local.track.field import LocalTrackField
from musify.shared.core.enum import TagMap


class FLAC(LocalTrack[mutagen.flac.FLAC]):

    valid_extensions = frozenset({".flac"})

    # noinspection SpellCheckingInspection
    #: Map of human-friendly tag name to ID3 tag ids for a given file type
    tag_map = TagMap(
        title=["title"],
        artist=["artist"],
        album=["album"],
        album_artist=["albumartist"],
        track_number=["tracknumber", "track"],
        track_total=["tracktotal"],
        genres=["genre"],
        date=["date", "year"],
        year=["year"],
        bpm=["bpm"],
        key=["initialkey"],
        disc_number=["discnumber"],
        disc_total=["disctotal"],
        compilation=["compilation"],
        comments=["comment", "description"],
    )

    def _read_images(self) -> list[Image.Image] | None:
        values = self._file.pictures
        return [Image.open(BytesIO(value.data)) for value in values] if len(values) > 0 else None

    def _check_for_images(self) -> bool:
        return len(self._file.pictures) > 0

    def _write_tag(self, tag_id: str | None, tag_value: Any, dry_run: bool = True) -> bool:
        result = super()._write_tag(tag_id=tag_id, tag_value=tag_value, dry_run=dry_run)
        if result is not None:
            return result

        if not dry_run:
            if isinstance(tag_value, (list, set, tuple)):
                self._file[tag_id] = list(map(str, tag_value))
            else:
                self._file[tag_id] = str(tag_value)
        return True

    def _write_images(self, dry_run: bool = True) -> bool:
        updated = False
        for image_kind, image_link in self.image_links.items():
            image = open_image(image_link)
            image_kind_attr = image_kind.upper().replace(" ", "_")

            picture = mutagen.flac.Picture()
            picture.type = getattr(mutagen.id3.PictureType, image_kind_attr)
            picture.mime = Image.MIME[image.format]
            picture.data = get_image_bytes(image)

            if not dry_run:
                # clear all images, adding back those that don't match the new image's type
                pictures_current = self._file.pictures.copy()
                self._file.clear_pictures()
                for pic in pictures_current:
                    if pic.type != picture.type:
                        self._file.add_picture(pic)

                self._file.add_picture(picture)

            image.close()
            self.has_image = True
            updated = True

        return updated

    def delete_tag(self, tag_name: str, dry_run: bool = True) -> bool:
        if tag_name == LocalTrackField.IMAGES.name.lower():
            self._file.clear_pictures()
            return True

        removed = False

        tag_ids = self.tag_map[tag_name]
        if tag_ids is None or len(tag_ids) is None:
            return removed

        for tag_id in tag_ids:
            if tag_id in self._file and self._file[tag_id]:
                if not dry_run:
                    del self._file[tag_id]
                removed = True

        return removed
