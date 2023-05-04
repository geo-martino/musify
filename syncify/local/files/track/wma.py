from io import BytesIO
from typing import Optional, List, Union

import mutagen
import mutagen.asf
from PIL import Image

from syncify.local.files.track.base import Track, TagMap
from syncify.local.files.utils.image import open_image, get_image_bytes


class WMA(Track):
    """
    Track object for extracting, modifying, and saving tags from WMA files.

    :param file: The path or Mutagen object of the file to load.
    """

    track_ext = [".wma"]

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

    def __init__(self, file: Union[str, mutagen.File]):
        Track.__init__(self, file=file)
        self._file: mutagen.asf.ASF = self._file

    def _read_tag(self, tag_ids: List[str]) -> Optional[list]:
        # wma tag values are return as mutagen.asf._attrs.ASFUnicodeAttribute
        values = []
        for tag_id in tag_ids:
            value: List[mutagen.asf.ASFBaseAttribute] = self._file.get(tag_id)
            if value is None:
                # skip null or empty/blank strings
                continue

            values.extend([v.value for v in value if not (isinstance(value, str) and len(value.strip()) == 0)])

        return values if len(values) > 0 else None

    def _read_images(self) -> Optional[List[Image.Image]]:
        raise NotImplementedError("Image extraction not supported for WMA files")

        values = self._read_tag(self.tag_map.images)
        return [Image.open(BytesIO(value)) for value in values] if values is not None else None

    def _write_tag(self, tag_id: Optional[str], tag_value: object, dry_run: bool = True) -> bool:
        if not dry_run and tag_id is not None:
            if isinstance(tag_value, list):
                self._file[tag_id] = [mutagen.asf.ASFUnicodeAttribute(str(v)) for v in tag_value]
            else:
                self._file[tag_id] = mutagen.asf.ASFUnicodeAttribute(str(tag_value))
        return tag_id is not None

    def _write_images(self, dry_run: bool = True) -> bool:
        raise NotImplementedError("Image embedding not supported for WMA files")

        tag_id = next(iter(self.tag_map.key), None)

        updated = False
        tag_value = []
        for image_link in self.image_links.values():
            image = open_image(image_link)

            tag_value.append(mutagen.asf.ASFByteArrayAttribute(data=get_image_bytes(image)))
            image.close()

        if len(tag_value) > 0:
            updated = self._write_tag(tag_id, tag_value, dry_run)

        self.has_image = updated or self.has_image
        return updated
