from abc import ABCMeta

from syncify.abstract.item import Track, Artist
from syncify.remote.library.base import RemoteItemWranglerMixin


class RemoteArtist(RemoteItemWranglerMixin, Artist, metaclass=ABCMeta):
    """Extracts key ``artist`` data from a remote API JSON response."""
    pass


class RemoteTrack(RemoteItemWranglerMixin, Track, metaclass=ABCMeta):
    """Extracts key ``track`` data from a remote API JSON response."""
    pass
