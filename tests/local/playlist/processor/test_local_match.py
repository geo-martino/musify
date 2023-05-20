from random import sample
from typing import Callable, Any

from syncify.enums.tags import TagName
from syncify.local.track import LocalTrack
from syncify.local.playlist.processor import TrackCompare, TrackMatch
from tests.common import random_str
from tests.local.track.track import random_tracks


def test_init():
    comparators = [
        TrackCompare(field=TagName.ALBUM, condition="is", expected="album name"),
        TrackCompare(field=TagName.ARTIST, condition="starts with", expected="artist")
    ]
    library_folder = "/Path/to/LIBRARY/on/linux"
    other_folders = ["../", "D:\\paTh\\on\\Windows"]
    exclude_paths = [f"{other_folders[1]}\\exclude\\{random_str()}.MP3" for _ in range(20)]
    include_paths = [f"{other_folders[1]}\\include\\{random_str()}.MP3" for _ in range(20)]

    matcher = TrackMatch(
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
        path.replace(other_folders[1], library_folder).replace("\\", "/").lower() for path in include_paths
    ]
    assert matcher.exclude_paths == [
        path.replace(other_folders[1], library_folder).replace("\\", "/").lower() for path in exclude_paths
    ]

    # removes paths from the include list that are present in both include and exclude lists
    exclude_paths = set(f"{other_folders[0]}/folder/{random_str(20, 50)}.MP3" for _ in range(20))
    include_paths = set(f"{other_folders[0]}/folder/{random_str(20, 50)}.MP3" for _ in range(20)) - exclude_paths

    matcher = TrackMatch(
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
        path.replace(other_folders[0], library_folder).lower() for path in sorted(include_paths)
    ]
    assert matcher.exclude_paths == [
        path.replace(other_folders[0], library_folder).lower() for path in sorted(exclude_paths)
    ]

    # none of the random file paths exist, check existence should return empty lists
    matcher = TrackMatch(include_paths=list(include_paths), exclude_paths=exclude_paths, check_existence=True)
    assert matcher.include_paths == []
    assert matcher.exclude_paths == []


def test_match():
    comparators = [
        TrackCompare(field=TagName.ALBUM, condition="is", expected="album name"),
        TrackCompare(field=TagName.ARTIST, condition="starts with", expected="artist")
    ]
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
    tracks_include_reduced = [track for track in tracks_include if track not in tracks_exclude]

    sort_key: Callable[[LocalTrack], Any] = lambda t: t.path

    # match on paths only
    matcher = TrackMatch(
        include_paths=[track.path for track in tracks_include],
        exclude_paths=[track.path for track in tracks_exclude],
        check_existence=False
    )

    assert matcher.include_paths == [track.path.lower() for track in tracks_include_reduced]
    assert matcher.exclude_paths == [track.path.lower() for track in tracks_exclude]
    assert matcher.match(tracks=tracks) == tracks_include_reduced

    match_result = matcher.match(tracks=tracks, combine=False)
    assert match_result.include == tracks_include_reduced
    assert match_result.exclude == tracks_exclude
    assert len(match_result.compared) == 0

    # match on paths and any comparators
    matcher = TrackMatch(
        comparators=comparators,
        match_all=False,
        include_paths=[track.path for track in tracks_include],
        exclude_paths=[track.path for track in tracks_exclude],
        check_existence=False
    )

    tracks_album_reduced = [track for track in tracks_album if track not in tracks_exclude]
    matches = sorted(matcher.match(tracks=tracks), key=sort_key)
    assert matches == sorted(tracks_album_reduced + tracks_include_reduced, key=sort_key)

    match_result = matcher.match(tracks=tracks, combine=False)
    assert match_result.include == tracks_include_reduced
    assert match_result.exclude == tracks_exclude
    assert sorted(match_result.compared, key=sort_key) == sorted(tracks_album, key=sort_key)

    # match on paths and all comparators
    matcher = TrackMatch(
        comparators=comparators,
        match_all=True,
        include_paths=[track.path for track in tracks_include],
        exclude_paths=[track.path for track in tracks_exclude],
        check_existence=False
    )

    tracks_artist_reduced = [track for track in tracks_artist if track not in tracks_exclude]
    matches = sorted(matcher.match(tracks=tracks), key=sort_key)
    assert matches == sorted(tracks_artist_reduced + tracks_include_reduced, key=sort_key)

    match_result = matcher.match(tracks=tracks, combine=False)
    assert match_result.include == tracks_include_reduced
    assert match_result.exclude == tracks_exclude
    assert sorted(match_result.compared, key=sort_key) == sorted(tracks_artist, key=sort_key)
