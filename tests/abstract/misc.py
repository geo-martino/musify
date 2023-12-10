import json
import re
from abc import ABC, abstractmethod

from syncify.abstract.misc import PrettyPrinter


class PrettyPrinterTester(ABC):
    """Run generic tests for :py:class:`PrettyPrinter` implementations"""
    dict_json_equal: bool = True

    @staticmethod
    @abstractmethod
    def obj(*args, **kwargs) -> PrettyPrinter:
        """Yields a :py:class:`PrettyPrinter` object to be tested as pytest.fixture"""
        raise NotImplementedError

    @staticmethod
    def test_dict(obj: PrettyPrinter):
        # check dict output and str+repr dunder methods that use this output
        obj_as_dict = obj.as_dict()
        name = obj.__class__.__name__

        assert re.match(rf"^{name}\([\s\S]*\)$", str(obj))
        # plus 2 for class name line and final closing bracket line
        assert len(str(obj).split('\n')) >= len(obj_as_dict) + 2
        assert repr(obj) == f"{name}({obj_as_dict})"

    def test_json(self, obj: PrettyPrinter):
        obj_as_dict = obj.as_dict()
        obj_as_json = obj.as_json()

        if self.dict_json_equal:
            assert len(obj_as_dict) == len(obj_as_json)
            assert obj_as_dict.keys() == obj_as_json.keys()

        # check json is serialisable
        assert isinstance(json.dumps(obj_as_json), str)


def test_case_conversion():
    assert PrettyPrinter._pascal_to_snake("PascalCase") == "pascal_case"
    assert PrettyPrinter._pascal_to_snake("camelCase") == "camel_case"
    assert PrettyPrinter._snake_to_pascal("snake_case") == "SnakeCase"
