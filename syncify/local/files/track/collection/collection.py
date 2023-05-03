from abc import ABCMeta, abstractmethod
from typing import Any, List, Mapping, MutableMapping, Optional, Self

from local.files.track.collection.limit import TrackLimit
from local.files.track.collection.match import TrackMatch
from local.files.track.collection.sort import TrackSort
from syncify.local.files.track.track import Track


class TrackCollection(TrackMatch, TrackSort, TrackLimit, metaclass=ABCMeta):
    """
    Generic class for a collection of tracks with functionality to
    match, limit, and sort a given collection of tracks.

    :param matcher: Initialised TrackMatch instance.
    :param limiter: Initialised TrackLimit instance.
    :param sorter: Initialised TrackSort instance.
    """

    @property
    @abstractmethod
    def tracks(self) -> List[Track]:
        raise NotImplementedError

    @tracks.getter
    def tracks(self) -> List[Track]:
        return self._tracks

    @tracks.setter
    def tracks(self, value: List[Track]):
        self._tracks = value

    def __init__(
            self,
            matcher: Optional[TrackMatch] = None,
            limiter: Optional[TrackLimit] = None,
            sorter: Optional[TrackSort] = None
    ):
        self._tracks: List[Track] = None

        TrackMatch.__init__(self)
        self.comparators = matcher.comparators
        self.match_all = matcher.match_all
        self.include_paths = matcher.include_paths
        self.exclude_paths = matcher.exclude_paths
        self.library_folder = matcher.library_folder
        self.original_folder = matcher.original_folder

        TrackSort.__init__(self)
        self.sort_fields = sorter.sort_fields
        self.shuffle_mode = sorter.shuffle_mode

        TrackLimit.__init__(self)
        self.limit = limiter.limit
        self.kind = limiter.kind
        self.allowance = limiter.allowance
        self.limit_sort = limiter.limit_sort

    @classmethod
    def from_xml(cls, xml: Optional[Mapping[str, Any]] = None) -> Self:
        matcher = TrackMatch.from_xml(xml=xml)
        limiter = TrackLimit.from_xml(xml=xml)
        sorter = TrackSort.from_xml(xml=xml)
        return cls(matcher=matcher, sorter=sorter, limiter=limiter)

    @abstractmethod
    def as_dict(self) -> MutableMapping[str, object]:
        """Return a dictionary representation of this collection"""
        raise NotImplementedError

    @abstractmethod
    def as_json(self) -> MutableMapping[str, object]:
        """Return a dictionary representation of this collection that is safe to output to json"""
        raise NotImplementedError

    def __str__(self) -> str:
        result = f"{self.__class__.__name__}(\n{{}}\n)"
        attributes = self.as_dict()
        attributes["tracks"] = self.tracks
        indent = 2

        max_width = max(len(tag_name) for tag_name in attributes)
        attributes_repr = []
        for key, attribute in attributes.items():
            if isinstance(attribute, list) and len(attribute) > 0 and isinstance(attribute[0], Track):
                tracks_repr = f"[\n{{}}\n" + " " * indent + "]"
                tracks = [" " * indent * 2 + str(track).replace("\n", "\n" + " " * indent * 2) for track in attribute]
                attribute = tracks_repr.format(",\n".join(tracks))
                attributes_repr.append(f"{key.title() : <{max_width}} = {attribute}")
            else:
                attributes_repr.append(f"{key.title() : <{max_width}} = {repr(attribute)}")

        return result.format("\n".join([" " * indent + attribute for attribute in attributes_repr]))

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.as_dict()})"
