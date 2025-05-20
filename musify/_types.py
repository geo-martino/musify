from typing import Annotated, Literal

from pydantic import StringConstraints, conlist

from musify.types import MusifyEnum

Character = Annotated[str, StringConstraints(min_length=1, max_length=1)]
StrippedCharacter = Annotated[str, StringConstraints(min_length=1, max_length=1, strip_whitespace=True)]
String = Annotated[str, StringConstraints(min_length=1)]
StrippedString = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
StrippedStringList = conlist(StrippedString, min_length=1)


class Source(MusifyEnum):
    """Represents source types"""


class LocalSource(Source):
    """Represents local repository types"""
    LOCAL = 1
    MUSICBEE = 2


class RemoteSource(Source):
    """Represents remote repository types"""
    SPOTIFY = 1


class Resource(MusifyEnum):
    """Represents resource types"""
    PLAYLIST = 1
    TRACK = 2
    ALBUM = 3
    ARTIST = 4
    USER = 5
    SHOW = 6
    EPISODE = 7
    AUDIOBOOK = 8
    CHAPTER = 9

    GENRE = 20
