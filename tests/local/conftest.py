import pytest

from musify.local.track import LocalTrack, FLAC, MP3, M4A, WMA
from musify.shared.file import PathStemMapper
from musify.shared.remote.processors.wrangle import RemoteDataWrangler
from musify.spotify.processors import SpotifyDataWrangler
from tests.local.utils import path_track_all, path_track_flac, path_track_mp3, path_track_m4a, path_track_wma
from tests.utils import path_resources


@pytest.fixture(scope="module")
def remote_wrangler(spotify_wrangler: SpotifyDataWrangler) -> RemoteDataWrangler:
    """Yields a :py:class:`SpotifyDataWrangler` to use in tests"""
    yield spotify_wrangler


@pytest.fixture(scope="module")
def path_mapper() -> PathStemMapper:
    """Yields a :py:class:`PathMapper` that can map paths from the test playlist files"""
    yield PathStemMapper(stem_map={"../": path_resources}, available_paths=path_track_all)


@pytest.fixture(params=[path_track_flac])
def track_flac(path: str, remote_wrangler: RemoteDataWrangler) -> FLAC:
    """Yields instantiated :py:class:`FLAC` objects for testing"""
    return FLAC(file=path, remote_wrangler=remote_wrangler)


@pytest.fixture(params=[path_track_mp3])
def track_mp3(path: str, remote_wrangler: RemoteDataWrangler) -> MP3:
    """Yields instantiated :py:class:`MP3` objects for testing"""
    return MP3(file=path, remote_wrangler=remote_wrangler)


@pytest.fixture(params=[path_track_m4a])
def track_m4a(path: str, remote_wrangler: RemoteDataWrangler) -> M4A:
    """Yields instantiated :py:class:`M4A` objects for testing"""
    return M4A(file=path, remote_wrangler=remote_wrangler)


@pytest.fixture(params=[path_track_wma])
def track_wma(path: str, remote_wrangler: RemoteDataWrangler) -> WMA:
    """Yields instantiated :py:class:`WMA` objects for testing"""
    return WMA(file=path, remote_wrangler=remote_wrangler)


@pytest.fixture(params=[
    pytest.lazy_fixture("track_flac"),
    pytest.lazy_fixture("track_mp3"),
    pytest.lazy_fixture("track_m4a"),
    pytest.lazy_fixture("track_wma")
])
def track(request) -> LocalTrack:
    """Yields instantiated :py:class:`LocalTrack` objects for testing"""
    return request.param
