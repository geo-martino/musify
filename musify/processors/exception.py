from musify.shared.exception import MusifyError


class ProcessorError(MusifyError):
    """Exception raised for errors related to processors."""


class ProcessorLookupError(ProcessorError):
    """Exception raised when processor name given is not valid."""


class ComparerError(ProcessorError):
    """Exception raised for errors related to comparer settings."""


class TimeMapperError(ProcessorError):
    """Exception raised for errors related to TimeMapper."""


###########################################################################
## Filter errors
###########################################################################
class FilterError(ProcessorError):
    """Exception raised for errors related to comparer settings."""


###########################################################################
## Item processor errors
###########################################################################
class ItemProcessorError(ProcessorError):
    """Exception raised for errors related to ItemProcessor logic."""


class ItemLimiterError(ItemProcessorError):
    """Exception raised for errors related to item limit settings."""


class ItemMatcherError(ItemProcessorError):
    """Exception raised for errors related to item matcher settings."""


class ItemSorterError(ItemProcessorError):
    """Exception raised for errors related to item sorter settings."""
