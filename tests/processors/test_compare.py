from datetime import datetime, date, timedelta

import pytest
import xmltodict

from musify.field import TrackField
from musify.libraries.local.track import MP3, M4A, FLAC
from musify.libraries.local.track.field import LocalTrackField
from musify.processors.compare import Comparer
from musify.processors.exception import ComparerError, ProcessorLookupError
from musify.utils import to_collection
from tests.core.printer import PrettyPrinterTester
from tests.libraries.local.track.utils import random_track
from tests.libraries.local.utils import path_playlist_xautopf_bp, path_playlist_xautopf_ra


class TestComparer(PrettyPrinterTester):

    @pytest.fixture
    def obj(self) -> Comparer:
        return Comparer(condition=" is  _", expected=[".mp3", ".flac"], field=LocalTrackField.EXT)

    @pytest.fixture
    def track(self) -> MP3:
        """Yields a :py:class:`MP3` object to be tested as pytest.fixture"""
        return random_track(MP3)

    def test_init_fails(self):
        with pytest.raises(ProcessorLookupError):
            Comparer(condition="this cond does not exist", field=LocalTrackField.EXT)

    def test_init_1(self):
        comparer = Comparer(condition="Contains", field=TrackField.IMAGES)
        assert comparer.field == TrackField.IMAGES
        assert comparer._expected is None
        assert not comparer._converted
        assert comparer.condition == "contains"
        assert comparer._processor_method == comparer._contains

    def test_init_2(self):
        comparer = Comparer(condition="___greater than_  ", field=LocalTrackField.DATE_ADDED)
        assert comparer.field == LocalTrackField.DATE_ADDED
        assert not comparer._converted
        assert comparer._expected is None
        assert comparer.condition == "greater_than"
        assert comparer._processor_method == comparer._is_after

    def test_init_3(self):
        comparer = Comparer(condition=" is  _", expected=[".mp3", ".flac"], field=LocalTrackField.EXT)
        assert comparer.field == LocalTrackField.EXT
        assert not comparer._converted
        assert comparer._expected == [".mp3", ".flac"]
        assert comparer.condition == "is"
        assert comparer._processor_method == comparer._is

    def test_compare_with_reference(self):
        track_1 = random_track()
        track_2 = random_track()

        comparer = Comparer(condition="StartsWith", field=TrackField.ALBUM)
        assert comparer._expected is None
        assert not comparer._converted

        with pytest.raises(ComparerError):
            comparer.compare(item=track_1)

        track_1.album = "album 124 is a great album"
        track_2.album = "album"
        assert comparer.compare(item=track_1, reference=track_2)
        assert comparer(item=track_1, reference=track_2)
        assert comparer._expected is None
        assert not comparer._converted

        with pytest.raises(ComparerError):
            comparer.compare(item=track_1)

    def test_compare_str(self, track: MP3):
        comparer = Comparer(condition=" is  _", expected=[".mp3", ".flac"], field=LocalTrackField.EXT)
        assert comparer._expected == [".mp3", ".flac"]
        assert comparer._processor_method == comparer._is

        assert track.ext == ".mp3"
        assert comparer.compare(track)
        assert comparer(track)
        assert comparer._expected == [".mp3", ".flac"]
        assert not comparer.compare(random_track(FLAC))
        assert not comparer.compare(random_track(M4A))

    def test_compare_int(self, track: MP3):
        comparer = Comparer(condition="is in", expected=["1", 2, "3"], field=TrackField.TRACK)
        assert comparer._expected == ["1", 2, "3"]
        assert not comparer._converted
        assert comparer._processor_method == comparer._is_in

        track.track_number = 3
        assert comparer.compare(track)
        assert comparer._expected == [1, 2, 3]
        assert comparer._converted

        track.track_number = 4
        assert not comparer.compare(track)
        assert comparer._expected == [1, 2, 3]
        assert comparer._converted

    def test_compare_int_for_times(self, track: MP3):
        comparer = Comparer(condition="greater than", expected="1:30,618", field=TrackField.RATING)
        assert comparer._expected == ["1:30,618"]
        assert not comparer._converted
        assert comparer._processor_method == comparer._is_after

        track.rating = 120
        assert comparer.compare(track)
        assert comparer._expected == [90]
        assert comparer._converted
        track.rating = 60
        assert not comparer.compare(track)
        assert comparer._expected == [90]
        assert comparer._converted

    def test_compare_float(self, track: MP3):
        comparer = Comparer(condition="in_range", expected=["81.96", 100.23], field=TrackField.BPM)
        assert comparer._expected == ["81.96", 100.23]
        assert not comparer._converted
        assert comparer._processor_method == comparer._in_range

        track.bpm = 90.0
        assert comparer.compare(track)
        assert comparer._expected == [81.96, 100.23]
        assert comparer._converted

        # does not convert again when giving a value of a different type
        track.bpm = 120
        assert not comparer.compare(track)
        assert comparer._expected == [81.96, 100.23]
        assert comparer._converted

    def test_compare_date(self, track: MP3):
        comparer = Comparer(
            condition="is", expected=datetime(2023, 4, 21, 19, 20), field=LocalTrackField.DATE_ADDED
        )
        assert comparer._expected == [datetime(2023, 4, 21, 19, 20)]
        assert not comparer._converted
        assert comparer._processor_method == comparer._is

        track.date_added = datetime(2023, 4, 21, 11, 30, 49, 203)
        assert comparer.compare(track)
        assert comparer._expected == [date(2023, 4, 21)]
        assert comparer._converted

    def test_compare_date_str(self, track: MP3):
        comparer = Comparer(condition="is_not", expected="20/01/01", field=LocalTrackField.DATE_ADDED)
        assert comparer._expected == ["20/01/01"]
        assert not comparer._converted
        assert comparer._processor_method == comparer._is_not

        assert comparer.compare(track)
        assert comparer._expected == [date(2001, 1, 20)]
        assert comparer._converted

        comparer = Comparer(condition="is_not", expected="13/8/2004", field=LocalTrackField.DATE_ADDED)
        assert comparer._expected == ["13/8/2004"]
        assert not comparer._converted
        assert comparer._processor_method == comparer._is_not

        assert comparer.compare(track)
        assert comparer._expected == [date(2004, 8, 13)]
        assert comparer._converted

    def test_compare_date_ranges(self, track: MP3):
        comparer = Comparer(condition="in_the_last", expected="8h", field=LocalTrackField.DATE_ADDED)
        assert comparer._expected == ["8h"]
        assert not comparer._converted
        assert comparer._processor_method == comparer._is_after

        track.date_added = datetime.now() - timedelta(hours=4)
        assert comparer.compare(track)
        # truncate to avoid time lag between assignment and test making the test fail
        exp_truncated = comparer._expected[0].replace(second=0, microsecond=0)
        test_truncated = datetime.now().replace(second=0, microsecond=0) - timedelta(hours=8)
        assert exp_truncated == test_truncated
        assert comparer._converted

    ###########################################################################
    ## XML I/O
    ###########################################################################
    def test_from_xml_bp(self):
        with open(path_playlist_xautopf_bp, "r", encoding="utf-8") as f:
            xml = xmltodict.parse(f.read())

        conditions = xml["SmartPlaylist"]["Source"]["Conditions"]
        comparers = [Comparer.from_xml(xml=condition) for condition in to_collection(conditions["Condition"])]
        assert len(comparers) == 3

        assert comparers[0].field == LocalTrackField.ALBUM
        assert not comparers[0]._converted
        assert comparers[0].expected == ["an album"]
        assert comparers[0].condition == "contains"
        assert comparers[0]._processor_method == comparers[0]._contains

        assert comparers[1].field == LocalTrackField.ARTIST
        assert not comparers[1]._converted
        assert comparers[1].expected is None
        assert comparers[1].condition == "is_null"
        assert comparers[1]._processor_method == comparers[1]._is_null

        assert comparers[2].field == LocalTrackField.TRACK_NUMBER
        assert not comparers[2]._converted
        assert comparers[2].expected == ["30"]
        assert comparers[2].condition == "less_than"
        assert comparers[2]._processor_method == comparers[2]._is_before

    def test_from_xml_ra(self):
        with open(path_playlist_xautopf_ra, "r", encoding="utf-8") as f:
            xml = xmltodict.parse(f.read())

        conditions = xml["SmartPlaylist"]["Source"]["Conditions"]
        comparers = [Comparer.from_xml(xml=condition) for condition in to_collection(conditions["Condition"])]
        assert len(comparers) == 1
        comparer = comparers[0]

        assert comparer.field == LocalTrackField.ALBUM
        assert not comparer._converted
        assert comparer.expected == [""]
        assert comparer.condition == "contains"
        assert comparer._processor_method == comparer._contains

    @pytest.mark.skip(reason="not implemented yet")
    def test_to_xml(self):
        pass
