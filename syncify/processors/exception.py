from syncify.exception import SyncifyError


class ProcessorError(SyncifyError):
    """Exception raised for errors related to processors."""


class ProcessorLookupError(ProcessorError):
    """Exception raised when processor name given is not valid."""


class TimeMapperError(ProcessorError):
    """Exception raised for errors related to TimeMapper."""


###########################################################################
## Item processor errors
###########################################################################
class ItemProcessorError(ProcessorError):
    """Exception raised for errors related to ItemProcessor logic."""


class ItemComparerError(ItemProcessorError):
    """Exception raised for errors related to item comparer settings."""


class ItemLimiterError(ItemProcessorError):
    """Exception raised for errors related to item limit settings."""


class ItemMatcherError(ItemProcessorError):
    """Exception raised for errors related to item matcher settings."""


class ItemSorterError(ItemProcessorError):
    """Exception raised for errors related to item sorter settings."""
