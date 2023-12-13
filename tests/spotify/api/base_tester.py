from collections.abc import Callable
from random import choice, randrange
from urllib.parse import urlparse, parse_qs

from requests_mock.mocker import Mocker

from syncify.remote.enums import RemoteIDType, RemoteItemType
from syncify.spotify.api import SpotifyAPI
from tests.spotify.utils import random_ids, random_id
from tests.utils import random_str


class SpotifyAPITesterHelpers:
    """Helper methods for :py:class:`SpotifyAPI` testers"""

    all_id_types = RemoteIDType.all()

    @staticmethod
    def limit_parameter_limited_test(
            test_function: Callable,
            requests_mock: Mocker,
            floor: int = 1,
            ceil: int = 50,
            **kwargs
    ):
        """Test to ensure the limit value was limited to be within acceptable values."""
        # too small
        test_function(limit=floor - 20, **kwargs)
        params = parse_qs(urlparse(requests_mock.last_request.url).query)
        assert "limit" in params
        assert int(params["limit"][0]) == floor

        # too big
        test_function(limit=ceil + 100, **kwargs)
        params = parse_qs(urlparse(requests_mock.last_request.url).query)
        assert "limit" in params
        assert int(params["limit"][0]) == ceil

    def random_id_type(self, api: SpotifyAPI, kind: RemoteItemType, id_: str = random_id()) -> str:
        """Convert the given ``id_`` to a random ID type"""
        type_in = RemoteIDType.ID
        type_out = choice(self.all_id_types)
        return api.convert(id_, kind=kind, type_in=type_in, type_out=type_out)

    def random_id_types(
            self,
            api: SpotifyAPI,
            kind: RemoteItemType,
            id_list: list[str] | None = None,
            start: int = 1,
            stop: int = 10
    ) -> list[str]:
        """Generate list of random ID types based on input item type"""
        if id_list:
            pass
        elif kind == RemoteItemType.USER:
            id_list = [random_str() for _ in range(randrange(start=start, stop=stop))]
        else:
            id_list = random_ids(start=start, stop=stop)

        return [self.random_id_type(id_=id_, api=api, kind=kind) for id_ in id_list]
