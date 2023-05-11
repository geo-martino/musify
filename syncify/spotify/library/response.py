from abc import abstractmethod
from typing import Any, MutableMapping

from syncify.spotify.api import API
from syncify.utils_new.generic import PrettyPrinter


class SpotifyResponse(PrettyPrinter):
    _list_sep = "; "
    _url_pad = 69

    api: API

    def __init__(self, response: MutableMapping[str, Any]):
        self.response = response
        self._check_type()

        self.id: str = response["id"]
        self.uri: str = response["uri"]
        self.has_uri: bool = True

        self.url: str = response["href"]
        self.url_ext: str = response["external_urls"]["spotify"]

    def _check_type(self) -> None:
        kind = self.__class__.__name__.lower().replace("spotify", "")
        if self.response.get("type") != kind:
            raise ValueError(f"Response is not of type '{kind}': {self.response.get('type')}")

    @classmethod
    def _check_for_api(cls):
        if cls.api is None:
            raise ValueError("API is not set. Assign an API to the SpotifyResponse class first.")

    @abstractmethod
    def reload(self, use_cache: bool = True) -> None:
        raise NotImplementedError

    def replace(self, response: MutableMapping[str, Any]) -> None:
        self.__init__(response)

    def as_dict(self) -> MutableMapping[str, Any]:
        """Return a dictionary representation of the tags/metadata for this response type."""
        return {k: v for k, v in self.__dict__.items() if k != "response"}
