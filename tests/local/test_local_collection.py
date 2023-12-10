from abc import ABCMeta
from collections.abc import Iterable
from random import randrange

import pytest

from syncify.local.collection import LocalFolder, LocalAlbum, LocalArtist, LocalGenres
from syncify.local.exception import LocalCollectionError
from syncify.local.track import LocalTrack
from tests import random_str
from tests.abstract.collection import ItemCollectionTester
from tests.local.track import random_tracks, random_track, path_track_resources, path_track_all


class LocalCollectionTester(ItemCollectionTester, metaclass=ABCMeta):

    @staticmethod
    @pytest.fixture
    def collection_merge_items() -> Iterable[LocalTrack]:
        return random_tracks(randrange(5, 10))


class TestLocalFolder(LocalCollectionTester):

    name = "folder name"

    @staticmethod
    @pytest.fixture
    def collection(folder: LocalFolder) -> LocalFolder:
        # needed to ensure __setitem__ check passes
        folder.tracks.append(random_track(cls=folder.tracks[0].__class__))
        return folder

    @pytest.fixture
    def folder(self, tracks: list[LocalTrack]) -> LocalFolder:
        """Yields a :py:class:`LocalFolder` object to be tested as pytest.fixture"""
        return LocalFolder(tracks=[track for track in tracks if track.folder == self.name])

    @pytest.fixture(scope="class")
    def tracks(self) -> list[LocalTrack]:
        """
        Yield a list of random LocalTracks with certain properties set to
        pass the filter test for this :py:class:`LocalCollection`
        """
        tracks = random_tracks(10)

        for i, track in enumerate(tracks[:7]):
            track._path = f"/test/{self.name}/{random_str(15, 20)}{track.ext}"
            if i < 4:
                track.compilation = True
            if i % 2 == 0:
                track.artist = "artist name"
                track.genres = ["rock", "pop"]
            if i % 2 != 0:
                track.artist = "another artist"
                track.genres = ["metal", "jazz"]

        return tracks
    
    @pytest.fixture(scope="class")
    def tracks_filtered(self, tracks: list[LocalTrack]) -> list[LocalTrack]:
        """Yield a list of tracks that match the conditions for this :py:class:`LocalCollection`"""
        return [track for track in tracks if track.folder == self.name]

    @staticmethod
    def test_init_fails(tracks: list[LocalTrack]):
        with pytest.raises(LocalCollectionError):
            LocalFolder(tracks=tracks)

    def test_filter(self, folder: LocalFolder, tracks_filtered: list[LocalTrack]):
        assert folder.name == self.name == folder.folder
        assert len(folder.tracks) == len(tracks_filtered)

        assert sorted(folder.artists) == sorted({track.artist for track in tracks_filtered if track.artist})
        assert folder.track_total == len(folder.tracks)
        genres = {genre for track in tracks_filtered if track.genres for genre in track.genres}
        assert sorted(folder.genres) == sorted(genres)
        assert folder.compilation
        assert folder.track_paths == {track.path for track in tracks_filtered}

        assert folder.last_added == sorted(tracks_filtered, key=lambda t: t.date_added, reverse=True)[0].date_added
        assert folder.last_played == sorted(tracks_filtered, key=lambda t: t.last_played, reverse=True)[0].last_played
        assert folder.play_count == sum(track.play_count for track in tracks_filtered if track.play_count)
    
    @staticmethod
    def test_empty_load():
        # load folder when no tracks given and only folder path given
        collection = LocalFolder(name=path_track_resources)
        assert {track.path for track in collection} == path_track_all


class TestLocalAlbum(LocalCollectionTester):

    name = "album name"

    @staticmethod
    @pytest.fixture
    def collection(album: LocalAlbum) -> LocalAlbum:
        # needed to ensure __setitem__ check passes
        album.tracks.append(random_track(cls=album.tracks[0].__class__))
        return album

    @pytest.fixture
    def album(self, tracks: list[LocalTrack]) -> LocalAlbum:
        """Yields a :py:class:`LocalAlbum` object to be tested as pytest.fixture"""
        return LocalAlbum(tracks=tracks.copy(), name=self.name)

    @pytest.fixture(scope="class")
    def tracks(self) -> list[LocalTrack]:
        """
        Yield a list of random LocalTracks with certain properties set to
        pass the filter test for this :py:class:`LocalCollection`
        """
        tracks = random_tracks(10)
        for i, track in enumerate(tracks[:7]):
            track.album = self.name
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

        return tracks
    
    @pytest.fixture(scope="class")
    def tracks_filtered(self, tracks: list[LocalTrack]) -> list[LocalTrack]:
        """Yield a list of tracks that match the conditions for this :py:class:`LocalCollection`"""
        return [track for track in tracks if track.album == self.name]

    @staticmethod
    def test_init_fails(tracks: list[LocalTrack]):
        with pytest.raises(LocalCollectionError):
            LocalAlbum(tracks=tracks)

    def test_filter(self, album: LocalAlbum, tracks_filtered: list[LocalTrack]):
        assert album.name == self.name == album.album
        assert len(album.tracks) == len(tracks_filtered)

        assert sorted(album.artists) == sorted({track.artist for track in tracks_filtered if track.artist})
        assert album.track_total == len(album.tracks)
        genres = {genre for track in tracks_filtered if track.genres for genre in track.genres}
        assert sorted(album.genres) == sorted(genres)
        assert not album.compilation
        ratings = list(track.rating for track in tracks_filtered if track.rating)
        if ratings:
            assert album.rating == sum(ratings) / len(ratings)
        else:
            assert album.rating is None
        assert album.track_paths == {track.path for track in tracks_filtered}

        assert album.last_added == sorted(tracks_filtered, key=lambda t: t.date_added, reverse=True)[0].date_added
        assert album.last_played == sorted(tracks_filtered, key=lambda t: t.last_played, reverse=True)[0].last_played
        assert album.play_count == sum(track.play_count for track in tracks_filtered if track.play_count)


class TestLocalArtist(LocalCollectionTester):

    name = "artist name"

    @staticmethod
    @pytest.fixture
    def collection(artist: LocalArtist) -> LocalArtist:
        # needed to ensure __setitem__ check passes
        artist.tracks.append(random_track(cls=artist.tracks[0].__class__))
        return artist

    @pytest.fixture
    def artist(self, tracks: list[LocalTrack]) -> LocalArtist:
        """Yields a :py:class:`LocalArtist` object to be tested as pytest.fixture"""
        return LocalArtist(tracks=tracks.copy(), name=self.name)

    @pytest.fixture(scope="class")
    def tracks(self) -> list[LocalTrack]:
        """
        Yield a list of random LocalTracks with certain properties set to
        pass the filter test for this :py:class:`LocalCollection`
        """
        tracks = random_tracks(10)
        for i, track in enumerate(tracks[:5]):
            track.artist = self.name
            if i % 2 == 0:
                track.album = "album name"
                track.genres = ["rock", "pop"]
            if i % 2 != 0:
                track.album = "another album"
                track.genres = None

        return tracks
    
    @pytest.fixture(scope="class")
    def tracks_filtered(self, tracks: list[LocalTrack]) -> list[LocalTrack]:
        """Yield a list of tracks that match the conditions for this :py:class:`LocalCollection`"""
        return [track for track in tracks if track.artist == self.name]

    @staticmethod
    def test_init_fails(tracks: list[LocalTrack]):
        with pytest.raises(LocalCollectionError):
            LocalArtist(tracks=tracks)

    def test_filter(self, artist: LocalArtist, tracks_filtered: list[LocalTrack]):
        assert artist.name == self.name == artist.artist
        assert len(artist.tracks) == len(tracks_filtered)

        assert sorted(artist.artists) == sorted({track.artist for track in tracks_filtered if track.artist})
        assert sorted(artist.albums) == sorted({track.album for track in tracks_filtered if track.album})
        assert artist.track_total == len(artist.tracks)
        genres = {genre for track in tracks_filtered if track.genres for genre in track.genres}
        assert sorted(artist.genres) == sorted(genres)
        ratings = list(track.rating for track in tracks_filtered if track.rating)
        if ratings:
            assert artist.rating == sum(ratings) / len(ratings)
        else:
            assert artist.rating is None
        assert artist.track_paths == {track.path for track in tracks_filtered}

        assert artist.last_added == sorted(tracks_filtered, key=lambda t: t.date_added, reverse=True)[0].date_added
        assert artist.last_played == sorted(tracks_filtered, key=lambda t: t.last_played, reverse=True)[0].last_played
        assert artist.play_count == sum(track.play_count for track in tracks_filtered if track.play_count)


class TestLocalGenres(LocalCollectionTester):

    name = "rock"

    @staticmethod
    @pytest.fixture
    def collection(genre: LocalGenres) -> LocalGenres:
        # needed to ensure __setitem__ check passes
        genre.tracks.append(random_track(cls=genre.tracks[0].__class__))
        return genre

    @pytest.fixture
    def genre(self, tracks: list[LocalTrack]) -> LocalGenres:
        """Yields a :py:class:`LocalGenres` object to be tested as pytest.fixture"""
        return LocalGenres(tracks=tracks.copy(), name=self.name)

    @pytest.fixture(scope="class")
    def tracks(self) -> list[LocalTrack]:
        """
        Yield a list of random LocalTracks with certain properties set to
        pass the filter test for this :py:class:`LocalCollection`
        """
        tracks = random_tracks(10)
        for i, track in enumerate(tracks):
            if i % 2 == 0 and i < 7:
                track.genres = [self.name, "pop"]
                track.artist = "artist name 1"
                track.album = "album name"
            elif i % 2 != 0 and i < 7:
                track.genres = ["metal", "jazz"]
                track.artist = "artist name 2"
                track.album = "album name"
            else:
                track.genres = ["dance", self.name]
                track.artist = "artist name 3"
                track.album = "album name"

        return tracks
    
    @pytest.fixture(scope="class")
    def tracks_filtered(self, tracks: list[LocalTrack]) -> list[LocalTrack]:
        """Yield a list of tracks that match the conditions for this :py:class:`LocalCollection`"""
        return [track for track in tracks if self.name in track.genres]

    @staticmethod
    def test_init_fails(tracks: list[LocalTrack]):
        with pytest.raises(LocalCollectionError):
            LocalGenres(tracks=tracks)

    def test_filter(self, genre: LocalGenres, tracks_filtered: list[LocalTrack]):
        assert genre.name == self.name == genre.genre
        assert len(genre.tracks) == len(tracks_filtered)

        assert sorted(genre.artists) == sorted({track.artist for track in tracks_filtered if track.artist})
        assert sorted(genre.albums) == sorted({track.album for track in tracks_filtered if track.album})
        assert genre.track_total == len(genre.tracks)
        genres = {genre for track in tracks_filtered if track.genres for genre in track.genres}
        assert sorted(genre.genres) == sorted(genres)
        assert genre.track_paths == {track.path for track in tracks_filtered}

        assert genre.last_added == sorted(tracks_filtered, key=lambda t: t.date_added, reverse=True)[0].date_added
        assert genre.last_played == sorted(tracks_filtered, key=lambda t: t.last_played, reverse=True)[0].last_played
        assert genre.play_count == sum(track.play_count for track in tracks_filtered if track.play_count)
