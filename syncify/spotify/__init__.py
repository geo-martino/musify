from typing import List, Union, MutableMapping, Any, Collection

from syncify.enums import SyncifyEnum

__UNAVAILABLE_URI_VALUE__ = "spotify:track:unavailable"
__URL_AUTH__ = "https://accounts.spotify.com"
__URL_API__ = "https://api.spotify.com/v1"
__URL_EXT__ = "https://open.spotify.com"

APIMethodInputType = Union[str, MutableMapping[str, Any], Collection[str], List[MutableMapping[str, Any]]]


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