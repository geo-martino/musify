"""
Just the core abstract class for the :py:mod:`Spotify` module.
Placed here separately to avoid circular import logic issues.
"""

from musify.shared.remote import Remote


class SpotifyRemote(Remote):
    """Base class for any object concerning Spotify functionality"""

    # noinspection PyPropertyDefinition
    @classmethod
    @property
    def source(cls) -> str:
        return "Spotify"
