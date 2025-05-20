"""
Defines property models to allow for property-specific validation and manipulation.

For properties which are common across multiple models, we also define Attribute models to help identify models
which make use of these common properties. By convention, they are usually denoted by their prefix
like `Has...` or `Is...`.
"""
from __future__ import annotations

import re
from abc import ABCMeta, abstractmethod
from datetime import date
from typing import Self, Annotated, Any, ClassVar

from PIL.Image import Image
from pydantic import Field, computed_field, PositiveInt, PositiveFloat, model_validator, field_validator, PrivateAttr, \
    InstanceOf
from pydantic_core.core_schema import ValidatorFunctionWrapHandler
from yarl import URL

from musify._types import String, StrippedString, RemoteSource, Resource
from musify.exception import MusifyValueError
from musify.model._base import MusifyModel, MusifyRootModel, _AttributeModel


class HasName(_AttributeModel):
    name: StrippedString = Field(
        description="A name for this object"
    )

    def __lt__(self, other: Self):
        return self.name < other.name

    def __le__(self, other: Self):
        return self.name <= other.name

    def __gt__(self, other: Self):
        return self.name > other.name

    def __ge__(self, other: Self):
        return self.name >= other.name


class HasSeparableTags(_AttributeModel):
    """Represents a resource that has a tag separator."""
    _tag_sep: ClassVar[String] = PrivateAttr(
        # description="The separator used to separate tags in this resource.",
        default=", ",
    )

    def _join_tags(self, tags: list[Any]) -> str:
        return self._tag_sep.join(map(str, tags))

    def _separate_tags(self, tags: str) -> list[str]:
        return [tag.strip() for tag in tags.split(self._tag_sep) if tag.strip()]


class RemoteURI(MusifyRootModel[StrippedString], metaclass=ABCMeta):
    """Stores a URI for a resource from a specific remote repository."""
    _source: ClassVar[RemoteSource] = PrivateAttr(
        # description=(
        #     "The remote repository that the URI is from. "
        #     "This is used to validate incoming URI values belong to this repository."
        # ),
    )
    _unavailable_id: ClassVar[StrippedString] = PrivateAttr(
        # description=(
        #     "A special ID that indicates this URI does not exist in the remote repository. "
        #     "This is used to indicate that the URI is not available."
        # ),
        default="unavailable",
    )

    # noinspection PyNestedDecorators
    @field_validator("source", mode="after", check_fields=True)
    @classmethod
    def _validate_source(cls, source: RemoteSource) -> RemoteSource:
        if source != cls._source:
            raise ValueError(f"Given URI does not belong to this repository type. Must be {cls._source}, not {source}")
        return source

    @computed_field(description="The remote repository that this URI is from.")
    @abstractmethod
    def source(self) -> RemoteSource:
        raise NotImplementedError

    @computed_field(description="The type of resource this URI represents.")
    @abstractmethod
    def type(self) -> Resource:
        raise NotImplementedError

    @computed_field(description="The unique identifier for this URI.")
    @abstractmethod
    def id(self) -> str:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def from_id[T](cls, id_: str, kind: Resource) -> T:
        raise NotImplementedError

    @computed_field(description="The URL of the API endpoint for this remote resource.")
    @abstractmethod
    def href(self) -> URL:
        raise NotImplementedError

    # noinspection PyNestedDecorators
    @field_validator("root", mode="wrap", check_fields=True)
    @staticmethod
    @abstractmethod
    def from_href[T](value: T, handler: ValidatorFunctionWrapHandler) -> str | T:
        raise NotImplementedError

    @computed_field(description="The public URL for this remote resource.")
    @abstractmethod
    def url(self) -> URL:
        raise NotImplementedError

    # noinspection PyNestedDecorators
    @field_validator("root", mode="wrap", check_fields=True)
    @classmethod
    @abstractmethod
    def from_url(cls, value: Any, handler: ValidatorFunctionWrapHandler) -> Any:
        raise NotImplementedError

    @computed_field(
        description="Whether this URI relates to a resource which actually exists in the remote repository."
    )
    @property
    def exists(self) -> bool:
        return self.id == self._unavailable_id

    def __str__(self):
        return self.uri

    def __eq__(self, other: str | RemoteURI):
        if self is other:
            return True
        if isinstance(other, RemoteURI):
            return self.uri == other.uri

        if isinstance(other, URL):
            if self.href == other or self.url == other:
                return True
            other = str(other)

        if isinstance(other, str):
            return self.uri == str

        return False


class HasImmutableURI(_AttributeModel):
    __unique_attributes__ = frozenset({"uri"})

    uri: RemoteURI = Field(
        description="The URI for this resource on the remote repository"
    )

    def __eq__(self, other: HasImmutableURI | HasMutableURI):
        if self is other:
            return True
        if isinstance(other, HasMutableURI) and not other.has_uri:
            return False
        return self.uri == other.uri


class HasMutableURI(_AttributeModel):
    source: RemoteSource | None = Field(
        description=(
            "The type of remote repository this item is associated with. "
            "Used to determine which URI to return from the `uri` attribute."
        ),
        default=None,
    )
    uris: list[RemoteURI] = Field(
        description="A list of URIs that represent this item.",
        default_factory=list,
    )

    # noinspection PyNestedDecorators
    @field_validator("uris", mode="after", check_fields=True)
    @staticmethod
    def _uris_must_be_from_unique_sources(uris: list[RemoteURI]) -> list[RemoteURI]:
        sources: set[str] = set()
        duplicates: set[str] = set()

        for uri in uris:
            if uri.source in sources:
                duplicates.add(uri.source.name)
            sources.add(uri.source.name)

        if duplicates:
            raise MusifyValueError(f"Duplicate URIs found from sources: {', '.join(duplicates)}")
        return uris

    __unique_attributes__ = frozenset({"uri"})

    @computed_field(description="The associated URI from the remote repository if it exists.")
    @property
    def uri(self) -> RemoteURI | None:
        if self.source is None:
            return
        return next((uri for uri in self.uris if uri.source == self.source and uri.exists), None)

    @uri.setter
    def uri(self, uri: str | RemoteURI):
        if isinstance(uri, str):
            uri = RemoteURI(uri)

        if self.source is not None and uri.source != self.source:
            raise MusifyValueError(f"Cannot set URI from {uri.source} to {self.source}")

        for idx, existing in enumerate(self.uris):  # replace matching source URI in-place at same position
            if existing.source == uri.source:
                self.uris.remove(existing)
                self.uris.insert(idx, uri)
                return

        self.uris.append(uri)

    @computed_field(
        description=(
                "Whether this item has a URI. Returns None if existence is unknown "
                "(usually because a mapping has not yet been attempted)."
        )
    )
    @property
    def has_uri(self) -> bool | None:
        return next((uri.exists for uri in self.uris if uri.source == self.source), None)

    def __eq__(self, other: HasImmutableURI | HasMutableURI):
        if self is other:
            return True
        if not self.has_uri:
            return False
        if isinstance(other, HasMutableURI) and not other.has_uri:
            return False
        return self.uri == other.uri


class Position(MusifyModel):
    """Represents the index position of a resource within a parent resource."""
    number: PositiveInt | None = Field(
        description="The index position of the resource within the parent resource.",
        default=None,
    )
    total: PositiveInt | None = Field(
        description="The total number of resources in the parent resource.",
        default=None,
    )

    @model_validator(mode="after")
    def _validate_position_is_less_than_total(self) -> Self:
        if self.number > self.total:
            raise MusifyValueError("Start position cannot be greater than end position.")
        return self


class Length(MusifyRootModel[PositiveInt | PositiveFloat]):
    # noinspection PyNestedDecorators
    @field_validator("root", mode="before", check_fields=True)
    @staticmethod
    def _convert_numeric_representation_to_number(value: Any) -> int | float:
        if not isinstance(value, str):
            return value

        if re.match(value, r"^\d+$"):
            return int(value)
        if re.match(value, r"^\d+\.\d+$"):
            return float(value)

        if matches := re.match(value, r"^(\d{1,2}):(\d{1,2})[$|\.\d+$]"):
            hours = 0
            minutes, seconds = tuple(map(int, matches.groups()))
        elif matches := re.match(value, r"^\d+:\d{1,2}:\d{1,2}[$|\.\d+$]"):
            hours, minutes, seconds = tuple(map(int, matches.groups()))
        else:
            raise MusifyValueError(f"Invalid length format: {value}")

        total_seconds = seconds + (minutes * 60) + (hours * 3600)

        if matches := re.match(value, r"^.*\.(\d+)$]"):
            milliseconds = int(matches.group(1))
            return float(total_seconds + (milliseconds / 1000))

        return total_seconds

    def __int__(self):
        return int(self.root)

    def __float__(self):
        return float(self.root)


class HasLength(_AttributeModel):
    """Represents a resource that has a length."""
    length: Length | None = Field(
        description="The length of this resource.",
        default=None,
    )


class Rating(MusifyRootModel[PositiveFloat]):
    pass


class HasRating(_AttributeModel):
    """Represents a resource that has a rating."""
    rating: float | None = Field(
        description="The rating of this resource.",
        default=None,
    )


class SparseDate(MusifyModel):
    """
    A sparse date represents a date which may not have all parts to make up a full date.

    This allows for defining a date as just the year, or just the year and month,
    while also allowing for a full date definition of year, month, and day.
    """
    year: PositiveInt = Field(
        description="The year.",
    )
    month: Annotated[int, Field(ge=1, le=12)] | None = Field(
        description="The month.",
        default=None,
    )
    day: Annotated[int, Field(ge=1, le=31)] | None = Field(
        description="The day.",
        default=None,
    )

    @property
    def date(self) -> date | None:
        """A :py:class:`date` object representing the full date definition if available."""
        if self.year and self.month and self.day:
            return date(self.year, self.month, self.day)


class HasReleaseDate(_AttributeModel):
    """Represents a resource that has an associated release date."""
    release: SparseDate | None = Field(
        description="The date this resource was released.",
        default=None,
    )


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

    def __str__(self) -> str:
        return str(self.url)

    def __eq_kind(self, other: Self) -> bool:
        return isinstance(other, ImageLink) and self.kind == other.kind

    def __eq__(self, other: Self) -> bool:
        if self is other:
            return True
        if not self.__eq_kind(other):
            return False
        return self.url == other.url or (self.height == other.height and self.width == other.width)

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


class HasImages(_AttributeModel):
    """Represents a resource that has associated images."""
    images: list[InstanceOf[Image] | ImageLink] = Field(
        description="Images associated with this track.",
        default_factory=list,
    )


class KeySignature(MusifyModel):
    """Represents a key signature."""
    _root_notes = ("C", "C#/Db", "D", "D#/Eb", "E", "F", "F#/Gb", "G", "G#/Ab", "A", "A#/Bb", "B")

    root: Annotated[int, Field(ge=0, le=11)] = Field(
        description="An index representing the root note of the key of this track.",
    )
    mode: Annotated[int, Field(ge=0, le=1)] = Field(
        description="The mode of this track.",
    )

    # noinspection PyNestedDecorators
    @field_validator("root", mode="before", check_fields=True)
    @classmethod
    def _get_root_index_from_key(cls, value: str) -> int:
        return cls._root_notes.index(value.rstrip("m"))

    # noinspection PyNestedDecorators
    @field_validator("root", mode="before", check_fields=True)
    @classmethod
    def _get_mode_index_from_key(cls, value: str) -> int:
        return int(value.endswith("m"))

    @computed_field(description="A string representation of the key in alphabetical musical notation format.")
    @property
    def key(self) -> str:
        return f"{self._root_notes[self.root]}{'m' if self.mode else ''}"

    # noinspection PyTypeChecker
    @key.setter
    def key(self, value: str) -> None:
        self.root = value
        self.mode = value

    def __str__(self):
        return self.key
