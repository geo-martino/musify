from typing import Optional, List, Union

import mutagen
import mutagen.flac
import mutagen.flac
from mutagen.id3 import PictureType

from _track import Track
from tags.helpers import TagMap


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

    def extract_images(self) -> Optional[List[bytes]]:
        images = self._file.pictures
        return [image.data for image in images] if len(images) > 0 else None

    def _update_tag_value(self, tag_id: Optional[str], tag_value: object, dry_run: bool = True) -> bool:
        if not dry_run and tag_id is not None:
            self._file[tag_id] = str(tag_value)
        return tag_id is not None

    def update_images(self, dry_run: bool = True) -> bool:
        # replace embedded images
        if not dry_run:
            self._file.clear_pictures()

        updated = False
        for image_type, image_url in self.image_urls.items():
            img = self._open_image_url(image_url)
            if img is None:
                continue

            image_obj = mutagen.flac.Picture()
            image_obj.type = getattr(mutagen.id3.PictureType, image_type.upper(), mutagen.id3.PictureType.COVER_FRONT)
            image_obj.mime = u"image/jpeg"
            image_obj.data = img.read()

            if not dry_run:
                self._file.add_picture(image_obj)

            img.close()
            self.has_image = True
            updated = True

        return updated
