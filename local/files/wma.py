from typing import Optional, List, Union

from local.files.tags.helpers import TagMap
from local.files._track import Track

import mutagen
import mutagen.asf


class WMA(Track):
    filetypes = [".wma"]

    tag_map = TagMap(
        title=["Title"],
        artist=["Author"],
        album=["WM/AlbumTitle"],
        track_number=["WM/TrackNumber"],
        track_total=["TotalTracks", "WM/TrackNumber"],
        genres=["WM/Genre"],
        year=["WM/Year"],
        bpm=["WM/BeatsPerMinute"],
        key=["WM/InitialKey"],
        disc_number=["WM/PartOfSet"],
        disc_total=["WM/PartOfSet"],
        compilation=["COMPILATION"],
        album_artist=["WM/AlbumArtist"],
        comments=["Description"],
        image=["WM/Picture"],
    )

    def __init__(self, file: Union[str, mutagen.File], position: Optional[int] = None):
        Track.__init__(self, file=file, position=position)
        self._file: mutagen.asf.ASF = self._file

    def _get_tag_values(self, tag_names: List[str]) -> Optional[list]:
        # wma tag values are return as mutagen.asf._attrs.ASFUnicodeAttribute
        values = []
        for tag_name in tag_names:
            value: List[mutagen.asf.ASFBaseAttribute] = self._file.get(tag_name)
            if value is None:
                # skip null or empty/blank strings
                continue

            values.extend([v.value for v in value if not (isinstance(value, str) and len(value.strip()) == 0)])

        return values if len(values) > 0 else None


if __name__ == "__main__":
    import json
    from utils.logger import Logger

    Logger.set_dev()
    WMA.set_file_paths("/mnt/d/Music")
    wma = WMA("/mnt/d/Music/Little Shop of Horrors - 2003 Broadway Revival Cast/1-01 - Prologue - Little Shop of Horrors.wma")

    data = vars(wma)
    for k, v in data.copy().items():
        if k in ["_logger", "_file", "date_modified"]:
            del data[k]

    print(json.dumps(data, indent=2))
