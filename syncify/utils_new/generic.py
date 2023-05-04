import re
from abc import ABCMeta, abstractmethod
from datetime import datetime
from typing import Tuple, Mapping, List, MutableMapping

sort_ignore_words = ["The", "A"]


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


def flatten_nested(nested: Mapping, sort_keys: bool = False, sort_ignore: bool = False, previous: list = None) -> List:
    if previous is None:
        previous = []

    if isinstance(nested, dict):
        if sort_keys:
            key_func = (lambda x: strip_ignore_words(x[0])) if sort_ignore else (lambda x: x[0])
            values = [v for _, v in sorted(nested.items(), key=key_func)]
        else:
            values = list(nested.values())

        for value in values:
            flatten_nested(value, sort_keys=sort_keys, previous=previous)
    elif isinstance(nested, list):
        previous.extend(nested)

    return previous


class PP(metaclass=ABCMeta):
    @abstractmethod
    def as_dict(self) -> MutableMapping[str, object]:
        """Return a dictionary representation of the key attributes of this object"""
        raise NotImplementedError

    def as_json(self) -> Mapping[str, object]:
        """Return a dictionary representation of the key attributes of this object that is safe to output to json"""
        attributes = {}

        for attr_name, attr_value in self.as_dict().items():
            if isinstance(attr_value, PP):
                attributes[attr_name] = attr_value.as_json()
            if isinstance(attr_value, datetime):
                attributes[attr_name] = attr_value.strftime("%Y-%m-%d %H:%M:%S")
            else:
                attributes[attr_name] = attr_value

        return attributes

    def __str__(self) -> str:
        result = f"{self.__class__.__name__}(\n{{}}\n)"
        attributes = self.as_dict()
        indent = 2

        max_key_width = max(len(tag_name) for tag_name in attributes)
        max_val_width = 120 - max_key_width
        attributes_repr = []
        for attr_key, attr_val in attributes.items():
            attr_val_repr = f"{attr_key.title() : <{max_key_width}} = {repr(attr_val)}"

            if isinstance(attr_val, set):
                attr_val = list(attr_val)

            if isinstance(attr_val, list):
                if len(attr_val) > 0 and hasattr(attr_val[0], "as_json") or len(str(attr_val)) > max_val_width:
                    pp_repr = f"[\n{{}}\n" + " " * indent + "]"
                    pp = [" " * indent * 2 + str(v).replace("\n", "\n" + " " * indent * 2) for v in attr_val]
                    attr_val = pp_repr.format(",\n".join(pp))
                    attr_val_repr = f"{attr_key.title() : <{max_key_width}} = {attr_val}"

            attributes_repr.append(attr_val_repr)

        return result.format("\n".join([" " * indent + attribute for attribute in attributes_repr]))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.as_dict()})"
