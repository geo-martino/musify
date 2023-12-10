import re
from abc import ABC, ABCMeta, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from syncify.utils.helpers import to_collection

_T_JSON_VALUE = str | int | float | list | dict | bool | None


@dataclass(frozen=True)
class Result(metaclass=ABCMeta):
    """Stores the results of an operation within Syncify"""
    pass


class PrettyPrinter(ABC):
    """Generic base class for pretty printing. Classes can inherit this class to gain pretty print functionality."""

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
        return self.__to_json(self.as_dict())

    def __to_json(self, attributes: Mapping[str, _T_JSON_VALUE]) -> dict[str, _T_JSON_VALUE]:
        result: dict[str, _T_JSON_VALUE] = {}

        for attr_key, attr_val in attributes.items():
            if isinstance(attr_val, set):
                attr_val = to_collection(attr_val)

            if isinstance(attr_val, (list, tuple)):
                result[attr_key] = []
                for item in attr_val:
                    if isinstance(item, PrettyPrinter):
                        result[attr_key].append(item.json())
                    elif isinstance(item, datetime):
                        result[attr_key].append(item.strftime("%Y-%m-%d %H:%M:%S"))
                    else:
                        result[attr_key].append(item)
            elif isinstance(attr_val, Mapping):
                result[attr_key] = self.__to_json(attr_val)
            elif isinstance(attr_val, PrettyPrinter):
                result[attr_key] = attr_val.json()
            elif isinstance(attr_val, datetime):
                result[attr_key] = attr_val.strftime("%Y-%m-%d %H:%M:%S")
            else:
                result[attr_key] = attr_val

        return result

    def __str__(self):
        obj_dict = self.as_dict()
        if not obj_dict:
            return f"{self.__class__.__name__}()"

        result = f"{self.__class__.__name__}(\n{{}}\n)"

        indent = 2
        attributes_repr = self.__to_str(obj_dict, indent=indent, increment=indent)

        return result.format("\n".join([" " * indent + attribute for attribute in attributes_repr]))

    def __to_str(self, attributes: Mapping[str, Any], indent: int = 2, increment: int = 2) -> list[str]:
        if len(attributes) == 0:
            return []
        max_key_width = max(len(tag_name) for tag_name in attributes)
        max_val_width = 120 - max_key_width
        attributes_repr: list[str] = []

        indent += increment
        indent_prev = indent - increment

        for attr_key, attr_val in attributes.items():
            attr_key = attr_key.title().replace('_', ' ')
            attr_val_repr = f"{attr_key: <{max_key_width}} = {repr(attr_val)}"

            if isinstance(attr_val, set):
                attr_val = tuple(attr_val)

            if isinstance(attr_val, PrettyPrinter) or isinstance(attr_val, datetime):
                attr_val_repr = f"{attr_key: <{max_key_width}} = {attr_val}"
            elif isinstance(attr_val, (list, tuple)) and len(attr_val) > 0:
                if isinstance(attr_val[0], PrettyPrinter) or len(str(attr_val)) > max_val_width:
                    pp_repr = "[\n" + "{}\n" + " " * indent_prev + "]"
                    pp = [" " * indent + str(v).replace("\n", "\n" + " " * indent) for v in attr_val]
                    attr_val = pp_repr.format(",\n".join(pp))
                    attr_val_repr = f"{attr_key: <{max_key_width}} = {attr_val}"
            elif isinstance(attr_val, Mapping):
                pp_repr = " " * indent + "{}"
                pp = self.__to_str(attr_val, indent=indent, increment=increment)

                if len(pp) == 0:
                    attr_val = "{}"
                elif len(str(pp)) < max_val_width:
                    attr_val = "{ " + ", ".join(pp) + " }"
                else:
                    pp_repr = pp_repr.format("\n".join(pp)).replace("\n", "\n" + " " * indent)
                    attr_val = "{\n" + pp_repr + "\n" + " " * indent_prev + "}"
                attr_val_repr = f"{attr_key: <{max_key_width}} = {attr_val}"

            attributes_repr.append(attr_val_repr)

        return attributes_repr

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.as_dict())})"
