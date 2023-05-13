import inspect
import re
from copy import copy
from typing import List, Optional, Union, Any, Literal, Iterable, TypeVar, Tuple

from syncify.abstract.collection import Album, ItemCollection
from syncify.abstract.item import Track, Base
from syncify.utils.logger import Logger

MatchTypes = Union[Track, Album]


T = TypeVar("T")


class ItemMatcher(Base, Logger):

    @property
    def name(self) -> str:
        return ""

    def _log_padded(self, log: List[str], pad: str = ' '):
        log[0] = pad * 3 + ' ' + log[0]
        self._logger.debug(" | ".join(log))

    def _log_algorithm(self, source: Base, extra: Optional[List[str]] = None):
        algorithm = inspect.stack()[1][0].f_code.co_name.upper().replace("_", " ")
        log = [source.name, algorithm]
        if extra:
            log += extra
        self._log_padded(log, pad='>')

    def _log_test(self, source: Base, result: MatchTypes, test: Any, extra: Optional[List[str]] = None) -> None:
        algorithm = inspect.stack()[1][0].f_code.co_name.replace("match").upper().replace("_", " ")
        log = [source.name, f">>> Testing URI: {result.uri}", f"{algorithm:<10}={test:<5}"]
        if extra:
            log += extra
        self._log_padded(log, pad=' ')

    def _log_match(self, source: Base, result: MatchTypes, extra: Optional[List[str]] = None) -> None:
        log = [source.name, f"<<< Matched URI: {result.uri}"]
        if extra:
            log += extra
        self._log_padded(log, pad='<')

    @staticmethod
    def clean_tags(source: T) -> T:
        """
        Clean tags on a copy of the input item and return the copy. Used for better matching/searching.
        Clean by removing redundant words, and only taking phrases before a certain word e.g. 'featuring', 'part'.

        :param source: The item with tags to clean
        :return: A copy of the original item with cleaned tags.
        """
        redundant_all = ["the", "a", "&", "and"]
        item_copy = copy(source)

        def process(value: str, redundant: Optional[List[str]] = None, split: Optional[List[str]] = None) -> str:
            value = re.sub(r"[(\[].*?[)\]]", "", value).lower()
            for word in redundant_all:
                value = value.replace(word + " ", "")

            if redundant:
                for word in redundant:
                    value = value.replace(word + " ", "")
            if split:
                for word in split:
                    value = value.split(word)[0].rstrip()

            return re.sub(r"[^\w']+", ' ', value).strip()

        title = getattr(item_copy, "title", None)
        if title:
            item_copy.title = process(title, redundant=["part"], split=["featuring", "feat.", "ft.", "/"])

        artist = getattr(item_copy, "artist", None)
        if artist:
            item_copy.artist = process(artist, split=["featuring", "feat.", "ft.", "vs"])

        album = getattr(item_copy, "album", None)
        if album:
            item_copy.album = process(album.split('-')[0], redundant=["ep"])

        return item_copy

    ###########################################################################
    ## Conditions
    ###########################################################################
    def not_karaoke(self, source: MatchTypes, result: MatchTypes) -> float:
        """Checks if a result is not a karaoke item."""
        karaoke_tags = ['karaoke', 'backing', 'instrumental']

        def is_karaoke(values: Union[str, List[str]]):
            karaoke = any(word in values for word in karaoke_tags)
            self._log_test(source=source, result=result, test=not karaoke, extra=[f"{karaoke_tags} -> {values}"])
            return karaoke

        if is_karaoke(result.name):  # title/album name
            return 0
        if is_karaoke(result.artist if isinstance(result, Track) else result.artists):  # artists
            return 0
        if isinstance(result, Track) and is_karaoke(result.album):  # album when the result is a track
            return 0
        return 1

    def match_name(self, source: Base, result: MatchTypes) -> float:
        """Match on names(/titles) and return a score. Score=0 when either value is None."""
        score = 0
        if source.name and result.name:
            score = sum(word in source.name for word in result.name) / len(source.name.split())

        self._log_test(source=source, result=result, test=score, extra=[f"{source.name} -> {result.name}"])
        return score

    def match_artist(self, source: MatchTypes, result: MatchTypes) -> float:
        """Match on artists and return a score. Score=0 when either value is None."""
        score = 0
        if source.artist and result.artist:
            self._log_test(source=source, result=result, test=score, extra=[f"{source.artist} -> {result.artist}"])
            return score

        artists_source = source.artist.replace(self.list_sep, "")
        artists_result = result.artist.split(self.list_sep)

        for i, artist in enumerate(artists_result, 1):
            score += (sum(word in artists_source for word in artist.split()) /
                      len(artists_source.split())) * (1 / i)
        return score

    def match_album(self, source: MatchTypes, result: MatchTypes) -> float:
        """Match on album and return a score. Score=0 when either value is None."""
        score = 0
        if source.album and result.album:
            score = sum(word in source.album for word in result.album) / len(source.album.split())

        self._log_test(source=source, result=result, test=score, extra=[f"{source.album} -> {result.album}"])
        return score

    def match_length(self, source: MatchTypes, result: MatchTypes) -> float:
        """Match on length and return a score. Score=0 when either value is None."""
        score = 0
        if source.length and result.length:
            score = (source.length - abs(source.length - result.length)) / source.length

        self._log_test(source=source, result=result, test=score, extra=[f"{source.length} -> {result.length}"])
        return score

    def match_year(self, source: MatchTypes, result: MatchTypes) -> float:
        """Match on year and return a score. Score=0 when either value is None."""
        score = 0
        if source.year and result.year:
            score = (source.year - abs(source.year - result.year)) / source.year

        self._log_test(source=source, result=result, test=score, extra=[f"{source.year} -> {result.year}"])
        return score

    ###########################################################################
    ## Algorithms
    ###########################################################################
    def score_match(
            self,
            source: MatchTypes,
            results: Iterable[MatchTypes],
            min_score: float = 1,
            max_score: float = 2,
            match_on: Optional[List[Literal["name", "artist", "album", "length", "year"]]] = None
    ) -> Optional[MatchTypes]:
        """
        Perform score match algorithm for a given item and its results.

        :param source: Source item to compare against and find a match for.
        :param results: Results for comparisons.
        :param min_score: Only return the result as a match if the score is above this value.
            Value will be limited to between 0.1 and 4.0.
        :param max_score: Stop matching once this score has been reached.
            Value will be limited to between 0.1 and 4.0.
        :param match_on: List of tags to match on.
        :return: dict. Metadata for locally stored track with added matched URI if found.
        """
        source_clean = self.clean_tags(source)
        score, result = self._get_score_from_results(source_clean=source_clean, results=results,
                                                     max_score=max_score, match_on=match_on)

        if score > min_score:
            self._log_match(source=source_clean, result=result)
            return result
        else:
            self._log_test(source=source_clean, result=result, test=score, extra=[f"NO MATCH: {score}<{min_score}"])

    def _get_score_from_results(
            self,
            source_clean: MatchTypes,
            results: Iterable[MatchTypes],
            max_score: float = 2,
            match_on: Optional[List[Literal["name", "artist", "album", "length", "year"]]] = None
    ) -> Optional[Tuple[float, MatchTypes]]:
        if not results:
            self._log_algorithm(source=source_clean, extra=[f"NO RESULTS GIVEN, SKIPPING"])
            return
        max_score = self._limit_value(max_score, floor=0.1, ceil=4)
        self._log_algorithm(source=source_clean, extra=[f"max_score={max_score}"])

        if not match_on:
            match_on = ["name", "artist", "album", "length", "year"]

        scores_highest = {}
        sum_highest = 0
        result = None

        for result in results:
            result_clean = self.clean_tags(result)
            scores_current = self._get_scores(source_clean=source_clean, result_clean=result_clean,
                                              max_score=max_score, match_on=match_on)

            sum_current = sum(scores_current.values())
            log_current = ', '.join(f'{k}={round(v, 2)}' for k, v in scores_current.items()) + f": {sum_current}"
            sum_highest = sum(scores_highest.values())
            log_highest = ', '.join(f'{k}={round(v, 2)}' for k, v in scores_highest.items()) + f": {sum_highest}"
            self._log_test(source=source_clean, result=result_clean, test=log_current, extra=[f"highest={log_highest}"])

            if sum_current > sum_highest:
                scores_highest = scores_current.copy()
                if sum_highest >= max_score:  # max threshold reached, match found
                    break

        return sum_highest, result

    def _get_scores(
            self,
            source_clean: MatchTypes,
            result_clean: MatchTypes,
            max_score: float = 2,
            match_on: Optional[List[Literal["name", "artist", "album", "length", "year"]]] = None
    ) -> dict[str, float]:
        scores_current: dict[str, float] = {}

        if "name" in match_on:
            scores_current["name"] = self.match_name(source=source_clean, result=result_clean)
        if "artist" in match_on:
            scores_current["artist"] = self.match_artist(source=source_clean, result=result_clean)
        if "album" in match_on and not isinstance(source_clean, ItemCollection):
            scores_current["album"] = self.match_album(source=source_clean, result=result_clean)
        if "length" in match_on and not isinstance(source_clean, ItemCollection):
            scores_current["length"] = self.match_length(source=source_clean, result=result_clean)
        if "year" in match_on:
            scores_current["year"] = self.match_year(source=source_clean, result=result_clean)
        if isinstance(source_clean, ItemCollection) and isinstance(result_clean, ItemCollection):
            # skip this if not a collection of tracks
            if not all(isinstance(i, Track) for i in source_clean.items):
                return scores_current
            if not all(isinstance(i, Track) for i in result_clean.items):
                return scores_current

            # also score all the items individually in the collection
            result_items: List[Track] = result_clean.items
            for i in source_clean.items:
                item_clean = self.clean_tags(i)
                score, _ = self._get_score_from_results(source_clean=item_clean, results=result_items,
                                                        match_on=match_on, max_score=max_score)
                scores_current["items"] += score / len(source_clean.items)

        return scores_current
