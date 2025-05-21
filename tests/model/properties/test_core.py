import pytest

from musify.model import MusifyModel
from musify.model.properties import HasSeparableTags
from tests.model.testers import MusifyResourceTester


class TestHasSeparableTags(MusifyResourceTester):
    @pytest.fixture
    def model(self) -> MusifyModel:
        return HasSeparableTags()

    def test_join_tags(self) -> None:
        tags = ["tag1", "tag2", "tag3"]
        assert HasSeparableTags._join_tags(tags) == HasSeparableTags._tag_sep.join(tags)

    def test_separate_tags(self) -> None:
        tags = ["tag1", "tag2", "tag3"]
        tag_string = HasSeparableTags._tag_sep.join(tags)
        assert HasSeparableTags._separate_tags(tag_string) == tags
