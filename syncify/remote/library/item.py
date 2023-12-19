from abc import ABCMeta

from syncify.abstract.item import Item, Track, Artist
from syncify.remote.library.object import RemoteObject
from syncify.remote.processors.wrangle import RemoteDataWrangler


class RemoteItem(RemoteObject, Item, metaclass=ABCMeta):
    """Generic base class for remote items. Extracts key data from a remote API JSON response."""
    pass


class RemoteItemWranglerMixin[T: RemoteObject](RemoteItem, RemoteDataWrangler, metaclass=ABCMeta):
    pass


class RemoteArtist(RemoteItemWranglerMixin, Artist, metaclass=ABCMeta):
    """Extracts key ``artist`` data from a remote API JSON response."""
    pass


class RemoteTrack(RemoteItemWranglerMixin, Track, metaclass=ABCMeta):
    """Extracts key ``track`` data from a remote API JSON response."""
    pass
