from random import choice

import pytest

from musify.model import MusifyModel
from musify.model.properties import HasSeparableTags
from tests.model.testers import MusifyResourceTester


class TestHasSeparableTags(MusifyResourceTester):
    @pytest.fixture
    def model(self) -> MusifyModel:
        return HasSeparableTags()

    def test_join_tags(self) -> None:
        tags = [f"tag{i}" for i in range(10)]

        HasSeparableTags._tag_sep = ("/", ";")
        assert HasSeparableTags._join_tags(tags) == "/".join(tags), "Should only join on first item in the sequence"

    def test_separate_tags(self) -> None:
        tags = [f"tag{i}" for i in range(10)]

        seps = ("/", ";")
        HasSeparableTags._tag_sep = ("/", ";")
        tags_joined = "".join(tag + choice(seps) for tag in tags).rstrip("".join(seps))
        assert HasSeparableTags._separate_tags(tags_joined) == tags
