from __future__ import annotations

from enum import Enum, IntEnum
from typing import List, Optional, Union, Set

from utils_new.helpers import make_list


__UNAVAILABLE_URI_VALUE__ = "spotify:track:unavailable"


class URIType(IntEnum):
    ALL = 0
    PLAYLIST = 1
    TRACK = 2
    ALBUM = 3
    ARTIST = 4
    USER = 5
    SHOW = 6
    EPISODE = 7

    @classmethod
    def all(cls) -> Set[SpotifyType]:
        all_enums = set(cls)
        all_enums.remove(cls.ALL)
        return all_enums


class SpotifyType(Enum):
    OPEN_URL: str = "https://open.spotify.com"
    API_URL: str = "https://api.spotify.com/v1"
    URI: int = 3
    ID: int = 22

    ALL: int = 0

    @classmethod
    def all(cls) -> Set[SpotifyType]:
        all_enums = set(cls)
        all_enums.remove(cls.ALL)
        return all_enums


def check_spotify_type(
        value: str, types: Union[SpotifyType, List[SpotifyType]] = SpotifyType.ALL
) -> Optional[SpotifyType]:
    """
    Check that the given value is of a valid Spotify type.

    :param value: URL/URI/ID to check.
    :param types: Spotify types to check for. None checks all.
    :return: The Spotify type if value is valid, None if invalid.
    """
    if not isinstance(value, str):
        return

    types: Set[SpotifyType] = set(make_list(types))
    if SpotifyType.ALL in types:
        types = SpotifyType.all()

    if SpotifyType.OPEN_URL in types and SpotifyType.OPEN_URL.value.lower() in value.lower():
        return SpotifyType.OPEN_URL
    elif SpotifyType.API_URL in types and SpotifyType.API_URL.value.lower() in value.lower():
        return SpotifyType.API_URL
    elif SpotifyType.URI in types and len(value.split(":")) == SpotifyType.URI.value:
        uri_list = value.split(":")
        if not uri_list[0] == "spotify":
            return None
        elif uri_list[1] != 'user' and len(uri_list[2]) == SpotifyType.ID.value:
            return SpotifyType.URI
    elif SpotifyType.ID in types and len(value) == SpotifyType.ID.value:
        return SpotifyType.ID
