from abc import ABCMeta

from syncify.abstract.misc import PrettyPrinter
from syncify.remote.base import Remote, RemoteObject, RemoteItem
from syncify.remote.enums import RemoteObjectType
from syncify.remote.exception import RemoteObjectTypeError
from syncify.spotify import SPOTIFY_SOURCE_NAME


class SpotifyRemote(Remote):
    """Base class for any object concerning Spotify functionality"""

    @property
    def remote_source(self) -> str:
        return SPOTIFY_SOURCE_NAME


class SpotifyObjectMixin(SpotifyRemote, RemoteObject, metaclass=ABCMeta):
    pass


class SpotifyObject(SpotifyObjectMixin, PrettyPrinter, metaclass=ABCMeta):
    """Generic base class for Spotify-stored objects. Extracts key data from a Spotify API JSON response."""

    _url_pad = 71

    @property
    def id(self) -> str:
        """The ID of this item/collection."""
        return self.response["id"]

    @property
    def uri(self) -> str:
        """The URI of this item/collection."""
        return self.response["uri"]

    @property
    def has_uri(self) -> bool:
        """Does this item/collection have a valid URI that is not a local URI."""
        return not self.response.get("is_local", False)

    @property
    def url(self) -> str:
        """The API URL of this item/collection."""
        return self.response["href"]

    @property
    def url_ext(self) -> str | None:
        """The external URL of this item/collection."""
        return self.response["external_urls"].get("spotify")

    def _check_type(self) -> None:
        """
        Checks the given response is compatible with this object type, raises an exception if not.

        :raise RemoteObjectTypeError: When the response type is not compatible with this object.
        """
        kind = self.__class__.__name__.casefold().replace("spotify", "")
        if self.response.get("type") != kind:
            kind = RemoteObjectType.from_name(kind)[0]
            raise RemoteObjectTypeError(f"Response type invalid", kind=kind, value=self.response.get("type"))


class SpotifyItem(SpotifyObject, RemoteItem, metaclass=ABCMeta):
    """Generic base class for Spotify-stored items. Extracts key data from a Spotify API JSON response."""
    pass
