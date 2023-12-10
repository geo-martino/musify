import struct
from collections.abc import Collection, Iterable
from io import BytesIO
from typing import Any

import mutagen
import mutagen.asf
import mutagen.id3
from PIL import Image, UnidentifiedImageError

from syncify.local.file import TagMap, open_image, get_image_bytes
from syncify.local.track.base.track import LocalTrack
from syncify.remote.processors.wrangle import RemoteDataWrangler


class WMA(LocalTrack):
    """
    Track object for extracting, modifying, and saving tags from WMA files.

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

    valid_extensions = frozenset({".wma"})

    tag_map = TagMap(
        title=["Title"],
        artist=["Author"],
        album=["WM/AlbumTitle"],
        album_artist=["WM/AlbumArtist"],
        track_number=["WM/TrackNumber"],
        track_total=["TotalTracks", "WM/TrackNumber"],
        genres=["WM/Genre"],
        year=["WM/Year"],
        bpm=["WM/BeatsPerMinute"],
        key=["WM/InitialKey"],
        disc_number=["WM/PartOfSet"],
        disc_total=["WM/PartOfSet"],
        compilation=["COMPILATION"],
        comments=["Description"],
        images=["WM/Picture"],
    )

    def __init__(
            self,
            file: str | mutagen.FileType | mutagen.asf.ASF,
            available: Iterable[str] = (),
            remote_wrangler: RemoteDataWrangler = None,
    ):
        super().__init__(file=file, available=available, remote_wrangler=remote_wrangler)
        # noinspection PyTypeChecker
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
