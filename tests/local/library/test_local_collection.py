import pytest

from syncify.local.exception import LocalCollectionError
from syncify.local.library.collection import LocalFolder, LocalAlbum, LocalArtist, LocalGenres
from tests.local.track.common import random_tracks


def test_folder():
    tracks = random_tracks(10)

    for i, track in enumerate(tracks[:7]):
        track._path = "/test/folder name/file.ext"
        if i < 4:
            track.compilation = True
        if i % 2 == 0:
            track.artist = "artist name"
            track.genres = ["rock", "pop"]
        if i % 2 != 0:
            track.artist = "another artist"
            track.genres = ["metal", "jazz"]

    last_played = sorted(tracks[:7], key=lambda t: t.last_played, reverse=True)[0].last_played
    last_added = sorted(tracks[:7], key=lambda t: t.date_added, reverse=True)[0].date_added

    # test generic collection functionality
    with pytest.raises(LocalCollectionError):
        LocalFolder(tracks=tracks)

    collection = LocalFolder(tracks=tracks[:7])
    assert collection.name == tracks[0].folder
    assert collection.tracks == tracks[:7]
    assert collection.last_played == last_played
    assert collection.last_added == last_added

    assert collection.artists == [tracks[0].artist, tracks[1].artist]
    assert sorted(collection.genres) == sorted(set(tracks[0].genres) | set(tracks[1].genres))
    assert collection.compilation


def test_album():
    tracks = random_tracks(10)
    for i, track in enumerate(tracks[:7]):
        track.album = "album name"
        if i < 2:
            track.compilation = True
        else:
            track.compilation = False

        if i % 2 == 0:
            track.artist = "artist name"
            track.genres = ["rock", "pop"]
        if i % 2 != 0:
            track.artist = None
            track.genres = None

    collection = LocalAlbum(tracks=tracks, name=tracks[0].album)
    assert collection.name == tracks[0].album
    assert collection.artists == [tracks[0].artist]
    assert collection.genres == tracks[0].genres
    assert not collection.compilation


def test_artist():
    tracks = random_tracks(10)
    for i, track in enumerate(tracks[:5]):
        track.artist = "artist name"
        if i % 2 == 0:
            track.album = "album name"
            track.genres = ["rock", "pop"]
        if i % 2 != 0:
            track.album = "another album"
            track.genres = None

    collection = LocalArtist(tracks=tracks, name=tracks[0].artist)
    assert collection.name == tracks[0].artist
    assert collection.albums == [tracks[0].album, tracks[1].album]
    assert collection.genres == tracks[0].genres


def test_genre():
    tracks = random_tracks(10)
    for i, track in enumerate(tracks):
        if i % 2 == 0 and i < 7:
            track.genres = ["rock", "pop"]
            track.artist = "artist name 1"
            track.album = "album name"
        elif i % 2 != 0 and i < 7:
            track.genres = ["metal", "jazz"]
            track.artist = "artist name 2"
            track.album = "album name"
        else:
            track.genres = ["dance", "rock"]
            track.artist = "artist name 3"
            track.album = "album name"

    collection = LocalGenres(tracks=tracks, name="rock")
    assert collection.name == list(tracks[0].genres)[0]
    assert collection.artists == [tracks[0].artist, tracks[-1].artist]
    assert collection.albums == [tracks[0].album]
    assert sorted(collection.genres) == sorted(set(tracks[0].genres) | set(tracks[-1].genres))

