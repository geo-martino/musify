import json
import re
from abc import ABCMeta, abstractmethod

from musify.printer import PrettyPrinter


class PrettyPrinterTester(metaclass=ABCMeta):
    """Run generic tests for :py:class:`PrettyPrinter` implementations"""
    dict_json_equal: bool = True

    @abstractmethod
    def obj(self, *args, **kwargs) -> PrettyPrinter:
        """Yields a :py:class:`PrettyPrinter` object to be tested as pytest.fixture."""
        raise NotImplementedError

    @staticmethod
    def test_dict(obj: PrettyPrinter):
        # check dict output and str+repr dunder methods that use this output
        obj_dict = obj.as_dict()
        name = obj.__class__.__name__

        assert re.match(rf"^{name}\([\s\S]*\)$", str(obj))
        # plus 2 for class name line and final closing bracket line
        assert len(str(obj).split("\n")) >= len(obj_dict) + (2 if "\n" in str(obj) else 0)
        assert repr(obj) == f"{name}({obj_dict})"

    def test_json(self, obj: PrettyPrinter):
        obj_dict = obj.as_dict()
        obj_json = obj.json()

        if self.dict_json_equal:
            assert len(obj_dict) == len(obj_json)
            assert obj_dict.keys() == obj_json.keys()

        # check json is serializable
        assert isinstance(json.dumps(obj_json), str)


def test_case_conversion():
    assert PrettyPrinter._pascal_to_snake("PascalCase") == "pascal_case"
    assert PrettyPrinter._pascal_to_snake("camelCase") == "camel_case"
    assert PrettyPrinter._snake_to_pascal("snake_case") == "SnakeCase"
