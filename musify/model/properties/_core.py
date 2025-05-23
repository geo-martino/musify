from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar, Iterable, Any

from pydantic import PrivateAttr

from musify._types import String
from musify.model._base import _AttributeModel


class HasSeparableTags(_AttributeModel):
    """Represents a resource that has a tag separator."""
    _tag_sep: ClassVar[Sequence[String]] = PrivateAttr(
        # description="The separator used to separate tags in this resource.",
        default=("; ", "\x00"),  # also split string values on null
    )

    @classmethod
    def _join_tags(cls, tags: Iterable[Any]) -> str:
        sep = next(iter(cls._tag_sep))
        return sep.join(map(str, tags))

    @classmethod
    def _separate_tags(cls, tags: str) -> list[str]:
        seps = iter(cls._tag_sep)
        tags = tags.split(next(seps))
        for sep in seps:
            tags = [t for tag in tags for t in tag.rstrip(sep).split(sep)]

        return tags
