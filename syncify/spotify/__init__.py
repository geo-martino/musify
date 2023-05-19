from typing import List, Optional, Union, Set

from syncify.enums import SyncifyEnum
from syncify.utils import make_list

__UNAVAILABLE_URI_VALUE__ = "spotify:track:unavailable"
__URL_AUTH__ = "https://accounts.spotify.com"
__URL_API__ = "https://api.spotify.com/v1"
__URL_EXT__ = "https://open.spotify.com"


class ItemType(SyncifyEnum):
    ALL = 0
    PLAYLIST = 1
    TRACK = 2
    ALBUM = 3
    ARTIST = 4
    USER = 5
    SHOW = 6
    EPISODE = 7
    AUDIOBOOK = 8
    CHAPTER = 9


class IDType(SyncifyEnum):
    ALL: int = 0

    ID: int = 22
    URI: int = 3
    URL: int = 1
    URL_EXT: int = 2


def check_spotify_type(
        value: str, types: Union[IDType, List[IDType]] = IDType.ALL
) -> Optional[IDType]:
    """
    Check that the given value is of a valid Spotify type.

    :param value: URL/URI/ID to check.
    :param types: Spotify types to check for. None checks all.
    :return: The Spotify type if value is valid, None if invalid.
    """
    if not isinstance(value, str):
        return

    types: Set[IDType] = set(make_list(types))
    if IDType.ALL in types:
        types = IDType.all()

    if IDType.URL in types and value.lower().startswith(__URL_API__):
        return IDType.URL
    elif IDType.URL_EXT in types and value.lower().startswith(__URL_EXT__):
        return IDType.URL_EXT
    elif IDType.URI in types and len(value.split(":")) == IDType.URI.value:
        uri_list = value.split(":")
        if not uri_list[0] == "spotify":
            return None
        elif uri_list[1] != 'user' and len(uri_list[2]) == IDType.ID.value:
            return IDType.URI
    elif IDType.ID in types and len(value) == IDType.ID.value:
        return IDType.ID
