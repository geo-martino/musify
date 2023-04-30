from typing import Optional, List, Union

import mutagen
import mutagen.asf

from syncify.local.files._track import Track
from syncify.local.files.tags.helpers import TagMap


class WMA(Track):
    filetypes = [".wma"]

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

    def __init__(self, file: Union[str, mutagen.File], position: Optional[int] = None):
        Track.__init__(self, file=file, position=position)
        self._file: mutagen.asf.ASF = self._file

    def _get_tag_values(self, tag_names: List[str]) -> Optional[list]:
        # wma tag values are return as mutagen.asf._attrs.ASFUnicodeAttribute
        values = []
        for tag_name in tag_names:
            value: List[mutagen.asf.ASFBaseAttribute] = self._file.get(tag_name)
            if value is None:
                # skip null or empty/blank strings
                continue

            values.extend([v.value for v in value if not (isinstance(value, str) and len(value.strip()) == 0)])

        return values if len(values) > 0 else None

    def _update_tag_value(self, tag_id: Optional[str], tag_value: object, dry_run: bool = True) -> bool:
        if not dry_run and tag_id is not None:
            if isinstance(tag_value, list):
                self._file[tag_id] = [mutagen.asf.ASFUnicodeAttribute(str(v)) for v in tag_value]
            else:
                self._file[tag_id] = mutagen.asf.ASFUnicodeAttribute(str(tag_value))
        return tag_id is not None

    def _update_images(self, dry_run: bool = True) -> bool:
        raise NotImplementedError("WMA Image embedding not currently supported")

        tag_id = next(iter(self.tag_map.key), None)

        image_type, image_url = next(iter(self.image_urls.items()), (None, None))
        img = self._open_image_url(image_url)
        if img is None:
            return False

        if not dry_run and tag_id is not None:
            file_raw[tag_id] = mutagen.asf.ASFByteArrayAttribute(data=img.read())

        img.close()
        self.has_image = tag_id is not None or self.has_image
        return tag_id is not None
