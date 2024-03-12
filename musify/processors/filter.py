"""
Processors that filter down objects and data types based on some given configuration.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence, Mapping
from typing import Any, Self

from musify.processors.base import Filter, FilterComposite
from musify.processors.compare import Comparer
from musify.shared.core.base import Nameable


class FilterDefinedList[T: str | Nameable](Filter[T], Collection[T]):

    __slots__ = ("values",)

    @property
    def ready(self):
        return len(self.values) > 0

    def __init__(self, values: Collection[T] = (), *_, **__):
        super().__init__()
        #: The values to include when processing for this filter
        self.values: Collection[T] = values

    def __call__(self, values: Collection[T] | None = None, *_, **__) -> Collection[T]:
        return self.process(values=values)

    def process(self, values: Collection[T] | None = None, *_, **__) -> Collection[T]:
        """Returns all ``values`` that match this filter's settings"""
        if self.ready:
            matches = [value for value in values if self.transform(value) in self.values]
            if isinstance(self.values, Sequence):
                matches = sorted((self.values.index(self.transform(match)), match) for match in matches)
                return [match[1] for match in matches]
            return matches
        return values

    def as_dict(self) -> dict[str, Any]:
        return {"values": self.values}

    def __iter__(self):
        return iter(self.values)

    def __len__(self):
        return len(self.values)

    def __contains__(self, item: Any):
        return item in self.values


class FilterComparers[T: str | Nameable](Filter[T]):

    __slots__ = ("comparers", "match_all")

    @property
    def ready(self):
        return len(self.comparers) > 0

    def __init__(
            self,
            comparers: Collection[Comparer] | Mapping[Comparer, tuple[bool, Self]] = (),
            match_all: bool = True,
            *_,
            **__
    ):
        super().__init__()
        if not isinstance(comparers, Mapping):
            comparers = {comparer: (False, FilterComparers()) for comparer in comparers}

        #: The comparers to use when processing for this filter
        #: When a mapping with other :py:class:`FilterComparers` is given,
        #: will apply this sub-filter to all parent filters when processing
        self.comparers: Mapping[Comparer, tuple[bool, Self]] = comparers
        #: When true, only include those items that match on all comparers
        self.match_all: bool = match_all

    def __call__(self, values: Collection[T], reference: T | None = None, *_, **__) -> Collection[T]:
        return self.process(values=values, reference=reference)

    def process(self, values: Collection[T], reference: T | None = None, *_, **__) -> Collection[T]:
        if not self.ready:
            return values

        def run_comparer(c: Comparer, v: T) -> bool:
            """Run the comparer ``c`` for the given value ``v``"""
            return c(self.transform(v), reference=reference) if c.expected is None else c(self.transform(v))

        def run_sub_filter(s: FilterComparers, c: bool, v: list[T]) -> Collection[T]:
            """Run the sub_filter ``s`` for the given value ``v`` and return the results"""
            if not s.ready:
                return v
            elif c:
                return sub_filter(v, reference=reference)
            else:
                v.extend([value for value in sub_filter(values, reference=reference) if value not in v])
                return v

        if self.match_all:
            for comparer, (combine, sub_filter) in self.comparers.items():
                matched = [value for value in values if run_comparer(comparer, value)]
                values = run_sub_filter(sub_filter, combine, matched)
            return values

        matches = []
        for comparer, (combine, sub_filter) in self.comparers.items():
            matched = [value for value in values if value not in matches and run_comparer(comparer, value)]
            matched = run_sub_filter(sub_filter, combine, matched)
            matches.extend([value for value in matched if value not in matches])

        return matches

    def as_dict(self) -> dict[str, Any]:
        return {"comparers": self.comparers, "match_all": self.match_all}


###########################################################################
## Composites
###########################################################################
class FilterIncludeExclude[T: Any, U: Filter, V: Filter](FilterComposite[T]):

    __slots__ = ("include", "exclude")

    def __init__(self, include: U, exclude: V, *_, **__):
        super().__init__(include, exclude)
        #: The filter that, when processed, returns items to include
        self.include: U = include
        #: The filter that, when processed, returns items to exclude
        self.exclude: V = exclude

    def __call__(self, values: Collection[T], *_, **__) -> list[T]:
        return self.process(values=values)

    def process(self, values: Collection[T], *_, **__) -> list[T]:
        """Filter down ``values`` that match this filter's settings from"""
        values = self.include.process(values) if self.include.ready else values
        exclude = self.exclude.process(values) if self.exclude.ready else ()
        return [v for v in values if v not in exclude]

    def as_dict(self) -> dict[str, Any]:
        return {"include": self.include, "exclude": self.exclude}
