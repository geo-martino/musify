import io
from typing import Optional, List, Union

import mutagen
import mutagen.flac
import mutagen.flac
from PIL import Image
from mutagen.id3 import PictureType

from syncify.local.files._track import Track
from syncify.local.files.tags.helpers import TagMap, TagEnums, open_image, get_image_bytes


class FLAC(Track):
    filetypes = [".flac"]

    tag_map = TagMap(
        title=["title"],
        artist=["artist"],
        album=["album"],
        track_number=["tracknumber"],
        track_total=["tracktotal", "tracknumber"],
        genres=["genre"],
        year=["year", "date"],
        bpm=["bpm"],
        key=["initialkey"],
        disc_number=["discnumber"],
        disc_total=["discnumber"],
        compilation=["compilation"],
        album_artist=["albumartist"],
        comments=["comment", "description"],
        images=[],
    )

    def __init__(self, file: Union[str, mutagen.File], position: Optional[int] = None):
        Track.__init__(self, file=file, position=position)
        self._file: mutagen.flac.FLAC = self._file

    def _extract_images(self) -> Optional[List[Image.Image]]:
        values = self._file.pictures
        return [Image.open(io.BytesIO(value.data)) for value in values] if len(values) > 0 else None

    def _check_for_images(self) -> bool:
        return len(self._file.pictures) > 0

    def _update_tag_value(self, tag_id: Optional[str], tag_value: object, dry_run: bool = True) -> bool:
        if not dry_run and tag_id is not None:
            if isinstance(tag_value, list):
                self._file[tag_id] = [str(v) for v in tag_value]
            else:
                self._file[tag_id] = str(tag_value)
        return tag_id is not None

    def _update_images(self, dry_run: bool = True) -> bool:
        updated = False
        for image_type, image_link in self.image_links.items():
            image = open_image(image_link)

            picture = mutagen.flac.Picture()
            picture.type = getattr(mutagen.id3.PictureType, image_type.upper(), mutagen.id3.PictureType.COVER_FRONT)
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

    def _clear_tag(self, tag_name: str, dry_run: bool = True) -> bool:
        if tag_name == TagEnums.IMAGES.name.lower():
            self._file.clear_pictures()
            return True

        removed = False

        tag_ids = getattr(self.tag_map, tag_name, None)
        if tag_ids is None or len(tag_ids) is None:
            return removed

        for tag_id in tag_ids:
            if tag_id in self._file:
                if not dry_run:
                    del self._file[tag_id]
                removed = True

        return removed
