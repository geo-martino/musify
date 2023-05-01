from typing import Optional, List, Union, Set

import mutagen
import mutagen.flac
import mutagen.flac
from PIL import Image
from mutagen.id3 import PictureType

from syncify.local.files._track import Track
from syncify.local.files.tags.helpers import TagMap, TagEnums
from syncify.utils.helpers import make_list


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
        images = self._file.pictures
        return [Image.open(image.data) for image in images] if len(images) > 0 else None

    def _check_for_images(self) -> bool:
        return len(self._file.pictures) > 0

    def clear_tags(self, tags: Optional[Union[TagEnums, List[TagEnums]]] = None, dry_run: bool = True) -> Set[TagEnums]:
        removed: Set[TagEnums] = set()

        tags: Set[TagEnums] = set(make_list(tags))
        if TagEnums.ALL in tags:
            tags = TagEnums.all()

        for tag in tags:
            if tag == TagEnums.IMAGE:
                self._file.clear_pictures()
                removed.add(tag)
                continue

            tag_ids = getattr(self.tag_map, tag.name)
            if tag_ids is None or len(tag_ids) is None:
                continue

            for tag_id in tag_ids:
                if tag_id in self._file:
                    if not dry_run:
                        del self._file[tag_id]
                    removed.add(tag)

        return removed

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
            image: Image.Image = self._open_image(image_link)
            if image is None:
                continue

            picture = mutagen.flac.Picture()
            picture.type = getattr(mutagen.id3.PictureType, image_type.upper(), mutagen.id3.PictureType.COVER_FRONT)
            picture.mime = Image.MIME[image.format]
            picture.data = image.tobytes()

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
