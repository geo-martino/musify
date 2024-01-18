"""
Meta-operations for all playlists/tracks etc. stored in a given library.

A library can be a simple set of folders containing playlists/tracks etc.,
or a defined settings folder for any of the supported library managers.

Specific library types should implement :py:class:`LocalLibrary`.
"""

from .library import LocalLibrary
from .musicbee import MusicBee

LIBRARY_CLASSES = frozenset({LocalLibrary, MusicBee})
