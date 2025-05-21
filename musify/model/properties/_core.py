from __future__ import annotations

from typing import ClassVar, Iterable, Any

from pydantic import PrivateAttr

from musify._types import String
from musify.model._base import _AttributeModel


class HasSeparableTags(_AttributeModel):
    """Represents a resource that has a tag separator."""
    _tag_sep: ClassVar[String] = PrivateAttr(
        # description="The separator used to separate tags in this resource.",
        default="; ",
    )

    @classmethod
    def _join_tags(cls, tags: Iterable[Any]) -> str:
        return cls._tag_sep.join(map(str, tags))

    @classmethod
    def _separate_tags(cls, tags: str) -> list[str]:
        return [tag.strip() for tag in tags.split(cls._tag_sep) if tag.strip()]
