from collections.abc import Callable
from dataclasses import dataclass
from random import sample
from typing import Any

from syncify.enums.tags import TagName
from syncify.processor.compare import ItemComparer
from syncify.local.playlist.match import LocalMatcher
from syncify.local.track import LocalTrack
from tests.common import random_str
from tests.local.track.common import random_tracks


def test_init():
    comparators = [
        ItemComparer(field=TagName.ALBUM, condition="is", expected="album name"),
        ItemComparer(field=TagName.ARTIST, condition="starts with", expected="artist")
    ]
    library_folder = "/Path/to/LIBRARY/on/linux"
    other_folders = ["../", "D:\\paTh\\on\\Windows"]
    exclude_paths = [f"{other_folders[1]}\\exclude\\{random_str()}.MP3" for _ in range(20)]
    include_paths = [f"{other_folders[1]}\\include\\{random_str()}.MP3" for _ in range(20)]

    matcher = LocalMatcher(
        comparators=comparators,
        include_paths=include_paths,
        exclude_paths=exclude_paths,
        library_folder=library_folder,
        other_folders=other_folders,
        check_existence=False
    )

    assert matcher.comparators == matcher.comparators
    assert matcher.original_folder == other_folders[1].rstrip("/\\")
    assert matcher.include_paths == [
        path.replace(other_folders[1], library_folder).replace("\\", "/").casefold() for path in include_paths
    ]
    assert matcher.exclude_paths == [
        path.replace(other_folders[1], library_folder).replace("\\", "/").casefold() for path in exclude_paths
    ]

    # removes paths from the include list that are present in both include and exclude lists
    exclude_paths = set(f"{other_folders[0]}/folder/{random_str(20, 50)}.MP3" for _ in range(20))
    include_paths = set(f"{other_folders[0]}/folder/{random_str(20, 50)}.MP3" for _ in range(20)) - exclude_paths

    matcher = LocalMatcher(
        comparators=comparators,
        include_paths=sorted(include_paths) + sorted(exclude_paths)[:5],
        exclude_paths=sorted(exclude_paths),
        library_folder=library_folder,
        other_folders=other_folders,
        check_existence=False
    )

    assert matcher.comparators == matcher.comparators
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


@dataclass
class MatchTestConfig:
    """Config setter for each match test"""
    comparators: list[ItemComparer]
    library_folder: str

    tracks: list[LocalTrack]
    tracks_album: list[LocalTrack]
    tracks_artist: list[LocalTrack]
    tracks_include: list[LocalTrack]
    tracks_exclude: list[LocalTrack]
    tracks_include_reduced: list[LocalTrack]

    sort_key: Callable[[LocalTrack], Any]


def get_config_for_match_test() -> MatchTestConfig:
    """Generate config for each match test"""
    library_folder = "/path/to/library"
    exclude_paths = [f"{library_folder}/exclude/{random_str()}.MP3" for _ in range(20)]
    include_paths = [f"{library_folder}/include/{random_str()}.MP3" for _ in range(20)]

    # set up track conditions to match on
    tracks = random_tracks(30)
    tracks_album = sample(tracks, 15)
    for track in tracks_album:
        track.album = "album name"
    tracks_artist = sample(tracks_album, 9)
    for track in tracks_artist:
        track.artist = "artist name"

    tracks_include = sample([track for track in tracks if track not in tracks_album], 7)
    for i, track in enumerate(tracks_include):
        track._path = include_paths[i]
    tracks_exclude = sample(tracks_artist, 3) + sample(tracks_include, 2)
    for i, track in enumerate(tracks_exclude):
        track._path = exclude_paths[i]

    return MatchTestConfig(
        comparators=[
            ItemComparer(field=TagName.ALBUM, condition="is", expected="album name"),
            ItemComparer(field=TagName.ARTIST, condition="starts with", expected="artist")
        ],
        library_folder=library_folder,
        tracks=tracks,
        tracks_album=tracks_album,
        tracks_artist=tracks_artist,
        tracks_include=tracks_include,
        tracks_exclude=tracks_exclude,
        tracks_include_reduced=[track for track in tracks_include if track not in tracks_exclude],
        sort_key=lambda t: t.path,
    )


def test_match_on_paths_only():
    config = get_config_for_match_test()
    matcher = LocalMatcher(
        include_paths=[track.path for track in config.tracks_include],
        exclude_paths=[track.path for track in config.tracks_exclude],
        check_existence=False
    )

    assert matcher.include_paths == [track.path.casefold() for track in config.tracks_include_reduced]
    assert matcher.exclude_paths == [track.path.casefold() for track in config.tracks_exclude]
    assert matcher.match(tracks=config.tracks) == config.tracks_include_reduced

    match_result = matcher.match(tracks=config.tracks, combine=False)
    assert match_result.include == config.tracks_include_reduced
    assert match_result.exclude == config.tracks_exclude
    assert len(match_result.compared) == 0


def test_match_on_paths_and_any_comparators():
    config = get_config_for_match_test()
    matcher = LocalMatcher(
        comparators=config.comparators,
        match_all=False,
        include_paths=[track.path for track in config.tracks_include],
        exclude_paths=[track.path for track in config.tracks_exclude],
        check_existence=False
    )

    tracks_album_reduced = [track for track in config.tracks_album if track not in config.tracks_exclude]
    matches = sorted(matcher.match(tracks=config.tracks), key=config.sort_key)
    assert matches == sorted(tracks_album_reduced + config.tracks_include_reduced, key=config.sort_key)

    match_result = matcher.match(tracks=config.tracks, combine=False)
    assert match_result.include == config.tracks_include_reduced
    assert match_result.exclude == config.tracks_exclude
    assert sorted(match_result.compared, key=config.sort_key) == sorted(config.tracks_album, key=config.sort_key)


def test_match_on_paths_and_all_comparators():
    config = get_config_for_match_test()
    matcher = LocalMatcher(
        comparators=config.comparators,
        match_all=True,
        include_paths=[track.path for track in config.tracks_include],
        exclude_paths=[track.path for track in config.tracks_exclude],
        check_existence=False
    )

    tracks_artist_reduced = [track for track in config.tracks_artist if track not in config.tracks_exclude]
    matches = sorted(matcher.match(tracks=config.tracks), key=config.sort_key)
    assert matches == sorted(tracks_artist_reduced + config.tracks_include_reduced, key=config.sort_key)

    match_result = matcher.match(tracks=config.tracks, combine=False)
    assert match_result.include == config.tracks_include_reduced
    assert match_result.exclude == config.tracks_exclude
    assert sorted(match_result.compared, key=config.sort_key) == sorted(config.tracks_artist, key=config.sort_key)
