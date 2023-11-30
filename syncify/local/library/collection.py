import sys
from abc import ABCMeta, abstractmethod
from collections.abc import Mapping, Collection, Iterable, Container
from datetime import datetime

from syncify.abstract.collection import ItemCollection, Folder, Album, Artist, Genre
from syncify.abstract.item import Item
from syncify.local.base import LocalObject
from syncify.local.exception import LocalCollectionError
from syncify.local.track.base.track import LocalTrack
from syncify.local.track.base.writer import SyncResultTrack
from syncify.spotify.enums import IDType
from syncify.spotify.utils import validate_id_type
from syncify.utils import UnitCollection
from syncify.utils.helpers import get_most_common_values, to_collection
from syncify.utils.logger import Logger, STAT

__max_str = "z" * 50


# noinspection PyShadowingNames
class LocalCollection[T: LocalObject](ItemCollection[T], Logger, metaclass=ABCMeta):
    """Generic class for storing a collection of local tracks."""

    @property
    @abstractmethod
    def tracks(self):
        """The tracks in this collection"""
        raise NotImplementedError

    @property
    def items(self):
        """The tracks in this collection"""
        return self.tracks

    @property
    def track_paths(self) -> set[str]:
        """Set of all unique track paths in this collection"""
        return {track.path for track in self.tracks}

    @property
    def artists(self) -> list[str]:
        """List of artists ordered by frequency of appearance on the tracks in this collection"""
        return get_most_common_values(track.artist for track in self.tracks if track.artist)

    @property
    def genres(self) -> list[str]:
        """List of genres ordered by frequency of appearance on the tracks in this collection"""
        genres = (genre for track in self.tracks for genre in (track.genres if track.genres else []))
        return get_most_common_values(genres)

    @property
    def length(self) -> float | None:
        """Total duration of all tracks in this collection in seconds"""
        lengths = {track.length for track in self.tracks}
        return sum(lengths) if lengths else None

    @property
    def last_modified(self) -> datetime:
        """Timestamp of the last modified track in this collection"""
        sort = sorted(filter(lambda t: t.date_modified, self.tracks), key=lambda t: t.date_modified, reverse=True)
        return sort[0].date_modified

    @property
    def last_added(self) -> datetime | None:
        """Timestamp of the track last added to the library in this collection"""
        sort = sorted(filter(lambda t: t.date_added, self.tracks), key=lambda t: t.date_added, reverse=True)
        return sort[0].date_added if sort else None

    @property
    def last_played(self) -> datetime | None:
        """Timestamp of the last played track in this collection"""
        sort = sorted(filter(lambda t: t.last_played, self.tracks), key=lambda t: t.last_played, reverse=True)
        return sort[0].last_played if sort else None

    def save_tracks(self, **kwargs) -> dict[LocalTrack, SyncResultTrack]:
        """Saves the tags of all tracks in this collection. Use arguments from :py:func:`LocalTrack.save()`"""
        bar = self.get_progress_bar(iterable=self.tracks, desc="Updating tracks", unit="tracks")
        results: dict[LocalTrack, SyncResultTrack] = {track: track.save(**kwargs) for track in bar}
        results_filtered = {track: result for track, result in results.items() if result.updated}

        return results_filtered

    def log_save_tracks(self, results: Mapping[LocalTrack, SyncResultTrack]) -> None:
        """Log stats from the results of a ``save_tracks`` operation"""
        if not results:
            return

        max_width = self.get_max_width([track.path for track in results], max_width=80)

        self.logger.stat("\33[1;96mSaved tags to the following tracks: \33[0m")
        for track, result in results.items():
            name = self.align_and_truncate(track.path, max_width=max_width, right_align=True)
            updated = tuple(t for tag in result.updated.keys() for t in tag.to_tag())

            self.logger.stat(
                f"\33[97m{name} \33[0m| " +
                ("\33[92mSAVED \33[0m| " if result.saved else "\33[91mNOT SAVED \33[0m| ") +
                f"\33[94m{', '.join(updated)} \33[0m"
            )
        self.print_line(STAT)

    def as_dict(self):
        return {
            "name": self.name,
            "artists": self.artists,
            "track_total": self.track_total,
            "genres": self.genres,
            "length": self.length,
            "tracks": self.tracks,
            "last_modified": self.last_modified,
            "last_added": self.last_added,
            "last_played": self.last_played,
        }

    def __getitem__(self, __key: str | int | Item) -> Item:
        """
        Returns the item in this collection by matching on a given path/index/URI.
        If an item is given, the URI or path is extracted from this item.
        """
        if isinstance(__key, int):  # simply index the list or items
            return self.items[__key]
        elif isinstance(__key, LocalTrack):  # take the path
            __key = __key.path
        elif isinstance(__key, Item):  # take the URI
            if not __key.has_uri or __key.uri is None:
                raise KeyError(f"Given item does not have a URI associated: {__key.name}")
            __key = __key.uri

        if not validate_id_type(__key, kind=IDType.URI):  # string is not a URI, assume it is a path or name
            if __key in self.track_paths:  # path is valid
                return next(track for track in self.tracks if track.path == __key)

            try:  # last try, assume given string is a name
                return next(item for item in self.items if item.name == __key)
            except StopIteration:
                raise KeyError(f"No matching name found: '{__key}'")

        try:  # string is a URI
            return next(item for item in self.items if item.uri == __key)
        except StopIteration:
            raise KeyError(f"No matching URI found: '{__key}'")


# noinspection PyShadowingNames
class LocalCollectionFiltered[T: LocalObject](LocalCollection[T]):
    """
    Generic class for storing and filtering on a collection of local tracks
    with methods for enriching the attributes of this object from the attributes of the collection of tracks

    :param tracks: A list of loaded tracks.
    :param name: The name of this collection.
        If given, the object only stores tracks that match the name given on the attribute of this object.
        If None, the list of tracks given are taken to be all the tracks contained in this collection.
    :raises LocalCollectionError: If the given tracks contain more than one unique value
        for the attribute of this collection when name is None.
    """

    @property
    def name(self):
        """The name of the key property of this collection"""
        return self._name

    @property
    def tracks(self):
        return self._tracks

    def __init__(self, tracks: Collection[LocalTrack], name: str | None = None):
        LocalCollection.__init__(self)
        if len(tracks) == 0:
            raise LocalCollectionError("No tracks were given")

        # get the tag key dynamically from the name of this class
        self._tag_key = self._camel_to_snake(self.__class__.__name__.replace("Local", ""))

        if name is None:  # attempt to determine the name of this collection from the given tracks
            names: list[UnitCollection[str]] = [track[self._tag_key] for track in tracks if track[self._tag_key]]
            names: set[str] = {(n for n in name) if isinstance(name, (list, set, tuple)) else name for name in names}

            if len(names) == 0:  # no valid name found
                raise LocalCollectionError(f"No {self._tag_key.rstrip('s')}s found in the given tracks")
            if len(names) != 1:  # too many names found
                raise LocalCollectionError(
                    f"Too many {self._tag_key.rstrip('s')}s found in the given tracks."
                    f" Only provide tracks from the same {self._tag_key.rstrip('s')}."
                )

            self._name: str = names.pop()
            self._tracks: list[LocalTrack] = to_collection(tracks, list)
        else:  # match tracks with a tag equal to the given name for this collection
            self._name: str = name
            self._tracks: list[LocalTrack] = self._get_matching_tracks(tracks)

    def _get_matching_tracks(self, tracks: Iterable[LocalTrack]) -> list[LocalTrack]:
        """Get a list of tracks that match this collection's name"""
        matched: list[LocalTrack] = []
        for track in tracks:
            value = track[self._tag_key]
            if isinstance(value, str) and self.name == value:
                matched.append(track)
            elif isinstance(value, Container) and self.name in value:
                matched.append(track)

        return matched


class LocalFolder(LocalCollectionFiltered[LocalTrack], Folder[LocalTrack]):
    """
    Object representing a collection of tracks in a folder on the local drive

    :param tracks: A list of loaded tracks.
    :param name: The name of this folder.
        If given, the object only stores tracks that match the folder ``name`` given.
        If None, the list of tracks given are taken to be all the tracks contained in this folder.
    :raises LocalCollectionError: If the given tracks contain more than one unique value for
        ``folder`` when name is None.
    """

    @property
    def albums(self):
        return get_most_common_values(track.album for track in self.tracks if track.album)

    @property
    def compilation(self):
        """Collection is a compilation if over 50% of tracks are marked as compilation"""
        return (sum(track.compilation is True for track in self.tracks) / len(self.tracks)) > 0.5

    def __init__(self, tracks: Collection[LocalTrack], name: str | None = None):
        LocalCollectionFiltered.__init__(self, tracks=tracks, name=name)
        self.tracks.sort(key=lambda x: x.filename or __max_str)

    def set_compilation_tags(self) -> None:
        """
        Modify tags for tracks in the folders of this library.

        The following steps are applied to all non-compilation folders:

        * Set compilation to False

        The following steps are applied to all compilation folders:

        * Set album name to folder name
        * Set album artist to 'Various'
        * Set track_number in ascending order by filename
        * Set track_total to the number of tracks in the folder
        * Set disc_number to 1
        * Set disc_total to 1
        * Set compilation to True
        """

        count = 0
        if self.compilation:
            tracks = sorted(self.tracks, key=lambda x: x.path)

            for i, track in enumerate(tracks, 1):  # set tags
                track.album = track.folder
                track.album_artist = "Various"
                track.track_number = i
                track.track_total = len(tracks)
                track.disc_number = 1
                track.disc_total = 1
                track.compilation = True
                count += 1
        else:
            for track in self.tracks:  # set tags
                track.compilation = False
                count += 1

    def as_dict(self):
        return {
            "name": self.folder,
            "artists": self.artists,
            "albums": self.albums,
            "track_total": self.track_total,
            "genres": self.genres,
            "compilation": self.compilation,
            "length": self.length,
            "tracks": self.tracks,
            "last_modified": self.last_modified,
            "last_added": self.last_added,
            "last_played": self.last_played,
        }


class LocalAlbum(LocalCollectionFiltered[LocalTrack], Album[LocalTrack]):
    """
    Object representing a collection of tracks of an album.

    :param tracks: A list of loaded tracks.
    :param name: The name of this album.
        If given, the object only stores tracks that match the album ``name`` given.
        If None, the list of tracks given are taken to be all the tracks for this album.
    :raises LocalCollectionError: If the given tracks contain more than one unique value for
        ``album`` when name is None.
    """

    @property
    def album_artist(self):
        """The most common artist in this collection"""
        return self.artists[0] if self.artists else None

    @property
    def year(self):
        """The most common year in this collection"""
        years = get_most_common_values(track.year for track in self.tracks if track.year)
        return years[0] if years else None

    @property
    def compilation(self):
        """Collection is a compilation if over 50% of tracks are marked as compilation"""
        return (sum(track.compilation is True for track in self.tracks) / len(self.tracks)) > 0.5

    @property
    def image_links(self):
        return self._image_links

    @property
    def has_image(self):
        return any(track.has_image for track in self.tracks)

    @property
    def rating(self):
        """Average rating of all tracks in this collection"""
        ratings = {track.rating for track in self.tracks if track.rating}
        return sum(ratings) / len(ratings) if ratings else None

    def __init__(self, tracks: Collection[LocalTrack], name: str | None = None):
        LocalCollectionFiltered.__init__(self, tracks=tracks, name=name)
        self.tracks.sort(
            key=lambda x: (x.disc_number or sys.maxsize, x.track_number or sys.maxsize, x.filename or __max_str)
        )
        self._image_links: dict[str, str] = {}

    def as_dict(self):
        return {
            "name": self.album,
            "artists": self.artists,
            "album_artist": self.album_artist,
            "genres": self.genres,
            "year": self.year,
            "compilation": self.compilation,
            "image_links": self.image_links,
            "has_image": self.has_image,
            "length": self.length,
            "rating": self.rating,
            "tracks": self.tracks,
            "last_played": self.last_played,
            "last_added": self.last_added,
            "last_modified": self.last_modified,
        }


class LocalArtist(LocalCollectionFiltered[LocalTrack], Artist[LocalTrack]):
    """
    Object representing a collection of tracks by a single artist.

    :param tracks: A list of loaded tracks.
    :param name: The name of this artist.
        If given, the object only stores tracks that match the artist ``name`` given.
        If None, the list of tracks given are taken to be all the tracks by this artist.
    :raises LocalCollectionError: If the given tracks contain more than one unique value for
        ``artist`` when name is None.
    """

    @property
    def albums(self):
        return get_most_common_values(track.album for track in self.tracks if track.album)

    def __init__(self, tracks: Collection[LocalTrack], name: str | None = None):
        LocalCollectionFiltered.__init__(self, tracks=tracks, name=name)
        self.tracks.sort(
            key=lambda x: (x.album or __max_str,
                           x.disc_number or sys.maxsize,
                           x.track_number or sys.maxsize,
                           x.filename or __max_str)
        )

    def as_dict(self):
        return {
            "name": self.artist,
            "artists": self.artists,
            "genres": self.genres,
            "length": self.length,
            "rating": self.rating,
            "tracks": self.tracks,
            "last_played": self.last_played,
            "last_added": self.last_added,
            "last_modified": self.last_modified,
        }


class LocalGenres(LocalCollectionFiltered[LocalTrack], Genre[LocalTrack]):
    """
    Object representing a collection of tracks within a genre.

    :param tracks: A list of loaded tracks.
    :param name: The name of this genre.
        If given, the object only stores tracks that match the genre ``name`` given.
        If None, the list of tracks given are taken to be all the tracks within this genre.
    :raises LocalCollectionError: If the given tracks contain more than one unique value for
        ``genre`` when name is None.
    """

    @property
    def albums(self):
        return get_most_common_values(track.album for track in self.tracks if track.album)

    def __init__(self, tracks: Collection[LocalTrack], name: str | None = None):
        LocalCollectionFiltered.__init__(self, tracks=tracks, name=name)
        self.tracks.sort(
            key=lambda x: (x.artist or __max_str,
                           x.album or __max_str,
                           x.disc_number or sys.maxsize,
                           x.track_number or sys.maxsize,
                           x.filename or __max_str)
        )

    def as_dict(self):
        return {
            "name": self.genre,
            "artists": self.artists,
            "genres": self.genres,
            "length": self.length,
            "tracks": self.tracks,
            "last_played": self.last_played,
            "last_added": self.last_added,
            "last_modified": self.last_modified,
        }
