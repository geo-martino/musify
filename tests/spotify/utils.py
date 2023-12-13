from syncify.remote.enums import RemoteItemType, RemoteIDType
from syncify.spotify import URL_API, URL_EXT, SPOTIFY_SOURCE_NAME

from tests.utils import random_str


def random_id() -> str:
    """Generates a valid looking random Spotify ID of item"""
    return random_str(RemoteIDType.ID.value, RemoteIDType.ID.value + 1)


def random_uri(kind: RemoteItemType = RemoteItemType.TRACK) -> str:
    """Generates a valid looking random Spotify URI of item :py:class:`RemoteItemType` ``kind``"""
    return f"{SPOTIFY_SOURCE_NAME.lower()}:{kind.name.lower()}:{random_id()}"


def random_api_url(kind: RemoteItemType = RemoteItemType.TRACK) -> str:
    """Generates a valid looking random Spotify API URL of item :py:class:`RemoteItemType` ``kind``"""
    return f"{URL_API}/{kind.name.lower()}/{random_id()}"


def random_ext_url(kind: RemoteItemType = RemoteItemType.TRACK) -> str:
    """Generates a valid looking random Spotify external URL of item :py:class:`RemoteItemType` ``kind``"""
    return f"{URL_EXT}/{kind.name.lower()}/{random_id()}"
