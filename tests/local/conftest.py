import pytest
from pytest_lazyfixture import lazy_fixture

from syncify.local.track import LocalTrack, FLAC, MP3, M4A, WMA
from syncify.shared.remote.processors.wrangle import RemoteDataWrangler
from syncify.spotify.processors.wrangle import SpotifyDataWrangler
from tests.local.utils import path_track_flac, path_track_mp3, path_track_m4a, path_track_wma, path_track_all


@pytest.fixture(scope="module")
def remote_wrangler(spotify_wrangler: SpotifyDataWrangler) -> RemoteDataWrangler:
    """Yields a :py:class:`SpotifyDataWrangler` to use in tests"""
    yield spotify_wrangler


@pytest.fixture(params=[path_track_flac])
def track_flac(path: str, remote_wrangler: RemoteDataWrangler) -> FLAC:
    """Yields instantiated :py:class:`FLAC` objects for testing"""
    return FLAC(file=path, available=path_track_all, remote_wrangler=remote_wrangler)


@pytest.fixture(params=[path_track_mp3])
def track_mp3(path: str, remote_wrangler: RemoteDataWrangler) -> MP3:
    """Yields instantiated :py:class:`MP3` objects for testing"""
    return MP3(file=path, available=path_track_all, remote_wrangler=remote_wrangler)


@pytest.fixture(params=[path_track_m4a])
def track_m4a(path: str, remote_wrangler: RemoteDataWrangler) -> M4A:
    """Yields instantiated :py:class:`M4A` objects for testing"""
    return M4A(file=path, available=path_track_all, remote_wrangler=remote_wrangler)


@pytest.fixture(params=[path_track_wma])
def track_wma(path: str, remote_wrangler: RemoteDataWrangler) -> WMA:
    """Yields instantiated :py:class:`WMA` objects for testing"""
    return WMA(file=path, available=path_track_all, remote_wrangler=remote_wrangler)


@pytest.fixture(params=[
    lazy_fixture("track_flac"),
    lazy_fixture("track_mp3"),
    lazy_fixture("track_m4a"),
    lazy_fixture("track_wma")
])
def track(request) -> LocalTrack:
    """Yields instantiated :py:class:`LocalTrack` objects for testing"""
    return request.param

