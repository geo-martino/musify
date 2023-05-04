from abc import ABCMeta
from typing import List, Optional

from syncify.local.files.track.base import Track
from syncify.local.files.track.collection import TrackLimit, TrackMatch, TrackSort
from utils_new.generic import PP


class TrackCollection(PP, TrackMatch, TrackSort, TrackLimit, metaclass=ABCMeta):
    """
    Generic class for a collection of tracks with functionality to
    match, limit, and sort a given collection of tracks.

    :param matcher: Initialised TrackMatch instance.
    :param limiter: Initialised TrackLimit instance.
    :param sorter: Initialised TrackSort instance.
    """

    def __init__(
            self,
            matcher: Optional[TrackMatch] = None,
            limiter: Optional[TrackLimit] = None,
            sorter: Optional[TrackSort] = None
    ):
        self.tracks: List[Track] = []

        TrackMatch.__init__(self)
        if matcher is not None:
            self.comparators = matcher.comparators
            self.match_all = matcher.match_all
            self.include_paths = matcher.include_paths
            self.exclude_paths = matcher.exclude_paths
            self.library_folder = matcher.library_folder
            self.original_folder = matcher.original_folder

        TrackLimit.__init__(self)
        if limiter is not None:
            self.limit_max = limiter.limit_max
            self.kind = limiter.kind
            self.allowance = limiter.allowance
            self.limit_sort = limiter.limit_sort

        TrackSort.__init__(self)
        if sorter is not None:
            self.sort_fields = sorter.sort_fields
