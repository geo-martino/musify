"""
Processor operations that help a user to:
    * Check whether the currently matched ID is valid for given items.
      Provides the user the ability to modify associated IDs using a Remote player as an interface for
      reviewing matches through temporary playlist creation.
    * Search for and match given items with remote items.
      Searches for matches on remote APIs, matches the item to the best matching result from the query,
      and assigns the ID of the matched object back to the item.
"""

from musify.shared.remote.config import RemoteObjectClasses
from musify.shared.remote.processors.check import RemoteItemChecker
from musify.shared.remote.processors.search import RemoteItemSearcher
from musify.spotify.config import SPOTIFY_OBJECT_CLASSES
from musify.spotify.processors.wrangle import SpotifyDataWrangler


class SpotifyItemChecker(SpotifyDataWrangler, RemoteItemChecker):
    """
    Runs operations for checking the URIs associated with a collection of items.

    When running :py:func:`check`, the object will do the following:
        * Make temporary playlists for each collection up to a ``interval`` limit of playlists.
          At which point, playlist creation pauses.
        * User can then check and modify the temporary playlists to match items to correct items or otherwise.
        * When operations resume at the user's behest, the program will search each playlist to find changes
          and attempt to match any new items to a source item.
        * If no matches are found for certain items, the program will prompt the user
          to determine how they wish to deal with these items.
        * Operation completes once user exists or all items have an associated URI.
    """

    @property
    def _object_cls(self) -> RemoteObjectClasses:
        return SPOTIFY_OBJECT_CLASSES


class SpotifyItemSearcher(SpotifyDataWrangler, RemoteItemSearcher):
    """Searches for remote matches for a list of item collections."""

    @property
    def _object_cls(self) -> RemoteObjectClasses:
        return SPOTIFY_OBJECT_CLASSES
