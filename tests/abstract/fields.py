from collections.abc import Container

from syncify.abstract.fields import Field, FieldCombined, TagField
from syncify.abstract.item import BaseObject


def check_values_match(field: type[Field]):
    """
    Check that all the enum values for a given :py:class:`Field` implementation
    match those in :py:class:`FieldCombined`
    """
    all_field_names = [enum.name for enum in FieldCombined.all()]
    for enum in field.all():
        if enum.name not in all_field_names:  # not a combined field enum
            continue
        enum_combined = FieldCombined.from_name(enum.name)
        assert len(enum_combined) == 1
        assert enum.value == enum_combined[0]


def tag_field_gives_valid_tags(field: type[TagField]):
    """Check the :py:meth:`to_tag` and :py:meth:`to_tags` methods of implementations of :py:class:`TagField`"""
    all_fields = field.all()
    all_tags = [tag for enum in all_fields for tag in enum.to_tag()]

    assert all(tag in field.__tags__ for tag in all_tags)
    assert all(tag in field.__tags__ for tag in field.to_tags(all_fields))


def check_all_fields_are_valid[T: Field](field: type[T], cls: type[BaseObject], ignore: Container[T] = ()):
    """
    Check that all the field names are present in the related class.

    :param field: The :py:class:`Field` type to test.
    :param cls: The associated class to check against.
    :param ignore: A set of :py:class:`Field` enums to skip checks for.
    """
    names = [e.name.lower() for enum in field.all() if enum not in ignore for e in field.map(enum)]

    for name in names:
        print(name)
        assert name in dir(cls)
        assert isinstance(getattr(cls, name), property)
