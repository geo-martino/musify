from datetime import datetime
from typing import Any, List, MutableMapping, Optional

from syncify.spotify import ItemType
from syncify.spotify.api import API
from syncify.spotify.library.item import SpotifyResponse, SpotifyTrack, SpotifyArtist


class SpotifyAlbum(SpotifyResponse):

    def __init__(self, response: MutableMapping[str, Any]):
        SpotifyResponse.__init__(self, response)

        self.artist: str = self._list_sep.join(artist["name"] for artist in response["artists"])
        self.album: str = response["name"]
        self.album_artist: str = self.artist
        self.track_total: int = response["total_tracks"]
        self.genres: List[str] = response["genres"]
        self.year: int = int(response["release_date"][:4])
        self.disc_total: int = 0
        self.compilation: bool = response['album_type'] == "compilation"
        self.comments: Optional[List[str]] = None

        images = {image["height"]: image["url"] for image in response["images"]}
        self.image_links: MutableMapping[str, str] = {"cover_front": url
                                                      for height, url in images.items() if height == max(images)}
        self.has_image: bool = len(self.image_links) > 0

        self.rating: int = response['popularity']

        self.artists = [SpotifyArtist(artist) for artist in response["artists"]]
        self.tracks = [SpotifyTrack(track) for track in response["tracks"]["items"]]
        self.disc_total = max(track.disc_number for track in self.tracks)

        for track in self.tracks:
            track.disc_total = self.disc_total

    def refresh_full(self, api: API, use_cache: bool = True) -> None:
        response = api.handler.get(self.url, use_cache=use_cache, log_pad=self._url_pad)
        api.get_items(response["tracks"]["items"], kind=ItemType.TRACK, use_cache=use_cache)
        api.get_audio_features(response["tracks"]["items"], use_cache=use_cache)

        self.__init__(response)


class SpotifyPlaylist(SpotifyResponse):

    def __init__(self, response: MutableMapping[str, Any]):
        SpotifyResponse.__init__(self, response)

        self.name: str = response["name"]
        self.description: str = response["description"]
        self.collaborative: bool = response["collaborative"]
        self.public: bool = response["public"]
        self.followers: int = response["followers"]["total"]
        self.track_total: int = response["tracks"]["total"]

        self.owner_name: str = response["owner"]["display_name"]
        self.owner_id: str = response["owner"]["id"]

        images = {image["height"]: image["url"] for image in response["images"]}
        self.image_links: MutableMapping[str, str] = {"cover_front": url
                                                      for height, url in images.items() if height == max(images)}
        self.has_image: bool = len(self.image_links) > 0

        self.length: float = 0.0
        self.date_created: Optional[datetime] = None
        self.date_modified: Optional[datetime] = None

        self.tracks = [SpotifyTrack(track["track"], track["added_at"]) for track in response["tracks"]["items"]]

        if len(self.tracks) > 0:
            self.length: float = sum(track.length for track in self.tracks)
            self.date_created: datetime = min(track.date_added for track in self.tracks)
            self.date_modified: datetime = max(track.date_added for track in self.tracks)

    def refresh_full(self, api: API, use_cache: bool = True) -> None:
        response = api.handler.get(self.url, use_cache=use_cache, log_pad=self._url_pad)

        tracks = [track["track"] for track in response["tracks"]["items"]]
        api.get_items(tracks, kind=ItemType.TRACK, use_cache=use_cache)
        api.get_audio_features(tracks, use_cache=use_cache)

        for old, new in zip(response["tracks"]["items"], tracks):
            old["track"] = new
        self.__init__(response)
