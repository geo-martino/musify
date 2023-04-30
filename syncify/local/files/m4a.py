from typing import Optional, Union

from tags.helpers import TagMap
from _track import Track

import mutagen
import mutagen.mp4

from syncify.utils.helpers import make_list


class M4A(Track):

    filetypes = [".m4a"]

    tag_map = TagMap(
        title=["©nam"],
        artist=["©ART"],
        album=["©alb"],
        track_number=["trkn"],
        track_total=["trkn"],
        genres=["©gen"],
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

    def extract_track_number(self) -> Optional[int]:
        values = self._get_tag_values(self.tag_map.track_number)
        return int(values[0][0]) if values is not None else None

    def extract_track_total(self) -> Optional[int]:
        values = self._get_tag_values(self.tag_map.track_total)
        return int(values[0][1]) if values is not None else None

    def extract_key(self) -> Optional[str]:
        values = self._get_tag_values(self.tag_map.key)
        return str(values[0][:].decode("utf-8")) if values is not None else None

    def extract_disc_number(self) -> Optional[int]:
        values = self._get_tag_values(self.tag_map.disc_number)
        return int(values[0][0]) if values is not None else None

    def extract_disc_total(self) -> Optional[int]:
        values = self._get_tag_values(self.tag_map.disc_total)
        return int(values[0][1]) if values is not None else None

    def _update_tag_value(self, tag_id: Optional[str], tag_value: object, dry_run: bool = True) -> bool:
        if not dry_run and tag_id is not None:
            self._file[tag_id] = make_list(tag_value)
        return tag_id is not None

    def update_track(self, dry_run: bool = True) -> bool:
        tag_id = next(iter(self.tag_map.track_number), None)
        tag_value = (self.track_number, self.track_total)
        return self._update_tag_value(tag_id, tag_value, dry_run)

    def update_disc(self, dry_run: bool = True) -> bool:
        tag_id = next(iter(self.tag_map.disc_number), None)
        tag_value = (self.disc_number, self.disc_total)
        return self._update_tag_value(tag_id, tag_value, dry_run)

    def update_key(self, dry_run: bool = True) -> bool:
        tag_id = next(iter(self.tag_map.key), None)
        if not dry_run and tag_id is not None:
            self._file[tag_id] = mutagen.mp4.MP4FreeForm(self.key.encode("utf-8"), 1)
        return tag_id is not None

    def update_images(self, dry_run: bool = True) -> bool:
        tag_id = next(iter(self.tag_map.key), None)

        image_type, image_url = next(iter(self.image_urls.items()), (None, None))
        img = self._open_image_url(image_url)
        if img is None:
            return False

        tag_value = [mutagen.mp4.MP4Cover(img.read(), imageformat=mutagen.mp4.MP4Cover.FORMAT_JPEG)]
        updated = self._update_tag_value(tag_id, tag_value, dry_run)

        img.close()
        self.has_image = updated or self.has_image
        return updated
