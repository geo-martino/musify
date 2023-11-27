from syncify.enums import SyncifyEnum


class ItemType(SyncifyEnum):
    """Represents Spotify item types."""
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
    """Represents Spotify ID types."""
    ALL: int = 0

    ID: int = 22
    URI: int = 3
    URL: int = 1
    URL_EXT: int = 2
