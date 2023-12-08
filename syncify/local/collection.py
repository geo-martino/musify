import sys
from abc import ABCMeta, abstractmethod
from collections.abc import Mapping, Collection, Iterable, Container
from datetime import datetime
from glob import glob
from os.path import splitext, join, basename, exists, isdir

from syncify.abstract.collection import ItemCollection, Folder, Album, Artist, Genre
from syncify.abstract.item import Item
from syncify.local.base import LocalItem
from syncify.local.exception import LocalCollectionError
from syncify.local.track import load_track, TRACK_FILETYPES
from syncify.local.track.base.track import LocalTrack
from syncify.local.track.base.writer import SyncResultTrack
from syncify.remote.enums import RemoteIDType
from syncify.remote.processors.wrangle import RemoteDataWrangler
from syncify.utils import UnitCollection
from syncify.utils.helpers import get_most_common_values, to_collection
from syncify.utils.logger import Logger, STAT

__max_str = "z" * 50


# noinspection PyShadowingNames
class LocalCollection[T: LocalItem](Logger, ItemCollection[T], metaclass=ABCMeta):
    """
    Generic class for storing a collection of local tracks.

    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on tracks.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
    """

    @property
    def items(self) -> list[LocalTrack]:
        """The tracks in this collection"""
        return self.tracks

    @property
    @abstractmethod
    def tracks(self) -> list[LocalTrack]:
        """The tracks in this collection"""
        raise NotImplementedError

    @property
    def artists(self) -> list[str]:
        """List of artists ordered by frequency of appearance on the tracks in this collection"""
        return get_most_common_values(track.artist for track in self.tracks if track.artist)

    @property
    def track_total(self) -> int:
        """The total number of tracks in this collection"""
        return len(self)

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
        # None condition will only be returned when using dummy tracks in tests therefore not included in typing
        return sort[0].date_modified if sort else None

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

    @property
    def play_count(self) -> int:
        """Total number of plays of all tracks in this collection"""
        return sum(track.play_count for track in self.tracks if track.play_count)

    @property
    def track_paths(self) -> set[str]:
        """Set of all unique track paths in this collection"""
        return {track.path for track in self.tracks}

    def __init__(self, remote_wrangler: RemoteDataWrangler = None):
        super().__init__(remote_wrangler=remote_wrangler)

    def save_tracks(self, **kwargs) -> dict[LocalTrack, SyncResultTrack]:
        """
        Saves the tags of all tracks in this collection. Use arguments from :py:func:`LocalTrack.save`

        :return: A map of the :py:class:`LocalTrack` saved to its result as a :py:class:`SyncResultTrack` object
        """
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

            self.logger.stat(
                f"\33[97m{name} \33[0m| " +
                ("\33[92mSAVED \33[0m| " if result.saved else "\33[91mNOT SAVED \33[0m| ") +
                f"\33[94m{', '.join(tag.name for tag in result.updated.keys())} \33[0m"
            )
        self.print_line(STAT)

    def __getitem__(self, __key: str | int | slice | Item) -> Item | list[T]:
        """
        Returns the item in this collection by matching on a given path/index/URI.
        If an item is given, the URI or path is extracted from this item
        and the matching Item from this collection is returned.
        """
        if isinstance(__key, int) or isinstance(__key, slice):  # simply index the list or items
            return self.items[__key]
        elif isinstance(__key, LocalTrack):  # take the path
            __key = __key.path
        elif isinstance(__key, Item):  # take the URI
            if not __key.has_uri or __key.uri is None:
                raise KeyError(f"Given item does not have a URI associated: {__key.name}")
            __key = __key.uri

        if self.remote_wrangler is None or not self.remote_wrangler.validate_id_type(__key, kind=RemoteIDType.URI):
            # string is not a URI, assume it is a path or name
            if __key in self.track_paths:  # path is valid
                try:
                    return next(track for track in self.tracks if track.path == __key)
                except StopIteration:
                    raise KeyError(f"No matching item found for path: '{__key}'")

            try:  # last try, assume given string is a name
                return next(item for item in self.items if item.name == __key)
            except StopIteration:
                raise KeyError(f"No matching item found for name: '{__key}'")

        try:  # string is a URI
            return next(item for item in self.items if item.uri == __key)
        except StopIteration:
            raise KeyError(f"No matching item found for URI: '{__key}'")

    def as_dict(self):
        return {
            "name": self.name,
            "artists": self.artists,
            "track_total": self.track_total,
            "genres": self.genres,
            "length": self.length,
            "tracks": self.tracks,
            "last_added": self.last_added,
            "last_modified": self.last_modified,
            "last_played": self.last_played,
            "remote_source": self.remote_wrangler.remote_source if self.remote_wrangler else None,
        }


# noinspection PyShadowingNames
class LocalCollectionFiltered[T: LocalItem](LocalCollection[T]):
    """
    Generic class for storing and filtering on a collection of local tracks
    with methods for enriching the attributes of this object from the attributes of the collection of tracks

    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.

    :param tracks: A list of loaded tracks.
    :param name: The name of this collection.
        If given, the object only stores tracks that match the name given on the attribute of this object.
        If None, the list of tracks given are taken to be all the tracks contained in this collection.
    :raise LocalCollectionError: If the given tracks contain more than one unique value
        for the attribute of this collection when name is None.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on tracks.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
    """

    @property
    def name(self):
        """The name of the key property of this collection"""
        return self._name

    @property
    def tracks(self):
        return self._tracks

    def __init__(
            self, tracks: Collection[LocalTrack], name: str | None = None, remote_wrangler: RemoteDataWrangler = None
    ):
        super().__init__(remote_wrangler=remote_wrangler)
        if len(tracks) == 0:
            raise LocalCollectionError("No tracks were given")

        # get the tag key dynamically from the name of this class
        self._tag_key = self._pascal_to_snake(self.__class__.__name__.replace("Local", ""))

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

    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.

    :param tracks: A list of loaded tracks.
    :param name: The name of this folder.
        If given, the object only stores tracks that match the folder ``name`` given.
        If None, the list of tracks given are taken to be all the tracks contained in this folder.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on tracks.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
    :raise LocalCollectionError: If the given tracks contain more than one unique value for
        ``folder`` when name is None.
    """

    @property
    def albums(self):
        return get_most_common_values(track.album for track in self.tracks if track.album)

    @property
    def compilation(self):
        """Collection is a compilation if over 50% of tracks are marked as compilation"""
        return (sum(track.compilation is True for track in self.tracks) / len(self.tracks)) > 0.5

    def __init__(
            self,
            tracks: Collection[LocalTrack] = (),
            name: str | None = None,
            remote_wrangler: RemoteDataWrangler = None
    ):
        if len(tracks) == 0 and name is not None and exists(name) and isdir(name):
            # name is path to a folder, load tracks in that folder
            tracks = [load_track(path) for path in glob(join(name, "*")) if splitext(path)[1] in TRACK_FILETYPES]
            name = basename(name)
        super().__init__(tracks=tracks, name=name, remote_wrangler=remote_wrangler)
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
            "last_added": self.last_added,
            "last_modified": self.last_modified,
            "last_played": self.last_played,
            "remote_source": self.remote_wrangler.remote_source if self.remote_wrangler else None,
        }


class LocalAlbum(LocalCollectionFiltered[LocalTrack], Album[LocalTrack]):
    """
    Object representing a collection of tracks of an album.

    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.

    :param tracks: A list of loaded tracks.
    :param name: The name of this album.
        If given, the object only stores tracks that match the album ``name`` given.
        If None, the list of tracks given are taken to be all the tracks for this album.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on tracks.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
    :raise LocalCollectionError: If the given tracks contain more than one unique value for
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

    def __init__(
            self, tracks: Collection[LocalTrack], name: str | None = None, remote_wrangler: RemoteDataWrangler = None
    ):
        super().__init__(tracks=tracks, name=name, remote_wrangler=remote_wrangler)
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
            "last_added": self.last_added,
            "last_modified": self.last_modified,
            "last_played": self.last_played,
            "remote_source": self.remote_wrangler.remote_source if self.remote_wrangler else None,
        }


class LocalArtist(LocalCollectionFiltered[LocalTrack], Artist[LocalTrack]):
    """
    Object representing a collection of tracks by a single artist.

    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.

    :param tracks: A list of loaded tracks.
    :param name: The name of this artist.
        If given, the object only stores tracks that match the artist ``name`` given.
        If None, the list of tracks given are taken to be all the tracks by this artist.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on tracks.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
    :raise LocalCollectionError: If the given tracks contain more than one unique value for
        ``artist`` when name is None.
    """

    @property
    def albums(self):
        return get_most_common_values(track.album for track in self.tracks if track.album)

    @property
    def rating(self) -> float | None:
        """Average rating of all tracks by this artist"""
        ratings = tuple(track.rating for track in self.tracks)
        return sum(ratings) / len(ratings) if ratings else None

    def __init__(
            self, tracks: Collection[LocalTrack], name: str | None = None, remote_wrangler: RemoteDataWrangler = None
    ):
        super().__init__(tracks=tracks, name=name, remote_wrangler=remote_wrangler)
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
            "last_added": self.last_added,
            "last_modified": self.last_modified,
            "last_played": self.last_played,
            "remote_source": self.remote_wrangler.remote_source if self.remote_wrangler else None,
        }


class LocalGenres(LocalCollectionFiltered[LocalTrack], Genre[LocalTrack]):
    """
    Object representing a collection of tracks within a genre.

    :ivar tag_sep: When representing a list of tags as a string, use this value as the separator.

    :param tracks: A list of loaded tracks.
    :param name: The name of this genre.
        If given, the object only stores tracks that match the genre ``name`` given.
        If None, the list of tracks given are taken to be all the tracks within this genre.
    :param remote_wrangler: Optionally, provide a RemoteDataWrangler object for processing URIs on tracks.
        If given, the wrangler can be used when calling __get_item__ to get an item from the collection from its URI.
    :raise LocalCollectionError: If the given tracks contain more than one unique value for
        ``genre`` when name is None.
    """

    @property
    def albums(self):
        return get_most_common_values(track.album for track in self.tracks if track.album)

    def __init__(
            self, tracks: Collection[LocalTrack], name: str | None = None, remote_wrangler: RemoteDataWrangler = None
    ):
        super().__init__(tracks=tracks, name=name, remote_wrangler=remote_wrangler)
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
            "last_added": self.last_added,
            "last_modified": self.last_modified,
            "last_played": self.last_played,
            "remote_source": self.remote_wrangler.remote_source if self.remote_wrangler else None,
        }
