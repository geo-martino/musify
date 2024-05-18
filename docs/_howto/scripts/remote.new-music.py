from musify.libraries.remote.spotify.api import SpotifyAPI
from musify.libraries.remote.spotify.library import SpotifyLibrary
api = SpotifyAPI()
library = SpotifyLibrary(api=api)

library.load_saved_artists()
library.enrich_saved_artists()

from datetime import datetime, date

start_date = date(2024, 1, 1)
end_date = datetime.now().date()


def match_date(alb) -> bool:
    """Match start and end dates to the release date of the given ``alb``"""
    if alb.date:
        return start_date <= alb.date <= end_date
    if alb.month:
        return start_date.year <= alb.year <= end_date.year and start_date.month <= alb.month <= end_date.month
    if alb.year:
        return start_date.year <= alb.year <= end_date.year
    return False


from musify.libraries.remote.core.enum import RemoteObjectType

albums = [album for artist in library.artists for album in artist.albums if match_date(album)]
albums_need_extend = [album for album in albums if len(album.tracks) < album.track_total]
if albums_need_extend:
    kind = RemoteObjectType.ALBUM
    key = api.collection_item_map[kind]

    bar = library.logger.get_progress_bar(iterable=albums_need_extend, desc="Getting album tracks", unit="albums")
    for album in bar:
        api.extend_items(album.response, kind=kind, key=key)
        album.refresh(skip_checks=False)

# log stats about the loaded artists
library.log_artists()

from musify.libraries.remote.spotify.object import SpotifyPlaylist

name = "New Music Playlist"
playlist = SpotifyPlaylist.create(api=api, name=name)

tracks = [track for album in sorted(albums, key=lambda x: x.date, reverse=True) for track in album]
playlist.extend(tracks, allow_duplicates=False)

# sync the object with Spotify and log the results
results = playlist.sync(kind="refresh", reload=False, dry_run=False)
library.log_sync({name: results})
