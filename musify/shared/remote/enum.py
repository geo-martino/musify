from musify.shared.core.enum import MusifyEnum


class RemoteIDType(MusifyEnum):
    """Represents remote ID type"""
    ALL: int = 0

    ID: int = 22  # value is the expected length of ID string
    URI: int = 3  # value is the expected number of chunks in a URI
    URL: int = 1
    URL_EXT: int = 2


class RemoteObjectType(MusifyEnum):
    """Represents remote object types"""
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
