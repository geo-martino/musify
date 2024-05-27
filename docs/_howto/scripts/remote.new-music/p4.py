from p3 import *

from musify.libraries.remote.core.enum import RemoteObjectType
from musify.libraries.remote.core.object import RemoteAlbum


async def get_albums(library: RemoteLibrary, start: date, end: date) -> list[RemoteAlbum]:
    """
    Get the albums that match the ``start`` and ``end`` date range from a given ``library``
    and get the tracks on those albums if needed.
    """
    albums = [album for artist in library.artists for album in artist.albums if match_date(album, start, end)]
    albums_need_extend = [album for album in albums if len(album.tracks) < album.track_total]

    if albums_need_extend:
        kind = RemoteObjectType.ALBUM
        key = api.collection_item_map[kind]

        bar = library.logger.get_iterator(iterable=albums_need_extend, desc="Getting album tracks", unit="albums")
        async with library:
            for album in bar:
                await api.extend_items(album.response, kind=kind, key=key)
                album.refresh(skip_checks=False)

    return albums
