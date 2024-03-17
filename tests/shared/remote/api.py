from abc import ABC, abstractmethod
from copy import deepcopy
from random import sample, choice
from typing import Any
from urllib.parse import parse_qs

import pytest
# noinspection PyProtectedMember,PyUnresolvedReferences
from requests_mock.request import _RequestObjectProxy as Request

from musify.shared.remote.api import RemoteAPI
from musify.shared.remote.enum import RemoteObjectType
from musify.shared.remote.factory import RemoteObjectFactory
from tests.shared.remote.utils import RemoteMock


class RemoteAPITester(ABC):
    """Run generic tests for :py:class:`RemoteAPI` implementations."""

    @property
    @abstractmethod
    def id_key(self) -> str:
        """The key to use to get the ID of a response."""
        raise NotImplementedError

    @abstractmethod
    def object_factory(self) -> RemoteObjectFactory:
        """Yield the object factory for objects of this remote service type as a pytest.fixture"""
        raise NotImplementedError

    @pytest.fixture
    def responses(self, object_type: RemoteObjectType, api_mock: RemoteMock) -> dict[str, dict[str, Any]]:
        """Yields valid responses mapped by ID for a given ``object_type`` as a pytest.fixture"""
        api_mock.reset_mock()  # tests check the number of requests made
        source = api_mock.item_type_map[object_type]
        if len(source) > api_mock.limit_lower:
            source = sample(source, k=api_mock.limit_lower)

        return {response[self.id_key]: deepcopy(response) for response in source}

    @pytest.fixture
    def response(self, responses: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Yields a random valid response from a given set of ``responses`` as a pytest.fixture"""
        return choice(list(responses.values()))

    @pytest.fixture
    def extend(self, object_type: RemoteObjectType, api: RemoteAPI) -> bool:
        """For a given ``object_type``, should the API object attempt to extend the results"""
        return object_type in api.collection_item_map

    @pytest.fixture
    def key(self, object_type: RemoteObjectType, extend: bool, api: RemoteAPI) -> str:
        """For a given ``object_type``, determine the key of its sub objects if ``extend`` is True. None otherwise."""
        return api.collection_item_map[object_type].name.lower() + "s" if extend else None

    ###########################################################################
    ## Assertions
    ###########################################################################
    @staticmethod
    def assert_similar(source: dict[str, Any], test: dict[str, Any], *omit: str):
        """Check ``source`` and ``test`` are the same, skip comparing on ``key`` for performance"""
        expected = {k: v for k, v in source.items() if k not in omit}
        assert {k: v for k, v in test.items() if k not in omit} == expected

    @staticmethod
    def assert_different(source: dict[str, Any], test: dict[str, Any], *omit: str):
        """Check ``source`` and ``test`` are different, skip comparing on ``key`` for performance"""
        expected = {k: v for k, v in source.items() if k not in omit}
        assert {k: v for k, v in test.items() if k not in omit} != expected

    @staticmethod
    def assert_params(requests: list[Request], params: dict[str, Any] | list[dict[str, Any]]):
        """Check for expected ``params`` in the given ``requests``"""
        for request in requests:
            request_params = parse_qs(request.query)
            if isinstance(params, list):
                assert any(request_params[k][0] == param[k] for param in params for k in param)
                continue

            for k, v in params.items():
                assert k in request_params
                assert request_params[k][0] == params[k]
