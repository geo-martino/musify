from typing import Annotated

from pydantic import StringConstraints
from annotated_types import MinLen

type Character = Annotated[str, StringConstraints(min_length=1, max_length=1)]
type StrippedCharacter = Annotated[str, StringConstraints(min_length=1, max_length=1, strip_whitespace=True)]
type String = Annotated[str, StringConstraints(min_length=1)]
type StrippedString = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
type ListWithValues[T] = Annotated[list[T], MinLen(1)]
