from io import BytesIO
from typing import Optional, List, Union

import mutagen
import mutagen.id3
import mutagen.mp3
from PIL import Image
from mutagen.id3 import Encoding

from syncify.local.files.track.base import Track, TagName, TagMap
from syncify.local.files.utils.image import open_image, get_image_bytes
from syncify.spotify.helpers import __UNAVAILABLE_URI_VALUE__


class MP3(Track):
    """
    Track object for extracting, modifying, and saving tags from MP3 files.

    :param file: The path or Mutagen object of the file to load.
    """

    valid_extensions = [".mp3"]

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

    def __init__(self, file: Union[str, mutagen.File]):
        Track.__init__(self, file=file)
        self._file: mutagen.mp3.MP3 = self._file

    def _read_tag(self, tag_ids: List[str]) -> Optional[list]:
        # mp3 tag ids come in parts separated by : i.e. 'COMM:ID3v1 Comment:eng'
        # need to search all actual mp3 tag ids to check if the first part equals any of the given base tag ids
        tag_ids = [mp3_id for mp3_id in self._file.keys() for tag_id in tag_ids if mp3_id.split(":")[0] == tag_id]

        values = []
        for tag_id in tag_ids:
            value = self._file.get(tag_id)
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

    def _read_genres(self) -> Optional[List[str]]:
        """Extract metadata from file for genre"""
        values = self._read_tag(self.tag_map.genres)
        if values is None:
            return

        return [genre for value in values for genre in value.split(";")]

    def _read_images(self) -> Optional[List[Image.Image]]:
        values = self._read_tag(self.tag_map.images)
        return [Image.open(BytesIO(value.data)) for value in values] if values is not None else None

    def _write_tag(self, tag_id: Optional[str], tag_value: object, dry_run: bool = True) -> bool:
        if not dry_run and tag_id is not None:
            self._file[tag_id] = getattr(mutagen.id3, tag_id)(3, text=str(tag_value))
        return tag_id is not None

    def _write_genres(self, dry_run: bool = True) -> bool:
        values = ";".join(self.genres)
        return self._write_tag(next(iter(self.tag_map.genres), None), values, dry_run)

    def _write_images(self, dry_run: bool = True) -> bool:
        tag_id_prefix = next(iter(self.tag_map.images), None)

        updated = False
        for image_kind, image_link in self.image_links.items():
            image = open_image(image_link)

            if not dry_run and tag_id_prefix is not None:
                image_kind_attr = image_kind.upper().replace(" ", "_")
                image_type: mutagen.id3.PictureType = getattr(
                    mutagen.id3.PictureType, image_kind_attr, mutagen.id3.PictureType.COVER_FRONT
                )
                tag_id = f"{tag_id_prefix}:{image_kind}"

                self._file[tag_id] = mutagen.id3.APIC(
                    encoding=Encoding.UTF8,
                    desc=image_kind,
                    mime=Image.MIME[image.format],
                    type=image_type,
                    data=get_image_bytes(image)
                )

            image.close()
            self.has_image = tag_id_prefix is not None or self.has_image
            updated = tag_id_prefix is not None
        return updated

    def _write_comments(self, dry_run: bool = True) -> bool:
        tag_id_prefix = next(iter(self.tag_map.comments), None)
        self.delete_tags(tags=TagName.COMMENTS, dry_run=dry_run)

        for i, comment in enumerate(self.comments, 1):
            comm = mutagen.id3.COMM(encoding=Encoding.UTF8, desc=f'ID3v1 Comment {i}', lang='eng', text=[comment])
            tag_id = f"{tag_id_prefix}:{comm.desc}:{comm.lang}"
            if not dry_run and tag_id is not None:
                self._file[tag_id] = comm

        return tag_id_prefix is not None

    def _write_uri(self, dry_run: bool = True) -> bool:
        tag_value = __UNAVAILABLE_URI_VALUE__ if not self.has_uri else self.uri

        # if applying uri as comment, clear comments and add manually with custom description
        if self.uri_tag == TagName.COMMENTS:
            tag_id_prefix = next(iter(self.tag_map.comments), None)
            self.delete_tags(tags=self.uri_tag, dry_run=dry_run)

            comm = mutagen.id3.COMM(encoding=Encoding.UTF8, lang='eng', desc='URI', text=[tag_value])
            tag_id = f"{tag_id_prefix}:{comm.desc}:{comm.lang}"
            if not dry_run and tag_id is not None:
                self._file[tag_id] = comm

            return tag_id is not None
        else:
            tag_id = next(iter(getattr(self.tag_map, self.uri_tag.name.lower(), [])), None)
            return self._write_tag(tag_id, tag_value, dry_run)

    def _delete_tag(self, tag_name: str, dry_run: bool = True) -> bool:
        removed = False

        tag_ids = getattr(self.tag_map, tag_name, None)
        if tag_ids is None or len(tag_ids) is None:
            return removed

        for tag_id_prefix in tag_ids:
            for mp3_id in list(self.file.keys()).copy():
                if mp3_id.split(":")[0] == tag_id_prefix:
                    if not dry_run:
                        del self._file[mp3_id]
                    removed = True

        return removed
