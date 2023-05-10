from abc import abstractmethod
from datetime import datetime
from typing import Any, List, MutableMapping, Optional, Union

from syncify.api import RequestHandler
from syncify.spotify import __URL_API__, ItemType
from syncify.spotify.api import API
from syncify.local.files.track.base.tags import Tags
from syncify.utils_new.generic import PrettyPrinter


class SpotifyResponse(PrettyPrinter):

    _list_sep = "; "
    _url_pad = 69

    def __init__(self, response: MutableMapping[str, Any]):
        self.response = response
        self.check_type()

        self.id: str = response["id"]
        self.uri: str = response["uri"]
        self.has_uri: bool = True

        self.url: str = response["href"]
        self.url_ext: str = response["external_urls"]["spotify"]

    def check_type(self) -> None:
        kind = self.__class__.__name__.lower().replace("spotify", "")
        if self.response.get("type") != kind:
            raise ValueError(f"Response is not of type '{kind}': {self.response.get('type')}")

    def enrich(self, response: MutableMapping[str, Any]) -> None:
        self.__init__(response)

    def refresh(self, api: Union[RequestHandler, API], use_cache: bool = True) -> None:
        get = api.get if isinstance(api, RequestHandler) else api.handler.get
        response = get(url=self.url, use_cache=use_cache, log_pad=self._url_pad)
        self.enrich(response)

    @abstractmethod
    def refresh_full(self, api: API, use_cache: bool = True) -> None:
        raise NotImplementedError

    def as_dict(self) -> MutableMapping[str, Any]:
        """Return a dictionary representation of the tags/metadata for this response type."""
        return {k: v for k, v in self.__dict__.items() if k != "response"}


class SpotifyTrack(SpotifyResponse, Tags):

    _song_keys = {
        0: 'C',
        1: 'C#/Db',
        2: 'D',
        3: 'D#/Eb',
        4: 'E',
        5: 'F',
        6: 'F#/Gb',
        7: 'G',
        8: 'G#/Ab',
        9: 'A',
        10: 'A#/Bb',
        11: 'B'
    }

    def __init__(self, response: MutableMapping[str, Any], date_added: Optional[Union[str, datetime]] = None):
        SpotifyResponse.__init__(self, response)

        artists = response.get("artists", {})
        album = response.get("album", {})

        self.title = response["name"]
        self.artist = self._list_sep.join(artist["name"] for artist in artists)
        self.album = album.get("name")
        self.album_artist = self._list_sep.join(artist["name"] for artist in album.get("artists", []))
        self.track_number = response["track_number"]
        self.track_total = album.get("total_tracks")
        self.genres = album.get("genres")
        self.year = int(album["release_date"][:4]) if album else None
        self.bpm = None
        self.key = None
        self.disc_number = response["disc_number"]
        self.disc_total = None
        self.compilation = album.get('album_group', "") == "compilation"
        self.comments = None

        images = {image["height"]: image["url"] for image in album.get("images", [])}
        self.image_links = {"cover_front": url for height, url in images.items() if height == max(images)}
        self.has_image = len(self.image_links) > 0

        self.length: float = response['duration_ms'] / 1000
        self.rating: Optional[int] = response.get('popularity')
        self.date_added: Optional[datetime] = date_added
        if isinstance(date_added, str):
            self.date_added = datetime.strptime(date_added, "%Y-%m-%dT%H:%M:%S%z")

        self.artists = [SpotifyArtist(artist) for artist in response["artists"]]

        if not self.album_artist:
            self.album_artist = None

        if "audio_features" in self.response:
            self.bpm = self.response["audio_features"]["tempo"]

            # correctly formatted song key string
            key: str = self._song_keys[self.response["audio_features"]["key"]]
            is_minor: bool = self.response["audio_features"]['mode'] == 0
            if '/' in key:
                key_sep = key.split('/')
                self.key = f"{key_sep[0]}{'m'*is_minor}/{key_sep[1]}{'m'*is_minor}"
            else:
                self.key = f"{key}{'m'*is_minor}"

    def refresh_full(self, api: API, use_cache: bool = True) -> None:
        response = api.handler.get(self.url, use_cache=use_cache, log_pad=self._url_pad)
        api.get_items(response["album"], use_cache=use_cache)
        api.get_items(response["artists"], kind=ItemType.ARTIST, use_cache=use_cache)
        api.get_audio_features(response, use_cache=use_cache)

        self.__init__(response, date_added=self.date_added)


class SpotifyArtist(SpotifyResponse):

    def __init__(self, response: MutableMapping[str, Any]):
        SpotifyResponse.__init__(self, response)

        self.artist: str = response["name"]
        self.genres: Optional[List[str]] = response.get("genres")

        images = {image["height"]: image["url"] for image in response.get("images", [])}
        self.image_links: MutableMapping[str, str] = {"cover_front": url
                                                      for height, url in images.items() if height == max(images)}
        self.has_image: bool = len(self.image_links) > 0

        self.rating: Optional[int] = response.get('popularity')

    def refresh_full(self, api: RequestHandler, use_cache: bool = True) -> None:
        self.refresh(api=api, use_cache=use_cache)
