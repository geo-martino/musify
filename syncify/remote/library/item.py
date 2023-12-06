from abc import ABCMeta

from syncify.abstract.item import Track, Artist
from syncify.remote.base import RemoteItem


class RemoteTrack(RemoteItem, Track, metaclass=ABCMeta):
    """Extracts key ``track`` data from a remote API JSON response."""
    pass


class RemoteArtist(RemoteItem, Artist, metaclass=ABCMeta):
    """Extracts key ``artist`` data from a remote API JSON response."""
    pass
