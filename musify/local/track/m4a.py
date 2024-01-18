"""
The M4A implementation of a :py:class:`LocalTrack`.
"""

from collections.abc import Iterable
from io import BytesIO
from typing import Any

import mutagen
import mutagen.mp4
from PIL import Image

from musify.local.file import open_image, get_image_bytes
from musify.local.track.base.track import LocalTrack
from musify.shared.core.enum import TagMap
from musify.shared.utils import to_collection


class M4A(LocalTrack[mutagen.mp4.MP4]):

    valid_extensions = frozenset({".m4a"})

    # noinspection SpellCheckingInspection
    #: Map of human-friendly tag name to ID3 tag ids for a given file type
    tag_map = TagMap(
        title=["©nam"],
        artist=["©ART"],
        album=["©alb"],
        album_artist=["aART"],
        track_number=["trkn"],
        track_total=["trkn"],
        genres=["----:com.apple.iTunes:GENRE", "©gen", "gnre"],
        date=["©day"],
        bpm=["tmpo"],
        key=["----:com.apple.iTunes:INITIALKEY"],
        disc_number=["disk"],
        disc_total=["disk"],
        compilation=["cpil"],
        comments=["©cmt"],
        images=["covr"],
    )

    def _read_tag(self, tag_ids: Iterable[str]) -> list[Any] | None:
        """Extract all tag values for a given list of tag IDs"""
        values = []
        for tag_id in tag_ids:
            value = self.file.get(tag_id)
            if value is None or (isinstance(value, str) and len(value.strip()) == 0):
                # skip null or empty/blank strings
                continue

            if tag_id.startswith("----:com.apple.iTunes") and isinstance(value, (list, set, tuple)):
                value = [v for val in value for v in val.decode("utf-8").split('\x00')]
            elif isinstance(value, bytes):
                value = value.decode("utf-8").split('\x00')

            values.extend(value) if isinstance(value, (list, set, tuple)) else values.append(value)

        return values if len(values) > 0 else None

    def _read_track_number(self) -> int | None:
        values = self._read_tag(self.tag_map.track_number)
        return int(values[0][0]) if values is not None else None

    def _read_track_total(self) -> int | None:
        values = self._read_tag(self.tag_map.track_total)
        return int(values[0][1]) if values is not None else None

    def _read_key(self) -> str | None:
        values = self._read_tag(self.tag_map.key)
        return str(values[0][:]) if values is not None else None

    def _read_disc_number(self) -> int | None:
        values = self._read_tag(self.tag_map.disc_number)
        return int(values[0][0]) if values is not None else None

    def _read_disc_total(self) -> int | None:
        values = self._read_tag(self.tag_map.disc_total)
        return int(values[0][1]) if values is not None else None

    def _read_images(self) -> list[Image.Image] | None:
        values = self._read_tag(self.tag_map.images)
        return [Image.open(BytesIO(bytes(value))) for value in values] if values is not None else None

    def _write_tag(self, tag_id: str | None, tag_value: Any, dry_run: bool = True) -> bool:
        result = super()._write_tag(tag_id=tag_id, tag_value=tag_value, dry_run=dry_run)
        if result is not None:
            return result

        if not dry_run:
            if tag_id.startswith("----:com.apple.iTunes"):
                self._file[tag_id] = [
                    mutagen.mp4.MP4FreeForm(str(v).encode("utf-8"), 1) for v in to_collection(tag_value)
                ]
            elif isinstance(tag_value, bool):
                self._file[tag_id] = tag_value
            elif isinstance(tag_value, tuple):
                self._file[tag_id] = [tag_value]
            else:
                self._file[tag_id] = to_collection(tag_value, list)
        return True

    def _write_track(self, dry_run: bool = True) -> bool:
        tag_id = next(iter(self.tag_map.track_number), None)
        tag_value = (self.track_number, self.track_total)
        return self._write_tag(tag_id, tag_value, dry_run)

    def _write_date(self, dry_run: bool = True) -> tuple[bool, bool, bool, bool]:
        date_str = self.date.strftime(self.date_format) if self.date else None
        date = self._write_tag(next(iter(self.tag_map.date), None), date_str, dry_run)

        year = self._write_tag(next(iter(self.tag_map.year), None), str(self.year) if self.year else None, dry_run)
        month = self._write_tag(next(iter(self.tag_map.month), None), str(self.month) if self.month else None, dry_run)
        day = self._write_tag(next(iter(self.tag_map.day), None), str(self.day) if self.day else None, dry_run)

        return date, year, month, day

    def _write_bpm(self, dry_run: bool = True) -> bool:
        return self._write_tag(next(iter(self.tag_map.bpm), None), int(self.bpm), dry_run)

    def _write_disc(self, dry_run: bool = True) -> bool:
        tag_id = next(iter(self.tag_map.disc_number), None)
        tag_value = (self.disc_number, self.disc_total)
        return self._write_tag(tag_id, tag_value, dry_run)

    def _write_compilation(self, dry_run: bool = True) -> bool:
        return self._write_tag(next(iter(self.tag_map.compilation), None), self.compilation, dry_run)

    def _write_images(self, dry_run: bool = True) -> bool:
        tag_id = next(iter(self.tag_map.images), None)

        updated = False
        tag_value = []
        for image_link in self.image_links.values():
            image = open_image(image_link)

            if image.format == "PNG":
                image_format = mutagen.mp4.MP4Cover.FORMAT_PNG
            else:
                image_format = mutagen.mp4.MP4Cover.FORMAT_JPEG

            tag_value.append(mutagen.mp4.MP4Cover(get_image_bytes(image), imageformat=image_format))
            image.close()

        if len(tag_value) > 0:
            updated = self._write_tag(tag_id, tag_value, dry_run)

        self.has_image = updated or self.has_image
        return updated
