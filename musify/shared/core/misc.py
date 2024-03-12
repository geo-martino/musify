"""
The fundamental core miscellaneous classes for the entire package.
"""

import re
from abc import ABC, ABCMeta, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, date
from typing import Any

from musify.shared.utils import to_collection

_T_JSON_VALUE = str | int | float | list | dict | bool | None


@dataclass(frozen=True)
class Result(metaclass=ABCMeta):
    """Stores the results of an operation"""
    pass


class PrettyPrinter(ABC):
    """Generic base class for pretty printing. Classes can inherit this class to gain pretty print functionality."""

    _upper_key_words = {"id", "uri", "url", "bpm"}
    _max_val_width = 120

    @staticmethod
    def _pascal_to_snake(value: str) -> str:
        """Convert snake_case to CamelCase."""
        value = re.sub(r"([A-Z])", lambda m: f"_{m.group(1).lower()}", value.strip("_ "))
        value = re.sub(r"[_ ]+", "_", value).strip("_ ")
        return value.lower()

    @staticmethod
    def _snake_to_pascal(value: str) -> str:
        """Convert snake_case to CamelCase."""
        return re.sub(r"_(.)", lambda m: m.group(1).upper(), value.strip())

    @abstractmethod
    def as_dict(self) -> dict[str, Any]:
        """
        Return a dictionary representation of the key attributes of this object.

        The results of this function are used to produce the following:
            * A JSON representation of the object when calling :py:func:`json`
            * The string representation of the object when calling str() on the object
            * The representation of the object when calling repr() on the object
        """
        raise NotImplementedError

    def json(self) -> dict[str, _T_JSON_VALUE]:
        """Return a dictionary representation of the key attributes of this object that is safe to output to JSON"""
        return self._to_json(self.as_dict())

    @classmethod
    def _to_json(cls, attributes: Mapping[str, _T_JSON_VALUE]) -> dict[str, _T_JSON_VALUE]:
        result: dict[str, _T_JSON_VALUE] = {}

        for attr_key, attr_val in attributes.items():
            attr_key = str(attr_key)
            if isinstance(attr_val, set):
                attr_val = to_collection(attr_val)

            if isinstance(attr_val, (list, tuple)):
                result[attr_key] = []
                for item in attr_val:
                    if isinstance(item, PrettyPrinter):
                        result[attr_key].append(item.json())
                    elif isinstance(item, (datetime, date)):
                        result[attr_key].append(str(item))
                    else:
                        result[attr_key].append(item)
            elif isinstance(attr_val, Mapping):
                result[attr_key] = cls._to_json(attr_val)
            elif isinstance(attr_val, PrettyPrinter):
                result[attr_key] = attr_val.json()
            elif isinstance(attr_val, (datetime, date)):
                result[attr_key] = str(attr_val)
            else:
                result[attr_key] = attr_val

        return result

    def __str__(self, indent: int = 2, increment: int = 2):
        obj_dict = self.as_dict()
        if not obj_dict:
            return f"{self.__class__.__name__}()"

        result = f"{self.__class__.__name__}(\n{{}}\n" + " " * (indent - increment) + ")"
        attributes_repr = self._to_str(obj_dict, indent=indent, increment=increment)
        return result.format("\n".join([" " * indent + attribute for attribute in attributes_repr]))

    @classmethod
    def _to_str(cls, attributes: Mapping[str, Any], indent: int = 2, increment: int = 2) -> list[str]:
        if len(attributes) == 0:
            return []
        max_key_width = max(len(str(attr_key)) for attr_key in attributes) + 1  # +1 for space after key
        max_key_width += max_key_width % increment
        max_val_width = cls._max_val_width - max_key_width

        indent_prev = indent
        indent += increment

        attributes_repr: list[str] = []
        for attr_key, attr_val in attributes.items():
            attr_key = str(attr_key).title().replace('_', ' ')
            for word in cls._upper_key_words:
                pattern = re.compile(rf"(^{word}$|^{word} | {word}$| {word})", flags=re.I)
                attr_key = re.sub(pattern, lambda m: m.group(1).upper(), attr_key)

            if isinstance(attr_val, PrettyPrinter):
                attr_val_str = attr_val.__str__(indent=indent, increment=increment)
            elif isinstance(attr_val, (datetime, date)):
                attr_val_str = str(attr_val)
            elif isinstance(attr_val, (list, tuple, set)) and len(attr_val) > 0:
                pp_repr = "[{}]"
                if isinstance(attr_val, set):
                    pp_repr = "{{}}"
                elif isinstance(attr_val, tuple):
                    pp_repr = "({})"

                attr_val_str = str(attr_val)

                if len(attr_val_str) > max_val_width:
                    pp_repr = pp_repr.format("\n" + " " * indent + "{}\n" + " " * indent_prev)
                    attr_val_pp = []
                    for val in attr_val:
                        if isinstance(val, PrettyPrinter):
                            attr_val_pp.append(val.__str__(indent=indent + increment, increment=increment))
                        else:
                            attr_val_pp.append(str(val))
                    attr_val_str = pp_repr.format((",\n" + " " * indent).join(attr_val_pp))
            elif isinstance(attr_val, Mapping) and len(attr_val) > 0:
                attr_val_pp = cls._to_str(attr_val, indent=indent, increment=increment)
                attr_val_str = "{" + ", ".join(attr_val_pp) + "}"

                if len(attr_val_str) > max_val_width:
                    pp_repr = "\n" + " " * indent + "{}\n" + " " * indent_prev
                    attr_val_str = "{" + pp_repr.format((",\n" + " " * indent).join(attr_val_pp)) + "}"
            else:
                attr_val_str = repr(attr_val)

            attr_val_repr = f"{attr_key} = {attr_val_str}"  # for single line format
            if len(attr_val_repr) > max_val_width or len(attributes) > 1:
                # reformat to indented list format
                attr_val_repr = f"{attr_key: <{max_key_width}}= {attr_val_str}"
            attributes_repr.append(attr_val_repr)

        return attributes_repr

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.as_dict())})"
