from abc import ABCMeta, abstractmethod

from syncify.remote.api.collection import RemoteAPICollections
from syncify.remote.api.core import RemoteAPICore
from syncify.remote.api.item import RemoteAPIItems
from syncify.remote.enums import RemoteIDType


class RemoteAPI(RemoteAPICore, RemoteAPIItems, RemoteAPICollections, metaclass=ABCMeta):
    """
    Collection of endpoints for a remote API.
    See :py:class:`RequestHandler` and :py:class:`APIAuthoriser`
    for more info on which params to pass to authorise and execute requests.

    :param handler_kwargs: The authorisation kwargs to be passed to :py:class:`APIAuthoriser`.
    """

    @property
    def user_id(self) -> str | None:
        return self._user_id

    @property
    def user_name(self) -> str | None:
        return self._user_name

    def __init__(self, **handler_kwargs):
        handler_kwargs = {k: v for k, v in handler_kwargs.items() if k != "name"}
        super().__init__(name=self.remote_source, **handler_kwargs)

        self._user_id = None
        self._user_name = None

    ###########################################################################
    ## Misc endpoints
    ###########################################################################
    def format_item_data(
            self, i: int, name: str, uri: str, length: float = 0, total: int = 1, max_width: int = 50
    ) -> str:
        """
        Pretty format item data for displaying to the user

        :param i: The position of this item in the collection.
        :param name: The name of the item.
        :param uri: The URI of the item.
        :param length: The duration of the item in seconds.
        :param total: The total number of items in the collection
        :param max_width: The maximum width to print names as. Any name lengths longer than this will be truncated.
        :return: The formatted string.
        """
        return (
            f"\t\33[92m{str(i).zfill(len(str(total)))} \33[0m- "
            f"\33[97m{self.align_and_truncate(name, max_width=max_width)} \33[0m| "
            f"\33[91m{str(int(length // 60)).zfill(2)}:{str(round(length % 60)).zfill(2)} \33[0m| "
            f"\33[93m{uri} \33[0m- "
            f"{self.convert(uri, type_in=RemoteIDType.URI, type_out=RemoteIDType.URL_EXT)}"
        )

    @abstractmethod
    def pretty_print_uris(
            self, value: str | None = None, kind: RemoteIDType | None = None, use_cache: bool = True
    ) -> None:
        """
        Diagnostic function. Print tracks from a given link in ``<track> - <title> | <URI> - <URL>`` format
        for a given URL/URI/ID.

        :param value: URL/URI/ID to print information for.
        :param kind: When an ID is provided, give the kind of ID this is here.
            If None and ID is given, user will be prompted to give the kind anyway.
        :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
        """
        raise NotImplementedError
