from abc import ABCMeta

from syncify.abstract.misc import PrettyPrinter
from syncify.remote.enums import RemoteObjectType
from syncify.remote.exception import RemoteObjectTypeError
from syncify.remote.library.object import RemoteObject
from syncify.spotify.api import SpotifyAPI
from syncify.spotify.base import SpotifyRemote


class SpotifyObjectMixin(RemoteObject, SpotifyRemote, metaclass=ABCMeta):
    pass


class SpotifyObject(SpotifyObjectMixin, PrettyPrinter, metaclass=ABCMeta):
    """
    Generic base class for Spotify-stored objects. Extracts key data from a Spotify API JSON response.

    :ivar api: The instantiated and authorised :py:class:`SpotifyAPI` object for this source type.
    """

    _url_pad = 71
    api: SpotifyAPI

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
