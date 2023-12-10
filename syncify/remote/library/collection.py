from abc import ABCMeta, abstractmethod
from collections.abc import Iterable, MutableSequence
from typing import Self

from syncify.abstract.collection import ItemCollection, Album
from syncify.abstract.item import Item
from syncify.remote.api import APIMethodInputType
from syncify.remote.base import RemoteObject
from syncify.remote.enums import RemoteIDType
from syncify.remote.exception import RemoteIDTypeError
from syncify.remote.library.item import RemoteTrack
from syncify.remote.processors.wrangle import RemoteObjectWranglerMixin


class RemoteCollection[T: RemoteObject](RemoteObjectWranglerMixin, ItemCollection[T], metaclass=ABCMeta):
    """Generic class for storing a collection of remote tracks."""

    @classmethod
    @abstractmethod
    def load(
            cls, value: APIMethodInputType, use_cache: bool = True, items: Iterable[T] = (), *args, **kwargs
    ) -> Self:
        """
        Generate a new object, calling all required endpoints to get a complete set of data for this item type.

        The given ``value`` may be:
            * A string representing a URL/URI/ID.
            * A MutableSequence of strings representing URLs/URIs/IDs of the same type.
            * A remote API JSON response for a collection with a valid ID value under an ``id`` key.
            * A MutableSequence of remote API JSON responses for a collection with
                a valid ID value under an ``id`` key.

        When a list is given, only the first item is processed.

        :param value: The value representing some remote artist. See description for allowed value types.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        :param items: Optionally, give a list of available items to build a response for this collection.
            In doing so, the method will first try to find the API responses for the items of this collection
            in the given list before calling the API for any items not found there.
            This helps reduce the number of API calls made on initialisation.
        """
        raise NotImplementedError

    def __getitem__(self, __key: str | int | slice | Item) -> T | MutableSequence[T, None, None]:
        """
        Returns the item in this collection by matching on a given index/Item/URI/ID/URL.
        If an item is given, the URI is extracted from this item
        and the matching Item from this collection is returned.
        """
        if isinstance(__key, int) or isinstance(__key, slice):  # simply index the list or items
            return self.items[__key]
        elif isinstance(__key, Item):  # take the URI
            if not __key.has_uri or __key.uri is None:
                raise KeyError(f"Given item does not have a URI associated: {__key.name}")
            __key = __key.uri
            key_type = RemoteIDType.URI
        else:  # determine the ID type
            try:
                key_type = self.get_id_type(__key)
            except RemoteIDTypeError:
                try:
                    return next(item for item in self.items if item.name == __key)
                except StopIteration:
                    raise KeyError(f"No matching name found: '{__key}'")

        try:  # get the item based on the ID type
            if key_type == RemoteIDType.URI:
                return next(item for item in self.items if item.uri == __key)
            elif key_type == RemoteIDType.ID:
                return next(item for item in self.items if item.uri.split(":")[2] == __key)
            elif key_type == RemoteIDType.URL:
                __key = self.convert(__key, type_in=RemoteIDType.URL, type_out=RemoteIDType.URI)
                return next(item for item in self.items if item.uri == __key)
            elif key_type == RemoteIDType.URL_EXT:
                __key = self.convert(__key, type_in=RemoteIDType.URL_EXT, type_out=RemoteIDType.URI)
                return next(item for item in self.items if item.uri == __key)
            else:
                raise KeyError(f"ID Type not recognised: '{__key}'")
        except StopIteration:
            raise KeyError(f"No matching {key_type.name} found: '{__key}'")


class RemoteAlbum[T: RemoteTrack](RemoteCollection[T], Album[T], metaclass=ABCMeta):
    """Extracts key ``album`` data from a remote API JSON response."""
    pass
