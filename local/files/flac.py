from typing import Optional

import mutagen.flac
from local.files.track import TagMap, Track

import mutagen
import mutagen.flac


class FLAC(Track):
    _filetypes = ["flac"]

    tag_map = TagMap(
        title=["title"],
        artist=["artist"],
        album=["album"],
        track_number=["tracknumber"],
        track_total=["tracktotal", "tracknumber"],
        genre=["genre"],
        year=["year", "date"],
        bpm=["bpm"],
        key=["initialkey"],
        disc_number=["discnumber"],
        disc_total=["discnumber"],
        compilation=["compilation"],
        album_artist=["albumartist"],
        comment=["comment", "description"],
        image=[],
    )

    def __init__(self, path: str):
        Track.__init__(self, path)
        self._file: mutagen.flac.FLAC = self._file

    def _extract_images(self) -> Optional[list[bytes]]:
        images = self._file.pictures
        return [image.data for image in images] if len(images) > 0 else None
