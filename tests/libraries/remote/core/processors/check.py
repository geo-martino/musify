import re
from abc import ABCMeta, abstractmethod
from itertools import batched
from random import randrange, choice

import pytest
from pytest_mock import MockerFixture

from musify.libraries.collection import BasicCollection
from musify.libraries.local.track import LocalTrack
from musify.libraries.remote.core.enum import RemoteObjectType
from musify.libraries.remote.core.object import RemotePlaylist
from musify.libraries.remote.core.processors.check import RemoteItemChecker
from tests.api.utils import path_token
from tests.core.printer import PrettyPrinterTester
from tests.libraries.local.track.utils import random_track, random_tracks
from tests.libraries.remote.core.processors.utils import patch_input
from tests.libraries.remote.core.utils import RemoteMock
from tests.libraries.remote.spotify.utils import random_uri, random_uris
from tests.utils import random_str, get_stdout


class RemoteItemCheckerTester(PrettyPrinterTester, metaclass=ABCMeta):
    """Run generic tests for :py:class:`RemoteItemSearcher` implementations."""

    @pytest.fixture
    def obj(self, checker: RemoteItemChecker) -> RemoteItemChecker:
        return checker

    @abstractmethod
    def checker(self, *args, **kwargs) -> RemoteItemChecker:
        """Yields a valid :py:class:`RemoteItemChecker` for the current remote source as a pytest.fixture."""
        raise NotImplementedError

    @abstractmethod
    def playlist_urls(self, *args, **kwargs) -> list[str]:
        """Yields a list of URLs that will return valid responses from the api_mock as a pytest.fixture."""
        raise NotImplementedError

    @pytest.fixture
    def collections(self, playlist_urls: list[str]) -> list[BasicCollection]:
        """Yields many valid :py:class:`BasicCollection` of :py:class:`LocalTrack` as a pytest.fixture."""
        count = randrange(6, len(playlist_urls))
        return [BasicCollection(name=random_str(30, 50), items=random_tracks()) for _ in range(count)]

    @staticmethod
    @pytest.fixture
    async def setup_playlist_collection(
            checker: RemoteItemChecker, playlist_urls: list[str]
    ) -> tuple[RemotePlaylist, BasicCollection]:
        """Setups up checker, playlist, and collection for testing match_to_remote functionality"""
        url = choice(playlist_urls)
        pl = checker.factory.playlist(next(iter(await checker.api.get_items(url, extend=True))))
        assert len(pl) > 10
        assert len({item.uri for item in pl}) == len(pl)  # all unique tracks

        collection = BasicCollection(name="test", items=pl.tracks.copy())
        checker._playlist_name_urls = {collection.name: url}
        checker._playlist_name_collection = {collection.name: collection}

        return pl, collection

    ###########################################################################
    ## Utilities
    ###########################################################################
    @pytest.fixture(params=[path_token])
    def token_file_path(self, path: str) -> str:
        """Yield the temporary path for the token JSON file"""
        return path

    @staticmethod
    async def test_make_temp_playlist(checker: RemoteItemChecker, api_mock: RemoteMock, token_file_path: str):
        # force auth test to fail and reload from token
        checker.api.handler.authoriser.token = None
        checker.api.handler.authoriser.token_file_path = token_file_path

        collection = BasicCollection(name=random_str(30, 50), items=random_tracks())
        for item in collection:
            item.uri = None

        # does nothing when no URIs to add
        await checker._create_playlist(collection=collection)
        assert not checker._playlist_name_urls
        assert not checker._playlist_name_collection
        api_mock.assert_not_called()

        for item in collection:
            item.uri = random_uri()

        await checker._create_playlist(collection=collection)
        assert checker.api.handler.authoriser.token is not None
        assert collection.name in checker._playlist_name_urls
        assert checker._playlist_name_collection[collection.name] == collection
        assert api_mock.total_requests >= 2

    @staticmethod
    async def test_delete_temp_playlists(
            checker: RemoteItemChecker,
            collections: list[BasicCollection],
            playlist_urls: list[str],
            api_mock: RemoteMock,
            token_file_path: str
    ):
        # force auth test to fail and reload from token
        checker.api.handler.authoriser.token = None
        checker.api.handler.authoriser.token_file_path = token_file_path

        checker._playlist_name_urls = {collection.name: url for collection, url in zip(collections, playlist_urls)}
        checker._playlist_name_collection = {collection.name: collection for collection in collections}

        await checker._delete_playlists()
        assert checker.api.handler.authoriser.token is not None
        assert not checker._playlist_name_urls
        assert not checker._playlist_name_collection
        assert len(await api_mock.get_requests(method="DELETE")) == min(len(playlist_urls), len(collections))

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
    async def test_pause_1(
            checker: RemoteItemChecker,
            setup_playlist_collection: tuple[RemotePlaylist, BasicCollection],
            mocker: MockerFixture,
            api_mock: RemoteMock,
            capfd: pytest.CaptureFixture,
    ):
        pl, collection = setup_playlist_collection
        patch_input(["h", collection.name, pl.uri], mocker=mocker)

        await checker._pause(page=1, total=1)
        mocker.stopall()
        capfd.close()

        stdout = get_stdout(capfd)  # removes colour codes
        assert stdout.count("Enter one of the following") == 2  # help text printed initially and reprinted on request
        assert "Input not recognised" not in stdout
        assert f"Showing items originally added to {collection.name}" in stdout  # <Name of playlist> entered
        assert f"Showing tracks for playlist: {pl.name}" in stdout  # <URL/URI> entered

        pl_pages = api_mock.calculate_pages(limit=20, total=len(pl))
        assert len(await api_mock.get_requests(method="GET", url=re.compile(pl.url))) == pl_pages + 1

        assert not checker._skip
        assert not checker._quit

    @staticmethod
    async def test_pause_2(
            checker: RemoteItemChecker,
            mocker: MockerFixture,
            api_mock: RemoteMock,
            capfd: pytest.CaptureFixture,
    ):
        patch_input([random_str(10, 20), "u", "s"], mocker=mocker)

        await checker._pause(page=1, total=1)
        mocker.stopall()
        capfd.close()

        stdout = get_stdout(capfd)
        assert stdout.count("Enter one of the following") == 1
        assert stdout.count("Input not recognised") == 2
        assert "Showing items originally added to" not in stdout
        assert "Showing tracks for playlist" not in stdout

        api_mock.assert_not_called()

        assert checker._skip
        assert not checker._quit

    @staticmethod
    async def test_pause_3(
            checker: RemoteItemChecker,
            mocker: MockerFixture,
            api_mock: RemoteMock,
            capfd: pytest.CaptureFixture,
    ):
        patch_input(["q"], mocker=mocker)

        await checker._pause(page=1, total=1)
        mocker.stopall()
        capfd.close()

        stdout = get_stdout(capfd)
        assert stdout.count("Enter one of the following") == 1
        assert "Input not recognised" not in stdout
        assert "Showing items originally added to" not in stdout
        assert "Showing tracks for playlist" not in stdout
        api_mock.assert_not_called()

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
    @pytest.mark.slow
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
    @pytest.mark.slow
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
    async def test_match_to_remote_no_changes(
            checker: RemoteItemChecker,
            setup_playlist_collection: tuple[RemotePlaylist, BasicCollection],
            api_mock: RemoteMock
    ):
        pl, collection = setup_playlist_collection

        # test collection == remote playlist; nothing happens
        await checker._match_to_remote(collection.name)
        assert not checker._switched
        assert not checker._remaining

        pl_pages = api_mock.calculate_pages_from_response(pl.response)
        assert len(await api_mock.get_requests(method="GET", url=re.compile(pl.url))) == pl_pages

    @staticmethod
    async def test_match_to_remote_removed(
            checker: RemoteItemChecker, setup_playlist_collection: tuple[RemotePlaylist, BasicCollection],
    ):
        pl, collection = setup_playlist_collection

        # extend collection i.e. simulate tracks removed from playlist
        extra_tracks = [track for track in random_tracks(10) if track.has_uri]
        collection.extend(extra_tracks)

        await checker._match_to_remote(collection.name)
        assert not checker._switched
        assert checker._remaining == extra_tracks

    @staticmethod
    async def test_match_to_remote_added(
            checker: RemoteItemChecker, setup_playlist_collection: tuple[RemotePlaylist, BasicCollection],
    ):
        pl, collection = setup_playlist_collection

        # remove from collection i.e. simulate unmatchable tracks added to playlist
        # tracks are unrelated to remote playlist tracks so this should return no matches
        for item in collection[:5]:
            collection.remove(item)

        await checker._match_to_remote(collection.name)
        assert not checker._switched
        assert not checker._remaining

    @staticmethod
    async def test_match_to_remote_switched(
            checker: RemoteItemChecker, setup_playlist_collection: tuple[RemotePlaylist, BasicCollection],
    ):
        pl, collection = setup_playlist_collection

        # switch URIs for some collection items i.e. simulate tracks on remote playlist have been switched
        for i, item in enumerate(collection[:5]):
            collection.items[i] = random_track()
            collection[i] |= item
            collection[i].uri = random_uri(kind=RemoteObjectType.TRACK)

        await checker._match_to_remote(collection.name)
        assert checker._switched == collection[:5]
        assert not checker._remaining

    @staticmethod
    @pytest.mark.slow
    async def test_match_to_remote_complex(
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

        await checker._match_to_remote(collection.name)
        assert checker._switched == collection[:5]
        assert checker._remaining == 2 * extra_tracks

    ###########################################################################
    ## ``check_uri`` meta-step
    ###########################################################################
    @staticmethod
    @pytest.mark.slow
    async def test_check_uri(
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

        await checker._check_uri()
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
        assert len(await api_mock.get_requests(method="GET", url=re.compile(pl.url))) == 2 * pl_pages

        assert checker._final_switched == collection[:5] + remaining[:len(uri_list)]
        assert checker._final_unavailable == remaining[len(uri_list):len(uri_list) + 3]
        assert checker._final_skipped == remaining[len(uri_list) + 3:]

    ###########################################################################
    ## Main ``check`` function
    ###########################################################################
    @staticmethod
    @pytest.mark.slow
    async def test_check(
            checker: RemoteItemChecker,
            collections: list[BasicCollection],
            playlist_urls: list[str],
            mocker: MockerFixture,
            api_mock: RemoteMock,
    ):
        count = 0

        async def add_collection(self, collection: BasicCollection):
            """Just simply add the collection and associated URL to the ItemChecker without calling API"""
            nonlocal count
            count += 1

            self._playlist_name_urls[collection.name] = playlist_name_urls[collection.name]
            self._playlist_name_collection[collection.name] = collection

        playlist_name_urls = {collection.name: url for collection, url in zip(collections, playlist_urls)}
        mocker.patch.object(RemoteItemChecker, "_create_playlist", new=add_collection)

        interval = len(collections) // 3
        checker.interval = interval
        batched_collections = batched(collections, interval)

        # mark all items in 1st and 2nd batch as unavailable, skip after the 2nd batch and quit
        batch_1 = next(batched_collections)
        batch_2 = next(batched_collections)
        values = ["", *["ua" for _ in batch_1], "s", *["ua" for _ in batch_2]]
        patch_input(values, mocker=mocker)

        result = await checker.check(collections)
        mocker.stopall()

        assert count == len(batch_1) + len(batch_2)  # only 2 batches executed

        # resets after each run
        assert not checker._remaining
        assert not checker._switched
        assert not checker._final_switched
        assert not checker._final_unavailable
        assert not checker._final_skipped

        assert not result.switched
        assert len(result.unavailable) == sum(len(collection) for collection in batch_1 + batch_2)
        assert not result.skipped

        # all items in all collections in the 1st and 2nd batches were marked as unavailable
        for coll in batch_1 + batch_2:
            for item in coll:
                assert item.uri is None
                assert not item.has_uri

        # deleted only the playlists in the first 2 batches
        requests = []
        for url in (playlist_name_urls[collection.name] for collection in batch_1 + batch_2):
            requests += await api_mock.get_requests(method="DELETE", url=re.compile(url))

        assert len(requests) == len(batch_1) + len(batch_2)
