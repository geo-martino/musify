import inspect
import re
from typing import List, Optional, Union, Any, Iterable, TypeVar, Tuple, Collection

from syncify.abstract.collection import Album, ItemCollection
from syncify.abstract.item import Track, Base
from syncify.enums.tags import TagName, PropertyName
from syncify.utils import limit_value
from syncify.utils.logger import Logger

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

    def _log_test(self, source: Base, result: MatchTypes, test: Any, extra: Optional[List[str]] = None):
        """Wrapper for initially logging a test result in a correctly aligned format"""
        algorithm = inspect.stack()[1][0].f_code.co_name.replace("match", "").upper().lstrip("_").replace("_", " ")
        log_result = f"> Testing URI: {result.uri}" if hasattr(result, "uri") else "> Test failed"
        log = [source.name, log_result, f"{algorithm:<10}={test:<5}"]
        if extra:
            log += extra
        self._log_padded(log)

    def _log_match(self, source: Base, result: MatchTypes, extra: Optional[List[str]] = None):
        """Wrapper for initially logging a match in a correctly aligned format"""
        log = [source.name, f"< Matched URI: {result.uri}"]
        if extra:
            log += extra
        self._log_padded(log, pad='<')

    def __init__(self, allow_karaoke: bool = False):
        Logger.__init__(self)
        self.allow_karaoke = allow_karaoke

    @staticmethod
    def clean_tags(source: Base):
        """
        Clean tags on the input item and assign to its ``clean_tags`` attribute. Used for better matching/searching.
        Clean by removing redundant words, and only taking phrases before a certain word e.g. 'featuring', 'part'.

        :param source: The base object with tags to clean.
        """
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

        redundant_all = ["the", "a", "&", "and"]
        source.clean_tags = {"name": ""}
        name = source.name

        title = getattr(source, "title", None)
        source.clean_tags["title"] = ""
        if title:
            source.clean_tags["title"] = process(title, redundant=["part"], split=["featuring", "feat.", "ft.", "/"])
            if name == title:
                source.clean_tags["name"] = source.clean_tags["title"]

        artist = getattr(source, "artist", None)
        source.clean_tags["artist"] = ""
        if artist:
            source.clean_tags["artist"] = process(artist, split=["featuring", "feat.", "ft.", "vs"])
            if name == artist:
                source.clean_tags["name"] = source.clean_tags["artist"]

        album = getattr(source, "album", None)
        source.clean_tags["album"] = ""
        if album:
            source.clean_tags["album"] = process(album.split('-')[0], redundant=["ep"])
            if name == album:
                source.clean_tags["name"] = source.clean_tags["album"]

        source.clean_tags["length"] = getattr(source, "length", None)
        source.clean_tags["year"] = getattr(source, "year", None)

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
        if is_karaoke(result.album.lower()):  # album
            return 0
        return 1

    def match_name(self, source: Base, result: MatchTypes) -> float:
        """Match on names and return a score. Score=0 when either value is None."""
        score = 0
        source_val = source.clean_tags["name"]
        result_val = result.clean_tags["name"]

        if source_val and result_val:
            score = sum(word in result_val for word in source_val.split()) / len(source_val.split())

            # reduce a score if certain keywords are present in result and not source
            reduce_factor = 0.5
            reduce_on = ["live", "demo", "acoustic"] + self.karaoke_tags
            if any(word in result.name.lower() and word not in source.name.lower() for word in reduce_on):
                score = max(score - reduce_factor, 0)

        self._log_test(source=source, result=result, test=round(score, 2), extra=[f"{source_val} -> {result_val}"])
        return score

    # noinspection PyProtectedMember
    def match_artist(self, source: MatchTypes, result: MatchTypes) -> float:
        """
        Match on artists and return a score. Score=0 when either value is None.
        When many artists are present, a scale factor is applied to the score of matches on subsequent artists.
        i.e. match on artist 1 is scaled by 1, match on artist 2 is scaled by 1/2,
        match on artist 3 is scaled by 1/3 etc.
        """
        score = 0
        source_val = source.clean_tags["artist"]
        result_val = result.clean_tags["artist"]

        if not source_val or not result_val:
            self._log_test(source=source, result=result, test=score, extra=[f"{source_val} -> {result_val}"])
            return score

        artists_source = source_val.replace(Base._list_sep, " ")
        artists_result = result_val.split(Base._list_sep)

        for i, artist in enumerate(artists_result, 1):
            score += (sum(word in artists_source for word in artist.split()) / len(artists_source.split())) * (1 / i)
        self._log_test(source=source, result=result, test=round(score, 2), extra=[f"{source_val} -> {result_val}"])
        return score

    def match_album(self, source: MatchTypes, result: MatchTypes) -> float:
        """Match on album and return a score. Score=0 when either value is None."""
        score = 0
        source_val = source.clean_tags["album"]
        result_val = result.clean_tags["album"]

        if source_val and result_val:
            score = sum(word in result_val for word in source_val.split()) / len(source_val.split())

        self._log_test(source=source, result=result, test=round(score, 2), extra=[f"{source_val} -> {result_val}"])
        return score

    def match_length(self, source: MatchTypes, result: MatchTypes) -> float:
        """Match on length and return a score. Score=0 when either value is None."""
        score = 0
        source_val = source.clean_tags["length"]
        result_val = result.clean_tags["length"]

        if source_val and result_val:
            score = max((source_val - abs(source_val - result_val)), 0) / source_val

        self._log_test(source=source, result=result, test=round(score, 2),
                       extra=[f"{round(source_val, 2) if source_val else None} -> "
                              f"{round(result_val, 2) if result_val else None}"])
        return score

    def match_year(self, source: MatchTypes, result: MatchTypes) -> float:
        """
        Match on year and return a score. Score=0 when either value is None.
        Matches within 10 years on a 0-1 scale where 1 is the exact same year and 0 is 10+ year difference.
        User may modify this max range via the ``year_range`` class attribute.
        """
        score = 0
        source_val = source.clean_tags["year"]
        result_val = result.clean_tags["year"]

        if source_val and result_val:
            score = max((self.year_range - abs(source_val - result_val)), 0) / self.year_range

        self._log_test(source=source, result=result, test=round(score, 2), extra=[f"{source_val} -> {result_val}"])
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
        if not source.clean_tags:
            self.clean_tags(source)
        score, result = self._score(source=source, results=results, max_score=max_score, match_on=match_on)

        if score > min_score:
            extra = f"best score: {'%.2f' % round(score, 2)} > {'%.2f' % round(min_score, 2)}" if score < max_score \
                else f"max score reached: {'%.2f' % round(score, 2)} > {'%.2f' % round(max_score, 2)}"
            self._log_match(source=source, result=result, extra=[extra])
            return result
        else:
            self._log_test(source=source, result=result, test=score, extra=[f"NO MATCH: {score}<{min_score}"])

    def _score(
            self,
            source: MatchTypes,
            results: Iterable[MatchTypes],
            max_score: float = 0.8,
            match_on:  Collection[Union[TagName, PropertyName]] = frozenset([TagName.ALL, PropertyName.ALL])
    ) -> Tuple[float, Optional[MatchTypes]]:
        """
        Gets the score and result from a cleaned source and a given list of results.

        :param source: Source item to compare against and find a match for with assigned ``clean_tags``.
        :param results: Result items for comparisons.
        :param max_score: Stop matching once this score has been reached.
            Value will be limited to between 0.1 and 1.0.
        :param match_on: List of tags to match on. Currently only the following tags/properties are supported:
            track, artist, album, year, length.
        :return: dict. Metadata for locally stored track with added matched URI if found.
        """
        if not results:
            self._log_algorithm(source=source, extra=[f"NO RESULTS GIVEN, SKIPPING"])
            return 0, None
        max_score = limit_value(max_score, floor=0.1, ceil=1.0)
        self._log_algorithm(source=source, extra=[f"max_score={max_score}"])

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
            self.clean_tags(current_result)
            scores = self._get_scores(source=source, result=current_result, match_on=match_on)
            if not scores:
                continue

            current_score = sum(scores.values()) / len(scores)
            self._log_test(source=source, result=current_result,
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
            result: MatchTypes,
            match_on: Collection[Union[TagName, PropertyName]] = frozenset([TagName.ALL, PropertyName.ALL])
    ) -> dict[str, float]:
        """
        Gets the scores from a cleaned source and result to match on.
        When an ItemCollection is given to match on, scores are also given for the items in the collection.

        :param source: Source item to compare against and find a match for with assigned ``clean_tags``.
        :param result: Result item to compare against with assigned ``clean_tags``.
        :param match_on: List of tags to match on. Currently only the following tags/properties are supported:
            track, artist, album, year, length.
        :return: dict. Metadata for locally stored track with added matched URI if found.
        """
        if not self.allow_karaoke and self.match_not_karaoke(source, result) < 1:
            return {}

        scores_current: dict[str, float] = {}

        if TagName.TITLE in match_on:
            scores_current["title"] = self.match_name(source=source, result=result)
        if TagName.ARTIST in match_on:
            scores_current["artist"] = self.match_artist(source=source, result=result)
        if TagName.ALBUM in match_on:
            scores_current["album"] = self.match_album(source=source, result=result)
        if PropertyName.LENGTH in match_on:
            scores_current["length"] = self.match_length(source=source, result=result)
        if TagName.YEAR in match_on:
            scores_current["year"] = self.match_year(source=source, result=result)
        if isinstance(source, ItemCollection) and isinstance(result, ItemCollection):
            # skip this if not a collection of tracks
            if not all(isinstance(i, Track) for i in source.items):
                return scores_current
            if not all(isinstance(i, Track) for i in result.items):
                return scores_current

            # also score all the items individually in the collection
            scores_current["items"] = 0
            for item in source.items:
                self.clean_tags(item)
                score, _ = self._score(source=item, results=result.items, match_on=match_on)
                scores_current["items"] += score / len(source.items)

        return scores_current
