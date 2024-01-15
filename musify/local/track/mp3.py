from collections.abc import Iterable
from io import BytesIO
from typing import Any

import mutagen
import mutagen.id3
import mutagen.mp3
from PIL import Image

from musify.local.file import open_image, get_image_bytes
from musify.local.track.base.track import LocalTrack
from musify.local.track.field import LocalTrackField
from musify.shared.core.enum import TagMap


class MP3(LocalTrack[mutagen.mp3.MP3]):

    valid_extensions = frozenset({".mp3"})

    # noinspection SpellCheckingInspection
    tag_map = TagMap(
        title=["TIT2"],
        artist=["TPE1"],
        album=["TALB"],
        album_artist=["TPE2"],
        track_number=["TRCK"],
        track_total=["TRCK"],
        genres=["TCON"],
        date=["TDRC", "TDAT", "TDOR"],
        year=["TYER", "TORY"],
        bpm=["TBPM"],
        key=["TKEY"],
        disc_number=["TPOS"],
        disc_total=["TPOS"],
        compilation=["TCMP"],
        comments=["COMM"],
        images=["APIC"],
    )

    def _read_tag(self, tag_ids: Iterable[str]) -> list[Any] | None:
        # MP3 tag ids come in parts separated by : i.e. 'COMM:ID3v1 Comment:eng'
        # need to search all actual MP3 tag ids to check if the first part equals any of the given base tag ids
        tag_ids = tuple(mp3_id for mp3_id in self._file.keys() for tag_id in tag_ids if mp3_id.split(":")[0] == tag_id)

        values = []
        for tag_id in tag_ids:
            value = self._file.get(tag_id)
            if value is None:
                continue

            # convert id3 object to python types, causes downstream if not
            if isinstance(value, mutagen.id3.TextFrame):
                values.extend(str(value).split('\x00'))
            elif isinstance(value, mutagen.id3.APIC):
                values.append(value)
            else:
                raise NotImplementedError(f"Unrecognised id3 type: {value} ({type(value)})")

        return values if len(values) > 0 else None

    def _read_genres(self) -> list[str] | None:
        """Extract metadata from file for genre"""
        values = self._read_tag(self.tag_map.genres)
        if values is None:
            return
        return [genre for value in values for genre in value.split(";")]

    def _read_images(self) -> list[Image.Image] | None:
        values = self._read_tag(self.tag_map.images)
        return [Image.open(BytesIO(value.data)) for value in values] if values is not None else None

    def _write_tag(self, tag_id: str | None, tag_value: Any, dry_run: bool = True) -> bool:
        if tag_value is None:
            remove = not dry_run and tag_id in self.file and self.file[tag_id]
            if remove:
                del self.file[tag_id]
            return remove

        if not dry_run and tag_id is not None:
            self._file[tag_id] = getattr(mutagen.id3, tag_id)(3, text=str(tag_value))
        return tag_id is not None

    def _write_genres(self, dry_run: bool = True) -> bool:
        values = ";".join(self.genres or [])
        return self._write_tag(next(iter(self.tag_map.genres), None), values, dry_run)

    def _write_images(self, dry_run: bool = True) -> bool:
        tag_id_prefix = next(iter(self.tag_map.images), None)

        updated = False
        for image_kind, image_link in self.image_links.items():
            image = open_image(image_link)

            if not dry_run and tag_id_prefix is not None:
                image_kind_attr = image_kind.upper().replace(" ", "_")
                image_type: mutagen.id3.PictureType = getattr(mutagen.id3.PictureType, image_kind_attr)
                tag_id = f"{tag_id_prefix}:{image_kind}"

                # noinspection PyUnresolvedReferences
                self._file[tag_id] = mutagen.id3.APIC(
                    encoding=mutagen.id3.Encoding.UTF8,
                    # desc=image_kind,
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
        self.delete_tags(tags=LocalTrackField.COMMENTS, dry_run=dry_run)

        for i, comment in enumerate(self.comments, 1):
            # noinspection PyUnresolvedReferences
            comm = mutagen.id3.COMM(
                encoding=mutagen.id3.Encoding.UTF8, desc=f"ID3v1 Comment {i}", lang="eng", text=[comment]
            )
            # noinspection PyUnresolvedReferences
            tag_id = f"{tag_id_prefix}:{comm.desc}:{comm.lang}"
            if not dry_run and tag_id is not None:
                self._file[tag_id] = comm

        return tag_id_prefix is not None

    def _write_uri(self, dry_run: bool = True) -> bool:
        if not self.remote_wrangler:
            return False

        tag_value = self.remote_wrangler.unavailable_uri_dummy if not self.has_uri else self.uri

        # if applying URI as comment, clear comments and add manually with custom description
        if self.uri_tag == LocalTrackField.COMMENTS:
            tag_id_prefix = next(iter(self.tag_map.comments), None)
            self.delete_tags(tags=self.uri_tag, dry_run=dry_run)

            # noinspection PyUnresolvedReferences
            comm = mutagen.id3.COMM(encoding=mutagen.id3.Encoding.UTF8, lang="eng", desc="URI", text=[tag_value])
            # noinspection PyUnresolvedReferences
            tag_id = f"{tag_id_prefix}:{comm.desc}:{comm.lang}"
            if not dry_run and tag_id is not None:
                self._file[tag_id] = comm

            return tag_id is not None
        else:
            tag_id = next(iter(self.tag_map[self.uri_tag.name.lower()]), None)
            return self._write_tag(tag_id, tag_value, dry_run)

    def delete_tag(self, tag_name: str, dry_run: bool = True) -> bool:
        removed = False

        tag_ids = self.tag_map[tag_name]
        if tag_ids is None or len(tag_ids) is None:
            return removed

        for tag_id_prefix in tag_ids:
            for mp3_id in list(self.file.keys()).copy():
                if mp3_id.split(":")[0] == tag_id_prefix and self._file[mp3_id]:
                    if not dry_run:
                        del self._file[mp3_id]
                    removed = True

        return removed
