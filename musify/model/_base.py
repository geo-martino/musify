from abc import abstractmethod
from functools import cached_property
from typing import Any, ClassVar

from pydantic import BaseModel, RootModel, Field, ConfigDict, TypeAdapter


def abstract_property() -> property:
    """Create a new abstract property for an attribute."""
    def fget(self) -> Any:
        raise NotImplementedError

    return property(abstractmethod(fget))


def readable_computed_field(name: str) -> property:
    """Create a new readable computed_field for an attribute with the given ``name``."""
    name = f"__{name.lstrip("_")}"

    def fget(self) -> Any:
        field = self.model_computed_fields[name.lstrip("_")]
        value = getattr(self, name, None)
        TypeAdapter(field.return_type).validate_python(value)  # validate return
        return value

    return property(fget)


def writeable_computed_field(name: str) -> property:
    """Create a new writeable computed_field for an attribute with the given ``name``."""
    name = f"__{name.lstrip("_")}"

    def fget(self) -> Any:
        field = self.model_computed_fields[name.lstrip("_")]
        value = getattr(self, name, None)
        TypeAdapter(field.return_type).validate_python(value)  # validate return
        return value

    def fset(self, value) -> None:
        field = self.model_computed_fields[name.lstrip("_")]
        value = TypeAdapter(field.return_type).validate_python(value)
        setattr(self, name, value)

    def fdel(self) -> None:
        delattr(self, name)

    return property(fget, fset, fdel)


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

    def __init__(self, **kwargs):
        # Allow setting writeable computed fields on init
        computed_field_values = {}
        for field in self.model_computed_fields.keys():
            if field in self.__pydantic_fields__ or field not in kwargs:
                continue

            attr = getattr(self.__class__, field)
            if attr.fset is not None:
                computed_field_values[field] = kwargs.pop(field)
            elif any(
                    name.endswith(field_private := f"_{field}")
                    for name in getattr(self.__class__, "__private_attributes__", ())
            ):
                computed_field_values[field_private] = kwargs.pop(field)

        super().__init__(**kwargs)
        for field, value in computed_field_values.items():
            setattr(self, field, value)


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
    type: ClassVar[str] = Field(description="The type of resource this is.")

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

    def __eq__(self, other):
        if not isinstance(other, MusifyResource):
            return super().__eq__(other)
        return self.unique_keys == other.unique_keys

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
        if key in self._unique_attribute_keys and hasattr(self, "unique_keys"):
            # noinspection PyPropertyAccess
            del self.unique_keys  # clear the cached property


class _AttributeModel(MusifyResource):
    """Defines a common base model for attributes made of common properties."""


class _CollectionModel(_AttributeModel):
    """Defines a common base model for attributes made of common collection properties."""
