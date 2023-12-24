from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from copy import copy
from random import randrange
from urllib.parse import parse_qs

import pytest
from pytest_mock import MockerFixture

from syncify.abstract.collection import BasicCollection, Album, ItemCollection
from syncify.abstract.item import Item
from syncify.remote.api import RemoteAPI
from syncify.remote.enums import RemoteObjectType
from syncify.remote.processors.check import RemoteItemChecker
from tests.api.utils import path_token
from tests.local.utils import random_track, random_tracks
from tests.remote.utils import RemoteMock
from tests.spotify.utils import random_uri
from tests.utils import random_str


class RemoteItemCheckerTester(ABC):
    """Run generic tests for :py:class:`RemoteItemSearcher` implementations."""

    @abstractmethod
    def remote_api(self, *args, **kwargs) -> RemoteAPI:
        """Yields a valid :py:class:`RemoteAPI` for the current remote source as a pytest.fixture"""
        raise NotImplementedError

    @abstractmethod
    def remote_mock(self, *args, **kwargs) -> RemoteMock:
        """Yields a requests_mock setup to return valid responses for the current remote source as a pytest.fixture"""
        raise NotImplementedError

    @abstractmethod
    def checker(self, *args, **kwargs) -> RemoteItemChecker:
        """Yields a valid :py:class:`RemoteItemChecker` for the current remote source as a pytest.fixture"""
        raise NotImplementedError

    @abstractmethod
    def playlist_urls(self, *args, **kwargs) -> list[str]:
        """Yields a list of URLs that will return valid responses from the remote_mock as a pytest.fixture"""
        raise NotImplementedError

    @pytest.fixture
    def collections(self) -> list[BasicCollection]:
        """Yields a valid :py:class:`BasicCollection` of :py:class:`LocalTrack` as a pytest.fixture"""
        return [BasicCollection(name=random_str(), items=random_tracks()) for _ in range(randrange(0, 10))]

    @staticmethod
    def test_make_temp_playlist(checker: RemoteItemChecker, remote_mock: RemoteMock):
        collection = BasicCollection(name=random_str(), items=random_tracks())
        for item in collection:
            item.uri = None

        # does nothing when no URIs to add
        checker._create_playlist(collection=collection)
        assert not checker.playlist_name_urls
        assert not checker.playlist_name_collection
        assert not remote_mock.request_history

        for item in collection:
            item.uri = random_uri()

        checker._create_playlist(collection=collection)
        assert collection.name in checker.playlist_name_urls
        assert checker.playlist_name_collection[collection.name] == collection
        assert len(remote_mock.request_history) >= 2

        # cause some bug to make the checker fail
        assert not checker.quit
        del checker.playlist_name_urls
        checker._create_playlist(collection=collection)
        assert checker.quit

    @staticmethod
    def test_delete_temp_playlists(
            checker: RemoteItemChecker,
            collections: list[BasicCollection],
            playlist_urls: list[str],
            remote_mock: RemoteMock
    ):
        # force auth test to fail and reload from token
        checker.api.token = None
        checker.api.token_file_path = path_token

        checker.playlist_name_urls = {collection.name: url for collection, url in zip(collections, playlist_urls)}
        checker.playlist_name_collection = {collection.name: collection for collection in collections}

        checker._delete_playlists()
        assert checker.api.token is not None
        assert not checker.playlist_name_urls
        assert not checker.playlist_name_collection
        assert len(remote_mock.get_requests(method="DELETE")) == len(collections)

    @staticmethod
    def test_finalise(checker: RemoteItemChecker):
        pass

    @staticmethod
    def test_check_pause(checker: RemoteItemChecker):
        pass

    @staticmethod
    def test_match_to_remote(checker: RemoteItemChecker):
        pass

    @staticmethod
    def test_match_to_input(checker: RemoteItemChecker):
        pass

    @staticmethod
    def test_check(checker: RemoteItemChecker):
        pass
