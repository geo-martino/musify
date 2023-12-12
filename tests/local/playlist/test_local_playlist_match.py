from random import sample

import pytest

from syncify.fields import LocalTrackField
from syncify.local.playlist import LocalMatcher
from syncify.local.track import LocalTrack
from syncify.processors.compare import ItemComparer
from tests import random_str
from tests.abstract.misc import PrettyPrinterTester
from tests.local.track import random_tracks


class TestLocalMatcher(PrettyPrinterTester):

    library_folder = "/path/to/library"

    @staticmethod
    @pytest.fixture(scope="class")
    def comparers() -> list[ItemComparer]:
        """Yields a list :py:class:`ItemComparer` objects to be used as pytest.fixture"""
        return [
            ItemComparer(field=LocalTrackField.ALBUM, condition="is", expected="album name"),
            ItemComparer(field=LocalTrackField.ARTIST, condition="starts with", expected="artist")
        ]

    @pytest.fixture
    def obj(self, comparers: list[ItemComparer]) -> LocalMatcher:
        return LocalMatcher(
            comparers=comparers,
            include_paths=[f"{self.library_folder}/include/{random_str()}.MP3" for _ in range(20)],
            exclude_paths=[f"{self.library_folder}/exclude/{random_str()}.MP3" for _ in range(20)],
            library_folder=self.library_folder,
            check_existence=False
        )

    @staticmethod
    def test_init_replaces_parent_folder(comparers: list[ItemComparer]):
        library_folder = "/Path/to/LIBRARY/on/linux"
        other_folders = ["../", "D:\\paTh\\on\\Windows"]
        exclude_paths = [f"{other_folders[1]}\\exclude\\{random_str()}.MP3" for _ in range(20)]
        include_paths = [f"{other_folders[1]}\\include\\{random_str()}.MP3" for _ in range(20)]

        matcher = LocalMatcher(
            comparers=comparers,
            include_paths=include_paths,
            exclude_paths=exclude_paths,
            library_folder=library_folder,
            other_folders=other_folders,
            check_existence=False
        )

        assert matcher.comparers == matcher.comparers
        assert matcher.original_folder == other_folders[1].rstrip("/\\")
        assert matcher.include_paths == [
            path.replace(other_folders[1], library_folder).replace("\\", "/").casefold() for path in include_paths
        ]
        assert matcher.exclude_paths == [
            path.replace(other_folders[1], library_folder).replace("\\", "/").casefold() for path in exclude_paths
        ]

    @staticmethod
    def test_init_include_and_exclude(comparers: list[ItemComparer]):
        # removes paths from the include list that are present in both include and exclude lists
        library_folder = "/Path/to/LIBRARY/on/linux"
        other_folders = ["../", "D:\\paTh\\on\\Windows"]
        exclude_paths = set(f"{other_folders[0]}/folder/{random_str()}.MP3" for _ in range(20))
        include_paths = set(f"{other_folders[0]}/folder/{random_str()}.MP3" for _ in range(20)) - exclude_paths

        matcher = LocalMatcher(
            comparers=comparers,
            include_paths=sorted(include_paths) + sorted(exclude_paths)[:5],
            exclude_paths=sorted(exclude_paths),
            library_folder=library_folder,
            other_folders=other_folders[0],
            check_existence=False
        )

        assert matcher.comparers == matcher.comparers
        assert matcher.original_folder == other_folders[0].rstrip("/\\")
        assert matcher.include_paths == [
            path.replace(other_folders[0], library_folder).casefold() for path in sorted(include_paths)
        ]
        assert matcher.exclude_paths == [
            path.replace(other_folders[0], library_folder).casefold() for path in sorted(exclude_paths)
        ]

        # none of the random file paths exist, check existence should return empty lists
        matcher = LocalMatcher(include_paths=include_paths, exclude_paths=exclude_paths, check_existence=True)
        assert matcher.include_paths == []
        assert matcher.exclude_paths == []

    @staticmethod
    def sort_key(track: LocalTrack) -> str:
        """The key to sort on when making assertions in tests"""
        return track.path

    @staticmethod
    @pytest.fixture(scope="class")
    def tracks() -> list[LocalTrack]:
        """Yield a list of random LocalTracks to use for testing the :py:class:`LocalMatcher`"""
        tracks = random_tracks(30)
        return tracks

    @staticmethod
    @pytest.fixture(scope="class")
    def tracks_album(tracks: list[LocalTrack]) -> list[LocalTrack]:
        """Sample the list of tracks to test and set the same album name for all these tracks"""
        tracks_album = sample(tracks, 15)
        for track in tracks_album:
            track.album = "album name"
        return tracks_album

    @staticmethod
    @pytest.fixture(scope="class")
    def tracks_artist(tracks_album: list[LocalTrack]) -> list[LocalTrack]:
        """Sample the list of tracks to test and set the same artist name for all these tracks"""
        tracks_artist = sample(tracks_album, 9)
        for track in tracks_artist:
            track.artist = "artist name"
        return tracks_artist

    @pytest.fixture(scope="class")
    def tracks_include(self, tracks: list[LocalTrack], tracks_album: list[LocalTrack]) -> list[LocalTrack]:
        """Sample the list of tracks to test and set the path to be included for all these tracks"""
        include_paths = [f"{self.library_folder}/include/{random_str()}.MP3" for _ in range(20)]
        tracks_include = sample([track for track in tracks if track not in tracks_album], 7)

        for i, track in enumerate(tracks_include):
            track._path = include_paths[i]
        return tracks_include

    @pytest.fixture(scope="class")
    def tracks_exclude(self, tracks_artist: list[LocalTrack], tracks_include: list[LocalTrack]) -> list[LocalTrack]:
        """Sample the list of tracks to test and set the path to be excluded for all these tracks"""
        exclude_paths = [f"{self.library_folder}/exclude/{random_str()}.MP3" for _ in range(20)]
        tracks_exclude = sample(tracks_artist, 3) + sample(tracks_include, 2)

        for i, track in enumerate(tracks_exclude):
            track._path = exclude_paths[i]
        return tracks_exclude

    @staticmethod
    def test_match_on_paths_only(
            tracks: list[LocalTrack], tracks_include: list[LocalTrack], tracks_exclude: list[LocalTrack],
    ):
        matcher = LocalMatcher(
            include_paths=[track.path for track in tracks_include],
            exclude_paths=[track.path for track in tracks_exclude],
            check_existence=False
        )
        tracks_include_reduced = [track for track in tracks_include if track not in tracks_exclude]

        assert matcher.include_paths == [track.path.casefold() for track in tracks_include_reduced]
        assert matcher.exclude_paths == [track.path.casefold() for track in tracks_exclude]
        assert matcher.match(tracks=tracks) == tracks_include_reduced

        match_result = matcher.match(tracks=tracks, combine=False)
        assert match_result.include == tracks_include_reduced
        assert match_result.exclude == tracks_exclude
        assert len(match_result.compare) == 0

    def test_match_on_paths_and_any_comparers(
            self,
            comparers: list[ItemComparer],
            tracks: list[LocalTrack],
            tracks_album: list[LocalTrack],
            tracks_include: list[LocalTrack],
            tracks_exclude: list[LocalTrack],
    ):
        matcher = LocalMatcher(
            comparers=comparers,
            match_all=False,
            include_paths=[track.path for track in tracks_include],
            exclude_paths=[track.path for track in tracks_exclude],
            check_existence=False
        )
        tracks_album_reduced = [track for track in tracks_album if track not in tracks_exclude]
        tracks_include_reduced = [track for track in tracks_include if track not in tracks_exclude]

        matches = sorted(matcher.match(tracks=tracks), key=self.sort_key)
        assert matches == sorted(tracks_album_reduced + tracks_include_reduced, key=self.sort_key)

        match_result = matcher.match(tracks=tracks, combine=False)
        assert match_result.include == tracks_include_reduced
        assert match_result.exclude == tracks_exclude
        assert sorted(match_result.compare, key=self.sort_key) == sorted(tracks_album, key=self.sort_key)

    def test_match_on_paths_and_all_comparers(
            self,
            comparers: list[ItemComparer],
            tracks: list[LocalTrack],
            tracks_album: list[LocalTrack],
            tracks_artist: list[LocalTrack],
            tracks_include: list[LocalTrack],
            tracks_exclude: list[LocalTrack],
    ):
        matcher = LocalMatcher(
            comparers=comparers,
            match_all=True,
            include_paths=[track.path for track in tracks_include],
            exclude_paths=[track.path for track in tracks_exclude],
            check_existence=False
        )
        tracks_artist_reduced = [track for track in tracks_artist if track not in tracks_exclude]
        tracks_include_reduced = [track for track in tracks_include if track not in tracks_exclude]

        matches = sorted(matcher.match(tracks=tracks), key=self.sort_key)
        assert matches == sorted(tracks_artist_reduced + tracks_include_reduced, key=self.sort_key)

        match_result = matcher.match(tracks=tracks, combine=False)
        assert match_result.include == tracks_include_reduced
        assert match_result.exclude == tracks_exclude
        assert sorted(match_result.compare, key=self.sort_key) == sorted(tracks_artist, key=self.sort_key)
