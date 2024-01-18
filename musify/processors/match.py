"""
Processor that matches objects and data types based on given configuration.
"""

import inspect
import logging
import re
from collections.abc import Iterable, Callable, MutableSequence
from dataclasses import dataclass, field
from typing import Any

from musify.processors.base import ItemProcessor
from musify.shared.core.base import Nameable, NameableTaggableMixin, Taggable
from musify.shared.core.collection import ItemCollection
from musify.shared.core.enum import TagField, TagFields as Tag, ALL_TAG_FIELDS
from musify.shared.core.misc import PrettyPrinter
from musify.shared.core.object import Track, Album
from musify.shared.logger import MusifyLogger
from musify.shared.types import UnitIterable
from musify.shared.utils import limit_value, to_collection


@dataclass
class CleanTagConfig(PrettyPrinter):
    """Config for processing string-type tag values before matching with :py:class:`ItemMatcher`"""
    #: The name of the tag to clean.
    tag: TagField
    #: A set of string values to remove from this tag.
    remove: set[str] = field(default_factory=lambda: set())
    #: A set of string values for which the cleaner will slice the tag on and remove anything that comes after.
    split: set[str] = field(default_factory=lambda: set())
    #: A function to apply before the remove and split values are applied.
    preprocess: Callable[[str], str] = field(default=lambda x: x)

    def as_dict(self) -> dict[str, Any]:
        return {
            "tag": self.tag.name.lower(),
            "remove": [value for value in self.remove],
            "split": [value for value in self.split],
            "preprocess": self.preprocess is not None,
        }


class ItemMatcher(ItemProcessor):
    """Matches source items/collections to given result(s)."""

    __slots__ = ("logger",)

    #: A set of words to search for in tag values that identify the item as being a karaoke item.
    karaoke_tags = {"karaoke", "backing", "instrumental"}
    #: A difference in years of this value gives a score of 0 for the :py:meth:`match_year` algorithm.
    #: See the :py:meth:`match_year` method for more information.
    year_range = 10

    # config for cleaning string-type tags for matching
    #: Apply these remove settings to all tags when processing tags as per :py:meth:`clean_tags` method.
    #: See also :py:class:`CleanTagConfig` for more info on this configuration.
    clean_tags_remove_all = {"the", "a", "&", "and"}
    #: Apply these split settings to all tags when processing tags as per :py:meth:`clean_tags` method.
    #: See also :py:class:`CleanTagConfig` for more info on this configuration.
    clean_tags_split_all = set()
    #: A list of configurations in the form of :py:class:`CleanTagConfig`
    #: to apply for each tag type. See also :py:class:`CleanTagConfig` for more info.
    clean_tags_config = (
        CleanTagConfig(tag=Tag.TITLE, remove={"part"}, split={"featuring", "feat.", "ft.", "/"}),
        CleanTagConfig(tag=Tag.ARTIST, split={"featuring", "feat.", "ft.", "vs"}),
        CleanTagConfig(tag=Tag.ALBUM, remove={"ep"}, preprocess=lambda x: x.split('-')[0])
    )

    # config for name score reduction
    #: A set of words to check for when applying name score reduction logic.
    #:
    #: If a word from this list is present in the name of the result to score against
    #: but not in the source :py:class:`Item`, apply the ``reduce_name_score_factor`` to reduce its score.
    #: This set is always combined with the ``karaoke_tags``.
    reduce_name_score_on = {"live", "demo", "acoustic"}
    #: The factor to apply to a name score when a word from ``reduce_name_score_on``
    #: is found in the result but not in the source :py:class:`Item`.
    reduce_name_score_factor = 0.5

    def __init__(self):
        super().__init__()

        # noinspection PyTypeChecker
        #: The :py:class:`MusifyLogger` for this  object
        self.logger: MusifyLogger = logging.getLogger(__name__)

    def _log_padded(self, log: MutableSequence[str], pad: str = ' ') -> None:
        """Wrapper for logging lists in a correctly aligned format"""
        log[0] = pad * 3 + ' ' + (log[0] if log[0] else "unknown")
        self.logger.debug(" | ".join(log))

    def _log_algorithm(self, source: Nameable, extra: Iterable[str] = ()) -> None:
        """Wrapper for initially logging an algorithm in a correctly aligned format"""
        algorithm = inspect.stack()[1][0].f_code.co_name.upper().lstrip("_").replace("_", " ")
        log = [source.name, algorithm]
        if extra:
            log.extend(extra)
        self._log_padded(log, pad='>')

    def _log_test[T: (Track, Album)](
            self, source: Nameable, result: T, test: Any, extra: Iterable[str] = ()
    ) -> None:
        """Wrapper for initially logging a test result in a correctly aligned format"""
        algorithm = inspect.stack()[1][0].f_code.co_name.replace("match", "").upper().lstrip("_").replace("_", " ")
        log_result = f"> Testing URI: {result.uri}" if hasattr(result, "uri") else "> Test failed"
        log = [source.name, log_result, f"{algorithm:<10}={test:<5}"]
        if extra:
            log.extend(extra)
        self._log_padded(log)

    def _log_match[T: (Track, Album)](self, source: Nameable, result: T, extra: Iterable[str] = ()) -> None:
        """Wrapper for initially logging a match in a correctly aligned format"""
        log = [source.name, f"< Matched URI: {result.uri}"]
        if extra:
            log.extend(extra)
        self._log_padded(log, pad='<')

    def clean_tags(self, source: NameableTaggableMixin) -> None:
        """
        Clean tags on the input item and assign to its ``clean_tags`` attribute. Used for better matching/searching.
        Clean by removing words, and only taking phrases before a certain word e.g. 'featuring', 'part'.
        Cleaning config for string-type tags is set in ``_clean_tags_config``.

        :param source: The base object with tags to clean.
        """
        def process(val: str, conf: CleanTagConfig) -> str:
            """Apply transformations to the given ``val`` to clean it"""
            val = conf.preprocess(val)
            val = re.sub(r"[(\[].*?[)\]]", "", val).casefold()

            for word in conf.remove | self.clean_tags_remove_all:
                val = re.sub(rf"\s{word}\s|^{word}\s|\s{word}$", " ", val)

            for word in conf.split | self.clean_tags_split_all:
                val = val.split(word)[0].rstrip()

            return re.sub(r"[^\w']+", ' ', val).strip()

        source.clean_tags.clear()
        source.clean_tags[Tag.NAME] = ""
        name = source.name

        # process string tags according to config
        for config in self.clean_tags_config:
            tag_name = config.tag.to_tag().pop()
            value = getattr(source, tag_name, None)
            if not value:
                source.clean_tags[config.tag] = ""
                continue

            value_cleaned = process(value, conf=config)
            source.clean_tags[config.tag] = value_cleaned
            if name == value:
                source.clean_tags[Tag.NAME] = value_cleaned

        source.clean_tags[Tag.LENGTH] = getattr(source, Tag.LENGTH.name.lower(), None)
        source.clean_tags[Tag.YEAR] = getattr(source, Tag.YEAR.name.lower(), None)

    ###########################################################################
    ## Conditions
    ###########################################################################
    def match_not_karaoke[T: (Track, Album)](self, source: T, result: T) -> int:
        """Checks if a result is not a karaoke item that is either 0 when item is karaoke or 1 when not karaoke."""
        def is_karaoke(*values: str) -> bool:
            """Check if the words in the given ``values`` match any word in ``karaoke_tags``"""
            values = {v for value in values for v in value.casefold().split()}
            karaoke = any(word.casefold() in values for word in self.karaoke_tags)
            self._log_test(source=source, result=result, test=karaoke, extra=[f"{self.karaoke_tags} -> {values}"])
            return karaoke

        if is_karaoke(result.name):  # title/album name
            return 0
        if is_karaoke(result.artist):  # artists
            return 0
        if is_karaoke(result.album):  # album
            return 0
        return 1

    def match_name[T: (Track, Album)](self, source: T, result: T) -> float:
        """Match on names and return a score between 0-1. Score=0 when either value is None."""
        score = 0
        source_val = source.clean_tags[Tag.NAME]
        result_val = result.clean_tags[Tag.NAME]

        if source_val and result_val:
            score = sum(word in result_val for word in source_val.split()) / len(source_val.split())

            # reduce a score if certain keywords are present in result and not source
            reduce_on = self.reduce_name_score_on | self.karaoke_tags
            reduce_on = {word.casefold() for word in reduce_on}
            if any(word in result.name.casefold() and word not in source.name.casefold() for word in reduce_on):
                score = max(score * self.reduce_name_score_factor, 0)

        self._log_test(source=source, result=result, test=round(score, 2), extra=[f"{source_val} -> {result_val}"])
        return score

    def match_artist[T: (Track, Album)](self, source: T, result: T) -> float:
        """
        Match on artists and return a score between 0-1. Score=0 when either value is None.
        When many artists are present, a scale factor is applied to the score of matches on subsequent artists.
        i.e. match on artist 1 is scaled by 1, match on artist 2 is scaled by 1/2,
        match on artist 3 is scaled by 1/3 etc.
        """
        score = 0
        source_val = source.clean_tags[Tag.ARTIST]
        result_val = result.clean_tags[Tag.ARTIST]

        if not source_val or not result_val:
            self._log_test(source=source, result=result, test=score, extra=[f"{source_val} -> {result_val}"])
            return score

        artists_source = source_val.replace(Taggable.tag_sep, " ")
        artists_result = result_val.split(Taggable.tag_sep)

        for i, artist in enumerate(artists_result, 1):
            score += (sum(word in artists_source for word in artist.split()) / len(artists_source.split())) * (1 / i)
        self._log_test(source=source, result=result, test=round(score, 2), extra=[f"{source_val} -> {result_val}"])
        return score

    def match_album[T: (Track, Album)](self, source: T, result: T) -> float:
        """Match on album and return a score between 0-1. Score=0 when either value is None."""
        score = 0
        source_val = source.clean_tags[Tag.ALBUM]
        result_val = result.clean_tags[Tag.ALBUM]

        if source_val and result_val:
            score = sum(word in result_val for word in source_val.split()) / len(source_val.split())

        self._log_test(source=source, result=result, test=round(score, 2), extra=[f"{source_val} -> {result_val}"])
        return score

    def match_length[T: (Track, Album)](self, source: T, result: T) -> float:
        """Match on length and return a score between 0-1. Score=0 when either value is None."""
        score = 0
        source_val = source.clean_tags[Tag.LENGTH]
        result_val = result.clean_tags[Tag.LENGTH]

        if source_val and result_val:
            score = max((source_val - abs(source_val - result_val)), 0) / source_val

        extra = [f"{round(source_val, 2) if source_val else None} -> {round(result_val, 2) if result_val else None}"]
        self._log_test(source=source, result=result, test=round(score, 2), extra=extra)
        return score

    def match_year[T: (Track, Album)](self, source: T, result: T) -> float:
        """
        Match on year and return a score between 0-1. Score=0 when either value is None.
        Matches within ``year_range`` years on a 0-1 scale where 1 is the exact same year
        and 0 is a difference in year greater that ``year_range``.
        User may modify this max range via the ``year_range`` class attribute.
        """
        score = 0
        source_val = source.clean_tags[Tag.YEAR]
        result_val = result.clean_tags[Tag.YEAR]

        if source_val and result_val:
            score = max((self.year_range - abs(source_val - result_val)), 0) / self.year_range

        self._log_test(source=source, result=result, test=round(score, 2), extra=[f"{source_val} -> {result_val}"])
        return score

    ###########################################################################
    ## Score match
    ###########################################################################
    def __call__[T: (Track, Album)](
            self,
            source: T,
            results: Iterable[T],
            min_score: float = 0.1,
            max_score: float = 0.8,
            match_on: UnitIterable[TagField] = ALL_TAG_FIELDS,
            allow_karaoke: bool = False,
    ) -> T | None:
        return self.match(
            source=source,
            results=results,
            min_score=min_score,
            max_score=max_score,
            match_on=match_on,
            allow_karaoke=allow_karaoke
        )

    def match[T: (Track, Album)](
            self,
            source: T,
            results: Iterable[T],
            min_score: float = 0.1,
            max_score: float = 0.8,
            match_on: UnitIterable[TagField] = ALL_TAG_FIELDS,
            allow_karaoke: bool = False,
    ) -> T | None:
        """
        Perform match algorithm for a given item and its results.

        :param source: Source item to compare against and find a match for.
        :param results: Results for comparisons.
        :param min_score: Only return the result as a match if the score is above this value.
            Value will be limited to between 0.01 and 1.0.
        :param max_score: Stop matching once this score has been reached.
            Value will be limited to between 0.01 and 1.0.
        :param match_on: List of tags to match on. Currently only the following fields are supported:
            ``title``, ``artist``, ``album``, ``year``, ``length``.
        :param allow_karaoke: When True, items determined to be karaoke are allowed when matching added items.
            Skip karaoke results otherwise. Karaoke items are identified using the ``karaoke_tags`` attribute.
        :return: T. The item that matched best if found, None if no item matched conditions.
        """
        if not source.clean_tags:
            self.clean_tags(source)

        # process and limit match options
        match_on_filtered = set()
        for match_field in to_collection(match_on, set):
            if match_field == Tag.ALL:
                match_on_filtered.update(match_field.all())
            else:
                match_on_filtered.add(match_field)

        score, result = self._score(
            source=source, results=results, max_score=max_score, match_on=match_on_filtered, allow_karaoke=allow_karaoke
        )

        min_score = limit_value(min_score, floor=0.01, ceil=1.0)
        if score > min_score:
            extra = [
                f"best score: {'%.2f' % round(score, 2)} > {'%.2f' % round(min_score, 2)}"
                if score < max_score else
                f"max score reached: {'%.2f' % round(score, 2)} > {'%.2f' % round(max_score, 2)}"
            ]
            self._log_match(source=source, result=result, extra=extra)
            return result
        else:
            self._log_test(source=source, result=result, test=score, extra=[f"NO MATCH: {score}<{min_score}"])

    def _score[T: (Track, Album)](
            self,
            source: T,
            results: Iterable[T],
            max_score: float = 0.8,
            match_on: set[TagField] = ALL_TAG_FIELDS,
            allow_karaoke: bool = False,
    ) -> tuple[float, T | None]:
        """
        Gets the score and result from a cleaned source and a given list of results.

        :param source: Source item to compare against and find a match for with assigned ``clean_tags``.
        :param results: Result items for comparisons.
        :param max_score: Stop matching once this score has been reached.
            Value will be limited to between 0.01 and 1.0.
        :param match_on: List of tags to match on. Currently only the following fields are supported:
            ``title``, ``artist``, ``album``, ``year``, ``length``.
        :param allow_karaoke: When True, items determined to be karaoke are allowed when matching added items.
            Skip karaoke results otherwise. Karaoke items are identified using the ``karaoke_tags`` attribute.
        :return: Tuple of (the score between 0-1, the item that had the best score)
        """
        if not results:
            self._log_algorithm(source=source, extra=["NO RESULTS GIVEN, SKIPPING"])
            return 0, None
        max_score = limit_value(max_score, floor=0.01, ceil=1.0)
        self._log_algorithm(source=source, extra=[f"max_score={max_score}"])

        best_score = 0
        best_result = None

        for current_result in results:
            self.clean_tags(current_result)
            scores = self._get_scores(
                source=source, result=current_result, match_on=match_on, allow_karaoke=allow_karaoke
            )
            if not scores:
                continue

            current_score = sum(scores.values()) / len(scores)
            log_extra = [f"BEST={round(best_score, 2)}"]
            self._log_test(source=source, result=current_result, test=round(current_score, 2), extra=log_extra)

            if current_score > best_score:
                best_result = current_result
                best_score = sum(scores.values()) / len(scores)
            if best_score >= max_score:  # max threshold reached, match found
                break

        return best_score, best_result

    def _get_scores[T: (Track, Album)](
            self, source: T, result: T, match_on: set[TagField] = ALL_TAG_FIELDS, allow_karaoke: bool = False
    ) -> dict[TagField, float]:
        """
        Gets the scores from a cleaned source and result to match on.
        When an ItemCollection is given to match on, scores are also calculated for each of the items in the collection.
        Scores are always between 0-1.

        :param source: Source item to compare against and find a match for with assigned ``clean_tags``.
        :param result: Result item to compare against with assigned ``clean_tags``.
        :param match_on: List of tags to match on. Currently only the following fields are supported:
            ``title``, ``artist``, ``album``, ``year``, ``length``.
        :param allow_karaoke: When True, items determined to be karaoke are allowed when matching added items.
            Skip karaoke results otherwise. Karaoke items are identified using the ``karaoke_tags`` attribute.
        :return: Map of score type name to score.
        """
        if not allow_karaoke and self.match_not_karaoke(source, result) < 1:
            return {}

        scores_current: dict[TagField, float] = {}

        if Tag.TITLE in match_on:
            scores_current[Tag.TITLE] = self.match_name(source=source, result=result)
        if Tag.ARTIST in match_on:
            scores_current[Tag.ARTIST] = self.match_artist(source=source, result=result)
        if Tag.ALBUM in match_on:
            scores_current[Tag.ALBUM] = self.match_album(source=source, result=result)
        if Tag.LENGTH in match_on:
            scores_current[Tag.LENGTH] = self.match_length(source=source, result=result)
        if Tag.YEAR in match_on:
            scores_current[Tag.YEAR] = self.match_year(source=source, result=result)

        if isinstance(source, ItemCollection) and isinstance(result, ItemCollection):
            # skip this if not a collection of items
            if not all(isinstance(i, Track) for i in source.items):
                return scores_current
            if not all(isinstance(i, Track) for i in result.items):
                return scores_current

            # also score all the items individually in the collection
            scores_current[Tag.ALL] = 0
            for item in source.items:
                self.clean_tags(item)
                score, _ = self._score(source=item, results=result.items, match_on=match_on)
                scores_current[Tag.ALL] += score / len(source.items)

        return scores_current

    def as_dict(self) -> dict[str, Any]:
        return {
            "clean_tags": {
                "remove_all": self.clean_tags_remove_all,
                "split_all": self.clean_tags_split_all,
                "config": self.clean_tags_config,
            },
            "karaoke_tags": self.karaoke_tags,
            "year_range": self.year_range,
        }
