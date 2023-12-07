import json
import re

from syncify.abstract.misc import PrettyPrinter


def pretty_printer_tests(obj: PrettyPrinter, dict_json_equal: bool = True) -> None:
    """Check that basic functionality of pretty printer has been implemented without errors for the given object"""
    # check dict output and str+repr dunder methods that use this output
    obj_as_dict = obj.as_dict()
    name = obj.__class__.__name__

    assert re.match(rf"^{name}\([\s\S]*\)$", str(obj))
    # plus 2 for class name line and final closing bracket line
    assert len(str(obj).split('\n')) >= len(obj_as_dict) + 2
    assert repr(obj) == f"{name}({obj_as_dict})"

    # check JSON output
    obj_as_json = obj.as_json()
    if dict_json_equal:
        assert len(obj_as_dict) == len(obj_as_json)
        assert obj_as_dict.keys() == obj_as_json.keys()

    # check json is serialisable
    assert isinstance(json.dumps(obj_as_json), str)


def test_case_conversion():
    assert PrettyPrinter._pascal_to_snake("PascalCase") == "pascal_case"
    assert PrettyPrinter._pascal_to_snake("camelCase") == "camel_case"
    assert PrettyPrinter._snake_to_pascal("snake_case") == "SnakeCase"
