"""
The fundamental core enum classes for the :py:mod:`Remote` module.

Represents ID and item types.
"""

from musify.shared.core.enum import MusifyEnum


class RemoteIDType(MusifyEnum):
    """Represents remote ID types"""
    ALL: int = 0

    #: Value is the expected length of ID string
    ID: int = 22
    #: Value is the expected number of chunks in a URI
    URI: int = 3
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
