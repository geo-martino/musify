from typing import Any

from syncify.spotify.library import SpotifyObject


def assert_id_attributes(item: SpotifyObject, response: dict[str, Any]):
    """Check a given :py:class:`SpotifyObject` has the expected attributes relating to its identification"""
    assert item.has_uri
    assert item.uri == response["uri"]
    assert item.id == response["id"]
    assert item.url == response["href"]
    assert item.url_ext == response["external_urls"]["spotify"]
