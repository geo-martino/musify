from syncify.remote.enums import RemoteItemType, RemoteIDType

from tests import random_str


def random_uri(kind: RemoteItemType = RemoteItemType.TRACK) -> str:
    """Generates a random Spotify URI of item type ``kind``"""
    return f"spotify:{kind.name.lower()}:{random_str(RemoteIDType.ID.value, RemoteIDType.ID.value + 1)}"
