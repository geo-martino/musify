from typing import Optional

from local.files.track import TagMap, Track

import mutagen
import mutagen.mp3


class MP3(Track):
    _filetypes = ["mp3"]

    tag_map = TagMap(
        title=["TIT2"],
        artist=["TPE1"],
        album=["TALB"],
        track_number=["TRCK"],
        track_total=["TRCK"],
        genre=["TCON"],
        year=["TDRC", "TYER", "TDAT"],
        bpm=["TBPM"],
        key=["TKEY"],
        disc_number=["TPOS"],
        disc_total=["TPOS"],
        compilation=["TCMP"],
        album_artist=["TPE2"],
        comment=["COMM"],
        image=["APIC"],
    )

    def __init__(self, path: str):
        Track.__init__(self, path)
        self._file: mutagen.mp3.MP3 = self._file

    def _get_tag_values(self, tag_ids: list[str]) -> Optional[list]:
        # mp3 tag ids can have extra suffixes to them i.e. 'COMM:ID3v1 Comment:eng'
        # need to search all actual mp3 tag ids to check if they contain some part of the given base tag ids
        base_ids = tag_ids.copy()
        tag_ids.clear()
        for i, tag_id in base_ids:
            tag_ids.extend([mp3_id for mp3_id in self._file.keys() if tag_id in mp3_id])

        values = []
        for tag_id in tag_ids:
            value = self._file.get(tag_id)
            if value is None:
                continue

            values.extend(value) if isinstance(value, list) else values.append(value)

        return values if len(values) > 0 else None

    def _extract_images(self) -> Optional[list[bytes]]:
        values = self._get_tag_values(self.tag_map.image)
        return [value.data for value in values] if values is not None else None
