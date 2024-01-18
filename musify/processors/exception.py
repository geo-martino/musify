"""
Exceptions relating to processor operations.
"""

from musify.shared.exception import MusifyError


class ProcessorError(MusifyError):
    """Exception raised for errors related to processors."""


class ProcessorLookupError(ProcessorError):
    """Exception raised when processor name given is not valid."""


class ComparerError(ProcessorError):
    """Exception raised for errors related to :py:class:`Comparer` settings."""


class TimeMapperError(ProcessorError):
    """Exception raised for errors related to :py:class:`TimeMapper` logic."""


###########################################################################
## Filter errors
###########################################################################
class FilterError(ProcessorError):
    """Exception raised for errors related to :py:class:`Filter` logic."""


###########################################################################
## Item processor errors
###########################################################################
class ItemProcessorError(ProcessorError):
    """Exception raised for errors related to :py:class:`ItemProcessor` logic."""


class ItemLimiterError(ItemProcessorError):
    """Exception raised for errors related to :py:class:`ItemLimiter` logic."""


class ItemMatcherError(ItemProcessorError):
    """Exception raised for errors related to :py:class:`ItemMatcher` logic."""


class ItemSorterError(ItemProcessorError):
    """Exception raised for errors related to :py:class:`ItemSorter` logic."""
