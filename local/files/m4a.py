from typing import Optional, Union

from local.files.tags.helpers import TagMap
from local.files._track import Track

import mutagen
import mutagen.mp4


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
        image=["covr"],
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


if __name__ == "__main__":
    import json
    from utils.logger import Logger

    Logger.set_dev()
    M4A.set_file_paths("/mnt/d/Music")
    m4a = M4A("/mnt/d/Music/Baldwin's Loft EP/01 - Hooktide.m4a")

    data = vars(m4a)
    for k, v in data.copy().items():
        if k in ["_logger", "_file", "date_modified"]:
            del data[k]

    print(json.dumps(data, indent=2))
