from io import BytesIO

import numpy
import pytest
from PIL import Image
from aioresponses import aioresponses, CallbackResult
from faker import Faker

from musify.model import MusifyModel
from musify.model.properties.image import ImageLink
from tests.model.testers import MusifyModelTester


class TestImageLink(MusifyModelTester):
    @pytest.fixture
    def model(self, faker: Faker) -> MusifyModel:
        # noinspection PyProtectedMember
        return ImageLink(
            url=faker.url(),
            kind="Cover Front",
            height=faker.random_int(min=600, max=1000),
            width=faker.random_int(min=600, max=1000),
        )

    def test_equality(self, model: ImageLink, faker: Faker) -> None:
        assert model == model
        assert model == ImageLink(
            url=model.url, kind=model.kind, height=faker.random_int(), width=faker.random_int(),
        )

        assert model != ImageLink(
            url=model.url, kind="A different kind", height=faker.random_int(), width=faker.random_int(),
        )
        assert model != ImageLink(
            url=faker.url(), kind=model.kind, height=faker.random_int(), width=faker.random_int(),
        )

    def test_rich_comparison_dunder_methods(self, model: ImageLink, faker: Faker) -> None:
        assert model < ImageLink(
            url=faker.url(), kind=model.kind, height=model.height + 100, width=model.width + 100,
        )
        assert model <= ImageLink(
            url=faker.url(), kind=model.kind, height=model.height + 100, width=model.width,
        )
        assert model <= ImageLink(
            url=faker.url(), kind=model.kind, height=model.height, width=model.width,
        )

        assert model > ImageLink(
            url=faker.url(), kind=model.kind, height=model.height - 100, width=model.width - 100,
        )
        assert model >= ImageLink(
            url=faker.url(), kind=model.kind, height=model.height - 100, width=model.width,
        )
        assert model >= ImageLink(
            url=faker.url(), kind=model.kind, height=model.height, width=model.width,
        )

    async def test_load(self, model: ImageLink, mock_response: aioresponses) -> None:
        body = BytesIO()
        img_array = numpy.random.rand(100, 100, 3) * 255
        img = Image.fromarray(img_array.astype("uint8")).convert("RGBA")
        img.save(body, format="PNG")

        mock_response.get(
            model.url,
            callback=lambda *_, **__: CallbackResult(method="GET", body=body.getvalue()),
        )
        assert (await model.load()).tobytes() == img.tobytes()
