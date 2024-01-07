

import pytest

from syncify.shared.core.enum import TagFields as Tag
from syncify.shared.exception import SyncifyEnumError
from syncify.local.collection import LocalAlbum
from syncify.local.track import LocalTrack
from syncify.processors.match import CleanTagConfig
from syncify.shared.remote.enum import RemoteIDType as IDType, RemoteObjectType as ObjectType
from syncify.shared.remote.exception import RemoteError, RemoteIDTypeError, RemoteObjectTypeError
from syncify.shared.remote.processors.search import SearchSettings
from syncify.spotify import URL_API, URL_EXT
from syncify.spotify.api import SpotifyAPI
from syncify.spotify.object import SpotifyTrack, SpotifyAlbum
from syncify.spotify.processors.processors import SpotifyItemSearcher, SpotifyItemChecker
from syncify.spotify.processors.wrangle import SpotifyDataWrangler
from tests.local.track.utils import random_track
from tests.shared.remote.processors.check import RemoteItemCheckerTester
from tests.shared.remote.processors.search import RemoteItemSearcherTester
from tests.spotify.api.mock import SpotifyMock
from tests.spotify.utils import random_id, random_ids, random_uri, random_api_url, random_ext_url
from tests.utils import random_str


# noinspection SpellCheckingInspection
def test_get_id_type(wrangler: SpotifyDataWrangler):
    assert wrangler.get_id_type(random_id()) == IDType.ID
    assert wrangler.get_id_type(random_str(1, IDType.ID.value - 1), kind=ObjectType.USER) == IDType.ID
    assert wrangler.get_id_type(random_uri()) == IDType.URI
    assert wrangler.get_id_type(random_api_url()) == IDType.URL
    assert wrangler.get_id_type(random_ext_url()) == IDType.URL_EXT

    with pytest.raises(RemoteIDTypeError):
        wrangler.get_id_type("Not an ID")


# noinspection SpellCheckingInspection
def test_validate_id_type(wrangler: SpotifyDataWrangler):
    assert wrangler.validate_id_type(random_id())
    assert wrangler.validate_id_type(random_uri())
    assert wrangler.validate_id_type(random_api_url())
    assert wrangler.validate_id_type(random_ext_url())

    assert wrangler.validate_id_type(random_id(), kind=IDType.ID)
    assert wrangler.validate_id_type(random_uri(), kind=IDType.URI)
    assert wrangler.validate_id_type(random_api_url(), kind=IDType.URL)
    assert wrangler.validate_id_type(random_ext_url(), kind=IDType.URL_EXT)

    assert not wrangler.validate_id_type(random_id(), kind=IDType.URL)
    assert not wrangler.validate_id_type(random_uri(), kind=IDType.URL_EXT)


# noinspection SpellCheckingInspection
def test_get_item_type(wrangler: SpotifyDataWrangler):
    assert wrangler.get_item_type(random_uri(ObjectType.PLAYLIST)) == ObjectType.PLAYLIST
    assert wrangler.get_item_type(random_uri(ObjectType.TRACK)) == ObjectType.TRACK
    assert wrangler.get_item_type(random_uri(ObjectType.ALBUM)) == ObjectType.ALBUM
    assert wrangler.get_item_type(random_uri(ObjectType.ARTIST)) == ObjectType.ARTIST
    assert wrangler.get_item_type(random_uri(ObjectType.USER)) == ObjectType.USER
    assert wrangler.get_item_type(random_uri(ObjectType.SHOW)) == ObjectType.SHOW
    assert wrangler.get_item_type(random_uri(ObjectType.EPISODE)) == ObjectType.EPISODE
    assert wrangler.get_item_type(random_uri(ObjectType.AUDIOBOOK)) == ObjectType.AUDIOBOOK
    assert wrangler.get_item_type(random_uri(ObjectType.CHAPTER)) == ObjectType.CHAPTER

    assert wrangler.get_item_type(random_api_url(ObjectType.PLAYLIST) + "/followers") == ObjectType.PLAYLIST
    assert wrangler.get_item_type(random_api_url(ObjectType.TRACK)) == ObjectType.TRACK
    assert wrangler.get_item_type(random_api_url(ObjectType.ALBUM)) == ObjectType.ALBUM
    assert wrangler.get_item_type(random_api_url(ObjectType.ARTIST)) == ObjectType.ARTIST
    assert wrangler.get_item_type(random_api_url(ObjectType.USER)) == ObjectType.USER
    assert wrangler.get_item_type(random_api_url(ObjectType.SHOW) + "/episodes") == ObjectType.SHOW
    assert wrangler.get_item_type(random_api_url(ObjectType.EPISODE)) == ObjectType.EPISODE
    assert wrangler.get_item_type(random_api_url(ObjectType.AUDIOBOOK) + "/chapters") == ObjectType.AUDIOBOOK
    assert wrangler.get_item_type(random_api_url(ObjectType.CHAPTER)) == ObjectType.CHAPTER

    assert wrangler.get_item_type({"type": "playlist"}) == ObjectType.PLAYLIST
    assert wrangler.get_item_type({"type": "TRACK"}) == ObjectType.TRACK
    assert wrangler.get_item_type({"type": "album"}) == ObjectType.ALBUM
    assert wrangler.get_item_type({"type": "ARTIST"}) == ObjectType.ARTIST
    assert wrangler.get_item_type({"type": "user"}) == ObjectType.USER
    assert wrangler.get_item_type({"type": "show"}) == ObjectType.SHOW
    assert wrangler.get_item_type({"type": "episode"}) == ObjectType.EPISODE
    assert wrangler.get_item_type({"type": "audiobook"}) == ObjectType.AUDIOBOOK
    assert wrangler.get_item_type({"type": "chapter"}) == ObjectType.CHAPTER

    values = [
        {"type": "playlist"},
        random_api_url(ObjectType.PLAYLIST) + "/followers",
        random_uri(ObjectType.PLAYLIST),
        random_id()
    ]
    assert wrangler.get_item_type(values) == ObjectType.PLAYLIST

    with pytest.raises(RemoteObjectTypeError):
        wrangler.get_item_type([])

    with pytest.raises(RemoteObjectTypeError):
        wrangler.get_item_type([random_id(), random_id()])

    with pytest.raises(RemoteObjectTypeError):
        values = [random_uri(ObjectType.SHOW), {"type": "track"}]
        wrangler.get_item_type(values)

    with pytest.raises(RemoteObjectTypeError):
        values = [random_uri(ObjectType.SHOW), random_api_url(ObjectType.PLAYLIST)]
        wrangler.get_item_type(values)

    with pytest.raises(RemoteObjectTypeError):
        response = {"type": "track", "is_local": True}
        wrangler.get_item_type(response)

    with pytest.raises(RemoteObjectTypeError):
        response = {"not_a_type": "track", "is_local": False}
        wrangler.get_item_type(response)

    with pytest.raises(RemoteObjectTypeError):
        wrangler.get_item_type(f"bad_uri:chapter:{random_id()}")

    with pytest.raises(SyncifyEnumError):
        wrangler.get_item_type(f"spotify:bad_type:{random_id()}")


# noinspection SpellCheckingInspection
def test_validate_item_type(wrangler: SpotifyDataWrangler):
    assert wrangler.validate_item_type(
        random_api_url(ObjectType.PLAYLIST) + "/followers", kind=ObjectType.PLAYLIST
    ) is None
    assert wrangler.validate_item_type(random_id(), kind=ObjectType.TRACK) is None
    assert wrangler.validate_item_type(random_str(1, IDType.ID.value - 1), kind=ObjectType.USER) is None
    assert wrangler.validate_item_type({"type": "album", "id": random_id()}, kind=ObjectType.ALBUM) is None
    assert wrangler.validate_item_type(random_uri(ObjectType.ARTIST), kind=ObjectType.ARTIST) is None
    assert wrangler.validate_item_type(random_uri(ObjectType.USER), kind=ObjectType.USER) is None
    assert wrangler.validate_item_type(random_api_url(ObjectType.SHOW) + "/episodes", kind=ObjectType.SHOW) is None
    assert wrangler.validate_item_type(random_uri(ObjectType.EPISODE), kind=ObjectType.EPISODE) is None
    assert wrangler.validate_item_type(
        f"{random_ext_url(ObjectType.AUDIOBOOK)}/chapters", kind=ObjectType.AUDIOBOOK
    ) is None
    assert wrangler.validate_item_type(random_uri(ObjectType.CHAPTER), kind=ObjectType.CHAPTER) is None

    values = [
        {"type": "playlist"},
        random_api_url(ObjectType.PLAYLIST) + "/followers",
        random_uri(ObjectType.PLAYLIST),
        random_id()
    ]
    assert wrangler.validate_item_type(values, kind=ObjectType.PLAYLIST) is None

    with pytest.raises(RemoteObjectTypeError):
        wrangler.validate_item_type(values, kind=ObjectType.TRACK)


# noinspection SpellCheckingInspection
def test_convert(wrangler: SpotifyDataWrangler):
    id_ = random_id()
    assert wrangler.convert(id_, kind=ObjectType.EPISODE, type_out=IDType.URL) == f"{URL_API}/episodes/{id_}"
    assert wrangler.convert(id_, kind=ObjectType.EPISODE, type_out=IDType.URL_EXT) == f"{URL_EXT}/episode/{id_}"
    assert wrangler.convert(id_, kind=ObjectType.EPISODE, type_out=IDType.URI) == f"spotify:episode:{id_}"
    assert wrangler.convert(id_, kind=ObjectType.EPISODE) == id_

    assert wrangler.convert(f"spotify:episode:{id_}", type_out=IDType.URL) == f"{URL_API}/episodes/{id_}"
    assert wrangler.convert(f" spotify:episode:{id_} ", type_out=IDType.URL_EXT) == f"{URL_EXT}/episode/{id_}"
    assert wrangler.convert(f"spotify:episode:{id_}", type_out=IDType.URI) == f"spotify:episode:{id_}"
    assert wrangler.convert(f" spotify:episode:{id_}  ") == id_

    assert wrangler.convert(f"{URL_API}/episodes/{id_}", type_out=IDType.URL) == f"{URL_API}/episodes/{id_}"
    assert wrangler.convert(f"{URL_API}/episodes/{id_}", type_out=IDType.URL_EXT) == f"{URL_EXT}/episode/{id_}"
    assert wrangler.convert(f"{URL_API}/episodes/{id_}", type_out=IDType.URI) == f"spotify:episode:{id_}"
    assert wrangler.convert(f"{URL_API}/episodes/{id_}", type_out=IDType.ID) == id_

    assert wrangler.convert(f"{URL_EXT}/episode/{id_}", type_out=IDType.URL) == f"{URL_API}/episodes/{id_}"
    assert wrangler.convert(f"{URL_EXT}/episode/{id_}", type_out=IDType.URL_EXT) == f"{URL_EXT}/episode/{id_}"
    assert wrangler.convert(f"{URL_EXT}/episode/{id_}", type_out=IDType.URI) == f"spotify:episode:{id_}"
    assert wrangler.convert(f"{URL_EXT}/episode/{id_}") == id_

    # incorrect type in given still gives the right output
    assert wrangler.convert(
        f"spotify:episode:{id_}", type_in=IDType.URL, type_out=IDType.URL
    ) == f"{URL_API}/episodes/{id_}"

    # no ID type given when input value is ID raises error
    with pytest.raises(RemoteIDTypeError):
        wrangler.convert(id_, type_out=IDType.URI)

    with pytest.raises(RemoteIDTypeError):
        wrangler.convert("bad value", type_out=IDType.URI)


# noinspection SpellCheckingInspection
def test_extract_ids(wrangler: SpotifyDataWrangler):
    id_ = random_id()
    assert wrangler.extract_ids(f"{URL_API}/playlists/{id_}/followers") == [id_]
    assert wrangler.extract_ids(f"{URL_EXT}/playlist/{id_}/followers") == [id_]
    assert wrangler.extract_ids(f"spotify:playlist:{id_}") == [id_]
    assert wrangler.extract_ids(id_) == [id_]
    assert wrangler.extract_ids({"id": id_}) == [id_]

    expected = random_ids(start=4, stop=4)
    values = [
        f"{URL_API}/playlists/{expected[0]}/followers",
        f"{URL_EXT}/playlist/{expected[1]}/followers",
        f"spotify:playlist:{expected[2]}",
        expected[3]
    ]
    assert wrangler.extract_ids(values) == expected

    assert wrangler.extract_ids([{"id": i} for i in expected[:2]]) == expected[:2]

    with pytest.raises(RemoteError):
        wrangler.extract_ids([{"id": expected[0]}, {"type": "track"}])

    with pytest.raises(RemoteError):
        wrangler.extract_ids([{"id": expected[0]}, [f"spotify:playlist:{expected[1]}"]])


class TestSpotifyItemSearcher(RemoteItemSearcherTester):

    @pytest.fixture(scope="class")
    def searcher(self, api: SpotifyAPI, api_mock: SpotifyMock) -> SpotifyItemSearcher:
        SpotifyItemSearcher.karaoke_tags = {"karaoke", "backing", "instrumental"}
        SpotifyItemSearcher.year_range = 10

        SpotifyItemSearcher.clean_tags_remove_all = {"the", "a", "&", "and"}
        SpotifyItemSearcher.clean_tags_split_all = set()
        SpotifyItemSearcher.clean_tags_config = (
            CleanTagConfig(tag=Tag.TITLE, _remove={"part"}, _split={"featuring", "feat.", "ft.", "/"}),
            CleanTagConfig(tag=Tag.ARTIST, _split={"featuring", "feat.", "ft.", "vs"}),
            CleanTagConfig(tag=Tag.ALBUM, _remove={"ep"}, _preprocess=lambda x: x.split('-')[0])
        )

        SpotifyItemSearcher.reduce_name_score_on = {"live", "demo", "acoustic"}
        SpotifyItemSearcher.reduce_name_score_factor = 0.5

        SpotifyItemSearcher.settings_items = SearchSettings(
            search_fields_1=[Tag.TITLE],  # query mock always returns match on name
            match_fields={Tag.TITLE},
            result_count=10,
            allow_karaoke=True,
            min_score=0.1,
            max_score=0.5
        )
        SpotifyItemSearcher.settings_albums = SearchSettings(
            search_fields_1=[Tag.ALBUM],  # query mock always returns match on name
            match_fields={Tag.ALBUM},
            result_count=5,
            allow_karaoke=True,
            min_score=0.1,
            max_score=0.5
        )

        return SpotifyItemSearcher(api=api)

    @pytest.fixture
    def search_items(
            self, searcher: SpotifyItemSearcher, api_mock: SpotifyMock, wrangler: SpotifyDataWrangler
    ) -> list[LocalTrack]:
        items = []
        for remote_track in map(SpotifyTrack, api_mock.tracks[:searcher.settings_items.result_count]):
            local_track = random_track()
            local_track.uri = None
            local_track.remote_wrangler = wrangler

            local_track.title = remote_track.title
            local_track.album = remote_track.album
            local_track.artist = remote_track.artist
            local_track.file.info.length = remote_track.length
            local_track.year = remote_track.year

            items.append(local_track)

        return items

    @pytest.fixture
    def search_albums(
            self,
            searcher: SpotifyItemSearcher,
            api: SpotifyAPI,
            api_mock: SpotifyMock,
            wrangler: SpotifyDataWrangler
    ) -> list[LocalAlbum]:

        limit = searcher.settings_items.result_count
        responses = [album for album in api_mock.albums if 2 < album["tracks"]["total"] <= api_mock.limit_lower][:limit]
        assert len(responses) > 4

        albums = []
        for album in map(lambda response: SpotifyAlbum(api=api, response=response, skip_checks=True), responses):
            tracks = []
            for remote_track in album:
                local_track = random_track()
                local_track.uri = None
                local_track.remote_wrangler = wrangler
                local_track.compilation = False

                local_track.title = remote_track.title
                local_track.album = album.name
                local_track.artist = remote_track.artist
                local_track.year = remote_track.year
                local_track.file.info.length = remote_track.length

                tracks.append(local_track)

            albums.append(LocalAlbum(tracks=tracks, name=album.name))

        return albums


class TestSpotifyItemChecker(RemoteItemCheckerTester):

    @pytest.fixture(scope="function")
    def checker(self, api: SpotifyAPI) -> SpotifyItemChecker:
        return SpotifyItemChecker(api=api)

    @pytest.fixture(scope="class")
    def playlist_urls(self, api_mock: SpotifyMock) -> list[str]:
        return [
            pl["href"] for pl in api_mock.user_playlists
            if api_mock.limit_lower < pl["tracks"]["total"] <= 60
        ]
