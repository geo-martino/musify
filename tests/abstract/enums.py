from collections.abc import Container

from syncify.abstract.enums import SyncifyEnum, Field, FieldCombined, TagField, ALL_FIELDS
from syncify.abstract.item import BaseObject


def gets_enum_from_name_and_value(cls: type[SyncifyEnum]):
    """Check the given :py:class:`SyncifyEnum` can get the enum back from its string representation and/or value"""
    all_enums = cls.all()
    for enum in all_enums:
        assert enum == cls.from_name(enum.name)[0]
        assert enum == cls.from_value(enum.value)[0]

    assert cls.from_name(*(enum.name for enum in all_enums)) == set(all_enums)
    assert cls.from_value(*all_enums, fail_on_many=False) == set(all_enums)


def gets_field_from_name_and_value(cls: type[Field]):
    """Check the given :py:class:`Field` can get the enum back from its string representation and/or value"""
    all_enums = cls.all()
    for enum in all_enums:
        assert cls.map(enum) == cls.from_name(enum.name)
        assert cls.map(enum) == cls.from_value(enum.value)

    all_mapped_enums = {e for enum in all_enums for e in cls.map(enum)}
    assert set(cls.from_name(*(enum.name for enum in all_enums))) == all_mapped_enums
    assert set(cls.from_value(*all_enums)) == all_mapped_enums


def check_values_match(cls: type[Field]):
    """
    Check that all the enum values for a given :py:class:`Field` implementation
    match those in :py:class:`FieldCombined`
    """
    all_field_names = [enum.name for enum in ALL_FIELDS]
    for enum in cls.all():
        if enum.name not in all_field_names:  # not a combined field enum
            continue
        enum_combined = FieldCombined.from_name(enum.name)
        assert len(enum_combined) == 1
        assert enum.value == enum_combined[0]


def tag_field_gives_valid_tags(cls: type[TagField]):
    """Check the :py:meth:`to_tag` and :py:meth:`to_tags` methods of implementations of :py:class:`TagField`"""
    all_fields = cls.all()
    all_tags = [tag for enum in all_fields for tag in enum.to_tag()]

    assert all(tag in cls.__tags__ for tag in all_tags)
    assert all(tag in cls.__tags__ for tag in cls.to_tags(all_fields))


def check_all_fields_are_valid[T: Field](cls: type[T], reference: type[BaseObject], ignore: Container[T] = ()):
    """
    Check that all the field names are present in the related class.

    :param cls: The :py:class:`Field` type to test.
    :param reference: The associated class to check against.
    :param ignore: A set of :py:class:`Field` enums to skip checks for.
    """
    names = [e.name.lower() for enum in cls.all() if enum not in ignore for e in cls.map(enum)]

    for name in names:
        assert name in dir(reference)
        assert isinstance(getattr(reference, name), property)
