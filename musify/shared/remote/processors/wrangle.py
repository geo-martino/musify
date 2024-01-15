from abc import ABCMeta, abstractmethod
from collections.abc import Mapping
from typing import Any

from musify.shared.remote import Remote
from musify.shared.remote.enum import RemoteIDType, RemoteObjectType
from musify.shared.remote.exception import RemoteObjectTypeError
from musify.shared.remote.types import APIMethodInputType


class RemoteDataWrangler(Remote, metaclass=ABCMeta):

    @property
    @abstractmethod
    def unavailable_uri_dummy(self) -> str:
        """
        The value to use as a URI for an item which does not have an associated remote object.
        An item that has this URI value will be excluded from most remote logic.
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def get_id_type(value: str, kind: RemoteObjectType | None = None) -> RemoteIDType:
        """
        Determine the remote ID type of the given ``value`` and return its type.

        :param value: URL/URI/ID to check.
        :param kind: When this is equal to ``USER``, ignore checks and always return ``ID`` as  type.
        :return: The :py:class:`RemoteIDType`.
        :raise RemoteIDTypeError: Raised when the function cannot determine the ID type
            of the input ``value``.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def validate_id_type(cls, value: str, kind: RemoteIDType = RemoteIDType.ALL) -> bool:
        """Check that the given ``value`` is a type of remote ID given by ``kind``"""
        raise NotImplementedError

    @classmethod
    def get_item_type(cls, values: APIMethodInputType, kind: RemoteObjectType | None = None) -> RemoteObjectType:
        """
        Determine the remote object type of ``values``.

        ``values`` may be:
            * A string representing a URL/URI/ID.
            * A MutableSequence of strings representing URLs/URIs/IDs of the same type.
            * A remote API JSON response for a collection including a valid item type value under a ``type`` key.
            * A MutableSequence of remote API JSON responses for a collection including the same structure as above.

        :param values: The values representing some remote objects. See description for allowed value types.
            These items must all be of the same type of item to pass i.e. all tracks OR all artists etc.
        :param kind: The :py:class:`RemoteObjectType` if the value is found to be an ID.
        :return: :py:class:`RemoteObjectType`
        :raise RemoteObjectTypeError: Raised when the function cannot determine the item type
            of the input ``values``.
            Or when the list contains strings representing many differing remote object types or only IDs.
        """
        if isinstance(values, str) or isinstance(values, Mapping):
            return cls._get_item_type(value=values, kind=kind)

        if len(values) == 0:
            raise RemoteObjectTypeError("No values given: collection is empty")

        kinds = {cls._get_item_type(value=value, kind=kind) for value in values if value is not None}
        kinds.discard(None)
        if len(kinds) == 0:
            raise RemoteObjectTypeError("Given items are invalid or are IDs with no kind given")
        if len(kinds) != 1:
            value = [kind.name for kind in kinds]
            raise RemoteObjectTypeError(f"Ensure all the given items are of the same type! Found", value=value)
        return kinds.pop()

    @staticmethod
    @abstractmethod
    def _get_item_type(value: str | Mapping[str, Any], kind: RemoteObjectType) -> RemoteObjectType | None:
        """
        Determine the remote object type of the given ``value`` and return its type.

        ``value`` may be:
            * A string representing a URL/URI/ID.
            * A remote API JSON response for a collection with a valid ID value under an ``id`` key.

        :param value: The value representing some remote collection. See description for allowed value types.
        :param kind: The :py:class:`RemoteObjectType` if the value is found to be an ID.
        :return: The :py:class:`RemoteObjectType`. If the given value is determined to be an ID, returns None.
        :raise RemoteObjectTypeError: Raised when the function cannot determine the item type
            of the input ``values``.
        :raise EnumNotFoundError: Raised when the item type of the given ``value`` is not
            a valid remote object type.
        """
        raise NotImplementedError

    @classmethod
    def validate_item_type(cls, values: APIMethodInputType, kind: RemoteObjectType) -> None:
        """
        Check that the given ``values`` are a type of item given by ``kind`` or a simple ID.

        ``values`` may be:
            * A string representing a URL/URI/ID.
            * A MutableSequence of strings representing URLs/URIs/IDs of the same type.
            * A remote API JSON response for a collection including a valid item type value under a ``type`` key.
            * A MutableSequence of remote API JSON responses for a collection including the same structure as above.

        :param values: The values representing some remote objects. See description for allowed value types.
            These items must all be of the same type of item to pass i.e. all tracks OR all artists etc.
        :param kind: The remote object type to check for.
        :raise RemoteObjectTypeError: Raised when the function cannot validate the item type
            of the input ``values`` is of type ``kind`` or a simple ID.
        """
        item_type = cls.get_item_type(values, kind=kind)
        if item_type is not None and not item_type == kind:
            item_str = "unknown" if item_type is None else item_type.name.lower() + "s"
            raise RemoteObjectTypeError(f"Given items must all be {kind.name.lower()} URLs/URIs/IDs, not {item_str}")

    @classmethod
    @abstractmethod
    def convert(
            cls,
            value: str,
            kind: RemoteObjectType | None = None,
            type_in: RemoteIDType = RemoteIDType.ALL,
            type_out: RemoteIDType = RemoteIDType.ID
    ) -> str:
        """
        Converts ID to required format - API URL, EXT URL, URI, or ID.

        :param value: URL/URI/ID to convert.
        :param kind: Optionally, give the item type of the input ``value`` to skip some checks.
            This is required when the given ``value`` is an ID.
        :param type_in: Optionally, give the ID type of the input ``value`` to skip some checks.
        :param type_out: The ID type of the output ``value``.
        :return: Formatted string.
        :raise RemoteIDTypeError: Raised when the function cannot determine the item type
            of the input ``value``.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def extract_ids(cls, values: APIMethodInputType, kind: RemoteObjectType | None = None) -> list[str]:
        """
        Extract a list of IDs from input ``values``.

        ``values`` may be:
            * A string representing a URL/URI/ID.
            * A MutableSequence of strings representing URLs/URIs/IDs of the same type.
            * A remote API JSON response for a collection including:
                - a valid ID value under an ``id`` key,
                - a valid item type value under a ``type`` key if ``kind`` is None.
            * A MutableSequence of remote API JSON responses for a collection including the same structure as above.

        :param values: The values representing some remote objects. See description for allowed value types.
            These items may be of mixed item types e.g. some tracks AND some artists.
        :param kind: Optionally, give the item type of the input ``value`` to skip some checks.
            This is required when the given ``value`` is an ID.
        :return: List of IDs.
        :raise RemoteError: Raised when the function cannot determine the item type of the input ``values``.
            Or when it does not recognise the type of the input ``values`` parameter.
        """
        raise NotImplementedError
