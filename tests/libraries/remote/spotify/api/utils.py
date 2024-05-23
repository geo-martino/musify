from collections.abc import Collection, Mapping
from itertools import batched
from typing import Any

from tests.libraries.remote.spotify.api.mock import SpotifyMock


def get_limit(values: Collection | int, max_limit: int, pages: int = 3) -> int:
    """
    Get a limit value for the expected number of ``pages`` when testing the given ``values``.
    Limit maximum value to ``max_limit``.
    """
    total = len(values) if isinstance(values, Collection) else values
    limit = max(min(total // pages, max_limit), 1)  # force pagination

    assert total >= limit  # ensure ranges are valid for test to work
    return limit


def assert_calls(
        expected: Collection[Mapping[str, Any]],
        requests: Collection,
        api_mock: SpotifyMock,
        key: str | None = None,
        limit: int | None = None,
):
    """Assert an appropriate number of calls were made for multi- or batch- call functions"""
    # assume at least 1 call was made in the case where call returned 0 results i.e. len(expected) == 0
    initial_calls = max(len(list(batched(expected, limit))) if limit else len(expected), 1)
    extend_calls = 0
    if key:
        # minus 1 for initial call to get the collection unless all items were present in the initial call
        extend_calls += sum(max(api_mock.calculate_pages_from_response(expect) - 1, 0) for expect in expected)

    assert len(requests) == initial_calls + extend_calls
