from __future__ import annotations

from typing import ClassVar, Annotated, Any

from pydantic import Field, field_validator, computed_field, model_validator

from musify.model import MusifyModel


class KeySignature(MusifyModel):
    """Represents a key signature."""
    _root_notes: ClassVar[tuple[str, ...]] = (
        "C", "C#/Db", "D", "D#/Eb", "E", "F", "F#/Gb", "G", "G#/Ab", "A", "A#/Bb", "B"
    )

    root: Annotated[int, Field(ge=0, le=11)] = Field(
        description="An index representing the root note of the key of this track.",
    )
    mode: Annotated[int, Field(ge=0, le=1)] = Field(
        description="The mode of this track.",
    )

    # noinspection PyNestedDecorators
    @model_validator(mode="before")
    @classmethod
    def _from_key(cls, value: str) -> Any:
        if not isinstance(value, str):
            return value
        return dict(root=cls._get_root_index_from_key(value), mode=cls._get_mode_index_from_key(value))

    # noinspection PyNestedDecorators
    @field_validator("root", mode="before", check_fields=True)
    @classmethod
    def _get_root_index_from_key(cls, value: str) -> Any:
        if not isinstance(value, str):
            return value
        return cls._root_notes.index(value.rstrip("m"))

    # noinspection PyNestedDecorators
    @field_validator("mode", mode="before", check_fields=True)
    @classmethod
    def _get_mode_index_from_key(cls, value: str) -> Any:
        if not isinstance(value, str):
            return value
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
