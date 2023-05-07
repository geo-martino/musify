from datetime import datetime
from typing import List, MutableMapping, Any, Optional, Callable, Tuple, Set

from syncify.local.files.track import LocalTrack, TrackCollection


class LocalCollection(TrackCollection):

    @property
    def tracks(self) -> List[LocalTrack]:
        return self._tracks

    @property
    def name(self) -> str:
        return self._name

    @property
    def last_added(self) -> Optional[datetime]:
        return self._last_added

    @property
    def last_modified(self) -> Optional[datetime]:
        return self._last_modified

    @property
    def last_played(self) -> Optional[datetime]:
        return self._last_played

    def __init__(self, tracks: List[LocalTrack], name: Optional[str] = None):
        if len(tracks) == 0:
            raise ValueError("No tracks were given")

        self._tag_key = self._camel_to_snake(self.__class__.__name__)

        if name is None:
            names = set(getattr(track, self._tag_key, None) for track in tracks)
            names_flat = []
            for name in names.copy():
                if name:
                    if isinstance(name, list) or isinstance(name, set):
                        names_flat.extend(name)
                    else:
                        names_flat.append(name)

            if len(names_flat) == 0:
                raise TypeError(f"No {self.__class__.__name__} found in the given tracks")
            if len(names_flat) != 1:
                raise TypeError(
                    f"Too many {self.__class__.__name__}s found in the given tracks."
                    " Only provide tracks from the same album.")

            name = names_flat[0]

        self._name: str = name
        self._tracks: List[LocalTrack] = [track for track in tracks if getattr(track, self._tag_key, None) == name]

        self._last_played: Optional[datetime] = None
        self._last_added: Optional[datetime] = None
        self._last_modified: Optional[datetime] = None

    def _get_times(self) -> None:
        key_type = Callable[[LocalTrack], Tuple[bool, datetime]]
        key: key_type = lambda t: (t.last_played is None, t.last_played)
        self._last_played = sorted(self._tracks, key=key, reverse=True)[0].last_played
        key: key_type = lambda t: (t.date_added is None, t.date_added)
        self._last_added = sorted(self._tracks, key=key, reverse=True)[0].date_added
        key: key_type = lambda t: (t.date_modified is None, t.date_modified)
        self._last_modified = sorted(self._tracks, key=key, reverse=True)[0].date_modified

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "name": self._name,
            "tracks": self._tracks,
            "last_added": self._last_added,
            "last_modified": self._last_modified,
            "last_played": self._last_played,
        }


class Folder(LocalCollection):

    @property
    def artists(self) -> Set[str]:
        return self._artists

    @property
    def genres(self) -> Set[str]:
        return self._genres

    @property
    def compilation(self) -> bool:
        return self._compilation

    def __init__(self, tracks: List[LocalTrack], name: Optional[str] = None):
        LocalCollection.__init__(self, tracks=tracks, name=name)
        self._get_times()

        self._artists = set(track.artist for track in self.tracks)
        self._genres = set(genre for track in self.tracks for genre in (track.genres if track.genres else []))
        # collection is a compilation if over 50% of tracks are marked as compilation
        self._compilation = (sum(track.compilation for track in self.tracks) / len(self.tracks)) > 0.5

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "name": self._name,
            "artists": self._artists,
            "genres": self._genres,
            "compilation": self._compilation,
            "tracks": self._tracks,
            "last_added": self._last_added,
            "last_modified": self._last_modified,
            "last_played": self._last_played,
        }


class Album(LocalCollection):

    @property
    def artists(self) -> Set[str]:
        return self._artists

    @property
    def genres(self) -> Set[str]:
        return self._genres

    @property
    def compilation(self) -> bool:
        return self._compilation

    def __init__(self, tracks: List[LocalTrack], name: Optional[str] = None):
        LocalCollection.__init__(self, tracks=tracks, name=name)
        self._get_times()

        self._artists = set(track.artist for track in self.tracks if track.artist)
        self._genres = set(genre for track in self.tracks for genre in (track.genres if track.genres else []))
        # collection is a compilation if over 50% of tracks are marked as compilation
        self._compilation = (sum(track.compilation for track in self.tracks) / len(self.tracks)) > 0.5

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "name": self._name,
            "artists": self._artists,
            "genres": self._genres,
            "compilation": self._compilation,
            "tracks": self._tracks,
            "last_added": self._last_added,
            "last_modified": self._last_modified,
            "last_played": self._last_played,
        }


class Artist(LocalCollection):

    @property
    def albums(self) -> Set[str]:
        return self._albums

    @property
    def genres(self) -> Set[str]:
        return self._genres

    def __init__(self, tracks: List[LocalTrack], name: Optional[str] = None):
        LocalCollection.__init__(self, tracks=tracks, name=name)
        self._get_times()

        self._albums = set(track.album for track in self.tracks if track.album)
        self._genres = set(genre for track in self.tracks for genre in (track.genres if track.genres else []))

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "name": self._name,
            "albums": self._albums,
            "genres": self._genres,
            "tracks": self._tracks,
            "last_added": self._last_added,
            "last_modified": self._last_modified,
            "last_played": self._last_played,
        }


class Genres(LocalCollection):

    @property
    def artists(self) -> Set[str]:
        return self._artists

    @property
    def albums(self) -> Set[str]:
        return self._albums

    @property
    def genres(self) -> Set[str]:
        return self._genres

    def __init__(self, tracks: List[LocalTrack], name: Optional[str] = None):
        LocalCollection.__init__(self, tracks=tracks, name=name)
        self._tracks: List[LocalTrack] = [track for track in tracks if name in getattr(track, self._tag_key, [])]
        self._get_times()

        self._artists = set(track.artist for track in self.tracks if track.artist)
        self._albums = set(track.album for track in self.tracks if track.album)
        self._genres = set(genre for track in self.tracks for genre in (track.genres if track.genres else []))

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "name": self._name,
            "artists": self._artists,
            "albums": self._albums,
            "tracks": self._tracks,
            "last_added": self._last_added,
            "last_modified": self._last_modified,
            "last_played": self._last_played,
        }
