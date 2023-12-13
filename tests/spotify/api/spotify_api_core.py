from requests_mock.mocker import Mocker
from tests.spotify.api.utils import SpotifyTestResponses

from syncify.spotify.api import SpotifyAPI


class SpotifyAPICoreTester:
    """Tester for core endpoints of :py:class:`SpotifyAPI`"""

    @staticmethod
    def test_get_self(api: SpotifyAPI, requests_mock: Mocker):
        url = f"{api.api_url_base}/me"
        expected = SpotifyTestResponses.user()
        requests_mock.get(url=url, status_code=200, json=expected)

        assert api._user_data == {}
        assert api.get_self(update_user_data=False) == expected
        assert api._user_data == {}

        assert api.get_self(update_user_data=True) == expected
        assert api._user_data == expected
