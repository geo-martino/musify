from __future__ import annotations

import asyncio
from collections.abc import Sequence
from http import HTTPMethod
from io import BytesIO
from typing import Any, Self

import aiohttp
from PIL import Image
from pydantic import InstanceOf, Field, PositiveInt, field_validator, field_serializer
from pydantic_core.core_schema import SerializerFunctionWrapHandler, FieldSerializationInfo
from yarl import URL

from musify._types import StrippedString
from musify.exception import MusifyTypeError
from musify.model import MusifyModel
from musify.model._base import _AttributeModel


class ImageLink(MusifyModel):
    """Represents an image link."""
    url: InstanceOf[URL] = Field(
        description="The URL of the image.",
    )
    kind: StrippedString | None = Field(
        description="The name or type of image.",
        default=None,
    )
    height: PositiveInt | None = Field(
        description="The height of the image in pixels.",
        default=None,
    )
    width: PositiveInt | None = Field(
        description="The width of the image in pixels.",
        default=None,
    )

    # noinspection PyNestedDecorators
    @field_validator("url", mode="before", check_fields=True)
    @staticmethod
    def _convert_to_url(value: str) -> Any:
        if not isinstance(value, str):
            return value
        return URL(value)

    def __str__(self) -> str:
        return str(self.url)

    def __eq_kind(self, other: Self) -> bool:
        return isinstance(other, ImageLink) and self.kind == other.kind

    def __eq__(self, other: Self) -> bool:
        if self is other:
            return True
        if not isinstance(other, ImageLink):
            return super().__eq__(other)
        return self.kind == other.kind and self.url == other.url

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self.__eq_kind(other) and self.height < other.height and self.width < other.width

    def __le__(self, other):
        return self.__eq_kind(other) and self.height <= other.height and self.width <= other.width

    def __gt__(self, other):
        return self.__eq_kind(other) and self.height > other.height and self.width > other.width

    def __ge__(self, other):
        return self.__eq_kind(other) and self.height >= other.height and self.width >= other.width

    async def load(self, session: aiohttp.ClientSession = None) -> Image:
        """Load the image from the URL."""
        close_session = False
        if session is None:
            close_session = True
            session = aiohttp.ClientSession()

        async with session.request(method=HTTPMethod.GET, url=self.url) as response:
            image_bytes = await response.read()

        if close_session:
            await session.close()

        return Image.open(BytesIO(image_bytes))


class HasImages(_AttributeModel):
    """Represents a resource that has associated images."""
    images: list[InstanceOf[Image.Image] | ImageLink] = Field(
        description="Images associated with this resource.",
        default_factory=list,
    )

    # noinspection PyNestedDecorators
    @field_validator("images", mode="before")
    @staticmethod
    def _images_from_bytes[T](data: T) -> T | list[Image.Image]:
        if isinstance(data, bytes | bytearray):
            data = [data]
        if isinstance(data, str) or not isinstance(data, Sequence):
            return data

        return [Image.open(BytesIO(img)) if isinstance(img, bytes | bytearray) else img for img in data]

    # noinspection PyNestedDecorators
    @field_serializer("images", mode="wrap", when_used="unless-none")
    @staticmethod
    def _bytes_from_images(
            images: list[Image.Image | ImageLink],
            handler: SerializerFunctionWrapHandler,
            info: FieldSerializationInfo,
    ) -> list[bytes]:
        data: list[bytes] = []
        for img in images:
            if isinstance(img, ImageLink):
                loop = asyncio.get_event_loop()
                img = loop.run_until_complete(img.load())

            img_bytes = BytesIO()
            img.save(img_bytes, format=img.format)
            img_bytes = img_bytes.getvalue()
            data.append(img_bytes)

        return handler(data)
