from typing import List, Optional, MutableMapping

from syncify.local.files.track.track import Track
from syncify.local.library.collection.track import TrackCollection


class Album(TrackCollection):

    @property
    def tracks(self) -> List[Track]:
        return self._tracks

    def __init__(self, name: str, tracks: List[Track]):
        self.name: str = name
        self._tracks: List[Track] = [track for track in tracks if track.album.lower() == name.lower()]

    def as_dict(self) -> MutableMapping[str, object]:
        return {
            "name": self.name,
            "tracks": [track.as_dict() for track in self.tracks]
        }

    def as_json(self) -> MutableMapping[str, object]:
        return {
            "name": self.name,
            "tracks": [track.as_json() for track in self.tracks]
        }


class Folder(TrackCollection):

    @property
    def tracks(self) -> List[Track]:
        return self._tracks

    def __init__(self, name: str, tracks: List[Track]):
        self.name: str = name
        self._tracks: List[Track] = [track for track in tracks if track.folder.lower() == name.lower()]

    def as_dict(self) -> MutableMapping[str, object]:
        return {
            "name": self.name,
            "tracks": [track.as_dict() for track in self.tracks]
        }

    def as_json(self) -> MutableMapping[str, object]:
        return {
            "name": self.name,
            "tracks": [track.as_json() for track in self.tracks]
        }


class Playlist(TrackCollection):

    @property
    def tracks(self) -> List[Track]:
        return self._tracks

    def __init__(self, name: str, tracks: List[Track], filepath: Optional[str] = None):
        self.name: str = name
        self.filepath: Optional[str] = filepath
        self._tracks: List[Track] = []

        self._tracks: List[Track] = tracks

    def as_dict(self) -> MutableMapping[str, object]:
        return {
            "name": self.name,
            "filepath": self.filepath,
            "tracks": [track.as_json() for track in self.tracks]
        }

    def as_json(self) -> MutableMapping[str, object]:
        return {
            "name": self.name,
            "filepath": self.filepath,
            "tracks": [track.as_dict() for track in self.tracks]
        }


if __name__ == "__main__":
    from glob import glob
    from os.path import join

    from syncify.local.files.file import load_track

    music_folder = "/mnt/d/Music"
    folder = "Audioslave"
    tracks = [load_track(path) for path in glob(join(music_folder, folder, "*.flac"))]
    folder = Folder(name=folder, tracks=tracks)
    print(folder)
    print(repr(folder))
