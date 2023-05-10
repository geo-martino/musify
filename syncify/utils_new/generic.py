import re
from abc import ABCMeta, abstractmethod, ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Tuple, Mapping, List, MutableMapping, Any, TypeVar, Union, Optional

from utils_new.helpers import make_list

sort_ignore_words = ["The", "A"]

T = TypeVar('T')
UnionList = Union[T, List[T]]


def strip_ignore_words(value: str) -> Tuple[bool, str]:
    if not value:
        return False, value

    new_value = value
    not_special = not any(value.startswith(c) for c in list('!"£$%^&*()_+-=…'))

    for word in sort_ignore_words:
        new_value = re.sub(f"^{word} ", "", value)
        if new_value != value:
            break

    return not_special, new_value


def flatten_nested(nested: Mapping, previous: List = None) -> List:
    if previous is None:
        previous = []

    if isinstance(nested, dict):
        for key, value in nested.items():
            flatten_nested(value, previous=previous)
    elif isinstance(nested, list):
        previous.extend(nested)

    return previous


class PrettyPrinter(metaclass=ABCMeta):

    @staticmethod
    def _camel_to_snake(value: str, prefix: Optional[str] = None) -> str:
        """Convert snake_case to CamelCase. Optionally, add a given prefix"""
        value = re.sub('([A-Z])', lambda m: f"_{m.group(1).lower()}", value.strip("_ "))
        value = re.sub(r"[_ ]+", "_", value).strip("_ ")
        if prefix is not None:
            value = f"{prefix}_{value}"
        return value.lower()

    @staticmethod
    def _snake_to_camel(value: str, prefix: Optional[str] = None) -> str:
        """Convert snake_case to CamelCase. Optionally, remove a given prefix"""
        if prefix is not None:
            value = re.sub(f'^{prefix}', "", value)
        return re.sub('_(.)', lambda m: m.group(1).upper(), value.strip())

    @abstractmethod
    def as_dict(self) -> MutableMapping[str, Any]:
        """Return a dictionary representation of the key attributes of this object"""
        raise NotImplementedError

    def as_json(self) -> Mapping[str, object]:
        """Return a dictionary representation of the key attributes of this object that is safe to output to json"""
        return self._as_json(self.as_dict())

    def _as_json(self, attributes: Mapping[str, object]) -> Mapping[str, object]:
        result = {}

        for attr_key, attr_val in attributes.items():
            if isinstance(attr_val, set):
                attr_val = make_list(attr_val)

            if isinstance(attr_val, list):
                result[attr_key] = []
                for item in attr_val:
                    if isinstance(item, self.__class__):
                        result[attr_key].append(item.as_json())
                    elif isinstance(item, datetime):
                        result[attr_key].append(item.strftime("%Y-%m-%d %H:%M:%S"))
                    else:
                        result[item].append(item)
            elif isinstance(attr_val, dict):
                result[attr_key] = self._as_json(attr_val)
            elif isinstance(attr_val, self.__class__):
                result[attr_key] = attr_val.as_json()
            elif isinstance(attr_val, datetime):
                result[attr_key] = attr_val.strftime("%Y-%m-%d %H:%M:%S")
            else:
                result[attr_key] = attr_val

        return result

    def __str__(self) -> str:
        result = f"{self.__class__.__name__}(\n{{}}\n)"

        indent = 2
        attributes_repr = self._to_str(self.as_dict(), indent=indent, increment=indent)

        return result.format("\n".join([" " * indent + attribute for attribute in attributes_repr]))

    def _to_str(self, attributes: Mapping[str, Any], indent: int = 2, increment: int = 2) -> List[str]:
        if len(attributes) == 0:
            return []
        max_key_width = max(len(tag_name) for tag_name in attributes)
        max_val_width = 120 - max_key_width
        attributes_repr = []

        indent += increment
        indent_prev = indent - increment

        for attr_key, attr_val in attributes.items():
            attr_key = attr_key.title().replace('_', ' ')
            attr_val_repr = f"{attr_key : <{max_key_width}} = {repr(attr_val)}"

            if isinstance(attr_val, set):
                attr_val = list(attr_val)

            if isinstance(attr_val, PrettyPrinter) or isinstance(attr_val, datetime):
                attr_val_repr = f"{attr_key : <{max_key_width}} = {attr_val}"
            elif isinstance(attr_val, list) and len(attr_val) > 0:
                if isinstance(attr_val[0], PrettyPrinter) or len(str(attr_val)) > max_val_width:
                    pp_repr = "[\n" + "{}\n" + " " * indent_prev + "]"
                    pp = [" " * indent + str(v).replace("\n", "\n" + " " * indent) for v in attr_val]
                    attr_val = pp_repr.format(",\n".join(pp))
                    attr_val_repr = f"{attr_key : <{max_key_width}} = {attr_val}"
            elif isinstance(attr_val, dict):
                pp_repr = " " * indent + "{}"
                pp = self._to_str(attr_val, indent=indent, increment=increment)

                if len(pp) == 0:
                    attr_val = "{}"
                elif len(str(pp)) < max_val_width:
                    attr_val = "{ " + ", ".join(pp) + " }"
                else:
                    pp_repr = pp_repr.format("\n".join(pp)).replace("\n", "\n" + " " * indent)
                    attr_val = "{\n" + pp_repr + "\n" + " " * indent_prev + "}"
                attr_val_repr = f"{attr_key : <{max_key_width}} = {attr_val}"

            attributes_repr.append(attr_val_repr)

        return attributes_repr

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.as_dict()})"


@dataclass
class UpdateResult(ABC):
    pass
