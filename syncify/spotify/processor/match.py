import inspect
import re
from copy import copy
from typing import List, Optional, Union, Any, Literal, Iterable

from syncify.abstract.collection import Album
from syncify.abstract.item import Track, Base
from syncify.utils.logger import Logger

MatchTypes = Union[Track, Album]


class ItemMatcher(Base, Logger):

    _log_prefix = ">>>"

    def _log_algorithm(self, item: MatchTypes, extra: Optional[List[str]] = None):
        algorithm = inspect.stack()[1][0].f_code.co_name.upper().replace("_", " ")
        log = [f"{self._log_prefix} {item.name}", algorithm]
        if extra:
            log += extra
        self._logger.debug(" | ".join(log))

    def _log_test(self, item: MatchTypes, result: MatchTypes, test: Any, extra: Optional[List[str]] = None) -> None:
        algorithm = inspect.stack()[1][0].f_code.co_name.replace("match").upper().replace("_", " ")
        log = [re.sub(r'\S', ' ', self._log_prefix) + " " + item.name,
               f">>> Testing URI: {result.uri}", f"{algorithm:<10}={test:<5}"]
        if extra:
            log += extra

        self._logger.debug(" | ".join(log))

    def _log_match(self, item: MatchTypes, result: MatchTypes, extra: Optional[List[str]] = None) -> None:
        log = [re.sub(r'\S', '<', self._log_prefix) + " " + item.name, f"<<< Matched URI: {result.uri}"]
        if extra:
            log += extra
        self._logger.debug(" | ".join(log))

    @staticmethod
    def clean_tags(item: MatchTypes) -> MatchTypes:
        """
        Clean tags on a copy of the input item and return the copy. Used for better matching/searching.
        Clean by removing redundant words, and only taking phrases before a certain word e.g. 'featuring', 'part'.

        :param item: The item with tags to clean
        :return: A copy of the original item with cleaned tags.
        """
        redundant_all = ["the", "a", "&", "and"]
        item_copy = copy(item)

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
    def not_karaoke(self, item: MatchTypes, result: MatchTypes) -> float:
        """Checks if a result is not a karaoke item."""
        karaoke_tags = ['karaoke', 'backing', 'instrumental']

        def is_karaoke(values: Union[str, List[str]]):
            karaoke = any(word in values for word in karaoke_tags)
            self._log_test(item=item, result=result, test=not karaoke, extra=[f"{karaoke_tags} -> {values}"])
            return karaoke

        if is_karaoke(result.name):  # title/album name
            return 0
        if is_karaoke(result.artist if isinstance(result, Track) else result.artists):  # artists
            return 0
        if isinstance(result, Track) and is_karaoke(result.album):  # album when the result is a track
            return 0
        return 1

    def match_name(self, item: MatchTypes, result: MatchTypes) -> float:
        """Match on names(/titles)"""
        score = sum(word in item.name for word in result.name) / len(item.name.split())
        self._log_test(item=item, result=result, test=score, extra=[f"{item.name} -> {result.name}"])
        return score

    def match_artist(self, item: MatchTypes, result: MatchTypes) -> float:
        """Match on artists"""
        artists_result = result.artist.split(self.list_sep)
        artists_item = result.artist.replace(self.list_sep, "")

        score = 0
        for i, artist in enumerate(artists_result, 1):
            score += (sum(word in artists_item for word in artist.split()) / len(artists_item.split())) * (1 / i)

        score = sum(word in artists_item for word in artists_result) / len(artists_item)
        self._log_test(item=item, result=result, test=score, extra=[f"{artists_item} -> {artists_result}"])
        return score

    def match_album(self, item: MatchTypes, result: MatchTypes) -> float:
        """Match on album"""
        score = sum(word in item.album for word in result.album) / len(item.album.split())
        self._log_test(item=item, result=result, test=score, extra=[f"{item.album} -> {result.album}"])
        return score

    def match_length(self, item: MatchTypes, result: MatchTypes) -> float:
        """Match on length"""
        score = (item.length - abs(item.length - result.length)) / item.length
        self._log_test(item=item, result=result, test=score, extra=[f"{item.length} -> {result.length}"])
        return score

    def match_year(self, item: MatchTypes, result: MatchTypes) -> float:
        """Match on length"""
        score = (item.year - abs(item.year - result.year)) / item.year
        self._log_test(item=item, result=result, test=score, extra=[f"{item.year} -> {result.year}"])
        return score

    ###########################################################################
    ## Algorithms
    ###########################################################################
    def score_match(
            self,
            item: MatchTypes,
            results: Iterable[MatchTypes],
            min_score: float = 1,
            max_score: float = 2,
            match_on: Optional[List[Literal["name", "artist", "album", "length", "year"]]] = None
    ) -> Optional[MatchTypes]:
        """
        Perform score match algorithm for a given item and its results.

        :param item: Source item to compare against and find a match for.
        :param results: Results for comparisons.
        :param min_score: Only return the result as a match if the score is above this value.
            Value will be limited to between 0.1 and 4.0.
        :param max_score: Stop matching once this score has been reached.
            Value will be limited to between 0.1 and 4.0.
        :param match_on: List of tags to match on.
        :return: dict. Metadata for locally stored track with added matched URI if found.
        """
        if not results:
            self._log_algorithm(item=item, extra=[f"NO RESULTS GIVEN, SKIPPING"])
            return

        item_clean = self.clean_tags(item)
        min_score = self._limit_value(min_score, floor=0.1, ceil=4)
        max_score = self._limit_value(max_score, floor=0.1, ceil=4)
        self._log_algorithm(item=item_clean, extra=[f"max_score={max_score}"])

        if not match_on:
            match_on = ["name", "artist", "album", "length", "year"]

        scores_highest = {}
        sum_highest = 0
        result = None

        for result in results:
            result_clean = self.clean_tags(result)
            scores_current = {}

            if "name" in match_on:
                scores_current["name"] = self.match_name(item=item_clean, result=result_clean)
            if "artist" in match_on:
                scores_current["artist"] = self.match_artist(item=item_clean, result=result_clean)
            if "album" in match_on and not isinstance(item, Album):
                scores_current["album"] = self.match_album(item=item_clean, result=result_clean)
            if "length" in match_on:
                scores_current["length"] = self.match_length(item=item_clean, result=result_clean)
            if "year" in match_on:
                scores_current["year"] = self.match_year(item=item_clean, result=result_clean)

            sum_current = sum(scores_current.values())
            log_current = ', '.join(f'{k}={round(v, 2)}' for k, v in scores_current.items()) + f": {sum_current}"
            sum_highest = sum(scores_highest.values())
            log_highest = ', '.join(f'{k}={round(v, 2)}' for k, v in scores_highest.items()) + f": {sum_highest}"
            self._log_test(item=item_clean, result=result_clean, test=log_current, extra=[f"highest={log_highest}"])

            if sum_current > sum_highest:
                scores_highest = scores_current.copy()
                if sum_highest >= max_score:  # max threshold reached, match found
                    break

        if sum_highest > min_score:
            self._log_match(item=item_clean, result=result)
            return result
        else:
            self._log_test(item=item_clean, result=result, test=sum_highest,
                           extra=[f"NO MATCH: {sum_highest}<{min_score}"])
