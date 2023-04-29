from enum import Enum
from typing import List, Optional, Union


class SpotifyTypes(Enum):
    OPEN_URL: str = "https://open.spotify.com"
    API_URL: str = "https://api.spotify.com/v1"
    URI: int = 3
    ID: int = 22


def check_valid_spotify_type(
        string: str, types: Optional[Union[SpotifyTypes, list[SpotifyTypes]]] = SpotifyTypes
) -> bool:
    """
    Check that the given string is of a valid Spotify type.

    :param string: URL/URI/ID to check.
    :param types: Spotify types to check for. None checks all.
    :return: True if valid, False if not.
    """
    if not isinstance(string, str):
        return False
    elif types is None:
        types = [e.value for e in SpotifyTypes]

    if SpotifyTypes.OPEN_URL in types and SpotifyTypes.OPEN_URL.lower() in string.lower():
        return True
    elif SpotifyTypes.API_URL in types and SpotifyTypes.API_URL.lower() in string.lower():
        return True
    elif SpotifyTypes.URI in types and len(string.split(":")) == SpotifyTypes.URI:
        uri_list = string.split(":")
        if not uri_list[0] == "spotify":
            return False
        if uri_list[1] != 'user' and len(uri_list[2]) == SpotifyTypes.ID:
            return True
    elif SpotifyTypes.ID in types and len(string) == SpotifyTypes.ID:
        return True

    return False
