from local.files.track import TagMap, Track

import mutagen
import mutagen.asf


class WMA(Track):
    _filetypes = ["wma"]

    tag_map = TagMap(
        title=["Title"],
        artist=["Author"],
        album=["WM/AlbumTitle"],
        track_number=["WM/TrackNumber"],
        track_total=["TotalTracks", "WM/TrackNumber"],
        genre=["WM/Genre"],
        year=["WM/Year"],
        bpm=["WM/BeatsPerMinute"],
        key=["WM/InitialKey"],
        disc_number=["WM/PartOfSet"],
        disc_total=["WM/PartOfSet"],
        compilation=["COMPILATION"],
        album_artist=["WM/AlbumArtist"],
        comment=["Description"],
        image=["WM/Picture"],
    )

    def __init__(self, path: str):
        Track.__init__(self, path)
        self._file: mutagen.asf.ASF = self._file
