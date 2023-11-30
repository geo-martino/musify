import struct
from collections.abc import Collection, Iterable
from io import BytesIO
from typing import Any

import mutagen
import mutagen.asf
import mutagen.id3
from PIL import Image, UnidentifiedImageError

from syncify.enums.tags import TagMap
from syncify.local.file import open_image, get_image_bytes
from syncify.local.track.base.track import LocalTrack


class WMA(LocalTrack):
    """
    Track object for extracting, modifying, and saving tags from WMA files.

    :param file: The path or Mutagen object of the file to load.
    :param available: A list of available track paths that are known to exist and are valid for this track type.
        Useful for case-insensitive path loading and correcting paths to case-sensitive.
    """

    valid_extensions = frozenset({".wma"})

    tag_map = TagMap(
        title=["Title"],
        artist=["Author"],
        album=["WM/AlbumTitle"],
        track_number=["WM/TrackNumber"],
        track_total=["TotalTracks", "WM/TrackNumber"],
        genres=["WM/Genre"],
        year=["WM/Year"],
        bpm=["WM/BeatsPerMinute"],
        key=["WM/InitialKey"],
        disc_number=["WM/PartOfSet"],
        disc_total=["WM/PartOfSet"],
        compilation=["COMPILATION"],
        album_artist=["WM/AlbumArtist"],
        comments=["Description"],
        images=["WM/Picture"],
    )

    # noinspection PyTypeChecker
    def __init__(self, file: str | mutagen.FileType | mutagen.asf.ASF, available: Iterable[str] | None = None):
        super().__init__(file=file, available=available)
        self._file: mutagen.asf.ASF = self._file

    def _read_tag(self, tag_ids: Iterable[str]) -> list[Any] | None:
        # WMA tag values are returned as mutagen.asf._attrs.ASFUnicodeAttribute
        values = []
        for tag_id in tag_ids:
            value: Collection[mutagen.asf.ASFBaseAttribute] = self._file.get(tag_id)
            if value is None:
                # skip null or empty/blank strings
                continue

            values.extend([v.value for v in value if not (isinstance(value, str) and len(value.strip()) == 0)])

        return values if len(values) > 0 else None

    def _read_images(self) -> list[Image.Image] | None:
        values = self._read_tag(self.tag_map.images)
        if values is None:
            return

        images: list[Image.Image] = []
        for i, value in enumerate(values):
            try:
                # first attempt to open image from bytes; assumes bytes value refer only to the image data
                images.append(Image.open(BytesIO(value)))
                continue
            except UnidentifiedImageError:
                # the bytes are encoded per WMA spec
                # bytes need to be analysed first to extract the bytes that refer to the image data
                pass

            v_type, v_size = struct.unpack_from(b"<bi", value)

            pos = 5
            mime = b""
            while value[pos:pos + 2] != b"\x00\x00":
                mime += value[pos:pos + 2]
                pos += 2

            pos += 2
            description = b""

            while value[pos:pos + 2] != b"\x00\x00":
                description += value[pos:pos + 2]
                pos += 2
            pos += 2

            image_data: bytes = value[pos:pos + v_size]
            images.append(Image.open(BytesIO(image_data)))

        return images

    def _write_tag(self, tag_id: str | None, tag_value: Any, dry_run: bool = True) -> bool:
        if tag_value is None:
            return self.delete_tag(tag_id, dry_run=dry_run)

        if not dry_run and tag_id is not None:
            if isinstance(tag_value, (list, set, tuple)):
                if all(isinstance(v, mutagen.asf.ASFByteArrayAttribute) for v in tag_value):
                    self._file[tag_id] = tag_value
                else:
                    self._file[tag_id] = [mutagen.asf.ASFUnicodeAttribute(str(v)) for v in tag_value]
            else:
                self._file[tag_id] = mutagen.asf.ASFUnicodeAttribute(str(tag_value))
        return tag_id is not None

    def _write_images(self, dry_run: bool = True) -> bool:
        tag_id = next(iter(self.tag_map.images), None)

        updated = False
        tag_value = []
        for image_kind, image_link in self.image_links.items():
            image_kind_attr = image_kind.upper().replace(" ", "_")
            image_type: mutagen.id3.PictureType = getattr(mutagen.id3.PictureType, image_kind_attr)

            image = open_image(image_link)
            data = get_image_bytes(image)
            tag_data = struct.pack("<bi", image_type, len(data))
            tag_data += Image.MIME[image.format].encode("utf-16") + b"\x00\x00"  # mime
            tag_data += "".encode("utf-16") + b"\x00\x00"  # description
            tag_data += data

            tag_value.append(mutagen.asf.ASFByteArrayAttribute(tag_data))
            image.close()

        if len(tag_value) > 0:
            updated = self._write_tag(tag_id, tag_value, dry_run)

        self.has_image = updated or self.has_image
        return updated
