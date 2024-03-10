"""
Processor operations that search for and match given items with remote items.

Searches for matches on remote APIs, matches the item to the best matching result from the query,
and assigns the ID of the matched object back to the item.
"""

from abc import ABCMeta, abstractmethod
from collections.abc import Mapping, Sequence, Iterable, Collection
from dataclasses import dataclass, field
from typing import Any

from musify.processors.match import ItemMatcher
from musify.shared.core.base import NameableTaggableMixin, Item
from musify.shared.core.collection import ItemCollection
from musify.shared.core.enum import TagField, TagFields as Tag
from musify.shared.core.misc import Result
from musify.shared.core.object import Track
from musify.shared.logger import REPORT
from musify.shared.remote import Remote
from musify.shared.remote.api import RemoteAPI
from musify.shared.remote.config import RemoteObjectClasses
from musify.shared.remote.enum import RemoteObjectType
from musify.shared.utils import align_string, get_max_width


@dataclass(frozen=True)
class ItemSearchResult(Result):
    """Stores the results of the searching process."""
    #: Sequence of Items for which matches were found from the search.
    matched: Sequence[Item] = field(default=tuple())
    #: Sequence of Items for which matches were not found from the search.
    unmatched: Sequence[Item] = field(default=tuple())
    #: Sequence of Items which were skipped during the search.
    skipped: Sequence[Item] = field(default=tuple())


@dataclass(frozen=True)
class SearchSettings:
    """Key settings related to a search algorithm."""
    #: A sequence of the tag names to use as search fields in the 1st pass.
    search_fields_1: Sequence[TagField]
    #: The fields to match results on.
    match_fields: TagField | Iterable[TagField]
    #: The number of the results to request when querying the API.
    result_count: int
    #: When True, items determined to be karaoke are allowed when matching added items.
    #: Skip karaoke results otherwise.
    allow_karaoke: bool = False

    #: The minimum acceptable score for an item to be considered a match.
    min_score: float = 0.1
    #: The maximum score for an item to be considered a perfect match.
    #: After this score is reached by an item, any other items are disregarded as potential matches.
    max_score: float = 0.8

    #: If no results are found from the tag names in ``search_fields_1`` on the 1st pass,
    #: an optional sequence of the tag names to use as search fields in the 2nd pass.
    search_fields_2: Iterable[TagField] = ()
    #: If no results are found from the tag names in ``search_fields_2`` on the 2nd pass,
    #: an optional sequence of the tag names to use as search fields in the 3rd pass.
    search_fields_3: Iterable[TagField] = ()


class RemoteItemSearcher(Remote, ItemMatcher, metaclass=ABCMeta):
    """
    Searches for remote matches for a list of item collections.

    :param api: An API object for calling the remote query endpoint.
    :param use_cache: Use the cache when calling the API endpoint. Set as False to refresh the cached response.
    """

    __slots__ = ("api", "use_cache")

    #: The :py:class:`SearchSettings` to use when running item searches
    settings_items = SearchSettings(
        search_fields_1=[Tag.NAME, Tag.ARTIST],
        search_fields_2=[Tag.NAME, Tag.ALBUM],
        search_fields_3=[Tag.NAME],
        match_fields={Tag.TITLE, Tag.ARTIST, Tag.ALBUM, Tag.LENGTH},
        result_count=10,
        allow_karaoke=False,
        min_score=0.1,
        max_score=0.8
    )
    #: The :py:class:`SearchSettings` to use when running album searches
    settings_albums = SearchSettings(
        search_fields_1=[Tag.NAME, Tag.ARTIST],
        search_fields_2=[Tag.NAME],
        match_fields={Tag.ARTIST, Tag.ALBUM, Tag.LENGTH},
        result_count=5,
        allow_karaoke=False,
        min_score=0.1,
        max_score=0.7
    )

    @property
    @abstractmethod
    def _object_cls(self) -> RemoteObjectClasses:
        """Stores the key object classes for a remote source."""
        raise NotImplementedError

    def __init__(self, api: RemoteAPI, use_cache: bool = False):
        super().__init__()

        #: The :py:class:`RemoteAPI` to call
        self.api = api
        #: When true, use the cache when calling the API endpoint
        self.use_cache = use_cache

    def _get_results(
            self, item: NameableTaggableMixin, kind: RemoteObjectType, settings: SearchSettings
    ) -> list[dict[str, Any]] | None:
        """Query the API to get results for the current item based on algorithm settings"""
        self.clean_tags(item)

        def execute_query(keys: Iterable[TagField]) -> tuple[list[dict[str, Any]], str]:
            """Generate and execute the query against the API for the given item's cleaned ``keys``"""
            attributes = [item.clean_tags.get(key) for key in keys]
            q = " ".join(str(attr) for attr in attributes if attr)
            return self.api.query(q, kind=kind, limit=settings.result_count), q

        results, query = execute_query(settings.search_fields_1)
        if not results and settings.search_fields_2:
            results, query = execute_query(settings.search_fields_2)
        if not results and settings.search_fields_3:
            results, query = execute_query(settings.search_fields_3)

        if results:
            self._log_padded([item.name, f"Query: {query}", f"{len(results)} results"])
            return results
        self._log_padded([item.name, f"Query: {query}", "Match failed: No results."], pad="<")

    def _log_results(self, results: Mapping[str, ItemSearchResult]) -> None:
        """Logs the final results of the ItemSearcher"""
        if not results:
            return

        max_width = get_max_width(results)

        total_matched = 0
        total_unmatched = 0
        total_skipped = 0
        total_all = 0

        for name, result in results.items():
            matched = len(result.matched)
            unmatched = len(result.unmatched)
            skipped = len(result.skipped)
            total = total_matched + total_unmatched + total_skipped

            total_matched += matched
            total_unmatched += unmatched
            total_skipped += skipped
            total_all += total

            colour1 = "\33[92m" if matched > 0 else "\33[94m"
            colour2 = "\33[92m" if unmatched == 0 else "\33[91m"
            colour3 = "\33[92m" if skipped == 0 else "\33[93m"

            self.logger.report(
                f"\33[1m{align_string(name, max_width=max_width)} \33[0m|"
                f"{colour1}{matched:>6} matched \33[0m| "
                f"{colour2}{unmatched:>6} unmatched \33[0m| "
                f"{colour3}{skipped:>6} skipped \33[0m| "
                f"\33[97m{total:>6} total \33[0m"
            )

        self.logger.report(
            f"\33[1;96m{'TOTALS':<{max_width}} \33[0m|"
            f"\33[92m{total_matched:>6} matched \33[0m| "
            f"\33[91m{total_unmatched:>6} unmatched \33[0m| "
            f"\33[93m{total_skipped:>6} skipped \33[0m| "
            f"\33[97m{total_all:>6} total \33[0m"
        )
        self.logger.print(REPORT)

    # noinspection PyMethodOverriding
    def __call__(self, collections: Collection[ItemCollection]) -> dict[str, ItemSearchResult]:
        return self.search(collections=collections)

    def search(self, collections: Collection[ItemCollection]) -> dict[str, ItemSearchResult]:
        """
        Searches for remote matches for the given list of item collections.

        :return: Map of the collection's name to its :py:class:`ItemSearchResult` object.
        """
        self.logger.debug("Searching: START")
        if not [item for c in collections for item in c.items if item.has_uri is None]:
            self.logger.debug("\33[93mNo items to search. \33[0m")
            return {}

        kinds = {coll.__class__.__name__ for coll in collections}
        kind = kinds.pop() if len(kinds) == 1 else "collection"
        self.logger.info(
            f"\33[1;95m ->\33[1;97m "
            f"Searching for matches on {self.source} for {len(collections)} {kind}s\33[0m"
        )

        bar = self.logger.get_progress_bar(iterable=collections, desc="Searching", unit=f"{kind}s")
        search_results = {coll.name: self._search_collection(collection=coll) for coll in bar}

        self.logger.print()
        self._log_results(search_results)
        self.logger.debug("Searching: DONE\n")
        return search_results

    def _search_collection(self, collection: ItemCollection) -> ItemSearchResult:
        kind = collection.__class__.__name__

        skipped = tuple(item for item in collection if item.has_uri is not None)
        if len(skipped) == len(collection):
            self._log_padded([collection.name, "Skipping search, no tracks to search"], pad='<')

        if getattr(collection, "compilation", True) is False:
            self._log_padded([collection.name, "Searching with album algorithm"], pad='>')
            self._search_album(collection=collection)

            missing = [item for item in collection.items if item.has_uri is None]
            if missing:
                self._log_padded([collection.name, f"Searching for {len(missing)} unmatched items in this {kind}"])
                self._search_items(collection=collection)
        else:
            self._log_padded([collection.name, "Searching with item algorithm"], pad='>')
            self._search_items(collection=collection)

        return ItemSearchResult(
            matched=tuple(item for item in collection if item.has_uri and item not in skipped),
            unmatched=tuple(item for item in collection if item.has_uri is None and item not in skipped),
            skipped=skipped
        )

    def _search_items(self, collection: Iterable[Item]) -> None:
        """Search for matches on individual items in an item collection that have ``None`` on ``has_uri`` attribute"""
        for item in filter(lambda i: i.has_uri is None, collection):
            if not isinstance(item, Track):
                # TODO: expand search logic to include all item types (low priority)
                raise NotImplementedError(
                    f"Currently only able to search for Track items, not {item.__class__.__name__}"
                )

            results = self._get_results(item, kind=RemoteObjectType.TRACK, settings=self.settings_items)
            if not results:
                continue

            result = self.match(
                item,
                results=map(lambda response: self._object_cls.track(api=self.api, response=response), results),
                match_on=self.settings_items.match_fields,
                min_score=self.settings_items.min_score,
                max_score=self.settings_items.max_score,
                allow_karaoke=self.settings_items.allow_karaoke,
            )

            if result and result.has_uri:
                item.uri = result.uri

    def _search_album(self, collection: ItemCollection) -> None:
        """Search for matches on an entire album"""
        if all(item.has_uri for item in collection):
            return

        results = self._get_results(collection, kind=RemoteObjectType.ALBUM, settings=self.settings_albums)

        # convert to RemoteAlbum objects and extend items on each response
        albums = list(map(
            lambda response: self._object_cls.album(api=self.api, response=response, skip_checks=True), results
        ))
        kind = RemoteObjectType.ALBUM
        key = self.api.collection_item_map[kind]
        for album in albums:  # extend album's tracks
            self.api.extend_items(album.response, kind=kind, key=key, use_cache=self.use_cache)

        # order to prioritise results that are closer to the item count of the input collection
        albums.sort(key=lambda x: abs(x.track_total - len(collection)))
        # noinspection PyTypeChecker
        result = self.match(
            collection,
            results=albums,
            match_on=self.settings_albums.match_fields,
            min_score=self.settings_albums.min_score,
            max_score=self.settings_albums.max_score,
            allow_karaoke=self.settings_albums.allow_karaoke,
        )

        if not result:
            return

        for item in filter(lambda i: i.has_uri is None, collection):
            # match items back onto the result to discern which URI matches which
            item_result = self.match(
                item,
                results=result.items,
                match_on=[Tag.TITLE],
                min_score=self.settings_items.min_score,
                max_score=self.settings_items.max_score,
                allow_karaoke=self.settings_items.allow_karaoke,
            )
            if item_result:
                item.uri = item_result.uri
