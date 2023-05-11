from datetime import datetime
from typing import List, MutableMapping, Any, Optional, Callable, Tuple, Set

from syncify.local.files.track import LocalTrack, LocalTrackCollection


class LocalCollection(LocalTrackCollection):
    """
    Generic class for storing a collection of local tracks
    with methods for enriching the attributes of this object from the attributes of the collection of tracks

    :param tracks: A list of loaded tracks.
    :param name: The name of this collection.
        If given, the object only stores tracks that match the name given on the attribute of this object.
        If None, the list of tracks given are taken to be all the tracks contained in this collection.
    :raises ValueError: If the given tracks contain more than one unique value
        for the attribute of this collection when name is None.
    """

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
        """Extract key time data for this track collection from the loaded tracks"""
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
    """
    Object representing a collection of tracks in a folder on the local drive

    :param tracks: A list of loaded tracks.
    :param name: The name of this folder.
        If given, the object only stores tracks that match the folder ``name`` given.
        If None, the list of tracks given are taken to be all the tracks contained in this folder.
    :raises ValueError: If the given tracks contain more than one unique value for ``folder`` when name is None.
    """

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
    """
    Object representing a collection of tracks of an album.

    :param tracks: A list of loaded tracks.
    :param name: The name of this album.
        If given, the object only stores tracks that match the album ``name`` given.
        If None, the list of tracks given are taken to be all the tracks for this album.
    :raises ValueError: If the given tracks contain more than one unique value for ``album`` when name is None.
    """

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
    """
    Object representing a collection of tracks by a single artist.

    :param tracks: A list of loaded tracks.
    :param name: The name of this artist.
        If given, the object only stores tracks that match the artist ``name`` given.
        If None, the list of tracks given are taken to be all the tracks by this artist.
    :raises ValueError: If the given tracks contain more than one unique value for ``artist`` when name is None.
    """

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
    """
    Object representing a collection of tracks within a genre.

    :param tracks: A list of loaded tracks.
    :param name: The name of this genre.
        If given, the object only stores tracks that match the genre ``name`` given.
        If None, the list of tracks given are taken to be all the tracks within this genre.
    :raises ValueError: If the given tracks contain more than one unique value for ``genre`` when name is None.
    """

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
