from typing import Optional, List, Union

import mutagen.flac

from local.files.tags.helpers import TagMap
from local.files._track import Track

import mutagen
import mutagen.flac


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
        image=[],
    )

    def __init__(self, file: Union[str, mutagen.File], position: Optional[int] = None):
        Track.__init__(self, file=file, position=position)
        self._file: mutagen.flac.FLAC = self._file

    def extract_images(self) -> Optional[List[bytes]]:
        images = self._file.pictures
        return [image.data for image in images] if len(images) > 0 else None


if __name__ == "__main__":
    import json
    from utils.logger import Logger

    Logger.set_dev()
    FLAC.set_file_paths("/mnt/d/Music")
    flac = FLAC("/mnt/d/Music/(What's the Story) Morning Glory/01 - Hello.flac")

    data = vars(flac)
    for k, v in data.copy().items():
        if k in ["_logger", "_file", "date_modified"]:
            del data[k]

    print(json.dumps(data, indent=2))
