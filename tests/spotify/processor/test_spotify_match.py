from tests.local.track.track import random_track
from syncify.spotify.processor.match import ItemMatcher


def test_clean_tags():
    track = random_track()
    track.has_uri = True
    track.uri = "spotify:track:ASDFGHJKLQWERTYUIOPZX"

    track.title = "A Song Part 2"
    track.artist = "Artist 1 & Artist two Feat. Artist 3"
    track.album = "The Best EP - the new one"

    track_clean = ItemMatcher.clean_tags(track)
    assert id(track_clean) != id(track)
    assert track_clean == track
    assert track_clean.title == "song 2"
    assert track_clean.artist == "artist 1 artist two"
    assert track_clean.album == "best"


def test_match_not_karaoke():
    matcher = ItemMatcher()

    track = random_track()
    track.title = "title"
    track.artist = "artist"
    track.album = "album"

    assert matcher.match_not_karaoke(track, track) == 1

    track.title = "title backing"
    assert matcher.match_not_karaoke(track, track) == 0

    track.title = "title"
    track.album = "album instrumental"
    assert matcher.match_not_karaoke(track, track) == 0


def test_match_name():
    matcher = ItemMatcher()

    track1 = random_track()
    track2 = random_track()

    # no names in at least one item always returns 0
    track1.title = None
    track2.title = None
    assert matcher.match_name(track1, track2) == 0

    # 1/1 word match
    track1.title = "title"
    track2.title = "other title"
    assert matcher.match_name(track1, track2) == 1

    # 0/4 words match
    track1.title = "title of a track"
    track2.title = "song"
    assert matcher.match_name(track1, track2) == 0

    # 2/3 words match
    track1.title = "a longer title"
    track2.title = "this is a different title"
    assert round(matcher.match_name(track1, track2), 2) == 0.67


def test_match_artist():
    matcher = ItemMatcher()

    track1 = random_track()
    track2 = random_track()
    sep = track1.list_sep

    # no artists in at least one item always returns 0
    track1.artist = "artist"
    track2.artist = None
    assert matcher.match_artist(track1, track2) == 0

    # 1/4 words match
    track1.artist = f"band{sep}a singer{sep}artist"
    track2.artist = f"artist{sep}nope{sep}other"
    assert matcher.match_artist(track1, track2) == 0.25

    # 2/4 words match, but now weighted
    # match 'artist' = 0.25 + match 'singer' = 0.125
    track1.artist = f"band{sep}a singer{sep}artist"
    track2.artist = f"artist{sep}singer{sep}other"
    assert matcher.match_artist(track1, track2) == 0.375


def test_match_album():
    matcher = ItemMatcher()

    track1 = random_track()
    track2 = random_track()

    # no albums in at least one item always returns 0
    track1.album = None
    track2.album = "album"
    assert matcher.match_album(track1, track2) == 0

    # 1/2 words match
    track1.album = "album name"
    track2.album = "name"
    assert matcher.match_album(track1, track2) == 0.5

    # 3/3 words match
    track1.album = "brand new album"
    track2.album = "this is a brand new really cool album"
    assert matcher.match_album(track1, track2) == 1


def test_match_length():
    matcher = ItemMatcher()

    track1 = random_track()
    track2 = random_track()

    # no lengths for at least one item always returns 0
    track1.length = 110.20
    track2.length = None
    assert matcher.match_length(track1, track2) == 0

    track1.length = 100
    track2.length = 90
    assert matcher.match_length(track1, track2) == 0.9


def test_match_year():
    matcher = ItemMatcher()
    matcher.year_range = 10  # 10 year range max difference

    track1 = random_track()
    track2 = random_track()

    # no year for at least one item always returns 0
    track1.year = 2023
    track2.year = None
    assert matcher.match_year(track1, track2) == 0

    track1.year = 2020
    track2.year = 2015
    assert matcher.match_year(track1, track2) == 0.5

    track1.year = 2020
    track2.year = 2010
    assert matcher.match_year(track1, track2) == 0

    track1.year = 2020
    track2.year = 2005
    assert matcher.match_year(track1, track2) == 0


def test_match_score():
    matcher = ItemMatcher()
    matcher.year_range = 10  # 10 year range max difference

    track1 = random_track()
    track2 = random_track()
    sep = track1.list_sep

    track1.title = "a longer title"
    track2.title = "this is a different title"
    track1.artist = f"band{sep}a singer{sep}artist"
    track2.artist = f"nope"
    track1.album = "album"
    track2.album = "name"
    track1.length = 100
    track2.length = 10
    track1.year = 2020
    track2.year = 2010

    # track2 score is below min_score
    assert matcher.score_match(track1, [track2], min_score=0.2, max_score=0.8) is None

    # track3 score is above min_score
    track3 = random_track()
    track3.title = "this is a different title"
    track3.artist = f"artist{sep}nope{sep}other"
    track3.year = 2015
    assert matcher.score_match(track1, [track2, track3], min_score=0.2, max_score=0.8) == track3

    # track4 score is above max_score causing an early stop
    track4 = random_track()
    track4.title = "a longer title"
    track4.artist = f"band{sep}a singer{sep}artist"
    track4.album = "album"
    track4.length = 100
    track4.year = 2015
    assert matcher.score_match(track1, [track2, track4, track3], min_score=0.2, max_score=0.8) == track4
