from io import BytesIO
from typing import Optional, Union, List

import mutagen
import mutagen.mp4
from PIL import Image

from syncify.local.files._track import Track
from syncify.local.files.tags.helpers import TagMap, open_image, get_image_bytes
from syncify.utils.helpers import make_list


class M4A(Track):

    filetypes = [".m4a"]

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
    
    def __init__(self, file: Union[str, mutagen.File], position: Optional[int] = None):
        Track.__init__(self, file=file, position=position)
        self._file: mutagen.mp4.MP4 = self._file

    def _get_tag_values(self, tag_ids: List[str]) -> Optional[list]:
        """Extract all tag values for a given list of tag IDs"""
        values = []
        for tag_id in tag_ids:
            value = self.file.get(tag_id)
            if value is None or (isinstance(value, str) and len(value.strip()) == 0):
                # skip null or empty/blank strings
                continue

            if tag_id.startswith("----:com.apple.iTunes") and isinstance(value, list):
                value = [v.decode("utf-8") for v in value]
            elif isinstance(value, bytes):
                value = value.decode("utf-8")

            values.extend(value) if isinstance(value, list) else values.append(value)

        return values if len(values) > 0 else None

    def _extract_track_number(self) -> Optional[int]:
        values = self._get_tag_values(self.tag_map.track_number)
        return int(values[0][0]) if values is not None else None

    def _extract_track_total(self) -> Optional[int]:
        values = self._get_tag_values(self.tag_map.track_total)
        return int(values[0][1]) if values is not None else None

    def _extract_key(self) -> Optional[str]:
        values = self._get_tag_values(self.tag_map.key)
        return str(values[0][:]) if values is not None else None

    def _extract_disc_number(self) -> Optional[int]:
        values = self._get_tag_values(self.tag_map.disc_number)
        return int(values[0][0]) if values is not None else None

    def _extract_disc_total(self) -> Optional[int]:
        values = self._get_tag_values(self.tag_map.disc_total)
        return int(values[0][1]) if values is not None else None

    def _extract_images(self) -> Optional[List[Image.Image]]:
        values = self._get_tag_values(self.tag_map.images)
        return [Image.open(BytesIO(bytes(value))) for value in values] if values is not None else None

    def _update_tag_value(self, tag_id: Optional[str], tag_value: object, dry_run: bool = True) -> bool:
        if not dry_run and tag_id is not None:
            if tag_id.startswith("----:com.apple.iTunes"):
                self._file[tag_id] = [mutagen.mp4.MP4FreeForm(str(v).encode("utf-8"), 1) for v in make_list(tag_value)]
            elif isinstance(tag_value, bool):
                self._file[tag_id] = tag_value
            else:
                self._file[tag_id] = make_list(tag_value)
        return tag_id is not None

    def _update_track(self, dry_run: bool = True) -> bool:
        tag_id = next(iter(self.tag_map.track_number), None)
        tag_value = (self.track_number, self.track_total)
        return self._update_tag_value(tag_id, tag_value, dry_run)

    def _update_year(self, dry_run: bool = True) -> bool:
        return self._update_tag_value(next(iter(self.tag_map.year), None), str(self.year), dry_run)

    def _update_bpm(self, dry_run: bool = True) -> bool:
        return self._update_tag_value(next(iter(self.tag_map.bpm), None), int(self.bpm), dry_run)

    def _update_disc(self, dry_run: bool = True) -> bool:
        tag_id = next(iter(self.tag_map.disc_number), None)
        tag_value = (self.disc_number, self.disc_total)
        return self._update_tag_value(tag_id, tag_value, dry_run)

    def _update_compilation(self, dry_run: bool = True) -> bool:
        return self._update_tag_value(next(iter(self.tag_map.compilation), None), self.compilation, dry_run)

    def _update_images(self, dry_run: bool = True) -> bool:
        tag_id = next(iter(self.tag_map.images), None)

        updated = False
        tag_value = []
        for image_link in self.image_links.values():
            image = open_image(image_link)

            if image.format == 'PNG':
                image_format = mutagen.mp4.MP4Cover.FORMAT_PNG
            else:
                image_format = mutagen.mp4.MP4Cover.FORMAT_JPEG

            tag_value.append(mutagen.mp4.MP4Cover(get_image_bytes(image), imageformat=image_format))
            image.close()

        if len(tag_value) > 0:
            updated = self._update_tag_value(tag_id, tag_value, dry_run)

        self.has_image = updated or self.has_image
        return updated
