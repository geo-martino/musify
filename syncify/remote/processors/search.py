from abc import ABCMeta, abstractmethod
from collections.abc import Mapping, Sequence, Iterable, Collection
from dataclasses import dataclass, field
from typing import Any

from syncify.abstract.collection import ItemCollection, Album
from syncify.abstract.enums import Field, FieldCombined
from syncify.abstract.item import Item, Track, BaseObject
from syncify.abstract.misc import Result
from syncify.processors.match import ItemMatcher
from syncify.remote.api import RemoteAPI
from syncify.remote.base import Remote
from syncify.remote.config import RemoteObjectClasses
from syncify.remote.enums import RemoteObjectType
from syncify.utils.logger import REPORT


@dataclass(frozen=True)
class ItemSearchResult(Result):
    """Stores the results of the searching process

    :ivar matched: Sequence of Items for which matches were found from the search.
    :ivar unmatched: Sequence of Items for which matches were not found from the search.
    :ivar skipped: Sequence of Items which were skipped during the search.
    """
    matched: Sequence[Item] = field(default=tuple())
    unmatched: Sequence[Item] = field(default=tuple())
    skipped: Sequence[Item] = field(default=tuple())


@dataclass(frozen=True)
class Algorithm:
    """
    Key settings related to a search algorithm.

    :ivar search_fields_1: A list of the tag names to use as search fields in the 1st pass.
    :ivar search_fields_2: If no results are found from the tag names in ``search_fields_1`` on the 1st pass,
        an optional list of the tag names to use as search fields in the 2nd pass.
    :ivar search_fields_3: If no results are found from the tag names in ``search_fields_2`` on the 2nd pass,
        an optional list of the tag names to use as search fields in the 3rd pass.
    :ivar match_fields: The fields to match results on.
    :ivar result_count: The number of the results to request when querying the API.
    :ivar allow_karaoke: When True, items determined to be karaoke are allowed when matching added items.
        Skip karaoke results otherwise.
    :ivar min_score: The minimum acceptable score for an item to be considered a match.
    :ivar min_score: The maximum score for an item to be considered a perfect match.
        After this score is reached by an item, any other items are disregarded as potential matches.
    """
    search_fields_1: Iterable[str]
    match_fields: set[Field]
    result_count: int
    allow_karaoke: bool = False

    min_score: float = 0.1
    max_score: float = 0.8

    search_fields_2: Iterable[str] = ()
    search_fields_3: Iterable[str] = ()


@dataclass
class AlgorithmSettings:
    """Stores algorithm settings for the search operation"""
    ITEMS: Algorithm = Algorithm(
        search_fields_1=["name", "artist"],
        search_fields_2=["name", "album"],
        search_fields_3=["name"],
        match_fields={FieldCombined.TITLE, FieldCombined.ARTIST, FieldCombined.ALBUM, FieldCombined.LENGTH},
        result_count=10,
        allow_karaoke=False,
        min_score=0.1,
        max_score=0.
    )
    ALBUM: Algorithm = Algorithm(
        search_fields_1=["name", "artist"],
        search_fields_2=["name"],
        match_fields={FieldCombined.ARTIST, FieldCombined.ALBUM, FieldCombined.LENGTH},
        result_count=5,
        allow_karaoke=False,
        min_score=0.1,
        max_score=0.7
    )


class RemoteItemSearcher(Remote, ItemMatcher, metaclass=ABCMeta):
    """
    Searches for remote matches for a list of item collections.

    :param api: An API object for calling the remote query endpoint.
    :param allow_karaoke: When True, items determined to be karaoke are allowed when matching added items.
        Skip karaoke results otherwise.
    """

    @property
    @abstractmethod
    def _remote_types(self) -> RemoteObjectClasses:
        raise NotImplementedError

    def __init__(self, api: RemoteAPI, allow_karaoke: bool = False):
        super().__init__(allow_karaoke=allow_karaoke)
        self.api = api

    def _get_results(
            self, item: BaseObject, kind: RemoteObjectType, algorithm: Algorithm
    ) -> list[dict[str, Any]] | None:
        """Query the API to get results for the current item based on algorithm settings"""
        self.clean_tags(item)

        def execute_query(keys: Iterable[str]) -> tuple[list[dict[str, Any]], str]:
            """Generate and execute the query against the API for the given item's cleaned ``keys``"""
            attributes = set(item.clean_tags.get(key) for key in keys)
            q = " ".join(attr for attr in attributes if attr)
            return self.api.query(q, kind=kind, limit=algorithm.result_count), q

        results, query = execute_query(algorithm.search_fields_1)
        if not results and algorithm.search_fields_2:
            results, query = execute_query(algorithm.search_fields_2)
        if not results and algorithm.search_fields_3:
            results, query = execute_query(algorithm.search_fields_3)

        if not results:
            self._log_padded([item.name, f"Query: {query}", "Match failed: No results."], pad="<")
        else:
            self._log_padded([item.name, f"Query: {query}", f"{len(results)} results"])
            return results

    def _log_results(self, results: Mapping[ItemCollection, ItemSearchResult]) -> None:
        """Logs the final results of the ItemSearcher"""
        if not results:
            return

        max_width = self.get_max_width(results)

        total_matched = 0
        total_unmatched = 0
        total_skipped = 0
        total_all = 0

        for collection, result in results.items():
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
                f"\33[1m{self.align_and_truncate(collection.name, max_width=max_width)} \33[0m|"
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
        self.print_line(REPORT)

    def search(self, collections: Collection[ItemCollection]) -> dict[ItemCollection, ItemSearchResult]:
        """
        Searches for remote matches for the given list of item collections.

        :return: Map of the collection to its :py:class:`ItemSearchResult` object.
        """
        self.logger.debug("Searching items: START")
        if not [item for c in collections for item in c.items if item.has_uri is None]:
            self.logger.debug("\33[93mNo items to search. \33[0m")
            return {}

        self.logger.info(
            f"\33[1;95m ->\33[1;97m "
            f"Searching for matches on {self.remote_source} for {len(collections)} collections\33[0m"
        )

        search_results: dict[ItemCollection, ItemSearchResult] = {}
        for collection in self.get_progress_bar(iterable=collections, desc="Searching", unit="collections"):
            if not [item for item in collection.items if item.has_uri is None]:
                self._log_padded([collection.name, "Skipping search, no tracks to search"], pad='<')
            skipped = tuple(item for item in collection if item.has_uri is not None)

            if getattr(collection, "compilation", True) is not False:
                self._log_padded([collection.name, "Searching with item algorithm"], pad='>')
                self._search_items(collection=collection)
            else:
                self._log_padded([collection.name, "Searching with album algorithm"], pad='>')
                self._search_album(collection=collection)
                missing = [item for item in collection.items if item.has_uri is None]
                if missing:
                    self._log_padded(
                        [collection.name, f"Searching for {len(missing)} unmatched items in this collection"]
                    )
                    self._search_items(collection=collection)

            search_results[collection] = ItemSearchResult(
                matched=tuple(item for item in collection if item.has_uri),
                unmatched=tuple(item for item in collection if item.has_uri is None),
                skipped=skipped
            )

        self.print_line()
        self._log_results(search_results)
        self.logger.debug("Searching items: DONE\n")
        return search_results

    def _search_items(self, collection: ItemCollection) -> None:
        """Search for matches on individual items in an item collection that have ``None`` on ``has_uri`` attribute"""
        algorithm = AlgorithmSettings.ITEMS
        for item in [item for item in collection.items if item.has_uri is None]:
            if not isinstance(item, Track):
                # TODO: expand search logic to include all item types (low priority)
                raise NotImplementedError(
                    f"Currently only able to search for Track items, not {item.__class__.__name__}"
                )

            results = self._get_results(item, kind=RemoteObjectType.TRACK, algorithm=algorithm)
            tracks = list(map(self._remote_types.track, results))
            result = self.score_match(
                item,
                results=tracks,
                match_on=algorithm.match_fields,
                min_score=algorithm.min_score,
                max_score=algorithm.max_score
            )

            if result and result.has_uri:
                item.uri = result.uri

    def _search_album(self, collection: Album) -> None:
        """Search for matches on an entire album"""
        algorithm = AlgorithmSettings.ALBUM
        results = self._get_results(collection, kind=RemoteObjectType.ALBUM, algorithm=algorithm)
        albums = [self._remote_types.album(r) for r in results]
        [album.reload() for album in albums]

        # order and prioritise results that are closer to the item count of the input collection
        albums.sort(key=lambda x: abs(x.track_total - len(collection)))
        result = self.score_match(
            collection,
            results=albums,
            match_on=algorithm.match_fields,
            min_score=algorithm.min_score,
            max_score=algorithm.max_score
        )

        if not result:
            return

        for item in collection:
            item_result = self.score_match(
                item, results=result.items, match_on=[FieldCombined.TITLE], min_score=algorithm.min_score, max_score=0.8
            )
            if item_result:
                item.uri = item_result.uri
