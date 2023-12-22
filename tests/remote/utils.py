from abc import abstractmethod
from collections.abc import Iterable, Mapping
from random import choice, randrange
from typing import Any
from urllib.parse import parse_qs

from requests_mock import Mocker
# noinspection PyProtectedMember
from requests_mock.request import _RequestObjectProxy as Request

from syncify.remote.enums import RemoteIDType, RemoteObjectType
from syncify.remote.processors.wrangle import RemoteDataWrangler
from tests.spotify.utils import random_id, random_ids
from tests.utils import random_str

ALL_ID_TYPES = RemoteIDType.all()
ALL_ITEM_TYPES = RemoteObjectType.all()


def random_id_type(wrangler: RemoteDataWrangler, kind: RemoteObjectType, id_: str = random_id()) -> str:
    """Convert the given ``id_`` to a random ID type"""
    type_in = RemoteIDType.ID
    type_out = choice(ALL_ID_TYPES)
    return wrangler.convert(id_, kind=kind, type_in=type_in, type_out=type_out)


def random_id_types(
        wrangler: RemoteDataWrangler,
        kind: RemoteObjectType,
        id_list: Iterable[str] | None = None,
        start: int = 1,
        stop: int = 10
) -> list[str]:
    """Generate list of random ID types based on input item type"""
    if id_list:
        pass
    elif kind == RemoteObjectType.USER:
        id_list = [random_str() for _ in range(randrange(start=start, stop=stop))]
    else:
        id_list = random_ids(start=start, stop=stop)

    return [random_id_type(id_=id_, wrangler=wrangler, kind=kind) for id_ in id_list]


class RemoteMock(Mocker):
    """Generates responses and sets up Remote API requests mock"""

    @property
    @abstractmethod
    def item_type_map(self) -> dict[RemoteObjectType, list[dict[str, Any]]]:
        """Map of :py:class:`RemoteObjectType` to the mocked items mapped as {``id``: <item>}"""
        raise NotImplementedError

    @property
    @abstractmethod
    def item_type_map_user(self) -> dict[RemoteObjectType, list[dict[str, Any]]]:
        """Map of :py:class:`RemoteObjectType` to the mocked user items mapped as {``id``: <item>}"""
        raise NotImplementedError

    @staticmethod
    def calculate_pages(limit: int, total: int) -> int:
        """
        Calculates the numbers of a pages that need to be called from a given ``total`` and ``limit`` per page
        to get all items related to this response.
        """
        pages = total / limit
        return int(pages) + (pages % 1 > 0)  # round up

    @abstractmethod
    def calculate_pages_from_response(self, response: Mapping[str, Any]) -> int:
        """
        Calculates the numbers of a pages that need to be called for a given ``response``
        to get all items related to this response.
        """
        raise NotImplementedError

    def get_requests(
            self,
            url: str | None = None,
            method: str | None = None,
            params: dict[str, Any] | None = None,
            response: dict[str, Any] | None = None
    ) -> list[Request]:
        """Get a get request from the history from the given URL and params"""
        requests = []
        for request in self.request_history:
            match_url = url is None
            if not match_url:
                match_url = url.strip("/").endswith(request.path.strip("/"))

            match_method = method is None
            if not match_method:
                # noinspection PyProtectedMember
                match_method = request._request.method.upper() == method.upper()

            match_params = params is None
            if not match_params and request.query:
                for k, v in parse_qs(request.query).items():
                    if k in params and str(params[k]) != v[0]:
                        break
                    match_params = True

            match_response = response is None
            if not match_response and request.body:
                for k, v in request.json().items():
                    if k in response and str(response[k]) != str(v):
                        break
                    match_response = True

            if match_url and match_method and match_params and match_response:
                requests.append(request)

        return requests

