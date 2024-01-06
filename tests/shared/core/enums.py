from abc import ABC, abstractmethod, ABCMeta
from collections.abc import Container

from syncify.shared.core.base import NamedObject
from syncify.shared.core.enum import SyncifyEnum, Fields, TagField, ALL_FIELDS, Field


class EnumTester(ABC):
    """Run generic tests for :py:class:`SyncifyEnum` implementations"""

    @property
    @abstractmethod
    def cls(self) -> type[SyncifyEnum]:
        """The :py:class:`SyncifyEnum` class to test"""
        raise NotImplementedError

    def test_gets_enum_from_name_and_value(self):
        all_enums = self.cls.all()
        for enum in all_enums:
            assert enum == self.cls.from_name(enum.name)[0]
            assert enum == self.cls.from_value(enum.value)[0]

        assert self.cls.from_name(*(enum.name for enum in all_enums)) == set(all_enums)
        assert self.cls.from_value(*all_enums, fail_on_many=False) == set(all_enums)


class FieldTester(EnumTester, metaclass=ABCMeta):
    """Run generic tests for :py:class:`Field` enum implementations"""

    @abstractmethod
    def reference_cls(self) -> type[NamedObject]:
        """The associated class to validate field names against."""
        raise NotImplementedError

    @abstractmethod
    def reference_ignore(self) -> type[NamedObject]:
        """The associated class to validate field names against."""
        raise NotImplementedError

    def test_gets_enum_from_name_and_value(self):
        all_enums = self.cls.all()
        for enum in all_enums:
            assert self.cls.map(enum) == self.cls.from_name(enum.name)
            assert self.cls.map(enum) == self.cls.from_value(enum.value)

        all_mapped_enums = {e for enum in all_enums for e in self.cls.map(enum)}
        assert set(self.cls.from_name(*(enum.name for enum in all_enums))) == all_mapped_enums
        assert set(self.cls.from_value(*all_enums)) == all_mapped_enums

    def test_values_match(self):
        all_field_names = [enum.name for enum in ALL_FIELDS]
        for enum in self.cls.all():
            if enum.name not in all_field_names:  # not a combined field enum
                continue
            enum_combined = Fields.from_name(enum.name)
            assert len(enum_combined) == 1
            assert enum.value == enum_combined[0]

    def test_all_fields_are_valid(self, reference_cls: type[NamedObject], reference_ignore: Container[Field]):
        names = [e.name.lower() for enum in self.cls.all() if enum not in reference_ignore for e in self.cls.map(enum)]

        for name in names:
            assert name in dir(reference_cls)
            assert isinstance(getattr(reference_cls, name), property)


class TagFieldTester(FieldTester, metaclass=ABCMeta):
    """Run generic tests for :py:class:`TagField` enum implementations"""

    @property
    @abstractmethod
    def cls(self) -> type[TagField]:
        """The :py:class:`TagField` class to test"""
        raise NotImplementedError

    def test_tag_field_gives_valid_tags(self):
        all_fields = self.cls.all()
        all_tags = [tag for enum in all_fields for tag in enum.to_tag()]

        assert all(tag in self.cls.__tags__ for tag in all_tags)
        assert all(tag in self.cls.__tags__ for tag in self.cls.to_tags(all_fields))
