from syncify.exception import SyncifyError


class ItemProcessorError(SyncifyError):
    """Exception raised for errors related to MusicBee logic."""


class ItemComparerError(ItemProcessorError):
    """Exception raised for errors related to MusicBee comparer settings."""


class ItemLimiterError(ItemProcessorError):
    """Exception raised for errors related to MusicBee limit settings."""


class ItemMatcherError(ItemProcessorError):
    """Exception raised for errors related to MusicBee comparer settings."""


class ItemSorterError(ItemProcessorError):
    """Exception raised for errors related to MusicBee comparer settings."""
