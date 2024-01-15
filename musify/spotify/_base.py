from musify.shared.remote import Remote


class SpotifyRemote(Remote):
    """Base class for any object concerning Spotify functionality"""

    # noinspection PyPropertyDefinition
    @classmethod
    @property
    def source(cls) -> str:
        return "Spotify"
