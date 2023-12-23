from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from copy import copy
from urllib.parse import parse_qs

import pytest

from syncify.abstract.collection import BasicCollection, Album, ItemCollection
from syncify.abstract.item import Item
from syncify.remote.api import RemoteAPI
from syncify.remote.enums import RemoteObjectType
from syncify.remote.processors.check import RemoteItemChecker
from tests.local.utils import random_track, random_tracks
from tests.remote.utils import RemoteMock


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
