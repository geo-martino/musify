from abc import ABCMeta
from datetime import datetime
from typing import List, MutableMapping, Any, Optional, Callable, Mapping

from syncify.abstract.collection import ItemCollection, Folder, Album, Artist, Genre
from syncify.local.track import LocalTrack, SyncResultTrack
from syncify.utils import Logger, get_most_common_values


class LocalCollection(ItemCollection, Logger, metaclass=ABCMeta):
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

    @property
    def length(self) -> Optional[float]:
        if len(self.tracks) > 0:
            return sum(track.length for track in self.tracks)

    @property
    def last_played(self) -> Optional[datetime]:
        if len(self.tracks) > 0:
            key: Callable = lambda t: (t.last_played is None, t.last_played)
            return sorted(self.tracks, key=key, reverse=True)[0].last_played

    @property
    def last_added(self) -> Optional[datetime]:
        if len(self.tracks) > 0:
            key: Callable = lambda t: (t.date_added is None, t.date_added)
            return sorted(self.tracks, key=key, reverse=True)[0].date_added

    @property
    def last_modified(self) -> Optional[datetime]:
        if len(self.tracks) > 0:
            key: Callable = lambda t: (t.date_modified is None, t.date_modified)
            return sorted(self.tracks, key=key, reverse=True)[0].date_modified

    def __init__(self, tracks: List[LocalTrack], name: Optional[str] = None):
        Logger.__init__(self)
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

    def save_tracks(self, **kwargs) -> Mapping[str, SyncResultTrack]:
        """Saves the tags of all tracks in this collection. Use arguments from :py:func:`LocalTrack.save()`"""
        bar = self.get_progress_bar(iterable=self.tracks, desc="Updating tracks", unit="tracks")
        return {track.path: track.save(**kwargs) for track in bar}

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

    @folder.setter
    def folder(self, value: str):
        self._name = value

    def __init__(self, tracks: List[LocalTrack], name: Optional[str] = None):
        LocalCollection.__init__(self, tracks=tracks, name=name)

        self.tracks.sort(key=lambda x: x.filename)
        self.artists = get_most_common_values(track.artist for track in self.tracks if track.artist)
        self.albums = get_most_common_values(track.album for track in self.tracks if track.album)
        genres = (genre for track in self.tracks for genre in (track.genres if track.genres else []))
        self.genres = get_most_common_values(genres)

        self.track_total = len(self.tracks)
        # collection is a compilation if over 50% of tracks are marked as compilation
        self.compilation = (sum(track.compilation is True for track in self.tracks) / len(self.tracks)) > 0.5

    def set_compilation_tags(self) -> None:
        """
        Modify tags for tracks in the folders of this library.

        The following steps are applied to all folders:

        * Set compilation to True if folder is a compilation, False otherwise

        The following steps are also applied to all compilation folders:

        * Set album name to folder name
        * Set album artist to 'Various'
        * Set track_number in ascending order by filename
        * Set disc_number to 1
        """

        count = 0
        if self.compilation:
            tracks = sorted(self.tracks, key=lambda x: x.path)

            for i, track in enumerate(tracks, 1):  # set tags
                track.album = track.folder
                track.album_artist = "Various"
                track.track_number = i
                track.disc_number = 1
                track.compilation = True
                count += 1
        else:
            for track in self.tracks:  # set tags
                track.compilation = False
                count += 1

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "name": self.folder,
            "artists": self.artists,
            "albums": self.albums,
            "genres": self.genres,
            "track_total": self.track_total,
            "compilation": self.compilation,
            "length": self.length,
            "tracks": self.tracks,
            "last_played": self.last_played,
            "last_added": self.last_added,
            "last_modified": self.last_modified,
        }

    def __hash__(self):
        return hash((self.name, (item for item in self.items)))


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

    @album.setter
    def album(self, value: str):
        self._name = value

    def __init__(self, tracks: List[LocalTrack], name: Optional[str] = None):
        LocalCollection.__init__(self, tracks=tracks, name=name)

        self.tracks.sort(key=lambda x: x.track_number)
        self.artists = get_most_common_values(track.artist for track in self.tracks if track.artist)
        self.artist = self.list_sep.join(self.artists)
        self.album_artist = self.artists[0] if self.artists else None
        self.track_total = len(self.tracks)
        genres = (genre for track in self.tracks for genre in (track.genres if track.genres else []))
        self.genres = get_most_common_values(genres)
        years = get_most_common_values(track.year for track in self.tracks if track.year)
        self.year = years[0] if years else None
        self.disc_total = max(track.disc_number for track in self.tracks if track.disc_number)
        # collection is a compilation if over 50% of tracks are marked as compilation
        self.compilation = (sum(track.compilation is True for track in self.tracks) / len(self.tracks)) > 0.5

        self.image_links = {}
        self.has_image = any(track.has_image for track in tracks)

        self.rating = sum(track.rating for track in self.tracks if track.rating) / len(tracks)

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "name": self.album,
            "artists": self.artists,
            "genres": self.genres,
            "compilation": self.compilation,
            "length": self.length,
            "tracks": self.tracks,
            "last_played": self.last_played,
            "last_added": self.last_added,
            "last_modified": self.last_modified,
        }

    def __hash__(self):
        return hash((self.name, (item for item in self.items)))


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

    @artist.setter
    def artist(self, value: str):
        self._name = value

    def __init__(self, tracks: List[LocalTrack], name: Optional[str] = None):
        LocalCollection.__init__(self, tracks=tracks, name=name)

        self.tracks.sort(key=lambda x: (x.artist, x.album, x.track_number))
        self.albums = get_most_common_values(track.album for track in self.tracks if track.album)
        genres = (genre for track in self.tracks for genre in (track.genres if track.genres else []))
        self.genres = get_most_common_values(genres)

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "name": self.artist,
            "albums": self.albums,
            "genres": self.genres,
            "length": self.length,
            "tracks": self.tracks,
            "last_played": self.last_played,
            "last_added": self.last_added,
            "last_modified": self.last_modified,
        }

    def __hash__(self):
        return hash((self.name, (item for item in self.items)))


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

    @genre.setter
    def genre(self, value: str):
        self._name = value

    def __init__(self, tracks: List[LocalTrack], name: Optional[str] = None):
        LocalCollection.__init__(self, tracks=tracks, name=name)
        self.tracks: List[LocalTrack] = [track for track in tracks if name in getattr(track, self._tag_key, [])]

        self.tracks.sort(key=lambda x: (x.genres, x.artist, x.track_number))
        self.artists = get_most_common_values(track.artist for track in self.tracks if track.artist)
        self.albums = get_most_common_values(track.album for track in self.tracks if track.album)
        genres = (genre for track in self.tracks for genre in (track.genres if track.genres else []))
        self.genres = get_most_common_values(genres)

    def as_dict(self) -> MutableMapping[str, Any]:
        return {
            "name": self.genre,
            "artists": self.artists,
            "albums": self.albums,
            "genres": self.genres,
            "length": self.length,
            "tracks": self.tracks,
            "last_played": self.last_played,
            "last_added": self.last_added,
            "last_modified": self.last_modified,
        }

    def __hash__(self):
        return hash((self.name, (item for item in self.items)))
