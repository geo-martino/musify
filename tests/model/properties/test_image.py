from gc import callbacks
from io import BytesIO
from random import choice

import numpy
import pytest
from PIL import Image
from aioresponses import aioresponses, CallbackResult
from faker import Faker
from yarl import URL

from musify.model import MusifyModel
from musify.model.properties.image import ImageLink, HasImages
from tests.model.testers import MusifyModelTester
from tests.utils import assert_validator_skips


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


class TestHasImages(MusifyModelTester):
    @pytest.fixture
    def model(self, images: list[bytes], faker: Faker) -> MusifyModel:
        links = [ImageLink(url=faker.url()) for _ in range(faker.random_int(3, 6))]
        return HasImages(images=images + links)

    def test_images_from_bytes(self, faker: Faker):
        data = faker.image()
        images = HasImages._images_from_bytes(data)
        assert len(images) == 1

        image_bytes = BytesIO()
        images[0].save(image_bytes, format='PNG')
        assert image_bytes.getvalue() == data

    def test_images_from_sequence_of_bytes(self, images: list[bytes]):
        data = [choice([img, bytearray(img)]) for img in images]
        result = HasImages._images_from_bytes(data)
        assert result == list(map(Image.open, map(BytesIO, images)))

    def test_images_from_bytes_skips(self, faker: Faker):
        assert_validator_skips(HasImages._images_from_bytes, None)
        assert_validator_skips(HasImages._images_from_bytes, faker.pystr())
        assert_validator_skips(HasImages._images_from_bytes, faker.pyint())

    def test_bytes_from_images(
            self, model: HasImages, images: list[bytes], faker: Faker, mock_response: aioresponses
    ):
        for image in model.images:
            if not isinstance(image, ImageLink):
                continue

            image_bytes = faker.image()
            mock_response.get(image.url, callback=lambda *_, **__: CallbackResult(method="GET", body=image_bytes))
            images.append(image_bytes)

        result = model.model_dump(include={"images"})["images"]
        assert len(result) == len(images)
        assert all(isinstance(img, bytes) for img in result)
