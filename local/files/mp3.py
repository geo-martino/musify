from typing import Optional, List, Union

from local.files.tags.helpers import TagMap
from local.files._track import Track

import mutagen
import mutagen.mp3
import mutagen.id3


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
        image=["APIC"],
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

    def extract_genres(self) -> Optional[List[str]]:
        """Extract metadata from file for genre"""
        values = self._get_tag_values(self.tag_map.genres)
        if values is None:
            return

        return [genre for value in values for genre in value.split(";")]

    def extract_images(self) -> Optional[List[bytes]]:
        values = self._get_tag_values(self.tag_map.image)
        return [value.data for value in values] if values is not None else None


if __name__ == "__main__":
    import json
    from utils.logger import Logger

    Logger.set_dev()
    MP3.set_file_paths("/mnt/d/Music")
    mp3 = MP3("/mnt/d/Music/Come From Away - OBC/01 - Welcome to the Rock.mp3")

    data = vars(mp3)
    for k, v in data.copy().items():
        if k in ["_logger", "_file", "date_modified"]:
            del data[k]

    print(json.dumps(data, indent=2))
