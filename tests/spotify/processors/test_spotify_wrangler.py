import pytest

from syncify.exception import SyncifyEnumError
from syncify.remote.enums import RemoteIDType as IDType, RemoteObjectType as ObjectType
from syncify.remote.exception import RemoteError, RemoteIDTypeError, RemoteObjectTypeError
from syncify.spotify import URL_API, URL_EXT
from syncify.spotify.processors.wrangle import SpotifyDataWrangler
from tests.spotify.utils import random_id, random_ids


# TODO: add more test cases for when IDType is ID and ItemType is USER


# noinspection SpellCheckingInspection
def test_get_id_type(wrangler: SpotifyDataWrangler):
    assert wrangler.get_id_type(random_id()) == IDType.ID
    assert wrangler.get_id_type(f"spotify:show:{random_id()}") == IDType.URI
    assert wrangler.get_id_type(f"{URL_API}/{random_id()}") == IDType.URL
    assert wrangler.get_id_type(f"{URL_EXT}/{random_id()}") == IDType.URL_EXT

    with pytest.raises(RemoteIDTypeError):
        wrangler.get_id_type("Not an ID")


# noinspection SpellCheckingInspection
def test_validate_id_type(wrangler: SpotifyDataWrangler):
    assert wrangler.validate_id_type(random_id())
    assert wrangler.validate_id_type(f"spotify:show:{random_id()}")
    assert wrangler.validate_id_type(f"{URL_API}/{random_id()}")
    assert wrangler.validate_id_type(f"{URL_EXT}/{random_id()}")

    assert wrangler.validate_id_type(random_id(), kind=IDType.ID)
    assert wrangler.validate_id_type(f"spotify:show:{random_id()}", kind=IDType.URI)
    assert wrangler.validate_id_type(f"{URL_API}/{random_id()}", kind=IDType.URL)
    assert wrangler.validate_id_type(f"{URL_EXT}/{random_id()}", kind=IDType.URL_EXT)

    assert not wrangler.validate_id_type(random_id(), kind=IDType.URL)
    assert not wrangler.validate_id_type(f"spotify:show:{random_id()}", kind=IDType.URL_EXT)


# noinspection SpellCheckingInspection
def test_get_item_type(wrangler: SpotifyDataWrangler):
    assert wrangler.get_item_type(f"spotify:playlist:{random_id()}") == ObjectType.PLAYLIST
    assert wrangler.get_item_type(f"spotify:TRACK:{random_id()}") == ObjectType.TRACK
    assert wrangler.get_item_type(f"spotify:ALBUM:{random_id()}") == ObjectType.ALBUM
    assert wrangler.get_item_type(f"spotify:artist:{random_id()}") == ObjectType.ARTIST
    assert wrangler.get_item_type("spotify:user:ausername") == ObjectType.USER
    assert wrangler.get_item_type(f"spotify:show:{random_id()}") == ObjectType.SHOW
    assert wrangler.get_item_type(f"spotify:episode:{random_id()}") == ObjectType.EPISODE
    assert wrangler.get_item_type(f"spotify:audiobook:{random_id()}") == ObjectType.AUDIOBOOK
    assert wrangler.get_item_type(f"spotify:chapter:{random_id()}") == ObjectType.CHAPTER

    assert wrangler.get_item_type(f"{URL_API}/playlists/{random_id()}/followers") == ObjectType.PLAYLIST
    assert wrangler.get_item_type(f"{URL_EXT}/TRACKS/{random_id()}") == ObjectType.TRACK
    assert wrangler.get_item_type(f"{URL_API}/ALBUMS/{random_id()}") == ObjectType.ALBUM
    assert wrangler.get_item_type(f"{URL_EXT}/artists/{random_id()}") == ObjectType.ARTIST
    assert wrangler.get_item_type(f"{URL_EXT}/users/ausername") == ObjectType.USER
    assert wrangler.get_item_type(f"{URL_API}/shows/{random_id()}/episodes") == ObjectType.SHOW
    assert wrangler.get_item_type(f"{URL_EXT}/episodes/{random_id()}") == ObjectType.EPISODE
    assert wrangler.get_item_type(f"{URL_API}/audiobooks/{random_id()}/chapters") == ObjectType.AUDIOBOOK
    assert wrangler.get_item_type(f"{URL_EXT}/chapters/{random_id()}") == ObjectType.CHAPTER

    assert wrangler.get_item_type({"type": "playlist"}) == ObjectType.PLAYLIST
    assert wrangler.get_item_type({"type": "TRACK"}) == ObjectType.TRACK
    assert wrangler.get_item_type({"type": "album"}) == ObjectType.ALBUM
    assert wrangler.get_item_type({"type": "ARTIST"}) == ObjectType.ARTIST
    assert wrangler.get_item_type({"type": "user"}) == ObjectType.USER
    assert wrangler.get_item_type({"type": "show"}) == ObjectType.SHOW
    assert wrangler.get_item_type({"type": "episode"}) == ObjectType.EPISODE
    assert wrangler.get_item_type({"type": "audiobook"}) == ObjectType.AUDIOBOOK
    assert wrangler.get_item_type({"type": "chapter"}) == ObjectType.CHAPTER

    values = [
        {"type": "playlist"},
        f"{URL_EXT}/playlists/bnmhjkyuidfgertsdfertw/followers",
        "spotify:playlist:{random_id()}",
        "qwertyuiopASDFGHJKLZ12"
    ]
    assert wrangler.get_item_type(values) == ObjectType.PLAYLIST

    with pytest.raises(RemoteObjectTypeError):
        wrangler.get_item_type([])

    with pytest.raises(RemoteObjectTypeError):
        wrangler.get_item_type([random_id(), "qwertyuiopASDFGHJKLZ12"])

    with pytest.raises(RemoteObjectTypeError):
        values = [f"spotify:show:{random_id()}", {"type": "track"}]
        wrangler.get_item_type(values)

    with pytest.raises(RemoteObjectTypeError):
        values = [f"spotify:show:{random_id()}", f"{URL_API}/playlists/qwertyuiopASDFGHJKLZ12"]
        wrangler.get_item_type(values)

    with pytest.raises(RemoteObjectTypeError):
        response = {"type": "track", "is_local": True}
        wrangler.get_item_type(response)

    with pytest.raises(RemoteObjectTypeError):
        response = {"not_a_type": "track", "is_local": False}
        wrangler.get_item_type(response)

    with pytest.raises(RemoteObjectTypeError):
        wrangler.get_item_type(f"bad_uri:chapter:{random_id()}")

    with pytest.raises(SyncifyEnumError):
        wrangler.get_item_type(f"spotify:bad_type:{random_id()}")


# noinspection SpellCheckingInspection
def test_validate_item_type(wrangler: SpotifyDataWrangler):
    assert wrangler.validate_item_type(
        f"{URL_API}/playlist/{random_id()}/followers", kind=ObjectType.PLAYLIST
    ) is None
    assert wrangler.validate_item_type(random_id(), kind=ObjectType.TRACK) is None
    assert wrangler.validate_item_type({"type": "album", "id": random_id()}, kind=ObjectType.ALBUM) is None
    assert wrangler.validate_item_type(f"spotify:artist:{random_id()}", kind=ObjectType.ARTIST) is None
    assert wrangler.validate_item_type("spotify:user:ausername", kind=ObjectType.USER) is None
    assert wrangler.validate_item_type(f"{URL_API}/show/{random_id()}/episodes", kind=ObjectType.SHOW) is None
    assert wrangler.validate_item_type(f"spotify:episode:{random_id()}", kind=ObjectType.EPISODE) is None
    assert wrangler.validate_item_type(f"{URL_EXT}/audiobook/{random_id()}/chapters", kind=ObjectType.AUDIOBOOK) is None
    assert wrangler.validate_item_type(f"spotify:chapter:{random_id()}", kind=ObjectType.CHAPTER) is None

    values = [
        {"type": "playlist"},
        f"{URL_EXT}/playlist/bnmhjkyuidfgertsdfertw/followers",
        "spotify:playlist:{random_id()}",
        "qwertyuiopASDFGHJKLZ12"
    ]
    assert wrangler.validate_item_type(values, kind=ObjectType.PLAYLIST) is None

    with pytest.raises(RemoteObjectTypeError):
        wrangler.validate_item_type(values, kind=ObjectType.TRACK)


# noinspection SpellCheckingInspection
def test_convert(wrangler: SpotifyDataWrangler):
    id_ = random_id()
    assert wrangler.convert(id_, kind=ObjectType.EPISODE, type_out=IDType.URL) == f"{URL_API}/episodes/{id_}"
    assert wrangler.convert(id_, kind=ObjectType.EPISODE, type_out=IDType.URL_EXT) == f"{URL_EXT}/episode/{id_}"
    assert wrangler.convert(id_, kind=ObjectType.EPISODE, type_out=IDType.URI) == f"spotify:episode:{id_}"
    assert wrangler.convert(id_, kind=ObjectType.EPISODE) == id_

    assert wrangler.convert(f"spotify:episode:{id_}", type_out=IDType.URL) == f"{URL_API}/episodes/{id_}"
    assert wrangler.convert(f" spotify:episode:{id_} ", type_out=IDType.URL_EXT) == f"{URL_EXT}/episode/{id_}"
    assert wrangler.convert(f"spotify:episode:{id_}", type_out=IDType.URI) == f"spotify:episode:{id_}"
    assert wrangler.convert(f" spotify:episode:{id_}  ") == id_

    assert wrangler.convert(f"{URL_API}/episodes/{id_}", type_out=IDType.URL) == f"{URL_API}/episodes/{id_}"
    assert wrangler.convert(f"{URL_API}/episodes/{id_}", type_out=IDType.URL_EXT) == f"{URL_EXT}/episode/{id_}"
    assert wrangler.convert(f"{URL_API}/episodes/{id_}", type_out=IDType.URI) == f"spotify:episode:{id_}"
    assert wrangler.convert(f"{URL_API}/episodes/{id_}", type_out=IDType.ID) == id_

    assert wrangler.convert(f"{URL_EXT}/episode/{id_}", type_out=IDType.URL) == f"{URL_API}/episodes/{id_}"
    assert wrangler.convert(f"{URL_EXT}/episode/{id_}", type_out=IDType.URL_EXT) == f"{URL_EXT}/episode/{id_}"
    assert wrangler.convert(f"{URL_EXT}/episode/{id_}", type_out=IDType.URI) == f"spotify:episode:{id_}"
    assert wrangler.convert(f"{URL_EXT}/episode/{id_}") == id_

    # incorrect type in given still gives the right output
    assert wrangler.convert(
        f"spotify:episode:{id_}", type_in=IDType.URL, type_out=IDType.URL
    ) == f"{URL_API}/episodes/{id_}"

    # no ID type given when input value is ID raises error
    with pytest.raises(RemoteIDTypeError):
        wrangler.convert(id_, type_out=IDType.URI)

    with pytest.raises(RemoteIDTypeError):
        wrangler.convert("bad value", type_out=IDType.URI)


# noinspection SpellCheckingInspection
def test_extract_ids(wrangler: SpotifyDataWrangler):
    id_ = random_id()
    value = f"{URL_API}/playlists/8188181818181818129321/followers"
    assert wrangler.extract_ids(value) == ["8188181818181818129321"]
    value = f"{URL_EXT}/playlist/bnmhjkyuidfgertsdfertw/followers"
    assert wrangler.extract_ids(value) == ["bnmhjkyuidfgertsdfertw"]
    assert wrangler.extract_ids(f"spotify:playlist:{id_}") == [id_]
    assert wrangler.extract_ids(id_) == [id_]
    assert wrangler.extract_ids({"id": id_}) == [id_]

    expected = random_ids(start=4, stop=4)
    values = [
        f"{URL_API}/playlists/{expected[0]}/followers",
        f"{URL_EXT}/playlist/{expected[1]}/followers",
        f"spotify:playlist:{expected[2]}",
        expected[3]
    ]
    assert wrangler.extract_ids(values) == expected

    assert wrangler.extract_ids([{"id": i} for i in expected[:2]]) == expected[:2]

    with pytest.raises(RemoteError):
        wrangler.extract_ids([{"id": expected[0]}, {"type": "track"}])

    with pytest.raises(RemoteError):
        wrangler.extract_ids([{"id": expected[0]}, [f"spotify:playlist:{expected[1]}"]])
