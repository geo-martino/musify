from datetime import timedelta

import pytest
from dateutil.relativedelta import relativedelta

from syncify.processors.time import TimeMapper
from tests.abstract.misc import PrettyPrinterTester


class TestTimeMapper(PrettyPrinterTester):

    @staticmethod
    @pytest.fixture
    def obj() -> TimeMapper:
        return TimeMapper("hours")

    @staticmethod
    def test_time_mapper():
        assert TimeMapper("hours")("12") == timedelta(hours=12)
        assert TimeMapper("h")("12") == timedelta(hours=12)
        assert TimeMapper("days")("36") == timedelta(days=36)
        assert TimeMapper("d")("36") == timedelta(days=36)
        assert TimeMapper("weeks")("3") == timedelta(weeks=3)
        assert TimeMapper("w")("3") == timedelta(weeks=3)
        assert TimeMapper("months")("4") == relativedelta(months=4)
        assert TimeMapper("m")("4") == relativedelta(months=4)
