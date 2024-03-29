import inspect
from copy import deepcopy
from dataclasses import asdict
from random import sample, choice

import pytest

from musify.local.collection import LocalAlbum
from musify.local.track import LocalTrack
from musify.processors.match import CleanTagConfig
from musify.shared.core.enum import TagFields as Tag
from musify.shared.exception import MusifyEnumError
from musify.shared.remote import RemoteResponse
from musify.shared.remote.enum import RemoteIDType as IDType, RemoteObjectType
from musify.shared.remote.exception import RemoteError, RemoteIDTypeError, RemoteObjectTypeError
from musify.shared.remote.processors.check import RemoteItemChecker
from musify.shared.remote.processors.search import SearchSettings, RemoteItemSearcher
from musify.spotify.api import SpotifyAPI
from musify.spotify.factory import SpotifyObjectFactory
from musify.spotify.object import SpotifyTrack, SpotifyAlbum
from musify.spotify.processors import SpotifyDataWrangler
from tests.local.track.utils import random_track
from tests.shared.remote.processors.check import RemoteItemCheckerTester
from tests.shared.remote.processors.search import RemoteItemSearcherTester
from tests.spotify.api.mock import SpotifyMock
from tests.spotify.utils import random_id, random_ids, random_uri, random_api_url, random_ext_url
from tests.utils import random_str


@pytest.fixture(scope="class", params=[
    f for f in asdict(SpotifyObjectFactory()).values() if inspect.isclass(f) and issubclass(f, RemoteResponse)
])
def response(request, api_mock: SpotifyMock) -> RemoteResponse:
    """Yields a :py:class:`RemoteResponse` for each of the :py:class:`SpotifyObjectFactory` remote response items"""
    factory = request.param
    response = choice(api_mock.item_type_map[factory.__new__(factory).kind])
    return factory(response, skip_checks=True)


def test_get_id_type(wrangler: SpotifyDataWrangler):
    assert wrangler.get_id_type(random_id()) == IDType.ID
    assert wrangler.get_id_type(random_str(1, IDType.ID.value - 1), kind=RemoteObjectType.USER) == IDType.ID
    assert wrangler.get_id_type(random_uri()) == IDType.URI
    assert wrangler.get_id_type(random_api_url()) == IDType.URL
    assert wrangler.get_id_type(random_ext_url()) == IDType.URL_EXT

    with pytest.raises(RemoteIDTypeError):
        wrangler.get_id_type("Not an ID")


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


def test_get_item_type(wrangler: SpotifyDataWrangler, object_type: RemoteObjectType):
    # ID/URI
    assert wrangler.get_item_type(random_id(), kind=object_type) == object_type
    assert wrangler.get_item_type(random_uri(object_type)) == object_type

    # URL
    suffix = random_str(0, 10)
    assert wrangler.get_item_type(random_api_url(object_type) + (f"/{suffix}" if suffix else "")) == object_type
    assert wrangler.get_item_type(random_ext_url(object_type) + (f"/{suffix}" if suffix else "")) == object_type

    # Mapping
    kind_str = "".join(choice([char.upper(), char.lower()]) for char in object_type.name)
    kind_str = choice([kind_str, kind_str.upper(), kind_str.lower()])
    assert wrangler.get_item_type({"type": kind_str}) == object_type

    # RemoteResponse
    kind_str = "".join(choice([char.upper(), char.lower()]) for char in object_type.name)
    kind_str = choice([kind_str, kind_str.upper(), kind_str.lower()])
    assert wrangler.get_item_type({"type": kind_str}) == object_type

    values = [
        {"type": object_type.name.lower()},
        random_ext_url(object_type) + suffix,
        random_uri(object_type),
        random_id()
    ]
    assert wrangler.get_item_type(values) == object_type


def test_get_item_type_response(wrangler: SpotifyDataWrangler, response: RemoteResponse):
    assert wrangler.get_item_type(response) == response.kind
    values = [
        {"type": response.kind.name.lower()},
        random_ext_url(response.kind),
        random_uri(response.kind),
        random_id(),
        response
    ]
    assert wrangler.get_item_type(values) == response.kind


def test_get_item_type_fails(wrangler: SpotifyDataWrangler):
    with pytest.raises(RemoteObjectTypeError):
        wrangler.get_item_type([])

    with pytest.raises(RemoteObjectTypeError):
        wrangler.get_item_type([random_id(), random_id()])

    with pytest.raises(RemoteObjectTypeError):
        values = [random_uri(RemoteObjectType.SHOW), {"type": "track"}]
        wrangler.get_item_type(values)

    with pytest.raises(RemoteObjectTypeError):
        values = [random_uri(RemoteObjectType.SHOW), random_api_url(RemoteObjectType.PLAYLIST)]
        wrangler.get_item_type(values)

    with pytest.raises(RemoteObjectTypeError):
        response = {"type": "track", "is_local": True}
        wrangler.get_item_type(response)

    with pytest.raises(RemoteObjectTypeError):
        response = {"not_a_type": "track", "is_local": False}
        wrangler.get_item_type(response)

    with pytest.raises(RemoteObjectTypeError):
        wrangler.get_item_type(f"bad_uri:chapter:{random_id()}")

    with pytest.raises(MusifyEnumError):
        wrangler.get_item_type(f"spotify:bad_type:{random_id()}")


def test_validate_item_type(wrangler: SpotifyDataWrangler, object_type: RemoteObjectType):
    value = choice([
        random_id() if object_type != RemoteObjectType.USER else random_str(1, IDType.ID.value - 1),
        random_uri(object_type),
        random_api_url(object_type) + f"/{random_str(0, 10)}",
        random_ext_url(object_type) + f"/{random_str(0, 10)}",
        {"type": object_type.name.lower(), "id": random_id()}
    ])
    assert wrangler.validate_item_type(value, kind=object_type) is None

    values = [
        {"type": object_type.name.lower()},
        random_ext_url(object_type) + f"/{random_str(0, 10)}",
        random_uri(object_type),
        random_id()
    ]
    assert wrangler.validate_item_type(values, kind=object_type) is None

    uri = random_uri(choice([k for k in RemoteObjectType.all() if k != object_type]))
    with pytest.raises(RemoteObjectTypeError):
        wrangler.validate_item_type(uri, kind=object_type)


def test_validate_item_type_response(wrangler: SpotifyDataWrangler, response: RemoteResponse):
    assert wrangler.validate_item_type(response, kind=response.kind) is None

    values = [
        {"type": response.kind.name.lower()},
        random_ext_url(response.kind) + f"/{random_str(0, 10)}",
        random_uri(response.kind),
        random_id()
    ]
    assert wrangler.validate_item_type(values, kind=response.kind) is None


def test_convert(wrangler: SpotifyDataWrangler, object_type: RemoteObjectType):
    id_ = random_id()
    expected_map = {
        IDType.ID: id_,
        IDType.URI: f"spotify:{object_type.name.lower()}:{id_}",
        IDType.URL: f"{wrangler.url_api}/{object_type.name.lower()}s/{id_}",
        IDType.URL_EXT: f"{wrangler.url_ext}/{object_type.name.lower()}/{id_}"
    }
    for type_out, expected in expected_map.items():
        for type_in, value in expected_map.items():
            assert wrangler.convert(value, kind=object_type, type_out=type_out) == expected
            assert wrangler.convert(value, kind=object_type, type_in=type_in, type_out=type_out) == expected


def test_convert_fails(wrangler: SpotifyDataWrangler):
    # no ID type given when input value is ID raises error
    with pytest.raises(RemoteIDTypeError):
        wrangler.convert(random_id(), type_out=IDType.URI)

    with pytest.raises(RemoteIDTypeError):
        wrangler.convert("bad value", type_out=IDType.URI)


def test_extract_ids(wrangler: SpotifyDataWrangler, object_type: RemoteObjectType):
    id_ = random_id()
    values = [
        id_,
        f"spotify:{object_type.name.lower()}:{id_}",
        f"{wrangler.url_api}/{object_type.name.lower()}s/{id_}",
        f"{wrangler.url_ext}/{object_type.name.lower()}/{id_}",
        {"id": id_},
    ]
    for value in values:
        assert wrangler.extract_ids(value) == [id_]

    expected = random_ids(start=len(values), stop=len(values))
    expected_iter = iter(expected)
    values = [
        next(expected_iter),
        f"spotify:{object_type.name.lower()}:{next(expected_iter)}",
        f"{wrangler.url_api}/{object_type.name.lower()}s/{next(expected_iter)}",
        f"{wrangler.url_ext}/{object_type.name.lower()}/{next(expected_iter)}",
        {"id": next(expected_iter)},
    ]
    assert wrangler.extract_ids(values) == expected


def test_extract_ids_response(wrangler: SpotifyDataWrangler, response: RemoteResponse):
    assert wrangler.extract_ids(response) == [response.response["id"]]

    expected = random_ids(start=5, stop=5)
    expected_iter = iter(expected)
    values = [
        next(expected_iter),
        f"spotify:{response.kind.name.lower()}:{next(expected_iter)}",
        f"{wrangler.url_api}/{response.kind.name.lower()}s/{next(expected_iter)}",
        f"{wrangler.url_ext}/{response.kind.name.lower()}/{next(expected_iter)}",
        {"id": next(expected_iter)},
        response
    ]
    expected.append(response.response["id"])
    assert wrangler.extract_ids(values) == expected


def test_extract_ids_fails(wrangler: SpotifyDataWrangler):
    with pytest.raises(RemoteError):
        wrangler.extract_ids([{"id": random_id()}, {"type": "track"}])

    with pytest.raises(RemoteError):
        wrangler.extract_ids([{"id": random_id()}, [f"spotify:playlist:{random_id()}"]])


class TestSpotifyItemSearcher(RemoteItemSearcherTester):

    @pytest.fixture(scope="class")
    def searcher(self, api: SpotifyAPI, api_mock: SpotifyMock) -> RemoteItemSearcher:
        RemoteItemSearcher.karaoke_tags = {"karaoke", "backing", "instrumental"}
        RemoteItemSearcher.year_range = 10

        RemoteItemSearcher.clean_tags_remove_all = {"the", "a", "&", "and"}
        RemoteItemSearcher.clean_tags_split_all = set()
        RemoteItemSearcher.clean_tags_config = (
            CleanTagConfig(tag=Tag.TITLE, remove={"part"}, split={"featuring", "feat.", "ft.", "/"}),
            CleanTagConfig(tag=Tag.ARTIST, split={"featuring", "feat.", "ft.", "vs"}),
            CleanTagConfig(tag=Tag.ALBUM, remove={"ep"}, preprocess=lambda x: x.split('-')[0])
        )

        RemoteItemSearcher.reduce_name_score_on = {"live", "demo", "acoustic"}
        RemoteItemSearcher.reduce_name_score_factor = 0.5

        RemoteItemSearcher.settings_items = SearchSettings(
            search_fields_1=[Tag.TITLE],  # query mock always returns match on name
            match_fields={Tag.TITLE},
            result_count=10,
            allow_karaoke=True,
            min_score=0.1,
            max_score=0.5
        )
        RemoteItemSearcher.settings_albums = SearchSettings(
            search_fields_1=[Tag.ALBUM],  # query mock always returns match on name
            match_fields={Tag.ALBUM},
            result_count=5,
            allow_karaoke=True,
            min_score=0.1,
            max_score=0.5
        )

        return RemoteItemSearcher(object_factory=SpotifyObjectFactory(api=api))

    @pytest.fixture
    def search_items(
            self, searcher: RemoteItemSearcher, api_mock: SpotifyMock, wrangler: SpotifyDataWrangler
    ) -> list[LocalTrack]:
        items = []
        for remote_track in map(SpotifyTrack, sample(api_mock.tracks, k=searcher.settings_items.result_count)):
            local_track = random_track()
            local_track.uri = None
            local_track.remote_wrangler = wrangler

            local_track.title = remote_track.title
            local_track.album = remote_track.album
            local_track.artist = remote_track.artist
            local_track._reader.file.info.length = remote_track.length
            local_track.year = remote_track.year

            items.append(local_track)

        return items

    # noinspection PyTestUnpassedFixture
    @pytest.fixture
    def search_albums(
            self,
            searcher: RemoteItemSearcher,
            api: SpotifyAPI,
            api_mock: SpotifyMock,
            wrangler: SpotifyDataWrangler
    ) -> list[LocalAlbum]:
        limit = searcher.settings_items.result_count
        albums = [album for album in api_mock.albums if 2 < album["tracks"]["total"] <= api_mock.limit_lower]
        responses = deepcopy(sample(albums, k=min(len(albums), limit)))
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
                local_track._reader.file.info.length = remote_track.length

                tracks.append(local_track)

            albums.append(LocalAlbum(tracks=tracks, name=album.name))

        return albums


class TestSpotifyItemChecker(RemoteItemCheckerTester):

    @pytest.fixture
    def checker(self, api: SpotifyAPI) -> RemoteItemChecker:
        return RemoteItemChecker(object_factory=SpotifyObjectFactory(api=api))

    @pytest.fixture(scope="class")
    def playlist_urls(self, api_mock: SpotifyMock) -> list[str]:
        return [
            pl["href"] for pl in api_mock.user_playlists
            if api_mock.limit_lower < pl["tracks"]["total"] <= 60
        ]
