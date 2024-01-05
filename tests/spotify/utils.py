from random import randrange

from syncify.remote.enums import RemoteObjectType, RemoteIDType
from syncify.spotify import URL_API, URL_EXT, SPOTIFY_NAME
from tests.utils import random_str


def random_id() -> str:
    """Generates a valid looking random Spotify ID"""
    return random_str(RemoteIDType.ID.value, RemoteIDType.ID.value)


def random_ids(start: int = 1, stop: int = 50) -> list[str]:
    """Generates many valid looking random Spotify IDs"""
    range_ = randrange(start=start, stop=stop) if start < stop else start
    return [random_id() for _ in range(range_)]


def random_uri(kind: RemoteObjectType = RemoteObjectType.TRACK) -> str:
    """Generates a valid looking random Spotify URI of item :py:class:`RemoteObjectType` ``kind``"""
    return f"{SPOTIFY_NAME.lower()}:{kind.name.lower()}:{random_id()}"


def random_uris(kind: RemoteObjectType = RemoteObjectType.TRACK, start: int = 1, stop: int = 50) -> list[str]:
    """Generates many valid looking random Spotify URIs of item :py:class:`RemoteObjectType` ``kind``"""
    range_ = randrange(start=start, stop=stop) if start < stop else start
    return [random_uri(kind=kind) for _ in range(range_)]


def random_api_url(kind: RemoteObjectType = RemoteObjectType.TRACK) -> str:
    """Generates a valid looking random Spotify API URL of item :py:class:`RemoteObjectType` ``kind``"""
    return f"{URL_API}/{kind.name.lower()}s/{random_id()}"


def random_api_urls(kind: RemoteObjectType = RemoteObjectType.TRACK, start: int = 1, stop: int = 50) -> list[str]:
    """Generates many valid looking random Spotify API URLs of item :py:class:`RemoteObjectType` ``kind``"""
    range_ = randrange(start=start, stop=stop) if start < stop else start
    return [random_api_url(kind=kind) for _ in range(range_)]


def random_ext_url(kind: RemoteObjectType = RemoteObjectType.TRACK) -> str:
    """Generates a valid looking random Spotify external URL of item :py:class:`RemoteObjectType` ``kind``"""
    return f"{URL_EXT}/{kind.name.lower()}/{random_id()}"


def random_ext_urls(kind: RemoteObjectType = RemoteObjectType.TRACK, start: int = 1, stop: int = 50) -> list[str]:
    """Generates many valid looking random Spotify external URLs of item :py:class:`RemoteObjectType` ``kind``"""
    range_ = randrange(start=start, stop=stop) if start < stop else start
    return [random_ext_url(kind=kind) for _ in range(range_)]
