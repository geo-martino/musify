from enum import Enum
from typing import List, Optional, Union


class SpotifyTypes(Enum):
    OPEN_URL: str = "https://open.spotify.com"
    API_URL: str = "https://api.spotify.com/v1"
    URI: int = 3
    ID: int = 22


def check_valid_spotify_type(
        value: str, types: Optional[Union[SpotifyTypes, List[SpotifyTypes]]] = None
) -> bool:
    """
    Check that the given value is of a valid Spotify type.

    :param value: URL/URI/ID to check.
    :param types: Spotify types to check for. None checks all.
    :return: True if valid, False if not.
    """
    if not isinstance(value, str):
        return False
    elif not isinstance(types, list):
        types = [types]
    elif types is None:
        types = list(SpotifyTypes)

    if SpotifyTypes.OPEN_URL in types and SpotifyTypes.OPEN_URL.value.lower() in value.lower():
        return True
    elif SpotifyTypes.API_URL in types and SpotifyTypes.API_URL.value.lower() in value.lower():
        return True
    elif SpotifyTypes.URI in types and len(value.split(":")) == SpotifyTypes.URI.value:
        uri_list = value.split(":")
        if not uri_list[0] == "spotify":
            return False
        if uri_list[1] != 'user' and len(uri_list[2]) == SpotifyTypes.ID.value:
            return True
    elif SpotifyTypes.ID in types and len(value) == SpotifyTypes.ID.value:
        return True

    return False
