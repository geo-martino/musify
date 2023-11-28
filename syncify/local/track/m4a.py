from io import BytesIO
from collections.abc import Collection
from typing import Any

import mutagen
import mutagen.mp4
from PIL import Image

from syncify.enums.tags import TagMap
from syncify.local.file import open_image, get_image_bytes
from syncify.local.track.base.track import LocalTrack
from syncify.utils.helpers import to_collection


class M4A(LocalTrack):
    """
    Track object for extracting, modifying, and saving tags from M4A files.

    :param file: The path or Mutagen object of the file to load.
    :param available: A list of available track paths that are known to exist and are valid for this track type.
        Useful for case-insensitive path loading and correcting paths to case-sensitive.
    """

    valid_extensions = {".m4a"}

    # noinspection SpellCheckingInspection
    tag_map = TagMap(
        title=["©nam"],
        artist=["©ART"],
        album=["©alb"],
        track_number=["trkn"],
        track_total=["trkn"],
        genres=["----:com.apple.iTunes:genre", "©gen", "gnre"],
        year=["©day"],
        bpm=["tmpo"],
        key=["----:com.apple.iTunes:INITIALKEY"],
        disc_number=["disk"],
        disc_total=["disk"],
        compilation=["cpil"],
        album_artist=["aART"],
        comments=["©cmt"],
        images=["covr"],
    )

    # noinspection PyTypeChecker
    def __init__(
            self, file: str | mutagen.FileType | mutagen.mp4.MP4, available: Collection[str] | None = None
    ):
        LocalTrack.__init__(self, file=file, available=available)
        self._file: mutagen.mp4.MP4 = self._file

    def _read_tag(self, tag_ids: list[str]) -> list[Any] | None:
        """Extract all tag values for a given list of tag IDs"""
        values = []
        for tag_id in tag_ids:
            value = self.file.get(tag_id)
            if value is None or (isinstance(value, str) and len(value.strip()) == 0):
                # skip null or empty/blank strings
                continue

            if tag_id.startswith("----:com.apple.iTunes") and isinstance(value, list):
                value = list(v.decode("utf-8") for v in value)
            elif isinstance(value, bytes):
                value = value.decode("utf-8")

            values.extend(value) if isinstance(value, list) else values.append(value)

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
        if tag_value is None:
            return self.delete_tag(tag_id, dry_run=dry_run)

        if not dry_run and tag_id is not None:
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
        return tag_id is not None

    def _write_track(self, dry_run: bool = True) -> bool:
        tag_id = next(iter(self.tag_map.track_number), None)
        tag_value = (self.track_number, self.track_total)
        return self._write_tag(tag_id, tag_value, dry_run)

    def _write_year(self, dry_run: bool = True) -> bool:
        return self._write_tag(next(iter(self.tag_map.year), None), str(self.year), dry_run)

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
