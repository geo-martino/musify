import inspect
import re
from copy import copy
from typing import List, Optional, Union, Any, Iterable, TypeVar, Tuple, Collection

from syncify.abstract.item import Track, Base
from syncify.abstract.collection import Album, ItemCollection
from syncify.enums.tags import TagName, PropertyName
from syncify.utils import Logger

MatchTypes = Union[Track, Album]
T = TypeVar("T")


class Matcher(Logger):
    """
    Matches source items/collections to given result(s).

    :param allow_karaoke: Allow karaoke results to be matched, skip karaoke results otherwise.
    """

    karaoke_tags = ['karaoke', 'backing', 'instrumental']
    year_range = 10

    def _log_padded(self, log: List[str], pad: str = ' '):
        """Wrapper for logging lists in a correctly aligned format"""
        log[0] = pad * 3 + ' ' + (log[0] if log[0] else "unknown")
        self.logger.debug(" | ".join(log))

    def _log_algorithm(self, source: Base, extra: Optional[List[str]] = None):
        """Wrapper for initially logging an algorithm in a correctly aligned format"""
        algorithm = inspect.stack()[1][0].f_code.co_name.upper().lstrip("_").replace("_", " ")
        log = [source.name, algorithm]
        if extra:
            log += extra
        self._log_padded(log, pad='>')

    def _log_test(self, source: Base, result: MatchTypes, test: Any, extra: Optional[List[str]] = None) -> None:
        """Wrapper for initially logging a test result in a correctly aligned format"""
        algorithm = inspect.stack()[1][0].f_code.co_name.replace("match", "").upper().lstrip("_").replace("_", " ")
        log_result = f"> Testing URI: {result.uri}" if hasattr(result, "uri") else "> Test failed"
        log = [source.name, log_result, f"{algorithm:<10}={test:<5}"]
        if extra:
            log += extra
        self._log_padded(log, pad=' ')

    def _log_match(self, source: Base, result: MatchTypes, extra: Optional[List[str]] = None) -> None:
        """Wrapper for initially logging a match in a correctly aligned format"""
        log = [source.name, f"< Matched URI: {result.uri}"]
        if extra:
            log += extra
        self._log_padded(log, pad='<')

    def __init__(self, allow_karaoke: bool = False):
        Logger.__init__(self)
        self.allow_karaoke = allow_karaoke

    @staticmethod
    def clean_tags(source: T) -> T:
        """
        Clean tags on a copy of the input item and return the copy. Used for better matching/searching.
        Clean by removing redundant words, and only taking phrases before a certain word e.g. 'featuring', 'part'.

        :param source: The item with tags to clean.
        :return: A copy of the original item with cleaned tags.
        """
        redundant_all = ["the", "a", "&", "and"]
        item_copy = copy(source)

        def process(value: str, redundant: Optional[List[str]] = None, split: Optional[List[str]] = None) -> str:
            value = re.sub(r"[(\[].*?[)\]]", "", value).casefold()
            for word in redundant_all:
                value = re.sub(rf"\s{word}\s|^{word}\s|\s{word}$", " ", value)

            if redundant:
                for word in redundant:
                    value = re.sub(rf"\s{word}\s|^{word}\s|\s{word}$", " ", value)
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
    def match_not_karaoke(self, source: MatchTypes, result: MatchTypes) -> int:
        """Checks if a result is not a karaoke item."""
        def is_karaoke(values: Union[str, List[str]]):
            karaoke = any(word in values for word in self.karaoke_tags)
            self._log_test(source=source, result=result, test=karaoke, extra=[f"{self.karaoke_tags} -> {values}"])
            return karaoke

        if is_karaoke(result.name.lower()):  # title/album name
            return 0
        if is_karaoke(result.artist.lower()):  # artists
            return 0
        if isinstance(result, Track) and is_karaoke(result.album.lower()):  # album when the result is a track
            return 0
        return 1

    def match_name(self, source: Base, result: MatchTypes) -> float:
        """Match on names and return a score. Score=0 when either value is None."""
        score = 0
        if source.name and result.name:
            score = sum(word in result.name for word in source.name.split()) / len(source.name.split())

            # reduce a score if certain keywords are present in result and not source
            reduce_factor = 0.5
            reduce_on = ["live", "demo"] + self.karaoke_tags
            if any(word in result.name and word not in source.name for word in reduce_on):
                score = max(score - reduce_factor, 0)

        self._log_test(source=source, result=result, test=round(score, 2),
                       extra=[f"{source.name} -> {result.name}"])
        return score

    def match_artist(self, source: MatchTypes, result: MatchTypes) -> float:
        """
        Match on artists and return a score. Score=0 when either value is None.
        When many artists are present, a scale factor is applied to the score of matches on subsequent artists.
        i.e. match on artist 1 is scaled by 1, match on artist 2 is scaled by 1/2,
        match on artist 3 is scaled by 1/3 etc.
        """
        score = 0
        if not source.artist or not result.artist:
            self._log_test(source=source, result=result, test=score,
                           extra=[f"{source.artist} -> {result.artist}"])
            return score

        artists_source = source.artist.replace(Base.list_sep, " ")
        artists_result = result.artist.split(Base.list_sep)

        for i, artist in enumerate(artists_result, 1):
            score += (sum(word in artists_source for word in artist.split()) /
                      len(artists_source.split())) * (1 / i)
        self._log_test(source=source, result=result, test=round(score, 2),
                       extra=[f"{source.artist} -> {result.artist}"])
        return score

    def match_album(self, source: MatchTypes, result: MatchTypes) -> float:
        """Match on album and return a score. Score=0 when either value is None."""
        score = 0
        if source.album and result.album:
            score = sum(word in result.album for word in source.album.split()) / len(source.album.split())

        self._log_test(source=source, result=result, test=round(score, 2),
                       extra=[f"{source.album} -> {result.album}"])
        return score

    def match_length(self, source: MatchTypes, result: MatchTypes) -> float:
        """Match on length and return a score. Score=0 when either value is None."""
        score = 0
        if source.length and result.length:
            score = max((source.length - abs(source.length - result.length)), 0) / source.length

        self._log_test(source=source, result=result, test=round(score, 2),
                       extra=[f"{round(source.length, 2) if source.length else None} -> "
                              f"{round(result.length, 2) if result.length else None}"])
        return score

    def match_year(self, source: MatchTypes, result: MatchTypes) -> float:
        """
        Match on year and return a score. Score=0 when either value is None.
        Matches within 10 years on a 0-1 scale where 1 is the exact same year and 0 is 10+ year difference.
        User may modify this max range via the ``year_range`` class attribute.
        """
        score = 0
        if source.year and result.year:
            score = max((self.year_range - abs(source.year - result.year)), 0) / self.year_range

        self._log_test(source=source, result=result, test=round(score, 2),
                       extra=[f"{source.year} -> {result.year}"])
        return score

    ###########################################################################
    ## Algorithms
    ###########################################################################
    def score_match(
            self,
            source: MatchTypes,
            results: Iterable[MatchTypes],
            min_score: float = 0.1,
            max_score: float = 0.8,
            match_on: Collection[Union[TagName, PropertyName]] = frozenset([TagName.ALL, PropertyName.ALL])
    ) -> Optional[MatchTypes]:
        """
        Perform score match algorithm for a given item and its results.

        :param source: Source item to compare against and find a match for.
        :param results: Results for comparisons.
        :param min_score: Only return the result as a match if the score is above this value.
            Value will be limited to between 0.1 and 1.0.
        :param max_score: Stop matching once this score has been reached.
            Value will be limited to between 0.1 and 1.0.
        :param match_on: List of tags to match on. Currently only the following tags/properties are supported:
            track, artist, album, year, length.
        :return: dict. Metadata for locally stored track with added matched URI if found.
        """
        source_clean = self.clean_tags(source)
        score, result = self._score(source=source, source_clean=source_clean, results=results,
                                    max_score=max_score, match_on=match_on)

        if score > min_score:
            extra = f"best score: {'%.2f' % round(score, 2)} > {'%.2f' % round(min_score, 2)}" if score < max_score \
                else f"max score reached: {'%.2f' % round(score, 2)} > {'%.2f' % round(max_score, 2)}"
            self._log_match(source=source_clean, result=result, extra=[extra])
            return result
        else:
            self._log_test(source=source_clean, result=result, test=score, extra=[f"NO MATCH: {score}<{min_score}"])

    def _score(
            self,
            source: MatchTypes,
            source_clean: MatchTypes,
            results: Iterable[MatchTypes],
            max_score: float = 0.8,
            match_on:  Collection[Union[TagName, PropertyName]] = frozenset([TagName.ALL, PropertyName.ALL])
    ) -> Tuple[float, Optional[MatchTypes]]:
        """
        Gets the score and result from a cleaned source and a given list of results.

        :param source: Source item to compare against and find a match for.
        :param source_clean: Cleaned source item to compare against and find a match for.
        :param results: Results for comparisons.
        :param max_score: Stop matching once this score has been reached.
            Value will be limited to between 0.1 and 1.0.
        :param match_on: List of tags to match on. Currently only the following tags/properties are supported:
            track, artist, album, year, length.
        :return: dict. Metadata for locally stored track with added matched URI if found.
        """
        if not results:
            self._log_algorithm(source=source_clean, extra=[f"NO RESULTS GIVEN, SKIPPING"])
            return 0, None
        max_score = self.limit_value(max_score, floor=0.1, ceil=1.0)
        self._log_algorithm(source=source_clean, extra=[f"max_score={max_score}"])

        # process and limit match options
        match_on = set(match_on)
        if TagName.ALL in match_on:
            match_on.remove(TagName.ALL)
            match_on |= TagName.all()
        if PropertyName.ALL in match_on:
            match_on.remove(PropertyName.ALL)
            match_on |= PropertyName.all()

        best_score = 0
        best_result = None

        for current_result in results:
            result_clean = self.clean_tags(current_result)
            scores = self._get_scores(source=source, source_clean=source_clean,
                                      result=current_result, result_clean=result_clean, match_on=match_on)
            if not scores:
                continue

            current_score = sum(scores.values()) / len(scores)
            self._log_test(source=source_clean, result=result_clean,
                           test=round(current_score, 2), extra=[f"BEST={round(best_score, 2)}"])

            if current_score > best_score:
                best_result = current_result
                best_score = sum(scores.values()) / len(scores)
            if best_score >= max_score:  # max threshold reached, match found
                break

        return best_score, best_result

    def _get_scores(
            self,
            source: MatchTypes,
            source_clean: MatchTypes,
            result: MatchTypes,
            result_clean: MatchTypes,
            match_on: Collection[Union[TagName, PropertyName]] = frozenset([TagName.ALL, PropertyName.ALL])
    ) -> dict[str, float]:
        """
        Gets the scores from a cleaned source and result to match on.
        When an ItemCollection is given to match on, scores are also given for the items in the collection.

        :param source: Source item to compare against and find a match for.
        :param source_clean: Cleaned source item to compare against and find a match for.
        :param result: Result to compare against.
        :param result_clean: Cleaned result to compare against.
        :param match_on: List of tags to match on. Currently only the following tags/properties are supported:
            track, artist, album, year, length.
        :return: dict. Metadata for locally stored track with added matched URI if found.
        """
        if not self.allow_karaoke and self.match_not_karaoke(source_clean, result) < 1:
            return {}

        scores_current: dict[str, float] = {}

        if TagName.TITLE in match_on:
            scores_current["title"] = self.match_name(source=source_clean, result=result_clean)
        if TagName.ARTIST in match_on:
            scores_current["artist"] = self.match_artist(source=source_clean, result=result_clean)
        if TagName.ALBUM in match_on:
            scores_current["album"] = self.match_album(source=source_clean, result=result_clean)
        if PropertyName.LENGTH in match_on:
            scores_current["length"] = self.match_length(source=source_clean, result=result_clean)
        if TagName.YEAR in match_on:
            scores_current["year"] = self.match_year(source=source_clean, result=result_clean)
        if isinstance(source_clean, ItemCollection) and isinstance(result_clean, ItemCollection):
            # skip this if not a collection of tracks
            if not all(isinstance(i, Track) for i in source_clean.items):
                return scores_current
            if not all(isinstance(i, Track) for i in result_clean.items):
                return scores_current

            # also score all the items individually in the collection
            result_items = result_clean.items
            scores_current["items"] = 0
            for i in source_clean.items:
                item_clean = self.clean_tags(i)
                score, _ = self._score(source=source, source_clean=item_clean, results=result_items, match_on=match_on)
                scores_current["items"] += score / len(source_clean.items)

        return scores_current
