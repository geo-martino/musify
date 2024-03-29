import re
from abc import ABCMeta, abstractmethod
from itertools import batched
from random import randrange, choice

import pytest
from pytest_mock import MockerFixture

from musify.local.track import LocalTrack
from musify.shared.core.object import BasicCollection
from musify.shared.remote.enum import RemoteObjectType
from musify.shared.remote.object import RemotePlaylist
from musify.shared.remote.processors.check import RemoteItemChecker
from tests.local.track.utils import random_track, random_tracks
from tests.shared.api.utils import path_token
from tests.shared.core.misc import PrettyPrinterTester
from tests.shared.remote.processors.utils import patch_input
from tests.shared.remote.utils import RemoteMock
from tests.spotify.utils import random_uri, random_uris
from tests.utils import random_str, get_stdout


class RemoteItemCheckerTester(PrettyPrinterTester, metaclass=ABCMeta):
    """Run generic tests for :py:class:`RemoteItemSearcher` implementations."""

    @pytest.fixture
    def obj(self, checker: RemoteItemChecker) -> RemoteItemChecker:
        return checker

    @abstractmethod
    def checker(self, *args, **kwargs) -> RemoteItemChecker:
        """Yields a valid :py:class:`RemoteItemChecker` for the current remote source as a pytest.fixture"""
        raise NotImplementedError

    @abstractmethod
    def playlist_urls(self, *args, **kwargs) -> list[str]:
        """Yields a list of URLs that will return valid responses from the api_mock as a pytest.fixture"""
        raise NotImplementedError

    @pytest.fixture
    def collections(self, playlist_urls: list[str]) -> list[BasicCollection]:
        """Yields many valid :py:class:`BasicCollection` of :py:class:`LocalTrack` as a pytest.fixture"""
        count = randrange(6, len(playlist_urls))
        return [BasicCollection(name=random_str(30, 50), items=random_tracks()) for _ in range(count)]

    @staticmethod
    @pytest.fixture
    def setup_playlist_collection(
            checker: RemoteItemChecker, playlist_urls: list[str], api_mock: RemoteMock
    ) -> tuple[RemotePlaylist, BasicCollection]:
        """Setups up checker, playlist, and collection for testing match_to_remote functionality"""
        url = choice(playlist_urls)
        # noinspection PyProtectedMember
        pl = checker.factory.playlist(checker.api.get_items(url, extend=True, use_cache=False)[0])
        assert len(pl) > 10
        assert len({item.uri for item in pl}) == len(pl)  # all unique tracks

        collection = BasicCollection(name="test", items=pl.tracks.copy())
        checker._playlist_name_urls = {collection.name: url}
        checker._playlist_name_collection = {collection.name: collection}

        api_mock.reset_mock()  # tests check the number of requests made
        return pl, collection

    ###########################################################################
    ## Utilities
    ###########################################################################
    @pytest.fixture(params=[path_token])
    def token_file_path(self, path: str) -> str:
        """Yield the temporary path for the token JSON file"""
        return path

    @staticmethod
    def test_make_temp_playlist(checker: RemoteItemChecker, api_mock: RemoteMock, token_file_path: str):
        api_mock.reset_mock()  # test checks the number of requests made

        # force auth test to fail and reload from token
        checker.api.handler.token = None
        checker.api.handler.token_file_path = token_file_path

        collection = BasicCollection(name=random_str(30, 50), items=random_tracks())
        for item in collection:
            item.uri = None

        # does nothing when no URIs to add
        checker._create_playlist(collection=collection)
        assert not checker._playlist_name_urls
        assert not checker._playlist_name_collection
        assert not api_mock.request_history

        for item in collection:
            item.uri = random_uri()

        checker._create_playlist(collection=collection)
        assert checker.api.handler.token is not None
        assert collection.name in checker._playlist_name_urls
        assert checker._playlist_name_collection[collection.name] == collection
        assert len(api_mock.request_history) >= 2

    @staticmethod
    def test_delete_temp_playlists(
            checker: RemoteItemChecker,
            collections: list[BasicCollection],
            playlist_urls: list[str],
            api_mock: RemoteMock,
            token_file_path: str
    ):
        # force auth test to fail and reload from token
        checker.api.handler.token = None
        checker.api.handler.token_file_path = token_file_path

        checker._playlist_name_urls = {collection.name: url for collection, url in zip(collections, playlist_urls)}
        checker._playlist_name_collection = {collection.name: collection for collection in collections}

        checker._delete_playlists()
        assert checker.api.handler.token is not None
        assert not checker._playlist_name_urls
        assert not checker._playlist_name_collection
        assert len(api_mock.get_requests(method="DELETE")) == min(len(playlist_urls), len(collections))

    @staticmethod
    def test_finalise(checker: RemoteItemChecker):
        checker._skip = False
        checker._remaining.extend(random_tracks(3))
        checker._switched.extend(random_tracks(2))

        checker._final_switched = switched = random_tracks(1)
        checker._final_unavailable = unavailable = random_tracks(2)
        checker._final_skipped = skipped = random_tracks(3)

        result = checker._finalise()

        assert checker._skip
        assert not checker._remaining
        assert not checker._switched
        assert not checker._final_switched
        assert not checker._final_unavailable
        assert not checker._final_skipped

        assert result.switched == switched
        assert result.unavailable == unavailable
        assert result.skipped == skipped

    ###########################################################################
    ## ``pause`` step
    ###########################################################################
    @staticmethod
    def test_pause_1(
            checker: RemoteItemChecker,
            setup_playlist_collection: tuple[RemotePlaylist, BasicCollection],
            mocker: MockerFixture,
            api_mock: RemoteMock,
            capfd: pytest.CaptureFixture,
    ):
        api_mock.reset_mock()  # test checks the number of requests made
        pl, collection = setup_playlist_collection
        patch_input(["h", collection.name, pl.uri], mocker=mocker)

        checker._pause(page=1, total=1)
        mocker.stopall()
        capfd.close()

        stdout = get_stdout(capfd)  # removes colour codes
        assert stdout.count("Enter one of the following") == 2  # help text printed initially and reprinted on request
        assert "Input not recognised" not in stdout
        assert f"Showing items originally added to {collection.name}" in stdout  # <Name of playlist> entered
        assert f"Showing tracks for playlist: {pl.name}" in stdout  # <URL/URI> entered

        pl_pages = api_mock.calculate_pages(limit=20, total=len(pl))
        assert len(api_mock.get_requests(url=re.compile(pl.url + ".*"), method="GET")) == pl_pages + 1

        assert not checker._skip
        assert not checker._quit

    @staticmethod
    def test_pause_2(
            checker: RemoteItemChecker,
            mocker: MockerFixture,
            api_mock: RemoteMock,
            capfd: pytest.CaptureFixture,
    ):
        api_mock.reset_mock()  # test checks the number of requests made
        patch_input([random_str(10, 20), "u", "s"], mocker=mocker)

        checker._pause(page=1, total=1)
        mocker.stopall()
        capfd.close()

        stdout = get_stdout(capfd)
        assert stdout.count("Enter one of the following") == 1
        assert stdout.count("Input not recognised") == 2
        assert "Showing items originally added to" not in stdout
        assert "Showing tracks for playlist" not in stdout

        assert not api_mock.request_history

        assert checker._skip
        assert not checker._quit

    @staticmethod
    def test_pause_3(
            checker: RemoteItemChecker,
            mocker: MockerFixture,
            api_mock: RemoteMock,
            capfd: pytest.CaptureFixture,
    ):
        api_mock.reset_mock()  # test checks the number of requests made
        patch_input(["q"], mocker=mocker)

        checker._pause(page=1, total=1)
        mocker.stopall()
        capfd.close()

        stdout = get_stdout(capfd)
        assert stdout.count("Enter one of the following") == 1
        assert "Input not recognised" not in stdout
        assert "Showing items originally added to" not in stdout
        assert "Showing tracks for playlist" not in stdout
        assert not api_mock.request_history

        assert not checker._skip
        assert checker._quit

    ###########################################################################
    ## ``match_to_input`` step
    ###########################################################################
    # noinspection PyProtectedMember
    @pytest.fixture
    def remaining(self, checker: RemoteItemChecker) -> list[LocalTrack]:
        """
        Set up a random list of items in the ``remaining`` list with missing URIs to be matched via user input.
        Returns a shallow copy list of the items added.
        """
        tracks = random_tracks(20)
        for track in tracks:
            track.uri = None
            assert track.has_uri is None

        checker._remaining.clear()
        checker._remaining.extend(tracks)
        return tracks.copy()

    @staticmethod
    def test_match_to_input_unavailable_all(
            checker: RemoteItemChecker,
            remaining: list[LocalTrack],
            mocker: MockerFixture,
            capfd: pytest.CaptureFixture,
    ):
        # anything after 'ua' will be ignored
        values = ["u", "p", "h", "n", "", "zzzz", "n", "h", "u", "p", "ua", random_str(10, 20), "s", "q"]
        expected = values[-3:]  # stops after 'ua'
        patch_input(values, mocker=mocker)

        checker._match_to_input(name="test")
        mocker.stopall()
        capfd.close()

        assert values == expected

        stdout = get_stdout(capfd)
        assert stdout.count("Enter one of the following") == 3
        assert stdout.count("Input not recognised") == 1
        assert not checker._skip
        assert not checker._quit
        assert not checker._remaining
        assert not checker._switched

        # marked as unavailable
        assert remaining[0].path not in stdout
        assert remaining[0].uri is None
        assert not remaining[0].has_uri

        # skipped
        assert remaining[1].path in stdout
        assert remaining[1].uri is None
        assert remaining[1].has_uri is None

        # skipped
        assert remaining[2].path not in stdout
        assert remaining[2].uri is None
        assert remaining[2].has_uri is None

        # marked as unavailable
        assert remaining[3].path not in stdout
        assert remaining[3].uri is None
        assert not remaining[3].has_uri

        assert remaining[4].path in stdout
        for item in remaining[4:]:  # 'ua' triggered, marked as unavailable
            assert item.uri is None
            assert not item.has_uri

    @staticmethod
    def test_match_to_input_skip_all(
            checker: RemoteItemChecker,
            remaining: list[LocalTrack],
            mocker: MockerFixture,
            capfd: pytest.CaptureFixture,
    ):
        # anything after 'na...' will be ignored
        uri_list = random_uris(kind=RemoteObjectType.TRACK, start=5, stop=5)
        # noinspection SpellCheckingInspection
        patch_input(["p", "p", "p", *uri_list, "naaaaaaa", "r"], mocker=mocker)

        checker._match_to_input(name="test")
        mocker.stopall()
        capfd.close()

        stdout = get_stdout(capfd)
        assert stdout.count("Enter one of the following") == 1
        assert not checker._skip
        assert not checker._quit
        assert not checker._remaining
        assert checker._switched == remaining[:len(uri_list)]

        # results of each command on the remaining items
        assert stdout.count(remaining[0].path) == 3
        for uri, item in zip(uri_list, remaining[:len(uri_list)]):  # uri_list
            assert item.uri == uri
            assert item.has_uri

        for item in remaining[len(uri_list):]:  # 'na' triggered, skipped
            assert item.uri is None
            assert item.has_uri is None

    @staticmethod
    def test_match_to_input_return(
            checker: RemoteItemChecker,
            remaining: list[LocalTrack],
            mocker: MockerFixture,
            capfd: pytest.CaptureFixture,
    ):
        # anything after 'r' will be ignored
        patch_input(["u", "u", "u", "r", "q"], mocker=mocker)

        checker._match_to_input(name="test")
        mocker.stopall()
        capfd.close()

        stdout = get_stdout(capfd)
        assert stdout.count("Enter one of the following") == 1
        assert not checker._skip
        assert not checker._quit
        assert checker._remaining == remaining[3:]  # returned early before checking all remaining
        assert not checker._switched

        for item in remaining[:3]:  # marked as unavailable
            assert item.uri is None
            assert not item.has_uri

    @staticmethod
    def test_match_to_input_skip(
            checker: RemoteItemChecker,
            remaining: list[LocalTrack],
            mocker: MockerFixture,
            capfd: pytest.CaptureFixture,
    ):
        # anything after 's' will be ignored
        patch_input(["s", "q"], mocker=mocker)

        checker._match_to_input(name="test")
        mocker.stopall()
        capfd.close()

        stdout = get_stdout(capfd)
        assert stdout.count("Enter one of the following") == 1
        assert checker._skip
        assert not checker._quit
        assert not checker._remaining
        assert not checker._switched

        for item in remaining:  # skipped
            assert item.uri is None
            assert item.has_uri is None

    @staticmethod
    def test_match_to_input_quit(
            checker: RemoteItemChecker,
            remaining: list[LocalTrack],
            mocker: MockerFixture,
            capfd: pytest.CaptureFixture,
    ):
        # anything after 'q' will be ignored
        patch_input(["q", "s"], mocker=mocker)

        checker._match_to_input(name="test")
        mocker.stopall()
        capfd.close()

        stdout = get_stdout(capfd)
        assert stdout.count("Enter one of the following") == 1
        assert not checker._skip
        assert checker._quit
        assert not checker._remaining
        assert not checker._switched

        for item in remaining:  # skipped
            assert item.uri is None
            assert item.has_uri is None

    ###########################################################################
    ## ``match_to_remote`` step
    ###########################################################################
    @staticmethod
    def test_match_to_remote_no_changes(
            checker: RemoteItemChecker,
            setup_playlist_collection: tuple[RemotePlaylist, BasicCollection],
            api_mock: RemoteMock
    ):
        pl, collection = setup_playlist_collection

        # test collection == remote playlist; nothing happens
        checker._match_to_remote(collection.name)
        assert not checker._switched
        assert not checker._remaining

        pl_pages = api_mock.calculate_pages_from_response(pl.response)
        assert len(api_mock.get_requests(url=re.compile(pl.url + ".*"), method="GET")) == pl_pages

    @staticmethod
    def test_match_to_remote_removed(
            checker: RemoteItemChecker, setup_playlist_collection: tuple[RemotePlaylist, BasicCollection],
    ):
        pl, collection = setup_playlist_collection

        # extend collection i.e. simulate tracks removed from playlist
        extra_tracks = [track for track in random_tracks(10) if track.has_uri]
        collection.extend(extra_tracks)

        checker._match_to_remote(collection.name)
        assert not checker._switched
        assert checker._remaining == extra_tracks

    @staticmethod
    def test_match_to_remote_added(
            checker: RemoteItemChecker, setup_playlist_collection: tuple[RemotePlaylist, BasicCollection],
    ):
        pl, collection = setup_playlist_collection

        # remove from collection i.e. simulate unmatchable tracks added to playlist
        # tracks are unrelated to remote playlist tracks so this should return no matches
        for item in collection[:5]:
            collection.remove(item)

        checker._match_to_remote(collection.name)
        assert not checker._switched
        assert not checker._remaining

    @staticmethod
    def test_match_to_remote_switched(
            checker: RemoteItemChecker, setup_playlist_collection: tuple[RemotePlaylist, BasicCollection],
    ):
        pl, collection = setup_playlist_collection

        # switch URIs for some collection items i.e. simulate tracks on remote playlist have been switched
        for i, item in enumerate(collection[:5]):
            collection.items[i] = random_track()
            collection[i] |= item
            collection[i].uri = random_uri(kind=RemoteObjectType.TRACK)

        checker._match_to_remote(collection.name)
        assert checker._switched == collection[:5]
        assert not checker._remaining

    @staticmethod
    def test_match_to_remote_complex(
            checker: RemoteItemChecker, setup_playlist_collection: tuple[RemotePlaylist, BasicCollection],
    ):
        pl, collection = setup_playlist_collection

        # extend collection i.e. simulate tracks removed from playlist
        extra_tracks = [track for track in random_tracks(10) if track.has_uri]
        collection.extend(extra_tracks)
        collection.extend(extra_tracks)  # add twice, test duplicates processed as expected

        # switch URIs for some collection items i.e. simulate tracks on remote playlist have been switched
        for i, item in enumerate(collection[:5]):
            collection.items[i] = random_track()
            collection[i] |= item
            collection[i].uri = random_uri(kind=RemoteObjectType.TRACK)

        # remove from collection i.e. simulate unmatchable tracks added to playlist
        for item in collection[5:8]:
            collection.remove(item)

        checker._match_to_remote(collection.name)
        assert checker._switched == collection[:5]
        assert checker._remaining == 2 * extra_tracks

    ###########################################################################
    ## ``check_uri`` meta-step
    ###########################################################################
    @staticmethod
    def test_check_uri(
            checker: RemoteItemChecker,
            setup_playlist_collection: tuple[RemotePlaylist, BasicCollection],
            remaining: list[LocalTrack],
            mocker: MockerFixture,
            capfd: pytest.CaptureFixture,
            api_mock: RemoteMock,
    ):
        pl, collection = setup_playlist_collection

        # extend collection i.e. simulate tracks removed from playlist
        collection.extend(remaining)
        checker._remaining.clear()

        # switch URIs for some collection items i.e. simulate tracks on remote playlist have been switched
        for i, item in enumerate(collection[:5]):
            collection.items[i] = random_track()
            collection[i] |= item
            collection[i].uri = random_uri(kind=RemoteObjectType.TRACK)

        uri_list = random_uris(kind=RemoteObjectType.TRACK, start=8, stop=8)
        patch_input([*uri_list, "r", "u", "u", "u", "n", "n", "n", "n", "s"], mocker=mocker)  # end on skip
        checker._skip = False
        checker._playlist_name_collection["do not run"] = collection

        checker._check_uri()
        mocker.stopall()
        capfd.close()

        assert not checker._quit
        assert not checker._skip  # skip triggered by input, but should still hold initial value
        assert not checker._switched
        assert not checker._remaining

        stdout = get_stdout(capfd)
        assert "do not run" not in stdout  # skip triggered, 2nd collection should not be processed

        for uri, item in zip(uri_list, remaining[:len(uri_list)]):  # uri_list
            assert item.uri == uri
            assert item.has_uri
        for item in remaining[len(uri_list):]:  # marked as unavailable
            assert item.uri is None
            assert not item.has_uri

        # called 2x: 1 initial, 1 after user inputs 'r'
        pl_pages = api_mock.calculate_pages_from_response(pl.response)
        assert len(api_mock.get_requests(url=re.compile(pl.url + ".*"), method="GET")) == 2 * pl_pages

        assert checker._final_switched == collection[:5] + remaining[:len(uri_list)]
        assert checker._final_unavailable == remaining[len(uri_list):len(uri_list) + 3]
        assert checker._final_skipped == remaining[len(uri_list) + 3:]

    ###########################################################################
    ## Main ``check`` function
    ###########################################################################
    @staticmethod
    def test_check(
            checker: RemoteItemChecker,
            collections: list[BasicCollection],
            playlist_urls: list[str],
            mocker: MockerFixture,
            api_mock: RemoteMock,
    ):
        def add_collection(collection: BasicCollection):
            """Just simply add the collection and associated URL to the ItemChecker without calling API"""
            checker._playlist_name_urls[collection.name] = playlist_name_urls[collection.name]
            checker._playlist_name_collection[collection.name] = collection

        playlist_name_urls = {collection.name: url for collection, url in zip(collections, playlist_urls)}
        mocker.patch.object(checker, "_create_playlist", new=add_collection)

        interval = len(collections) // 3
        checker.interval = interval
        batch = next(batched(collections, interval))

        # initially skip at pause, then mark all items in all processed collections in the first batch as unavailable
        patch_input(["s", *["ua" for _ in batch]], mocker=mocker)

        api_mock.reset_mock()  # test checks the number of requests made
        result = checker.check(collections)
        mocker.stopall()

        # resets after each run
        assert not checker._remaining
        assert not checker._switched
        assert not checker._final_switched
        assert not checker._final_unavailable
        assert not checker._final_skipped

        assert not result.switched
        assert len(result.unavailable) == sum(len(collection) for collection in batch)
        assert not result.skipped

        # all items in all collections in the first batch were marked as unavailable
        for collection in batch:
            for item in collection:
                assert item.uri is None
                assert not item.has_uri

        # deleted only the playlists in the first batch
        requests = []
        for url in (playlist_name_urls[collection.name] for collection in batch):
            requests.append(api_mock.get_requests(url=url, method="DELETE"))
        assert len(requests) == len(batch)
