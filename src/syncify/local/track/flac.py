from collections.abc import Iterable
from io import BytesIO
from typing import Any

import mutagen
import mutagen.flac
import mutagen.id3
from PIL import Image

from syncify.shared.core.enums import TagMap
from syncify.local.track.fields import LocalTrackField
from syncify.local.file import open_image, get_image_bytes
from syncify.shared.remote.processors.wrangle import RemoteDataWrangler
from ._base import LocalTrack


class FLAC(LocalTrack):
    """
    Track object for extracting, modifying, and saving tags from FLAC files.

    :ivar valid_extensions: Extensions of files that can be loaded by this class.
    :ivar tag_map: Map of tag names as recognised by this object to the tag names in the file.
    :ivar uri_tag: The tag field to use as the URI tag in the file's metadata.
    :ivar num_sep: Some number values come as a combined string i.e. track number/track total
        Define the separator to use when representing both values as a combined string.
    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.

    :param file: The path or Mutagen object of the file to load.
    :param available: A list of available track paths that are known to exist and are valid for this track type.
        Useful for case-insensitive path loading and correcting paths to case-sensitive.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs.
        This object will be used to check for and validate a URI tag on the file.
        The tag that is used for reading and writing is set by the ``uri_tag`` class attribute.
        If no ``remote_wrangler`` is given, no URI processing will occur.
    """

    valid_extensions = frozenset({".flac"})

    # noinspection SpellCheckingInspection
    tag_map = TagMap(
        title=["title"],
        artist=["artist"],
        album=["album"],
        album_artist=["albumartist"],
        track_number=["tracknumber", "track"],
        track_total=["tracktotal"],
        genres=["genre"],
        date=["date"],
        year=["year"],
        bpm=["bpm"],
        key=["initialkey"],
        disc_number=["discnumber"],
        disc_total=["disctotal"],
        compilation=["compilation"],
        comments=["comment", "description"],
    )

    def __init__(
            self,
            file: str | mutagen.FileType | mutagen.flac.FLAC,
            available: Iterable[str] = (),
            remote_wrangler: RemoteDataWrangler = None,
    ):
        super().__init__(file=file, available=available, remote_wrangler=remote_wrangler)
        # noinspection PyTypeChecker
        self._file: mutagen.flac.FLAC = self._file

    def _read_images(self) -> list[Image.Image] | None:
        values = self._file.pictures
        return [Image.open(BytesIO(value.data)) for value in values] if len(values) > 0 else None

    def _check_for_images(self) -> bool:
        return len(self._file.pictures) > 0

    def _write_tag(self, tag_id: str | None, tag_value: Any, dry_run: bool = True) -> bool:
        if tag_value is None:
            remove = not dry_run and tag_id in self.file and self.file[tag_id]
            if remove:
                del self.file[tag_id]
            return remove

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
        if tag_name == LocalTrackField.IMAGES.name.casefold():
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
