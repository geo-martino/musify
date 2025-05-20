from functools import cached_property
from typing import Any, ClassVar

from pydantic import BaseModel, RootModel, Field, ConfigDict

from musify._types import Resource


class MusifyModel(BaseModel):
    """Generic base class for any Musify model."""
    model_config = ConfigDict(
        validate_default=True,
        validate_assignment=True,
        validate_by_name=True,
        validate_by_alias=True,
        extra="forbid",
    )
    # TODO: figure this out
    # _clean_tags: dict[TagField, Any] = PrivateAttr(
    #     # description="A map of tags that have been cleaned to use when matching/searching",
    #     default_factory=dict,
    # )


class MusifyRootModel[T](RootModel[T]):
    model_config = ConfigDict(
        validate_default=True,
        validate_assignment=True,
        validate_by_name=True,
        validate_by_alias=True,
    )


class MusifyResource(MusifyModel):
    """Generic class for storing an item."""
    __unique_attributes__: ClassVar[frozenset[str]] = frozenset()
    type: ClassVar[Resource] = Field(description="The type of resource this is.")

    @cached_property
    def _unique_attribute_keys(self) -> set[str]:
        return {
            key
            for cls in self.__class__.__mro__ if issubclass(cls, _AttributeModel)
            for key in cls.__unique_attributes__
        }

    @cached_property
    def unique_keys(self) -> set[Any]:
        """Get the keys to match on from the matchable attributes of this model"""
        values = {getattr(self, key) for key in self._unique_attribute_keys}
        if None in values:
            values.remove(None)

        # also always allow matching on the string representation of the key
        values.update({str(value) for value in values})
        # allow matching identifiers
        values.add(id(self))
        return values

    # TODO: figure this out
    # def __getitem__(self, key: str | TagField) -> Any:
    #     """Get the value of a given attribute key"""
    #     if isinstance(key, TagField):
    #         try:
    #             key = next(iter(sorted(key.to_tag())))
    #         except StopIteration:
    #             key = key.name.lower()
    #     return getattr(self, key)

    def __setattr__(self, key: str, value: Any) -> None:
        """Set the value of a given attribute key"""
        super().__setattr__(key, value)
        if key in self._unique_attribute_keys:
            # noinspection PyPropertyAccess
            del self.unique_keys  # clear the cached property


class _AttributeModel(MusifyResource):
    """Defines a common base model for attributes made of common properties."""


class _CollectionModel(_AttributeModel):
    """Defines a common base model for attributes made of common properties."""
