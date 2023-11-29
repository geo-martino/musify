import re
from abc import ABCMeta, abstractmethod
from collections.abc import Mapping, Hashable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from syncify.utils.helpers import to_collection


@dataclass(frozen=True)
class Result(metaclass=ABCMeta):
    """Stores the results of an operation within Syncify"""
    pass


class PrettyPrinter(metaclass=ABCMeta):
    """Generic base class for pretty printing. Classes can inherit this class to gain pretty print functionality."""

    @staticmethod
    def _camel_to_snake(value: str, prefix: str | None = None) -> str:
        """Convert snake_case to CamelCase. Optionally, add a given prefix"""
        value = re.sub("([A-Z])", lambda m: f"_{m.group(1).lower()}", value.strip("_ "))
        value = re.sub(r"[_ ]+", "_", value).strip("_ ")
        if prefix is not None:
            value = f"{prefix}_{value}"
        return value.lower()

    @staticmethod
    def _snake_to_camel(value: str, prefix: str | None = None) -> str:
        """Convert snake_case to CamelCase. Optionally, remove a given prefix"""
        if prefix is not None:
            value = re.sub(f"^{prefix}", "", value)
        return re.sub("_(.)", lambda m: m.group(1).upper(), value.strip())

    @abstractmethod
    def as_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the key attributes of this object"""
        raise NotImplementedError

    def as_json(self) -> dict[str, object]:
        """Return a dictionary representation of the key attributes of this object that is safe to output to json"""
        return self.__as_json(self.as_dict())

    def __as_json[T: Hashable](self, attributes: Mapping[T, Any]) -> dict[T, Any]:
        result: dict[str, Any] = {}

        for attr_key, attr_val in attributes.items():
            if isinstance(attr_val, set):
                attr_val = to_collection(attr_val)

            if isinstance(attr_val, (list, tuple)):
                result[attr_key] = []
                for item in attr_val:
                    if isinstance(item, PrettyPrinter):
                        result[attr_key].append(item.as_json())
                    elif isinstance(item, datetime):
                        result[attr_key].append(item.strftime("%Y-%m-%d %H:%M:%S"))
                    else:
                        result[attr_key].append(item)
            elif isinstance(attr_val, Mapping):
                result[attr_key] = self.__as_json(attr_val)
            elif isinstance(attr_val, PrettyPrinter):
                result[attr_key] = attr_val.as_json()
            elif isinstance(attr_val, datetime):
                result[attr_key] = attr_val.strftime("%Y-%m-%d %H:%M:%S")
            else:
                result[attr_key] = attr_val

        return result

    def __str__(self):
        as_dict = self.as_dict()
        if not as_dict:
            return f"{self.__class__.__name__}()"

        result = f"{self.__class__.__name__}(\n{{}}\n)"

        indent = 2
        attributes_repr = self.__to_str(as_dict, indent=indent, increment=indent)

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
        return f"{self.__class__.__name__}({self.as_dict()})"
