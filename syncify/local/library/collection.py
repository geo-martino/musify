from abc import ABCMeta
from collections import Counter
from datetime import datetime
from typing import List, MutableMapping, Any, Optional, Callable, Tuple

from syncify.abstract.collection import ItemCollection, Folder, Album, Artist, Genre
from syncify.local.track import LocalTrack


class LocalCollection(ItemCollection, metaclass=ABCMeta):
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
    def name(self) -> str:
        return self._name

    @property
    def items(self) -> List[LocalTrack]:
        return self.tracks

    def __init__(self, tracks: List[LocalTrack], name: Optional[str] = None):
        if len(tracks) == 0:
            raise ValueError("No tracks were given")

        self._tag_key = self._camel_to_snake(self.__class__.__name__.replace("Local", ""))

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
        self.tracks: List[LocalTrack] = [track for track in tracks if getattr(track, self._tag_key, None) == name]
        self.length: float = sum(track.length for track in self.tracks)

        self.last_played: Optional[datetime] = None
        self.last_added: Optional[datetime] = None
        self.last_modified: Optional[datetime] = None

    def _get_times(self) -> None:
        """Extract key time data for this track collection from the loaded tracks"""
        key_type = Callable[[LocalTrack], Tuple[bool, datetime]]
        key: key_type = lambda t: (t.last_played is None, t.last_played)
        self.last_played = sorted(self.tracks, key=key, reverse=True)[0].last_played
        key: key_type = lambda t: (t.date_added is None, t.date_added)
        self.last_added = sorted(self.tracks, key=key, reverse=True)[0].date_added
        key: key_type = lambda t: (t.date_modified is None, t.date_modified)
        self.last_modified = sorted(self.tracks, key=key, reverse=True)[0].date_modified

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "name": self.name,
            "tracks": self.tracks,
            "last_played": self.last_played,
            "last_added": self.last_added,
            "last_modified": self.last_modified,
        }


class LocalFolder(Folder, LocalCollection):
    """
    Object representing a collection of tracks in a folder on the local drive

    :param tracks: A list of loaded tracks.
    :param name: The name of this folder.
        If given, the object only stores tracks that match the folder ``name`` given.
        If None, the list of tracks given are taken to be all the tracks contained in this folder.
    :raises ValueError: If the given tracks contain more than one unique value for ``folder`` when name is None.
    """

    @property
    def folder(self) -> str:
        return self._name

    def __init__(self, tracks: List[LocalTrack], name: Optional[str] = None):
        LocalCollection.__init__(self, tracks=tracks, name=name)
        self._get_times()

        self.artists = set(track.artist for track in self.tracks if track.artist)
        self.albums = set(track.album for track in self.tracks if track.album)
        self.genres = set(genre for track in self.tracks for genre in (track.genres if track.genres else []))

        self.track_total = len(self.tracks)
        # collection is a compilation if over 50% of tracks are marked as compilation
        self.compilation = (sum(track.compilation for track in self.tracks) / len(self.tracks)) > 0.5

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "name": self.folder,
            "artists": self.artists,
            "albums": self.albums,
            "genres": self.genres,
            "track_total": self.track_total,
            "compilation": self.compilation,
            "tracks": self.tracks,
            "last_played": self.last_played,
            "last_added": self.last_added,
            "last_modified": self.last_modified,
        }


class LocalAlbum(Album, LocalCollection):
    """
    Object representing a collection of tracks of an album.

    :param tracks: A list of loaded tracks.
    :param name: The name of this album.
        If given, the object only stores tracks that match the album ``name`` given.
        If None, the list of tracks given are taken to be all the tracks for this album.
    :raises ValueError: If the given tracks contain more than one unique value for ``album`` when name is None.
    """

    @property
    def album(self) -> str:
        return self._name

    def __init__(self, tracks: List[LocalTrack], name: Optional[str] = None):
        LocalCollection.__init__(self, tracks=tracks, name=name)
        self._get_times()

        self.artist = self.list_sep.join(track.artist for track in self.tracks if track.artist)
        self.album_artist = Counter(track.artist for track in self.tracks if track.artist).most_common(1)[0][0]
        self.track_total = len(self.tracks)
        self.genres = set(genre for track in self.tracks for genre in (track.genres if track.genres else []))
        self.year = Counter(track.year for track in self.tracks if track.year).most_common(1)[0][0]
        self.disc_total = max(track.disc_number for track in self.tracks if track.disc_number)
        # collection is a compilation if over 50% of tracks are marked as compilation
        self.compilation = (sum(track.compilation for track in self.tracks) / len(self.tracks)) > 0.5

        self.image_links = {}
        self.has_image = any(track.has_image for track in tracks)

        self.length = sum(track.length for track in self.tracks if track.length)
        self.rating = sum(track.rating for track in self.tracks if track.rating) / len(tracks)

        self.artists = set(track.artist for track in self.tracks if track.artist)

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "name": self.album,
            "artists": self.artists,
            "genres": self.genres,
            "compilation": self.compilation,
            "tracks": self.tracks,
            "last_played": self.last_played,
            "last_added": self.last_added,
            "last_modified": self.last_modified,
        }


class LocalArtist(Artist, LocalCollection):
    """
    Object representing a collection of tracks by a single artist.

    :param tracks: A list of loaded tracks.
    :param name: The name of this artist.
        If given, the object only stores tracks that match the artist ``name`` given.
        If None, the list of tracks given are taken to be all the tracks by this artist.
    :raises ValueError: If the given tracks contain more than one unique value for ``artist`` when name is None.
    """

    @property
    def artist(self) -> str:
        return self._name

    def __init__(self, tracks: List[LocalTrack], name: Optional[str] = None):
        LocalCollection.__init__(self, tracks=tracks, name=name)
        self._get_times()

        self.albums = set(track.album for track in self.tracks if track.album)
        self.genres = set(genre for track in self.tracks for genre in (track.genres if track.genres else []))

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "name": self.artist,
            "albums": self.albums,
            "genres": self.genres,
            "tracks": self.tracks,
            "last_played": self.last_played,
            "last_added": self.last_added,
            "last_modified": self.last_modified,
        }


class LocalGenres(Genre, LocalCollection):
    """
    Object representing a collection of tracks within a genre.

    :param tracks: A list of loaded tracks.
    :param name: The name of this genre.
        If given, the object only stores tracks that match the genre ``name`` given.
        If None, the list of tracks given are taken to be all the tracks within this genre.
    :raises ValueError: If the given tracks contain more than one unique value for ``genre`` when name is None.
    """

    @property
    def genre(self) -> str:
        return self._name

    def __init__(self, tracks: List[LocalTrack], name: Optional[str] = None):
        LocalCollection.__init__(self, tracks=tracks, name=name)
        self.tracks: List[LocalTrack] = [track for track in tracks if name in getattr(track, self._tag_key, [])]
        self._get_times()

        self.artists = set(track.artist for track in self.tracks if track.artist)
        self.albums = set(track.album for track in self.tracks if track.album)
        self.genres = set(genre for track in self.tracks for genre in (track.genres if track.genres else []))

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "name": self.genre,
            "artists": self.artists,
            "albums": self.albums,
            "genres": self.genres,
            "tracks": self.tracks,
            "last_played": self.last_played,
            "last_added": self.last_added,
            "last_modified": self.last_modified,
        }
