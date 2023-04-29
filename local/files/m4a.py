from typing import Optional

from local.files.track import TagMap, Track

import mutagen
import mutagen.mp4


class M4A(Track):
    _filetypes = ["m4a"]

    tag_map = TagMap(
        title=["©nam"],
        artist=["©ART"],
        album=["©alb"],
        track_number=["trkn"],
        track_total=["trkn"],
        genre=["©gen"],
        year=["©day"],
        bpm=["tmpo"],
        key=["----:com.apple.iTunes:INITIALKEY"],
        disc_number=["disk"],
        disc_total=["disk"],
        compilation=["cpil"],
        album_artist=["aART"],
        comment=["©cmt"],
        image=["covr"],
    )
    
    def __init__(self, path: str):
        Track.__init__(self, path)
        self._file: mutagen.mp4.MP4 = self._file

    def _extract_track_number(self) -> Optional[int]:
        values = self._get_tag_values(self.tag_map.track_number)
        return int(values[0][0]) if values is not None else None

    def _extract_track_total(self) -> Optional[int]:
        values = self._get_tag_values(self.tag_map.track_total)
        return int(values[0][1]) if values is not None else None

    def _extract_key(self) -> Optional[str]:
        values = self._get_tag_values(self.tag_map.disc_number)
        return str(values[0][:].decode("utf-8")) if values is not None else None

    def _extract_disc_number(self) -> Optional[int]:
        values = self._get_tag_values(self.tag_map.disc_number)
        return int(values[0][0]) if values is not None else None

    def _extract_disc_total(self) -> Optional[int]:
        values = self._get_tag_values(self.tag_map.disc_total)
        return int(values[0][1]) if values is not None else None
