import pytest

from syncify.exception import EnumNotFoundError
from syncify.remote.enums import RemoteIDType, RemoteItemType
from syncify.remote.exception import RemoteError, RemoteIDTypeError, RemoteItemTypeError
from syncify.spotify import URL_API, URL_EXT
from syncify.spotify.processors.wrangle import SpotifyDataWrangler


# noinspection SpellCheckingInspection
def test_get_id_type():
    wrangler = SpotifyDataWrangler()
        
    assert wrangler.get_id_type("1234567890ASDFGHJKLZXC") == RemoteIDType.ID
    assert wrangler.get_id_type("spotify:show:1234567890ASDFGHJKLZXC") == RemoteIDType.URI
    assert wrangler.get_id_type(f"{URL_API}/1234567890ASDFGHJKLZXC") == RemoteIDType.URL
    assert wrangler.get_id_type(f"{URL_EXT}/1234567890ASDFGHJKLZXC") == RemoteIDType.URL_EXT

    with pytest.raises(RemoteIDTypeError):
        wrangler.get_id_type("Not an ID")


# noinspection SpellCheckingInspection
def test_validate_id_type():
    wrangler = SpotifyDataWrangler()
    
    assert wrangler.validate_id_type("1234567890ASDFGHJKLZXC")
    assert wrangler.validate_id_type("spotify:show:1234567890ASDFGHJKLZXC")
    assert wrangler.validate_id_type(f"{URL_API}/1234567890ASDFGHJKLZXC")
    assert wrangler.validate_id_type(f"{URL_EXT}/1234567890ASDFGHJKLZXC")

    assert wrangler.validate_id_type("1234567890ASDFGHJKLZXC", kind=RemoteIDType.ID)
    assert wrangler.validate_id_type("spotify:show:1234567890ASDFGHJKLZXC", kind=RemoteIDType.URI)
    assert wrangler.validate_id_type(f"{URL_API}/1234567890ASDFGHJKLZXC", kind=RemoteIDType.URL)
    assert wrangler.validate_id_type(f"{URL_EXT}/1234567890ASDFGHJKLZXC", kind=RemoteIDType.URL_EXT)

    assert not wrangler.validate_id_type("1234567890ASDFGHJKLZXC", kind=RemoteIDType.URL)
    assert not wrangler.validate_id_type("spotify:show:1234567890ASDFGHJKLZXC", kind=RemoteIDType.URL_EXT)


# noinspection SpellCheckingInspection
def test_get_item_type():
    wrangler = SpotifyDataWrangler()
    
    assert wrangler.get_item_type("spotify:playlist:1234567890ASDFGHJKLZXC") == RemoteItemType.PLAYLIST
    assert wrangler.get_item_type("spotify:TRACK:1234567890ASDFGHJKLZXC") == RemoteItemType.TRACK
    assert wrangler.get_item_type("spotify:ALBUM:1234567890ASDFGHJKLZXC") == RemoteItemType.ALBUM
    assert wrangler.get_item_type("spotify:artist:1234567890ASDFGHJKLZXC") == RemoteItemType.ARTIST
    assert wrangler.get_item_type("spotify:user:ausername") == RemoteItemType.USER
    assert wrangler.get_item_type("spotify:show:1234567890ASDFGHJKLZXC") == RemoteItemType.SHOW
    assert wrangler.get_item_type("spotify:episode:1234567890ASDFGHJKLZXC") == RemoteItemType.EPISODE
    assert wrangler.get_item_type("spotify:audiobook:1234567890ASDFGHJKLZXC") == RemoteItemType.AUDIOBOOK
    assert wrangler.get_item_type("spotify:chapter:1234567890ASDFGHJKLZXC") == RemoteItemType.CHAPTER

    assert wrangler.get_item_type(
        f"{URL_API}/playlists/1234567890ASDFGHJKLZXC/followers"
    ) == RemoteItemType.PLAYLIST
    assert wrangler.get_item_type(f"{URL_EXT}/TRACKS/1234567890ASDFGHJKLZXC") == RemoteItemType.TRACK
    assert wrangler.get_item_type(f"{URL_API}/ALBUMS/1234567890ASDFGHJKLZXC") == RemoteItemType.ALBUM
    assert wrangler.get_item_type(f"{URL_EXT}/artists/1234567890ASDFGHJKLZXC") == RemoteItemType.ARTIST
    assert wrangler.get_item_type(f"{URL_EXT}/users/ausername") == RemoteItemType.USER
    assert wrangler.get_item_type(f"{URL_API}/shows/1234567890ASDFGHJKLZXC/episodes") == RemoteItemType.SHOW
    assert wrangler.get_item_type(f"{URL_EXT}/episodes/1234567890ASDFGHJKLZXC") == RemoteItemType.EPISODE
    assert wrangler.get_item_type(
        f"{URL_API}/audiobooks/1234567890ASDFGHJKLZXC/chapters"
    ) == RemoteItemType.AUDIOBOOK
    assert wrangler.get_item_type(f"{URL_EXT}/chapters/1234567890ASDFGHJKLZXC") == RemoteItemType.CHAPTER

    assert wrangler.get_item_type({"type": "playlist"}) == RemoteItemType.PLAYLIST
    assert wrangler.get_item_type({"type": "TRACK"}) == RemoteItemType.TRACK
    assert wrangler.get_item_type({"type": "album"}) == RemoteItemType.ALBUM
    assert wrangler.get_item_type({"type": "ARTIST"}) == RemoteItemType.ARTIST
    assert wrangler.get_item_type({"type": "user"}) == RemoteItemType.USER
    assert wrangler.get_item_type({"type": "show"}) == RemoteItemType.SHOW
    assert wrangler.get_item_type({"type": "episode"}) == RemoteItemType.EPISODE
    assert wrangler.get_item_type({"type": "audiobook"}) == RemoteItemType.AUDIOBOOK
    assert wrangler.get_item_type({"type": "chapter"}) == RemoteItemType.CHAPTER

    values = [
        {"type": "playlist"},
        f"{URL_EXT}/playlists/bnmhjkyuidfgertsdfertw/followers",
        "spotify:playlist:1234567890ASDFGHJKLZXC",
        "qwertyuiopASDFGHJKLZ12"
    ]
    assert wrangler.get_item_type(values) == RemoteItemType.PLAYLIST

    with pytest.raises(RemoteItemTypeError):
        wrangler.get_item_type([])

    with pytest.raises(RemoteItemTypeError):
        wrangler.get_item_type(["1234567890ASDFGHJKLZXC", "qwertyuiopASDFGHJKLZ12"])

    with pytest.raises(RemoteItemTypeError):
        values = ["spotify:show:1234567890ASDFGHJKLZXC", {"type": "track"}]
        wrangler.get_item_type(values)

    with pytest.raises(RemoteItemTypeError):
        values = ["spotify:show:1234567890ASDFGHJKLZXC", f"{URL_API}/playlists/qwertyuiopASDFGHJKLZ12"]
        wrangler.get_item_type(values)

    with pytest.raises(RemoteItemTypeError):
        response = {"type": "track", "is_local": True}
        wrangler.get_item_type(response)

    with pytest.raises(RemoteItemTypeError):
        response = {"not_a_type": "track", "is_local": False}
        wrangler.get_item_type(response)

    with pytest.raises(RemoteItemTypeError):
        wrangler.get_item_type("bad_uri:chapter:1234567890ASDFGHJKLZXC")

    with pytest.raises(EnumNotFoundError):
        wrangler.get_item_type("spotify:bad_type:1234567890ASDFGHJKLZXC")


# noinspection SpellCheckingInspection
def test_validate_item_type():
    wrangler = SpotifyDataWrangler()
    
    assert wrangler.validate_item_type(
        f"{URL_API}/playlist/1234567890ASDFGHJKLZXC/followers", kind=RemoteItemType.PLAYLIST
    ) is None
    assert wrangler.validate_item_type("1234567890ASDFGHJKLZXC", kind=RemoteItemType.TRACK) is None
    assert wrangler.validate_item_type(
        {"type": "album", "id": "1234567890ASDFGHJKLZXC"}, kind=RemoteItemType.ALBUM
    ) is None
    assert wrangler.validate_item_type(
        "spotify:artist:1234567890ASDFGHJKLZXC", kind=RemoteItemType.ARTIST
    ) is None
    assert wrangler.validate_item_type("spotify:user:ausername", kind=RemoteItemType.USER) is None
    assert wrangler.validate_item_type(
        f"{URL_API}/show/1234567890ASDFGHJKLZXC/episodes", kind=RemoteItemType.SHOW
    ) is None
    assert wrangler.validate_item_type(
        "spotify:episode:1234567890ASDFGHJKLZXC", kind=RemoteItemType.EPISODE
    ) is None
    assert wrangler.validate_item_type(
        f"{URL_EXT}/audiobook/1234567890ASDFGHJKLZXC/chapters", kind=RemoteItemType.AUDIOBOOK
    ) is None
    assert wrangler.validate_item_type(
        "spotify:chapter:1234567890ASDFGHJKLZXC", kind=RemoteItemType.CHAPTER
    ) is None

    values = [
        {"type": "playlist"},
        f"{URL_EXT}/playlist/bnmhjkyuidfgertsdfertw/followers",
        "spotify:playlist:1234567890ASDFGHJKLZXC",
        "qwertyuiopASDFGHJKLZ12"
    ]
    assert wrangler.validate_item_type(values, kind=RemoteItemType.PLAYLIST) is None

    with pytest.raises(RemoteItemTypeError):
        wrangler.validate_item_type(values, kind=RemoteItemType.TRACK)


# noinspection SpellCheckingInspection
def test_convert():
    wrangler = SpotifyDataWrangler()
    
    id_ = "1234567890ASDFGHJKLZXC"
    assert wrangler.convert(
        id_, kind=RemoteItemType.EPISODE, type_out=RemoteIDType.URL
    ) == f"{URL_API}/episodes/{id_}"
    assert wrangler.convert(
        id_, kind=RemoteItemType.EPISODE, type_out=RemoteIDType.URL_EXT
    ) == f"{URL_EXT}/episode/{id_}"
    assert wrangler.convert(
        id_, kind=RemoteItemType.EPISODE, type_out=RemoteIDType.URI
    ) == f"spotify:episode:{id_}"
    assert wrangler.convert(id_, kind=RemoteItemType.EPISODE) == id_

    assert wrangler.convert(
        f"spotify:episode:{id_}", type_out=RemoteIDType.URL
    ) == f"{URL_API}/episodes/{id_}"
    assert wrangler.convert(
        f" spotify:episode:{id_} ", type_out=RemoteIDType.URL_EXT
    ) == f"{URL_EXT}/episode/{id_}"
    assert wrangler.convert(f"spotify:episode:{id_}", type_out=RemoteIDType.URI) == f"spotify:episode:{id_}"
    assert wrangler.convert(f" spotify:episode:{id_}  ") == id_

    assert wrangler.convert(
        f"{URL_API}/episodes/{id_}", type_out=RemoteIDType.URL
    ) == f"{URL_API}/episodes/{id_}"
    assert wrangler.convert(
        f"{URL_API}/episodes/{id_}", type_out=RemoteIDType.URL_EXT
    ) == f"{URL_EXT}/episode/{id_}"
    assert wrangler.convert(
        f"{URL_API}/episodes/{id_}", type_out=RemoteIDType.URI
    ) == f"spotify:episode:{id_}"
    assert wrangler.convert(f"{URL_API}/episodes/{id_}", type_out=RemoteIDType.ID) == id_

    assert wrangler.convert(
        f"{URL_EXT}/episode/{id_}", type_out=RemoteIDType.URL
    ) == f"{URL_API}/episodes/{id_}"
    assert wrangler.convert(
        f"{URL_EXT}/episode/{id_}", type_out=RemoteIDType.URL_EXT
    ) == f"{URL_EXT}/episode/{id_}"
    assert wrangler.convert(
        f"{URL_EXT}/episode/{id_}", type_out=RemoteIDType.URI
    ) == f"spotify:episode:{id_}"
    assert wrangler.convert(f"{URL_EXT}/episode/{id_}") == id_

    # incorrect type in given still gives the right output
    assert wrangler.convert(
        f"spotify:episode:{id_}", type_in=RemoteIDType.URL, type_out=RemoteIDType.URL
    ) == f"{URL_API}/episodes/{id_}"

    # no ID type given when input value is ID raises error
    with pytest.raises(RemoteIDTypeError):
        wrangler.convert(id_, type_out=RemoteIDType.URI)

    with pytest.raises(RemoteIDTypeError):
        wrangler.convert("bad value", type_out=RemoteIDType.URI)


# noinspection SpellCheckingInspection
def test_extract_ids():
    wrangler = SpotifyDataWrangler()
    
    value = f"{URL_API}/playlists/8188181818181818129321/followers"
    assert wrangler.extract_ids(value) == ["8188181818181818129321"]
    value = f"{URL_EXT}/playlist/bnmhjkyuidfgertsdfertw/followers"
    assert wrangler.extract_ids(value) == ["bnmhjkyuidfgertsdfertw"]
    assert wrangler.extract_ids("spotify:playlist:1234567890ASDFGHJKLZXC") == ["1234567890ASDFGHJKLZXC"]
    assert wrangler.extract_ids("1234567890ASDFGHJKLZXC") == ["1234567890ASDFGHJKLZXC"]
    assert wrangler.extract_ids({"id": "1234567890ASDFGHJKLZXC"}) == ["1234567890ASDFGHJKLZXC"]

    values = [
        f"{URL_API}/playlists/8188181818181818129321/followers",
        f"{URL_EXT}/playlist/bnmhjkyuidfgertsdfertw/followers",
        "spotify:playlist:1234567890ASDFGHJKLZXC",
        "qwertyuiopASDFGHJKLZ12"
    ]
    expected = ["8188181818181818129321", "bnmhjkyuidfgertsdfertw", "1234567890ASDFGHJKLZXC", "qwertyuiopASDFGHJKLZ12"]
    assert wrangler.extract_ids(values) == expected

    values = [
        {"id": "8188181818181818129321"},
        {"id": "bnmhjkyuidfgertsdfertw"},
        {"id": "1234567890ASDFGHJKLZXC"}
    ]
    expected = ["8188181818181818129321", "bnmhjkyuidfgertsdfertw", "1234567890ASDFGHJKLZXC"]
    assert wrangler.extract_ids(values) == expected

    with pytest.raises(RemoteError):
        wrangler.extract_ids([{"id": "8188181818181818129321"}, {"type": "track"}])

    with pytest.raises(RemoteError):
        wrangler.extract_ids([{"id": "8188181818181818129321"}, ["spotify:playlist:1234567890ASDFGHJKLZXC"]])
