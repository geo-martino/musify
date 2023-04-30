from typing import Optional, List, Union

import mutagen
import mutagen.mp3
import mutagen.id3

from syncify.local.files._track import Track
from syncify.local.files.tags.helpers import TagMap


class MP3(Track):
    filetypes = [".mp3"]

    tag_map = TagMap(
        title=["TIT2"],
        artist=["TPE1"],
        album=["TALB"],
        track_number=["TRCK"],
        track_total=["TRCK"],
        genres=["TCON"],
        year=["TDRC", "TYER", "TDAT"],
        bpm=["TBPM"],
        key=["TKEY"],
        disc_number=["TPOS"],
        disc_total=["TPOS"],
        compilation=["TCMP"],
        album_artist=["TPE2"],
        comments=["COMM"],
        images=["APIC"],
    )

    def __init__(self, file: Union[str, mutagen.File], position: Optional[int] = None):
        Track.__init__(self, file=file, position=position)
        self._file: mutagen.mp3.MP3 = self._file

    def _get_tag_values(self, tag_names: List[str]) -> Optional[list]:
        # mp3 tag ids can have extra suffixes to them i.e. 'COMM:ID3v1 Comment:eng'
        # need to search all actual mp3 tag ids to check if they contain some part of the given base tag ids
        base_ids = tag_names.copy()
        tag_names.clear()
        for tag_name in base_ids:
            tag_names.extend([mp3_id for mp3_id in self._file.keys() if tag_name in mp3_id])

        values = []
        for tag_name in tag_names:
            value = self._file.get(tag_name)
            if value is None:
                continue

            # convert id3 object to python types, causes downstream if not
            if isinstance(value, mutagen.id3.TextFrame):
                values.append(str(value))
            elif isinstance(value, mutagen.id3.APIC):
                values.append(value)
            else:
                raise NotImplementedError(f"Unrecognised id3 type: ${value} (${type(value)}")

        return values if len(values) > 0 else None

    def _extract_genres(self) -> Optional[List[str]]:
        """Extract metadata from file for genre"""
        values = self._get_tag_values(self.tag_map.genres)
        if values is None:
            return

        return [genre for value in values for genre in value.split(";")]

    def _extract_images(self) -> Optional[List[bytes]]:
        values = self._get_tag_values(self.tag_map.images)
        return [value.data for value in values] if values is not None else None

    def _update_tag_value(self, tag_id: Optional[str], tag_value: object, dry_run: bool = True) -> bool:
        if not dry_run and tag_id is not None:
            self._file[tag_id] = getattr(mutagen.id3, tag_id)(3, text=str(tag_value))
        return tag_id is not None

    def _update_genres(self, dry_run: bool = True) -> bool:
        values = ";".join(self.genres)
        return self._update_tag_value(next(iter(self.tag_map.genres), None), values, dry_run)

    def _update_images(self, dry_run: bool = True) -> bool:
        tag_id = next(iter(self.tag_map.key), None)

        image_type, image_url = next(iter(self.image_urls.items()), (None, None))
        img = self._open_image_url(image_url)
        if img is None:
            return False

        if not dry_run and tag_id is not None:
            self._file[tag_id] = mutagen.id3.APIC(
                mime='image/jpeg',
                type=getattr(mutagen.id3.PictureType, image_type.upper(), mutagen.id3.PictureType.COVER_FRONT),
                data=img.read()
            )

        img.close()
        self.has_image = tag_id is not None or self.has_image
        return tag_id is not None
