import io
from collections.abc import Iterable
from typing import Any

import mutagen
import mutagen.flac
import mutagen.id3
from PIL import Image

from syncify.enums.tags import TagName, TagMap
from syncify.local.file import open_image, get_image_bytes
from syncify.local.track.base.track import LocalTrack


class FLAC(LocalTrack):
    """
    Track object for extracting, modifying, and saving tags from FLAC files.

    :param file: The path or Mutagen object of the file to load.
    :param available: A list of available track paths that are known to exist and are valid for this track type.
        Useful for case-insensitive path loading and correcting paths to case-sensitive.
    """

    valid_extensions = {".flac"}

    # noinspection SpellCheckingInspection
    tag_map = TagMap(
        title=["title"],
        artist=["artist"],
        album=["album"],
        track_number=["tracknumber"],
        track_total=["tracktotal"],
        genres=["genre"],
        year=["year", "date"],
        bpm=["bpm"],
        key=["initialkey"],
        disc_number=["discnumber"],
        disc_total=["disctotal"],
        compilation=["compilation"],
        album_artist=["albumartist"],
        comments=["comment", "description"],
        images=[],
    )

    # noinspection PyTypeChecker
    def __init__(self, file: str | mutagen.FileType | mutagen.flac.FLAC, available: Iterable[str] | None = None):
        super().__init__(file=file, available=available)
        self._file: mutagen.flac.FLAC = self._file

    def _read_images(self) -> list[Image.Image] | None:
        values = self._file.pictures
        return [Image.open(io.BytesIO(value.data)) for value in values] if len(values) > 0 else None

    def _check_for_images(self) -> bool:
        return len(self._file.pictures) > 0

    def _write_tag(self, tag_id: str | None, tag_value: Any, dry_run: bool = True) -> bool:
        if tag_value is None:
            return self.delete_tag(tag_id, dry_run=dry_run)

        if not dry_run and tag_id is not None:
            if isinstance(tag_value, (list, set, tuple)):
                self._file[tag_id] = list(map(str, tag_value))
            else:
                self._file[tag_id] = str(tag_value)
        return tag_id is not None

    def _write_images(self, dry_run: bool = True) -> bool:
        updated = False
        for image_type, image_link in self.image_links.items():
            image = open_image(image_link)

            picture = mutagen.flac.Picture()
            # noinspection PyUnresolvedReferences
            picture.type = getattr(mutagen.id3.PictureType, image_type.upper())
            picture.mime = Image.MIME[image.format]
            picture.data = get_image_bytes(image)

            if not dry_run:
                # clear images that match the new image's type
                for pic in self._file.pictures.copy():
                    if pic.type == picture.type:
                        self._file.pictures.remove(pic)

                self._file.add_picture(picture)

            image.close()
            self.has_image = True
            updated = True

        return updated

    def delete_tag(self, tag_name: str, dry_run: bool = True) -> bool:
        if tag_name == TagName.IMAGES.name.casefold():
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
