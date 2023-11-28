import pytest

from syncify.enums import EnumNotFoundError
from syncify.spotify import __URL_API__, __URL_EXT__
from syncify.spotify.enums import IDType, ItemType
from syncify.spotify.exception import SpotifyError, SpotifyIDTypeError, SpotifyItemTypeError
from syncify.spotify.utils import get_id_type, validate_id_type, get_item_type, validate_item_type, convert, extract_ids


# noinspection SpellCheckingInspection
def test_get_id_type():
    assert get_id_type("1234567890ASDFGHJKLZXC") == IDType.ID
    assert get_id_type("spotify:show:1234567890ASDFGHJKLZXC") == IDType.URI
    assert get_id_type(f"{__URL_API__}/1234567890ASDFGHJKLZXC") == IDType.URL
    assert get_id_type(f"{__URL_EXT__}/1234567890ASDFGHJKLZXC") == IDType.URL_EXT

    with pytest.raises(SpotifyIDTypeError):
        get_id_type("Not an ID")


# noinspection SpellCheckingInspection
def test_validate_id_type():
    assert validate_id_type("1234567890ASDFGHJKLZXC", kind=IDType.ID)
    assert validate_id_type("spotify:show:1234567890ASDFGHJKLZXC", kind=IDType.URI)
    assert validate_id_type(f"{__URL_API__}/1234567890ASDFGHJKLZXC", kind=IDType.URL)
    assert validate_id_type(f"{__URL_EXT__}/1234567890ASDFGHJKLZXC", kind=IDType.URL_EXT)

    assert not validate_id_type("1234567890ASDFGHJKLZXC", kind=IDType.URL)
    assert not validate_id_type("spotify:show:1234567890ASDFGHJKLZXC", kind=IDType.URL_EXT)


# noinspection SpellCheckingInspection
def test_get_item_type():
    assert get_item_type("spotify:playlist:1234567890ASDFGHJKLZXC") == ItemType.PLAYLIST
    assert get_item_type("spotify:TRACK:1234567890ASDFGHJKLZXC") == ItemType.TRACK
    assert get_item_type("spotify:ALBUM:1234567890ASDFGHJKLZXC") == ItemType.ALBUM
    assert get_item_type("spotify:artist:1234567890ASDFGHJKLZXC") == ItemType.ARTIST
    assert get_item_type("spotify:user:ausername") == ItemType.USER
    assert get_item_type("spotify:show:1234567890ASDFGHJKLZXC") == ItemType.SHOW
    assert get_item_type("spotify:episode:1234567890ASDFGHJKLZXC") == ItemType.EPISODE
    assert get_item_type("spotify:audiobook:1234567890ASDFGHJKLZXC") == ItemType.AUDIOBOOK
    assert get_item_type("spotify:chapter:1234567890ASDFGHJKLZXC") == ItemType.CHAPTER

    assert get_item_type(f"{__URL_API__}/playlists/1234567890ASDFGHJKLZXC/followers") == ItemType.PLAYLIST
    assert get_item_type(f"{__URL_EXT__}/TRACKS/1234567890ASDFGHJKLZXC") == ItemType.TRACK
    assert get_item_type(f"{__URL_API__}/ALBUMS/1234567890ASDFGHJKLZXC") == ItemType.ALBUM
    assert get_item_type(f"{__URL_EXT__}/artists/1234567890ASDFGHJKLZXC") == ItemType.ARTIST
    assert get_item_type(f"{__URL_EXT__}/users/ausername") == ItemType.USER
    assert get_item_type(f"{__URL_API__}/shows/1234567890ASDFGHJKLZXC/episodes") == ItemType.SHOW
    assert get_item_type(f"{__URL_EXT__}/episodes/1234567890ASDFGHJKLZXC") == ItemType.EPISODE
    assert get_item_type(f"{__URL_API__}/audiobooks/1234567890ASDFGHJKLZXC/chapters") == ItemType.AUDIOBOOK
    assert get_item_type(f"{__URL_EXT__}/chapters/1234567890ASDFGHJKLZXC") == ItemType.CHAPTER

    assert get_item_type({"type": "playlist"}) == ItemType.PLAYLIST
    assert get_item_type({"type": "TRACK"}) == ItemType.TRACK
    assert get_item_type({"type": "album"}) == ItemType.ALBUM
    assert get_item_type({"type": "ARTIST"}) == ItemType.ARTIST
    assert get_item_type({"type": "user"}) == ItemType.USER
    assert get_item_type({"type": "show"}) == ItemType.SHOW
    assert get_item_type({"type": "episode"}) == ItemType.EPISODE
    assert get_item_type({"type": "audiobook"}) == ItemType.AUDIOBOOK
    assert get_item_type({"type": "chapter"}) == ItemType.CHAPTER

    values = [
        {"type": "playlist"},
        f"{__URL_EXT__}/playlists/bnmhjkyuidfgertsdfertw/followers",
        "spotify:playlist:1234567890ASDFGHJKLZXC",
        "qwertyuiopASDFGHJKLZ12"
    ]
    assert get_item_type(values) == ItemType.PLAYLIST

    with pytest.raises(SpotifyItemTypeError):
        get_item_type([])

    with pytest.raises(SpotifyItemTypeError):
        get_item_type(["1234567890ASDFGHJKLZXC", "qwertyuiopASDFGHJKLZ12"])

    with pytest.raises(SpotifyItemTypeError):
        values = ["spotify:show:1234567890ASDFGHJKLZXC", {"type": "track"}]
        get_item_type(values)

    with pytest.raises(SpotifyItemTypeError):
        values = ["spotify:show:1234567890ASDFGHJKLZXC", f"{__URL_API__}/playlists/qwertyuiopASDFGHJKLZ12"]
        get_item_type(values)

    with pytest.raises(SpotifyItemTypeError):
        response = {"type": "track", "is_local": True}
        get_item_type(response)

    with pytest.raises(SpotifyItemTypeError):
        response = {"not_a_type": "track", "is_local": False}
        get_item_type(response)

    with pytest.raises(SpotifyItemTypeError):
        get_item_type("bad_uri:chapter:1234567890ASDFGHJKLZXC")

    with pytest.raises(EnumNotFoundError):
        get_item_type("spotify:bad_type:1234567890ASDFGHJKLZXC")


# noinspection SpellCheckingInspection
def test_validate_item_type():
    assert validate_item_type(
        f"{__URL_API__}/playlist/1234567890ASDFGHJKLZXC/followers", kind=ItemType.PLAYLIST
    ) is None
    assert validate_item_type(
        "1234567890ASDFGHJKLZXC", kind=ItemType.TRACK
    ) is None
    assert validate_item_type(
        {"type": "album", "id": "1234567890ASDFGHJKLZXC"}, kind=ItemType.ALBUM
    ) is None
    assert validate_item_type(
        "spotify:artist:1234567890ASDFGHJKLZXC", kind=ItemType.ARTIST
    ) is None
    assert validate_item_type(
        "spotify:user:ausername", kind=ItemType.USER
    ) is None
    assert validate_item_type(
        f"{__URL_API__}/show/1234567890ASDFGHJKLZXC/episodes", kind=ItemType.SHOW
    ) is None
    assert validate_item_type(
        "spotify:episode:1234567890ASDFGHJKLZXC", kind=ItemType.EPISODE
    ) is None
    assert validate_item_type(
        f"{__URL_EXT__}/audiobook/1234567890ASDFGHJKLZXC/chapters", kind=ItemType.AUDIOBOOK
    ) is None
    assert validate_item_type(
        "spotify:chapter:1234567890ASDFGHJKLZXC", kind=ItemType.CHAPTER
    ) is None

    values = [
        {"type": "playlist"},
        f"{__URL_EXT__}/playlist/bnmhjkyuidfgertsdfertw/followers",
        "spotify:playlist:1234567890ASDFGHJKLZXC",
        "qwertyuiopASDFGHJKLZ12"
    ]
    assert validate_item_type(values, kind=ItemType.PLAYLIST) is None

    with pytest.raises(SpotifyItemTypeError):
        validate_item_type(values, kind=ItemType.TRACK)


# noinspection SpellCheckingInspection
def test_convert():
    id_ = "1234567890ASDFGHJKLZXC"
    assert convert(id_, kind=ItemType.EPISODE, type_out=IDType.URL) == f"{__URL_API__}/episodes/{id_}"
    assert convert(id_, kind=ItemType.EPISODE, type_out=IDType.URL_EXT) == f"{__URL_EXT__}/episode/{id_}"
    assert convert(id_, kind=ItemType.EPISODE, type_out=IDType.URI) == f"spotify:episode:{id_}"
    assert convert(id_, kind=ItemType.EPISODE) == id_

    assert convert(f"spotify:episode:{id_}", type_out=IDType.URL) == f"{__URL_API__}/episodes/{id_}"
    assert convert(f" spotify:episode:{id_} ", type_out=IDType.URL_EXT) == f"{__URL_EXT__}/episode/{id_}"
    assert convert(f"spotify:episode:{id_}", type_out=IDType.URI) == f"spotify:episode:{id_}"
    assert convert(f" spotify:episode:{id_}  ") == id_

    assert convert(f"{__URL_API__}/episodes/{id_}", type_out=IDType.URL) == f"{__URL_API__}/episodes/{id_}"
    assert convert(f"{__URL_API__}/episodes/{id_}", type_out=IDType.URL_EXT) == f"{__URL_EXT__}/episode/{id_}"
    assert convert(f"{__URL_API__}/episodes/{id_}", type_out=IDType.URI) == f"spotify:episode:{id_}"
    assert convert(f"{__URL_API__}/episodes/{id_}", type_out=IDType.ID) == id_

    assert convert(f"{__URL_EXT__}/episode/{id_}", type_out=IDType.URL) == f"{__URL_API__}/episodes/{id_}"
    assert convert(f"{__URL_EXT__}/episode/{id_}", type_out=IDType.URL_EXT) == f"{__URL_EXT__}/episode/{id_}"
    assert convert(f"{__URL_EXT__}/episode/{id_}", type_out=IDType.URI) == f"spotify:episode:{id_}"
    assert convert(f"{__URL_EXT__}/episode/{id_}") == id_

    # incorrect type in given still gives the right output
    assert convert(f"spotify:episode:{id_}", type_in=IDType.URL,
                   type_out=IDType.URL) == f"{__URL_API__}/episodes/{id_}"

    # no ID type given when input value is ID raises error
    with pytest.raises(SpotifyIDTypeError):
        convert(id_, type_out=IDType.URI)

    with pytest.raises(SpotifyIDTypeError):
        convert("bad value", type_out=IDType.URI)


# noinspection SpellCheckingInspection
def test_extract_ids():
    value = f"{__URL_API__}/playlists/8188181818181818129321/followers"
    assert extract_ids(value) == ["8188181818181818129321"]
    value = f"{__URL_EXT__}/playlist/bnmhjkyuidfgertsdfertw/followers"
    assert extract_ids(value) == ["bnmhjkyuidfgertsdfertw"]
    assert extract_ids("spotify:playlist:1234567890ASDFGHJKLZXC") == ["1234567890ASDFGHJKLZXC"]
    assert extract_ids("1234567890ASDFGHJKLZXC") == ["1234567890ASDFGHJKLZXC"]
    assert extract_ids({"id": "1234567890ASDFGHJKLZXC"}) == ["1234567890ASDFGHJKLZXC"]

    values = [
        f"{__URL_API__}/playlists/8188181818181818129321/followers",
        f"{__URL_EXT__}/playlist/bnmhjkyuidfgertsdfertw/followers",
        "spotify:playlist:1234567890ASDFGHJKLZXC",
        "qwertyuiopASDFGHJKLZ12"
    ]
    expected = ["8188181818181818129321", "bnmhjkyuidfgertsdfertw", "1234567890ASDFGHJKLZXC", "qwertyuiopASDFGHJKLZ12"]
    assert extract_ids(values) == expected

    values = [
        {"id": "8188181818181818129321"},
        {"id": "bnmhjkyuidfgertsdfertw"},
        {"id": "1234567890ASDFGHJKLZXC"}
    ]
    expected = ["8188181818181818129321", "bnmhjkyuidfgertsdfertw", "1234567890ASDFGHJKLZXC"]
    assert extract_ids(values) == expected

    with pytest.raises(SpotifyError):
        extract_ids([{"id": "8188181818181818129321"}, {"type": "track"}])

    with pytest.raises(SpotifyError):
        extract_ids([{"id": "8188181818181818129321"}, ["spotify:playlist:1234567890ASDFGHJKLZXC"]])
