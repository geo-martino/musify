import traceback
from abc import ABCMeta, abstractmethod
from collections import Counter
from collections.abc import Mapping, Sequence, MutableSequence, Collection
from dataclasses import dataclass, field

from syncify import PROGRAM_NAME
from syncify.abstract.collection import ItemCollection
from syncify.abstract.fields import FieldCombined
from syncify.abstract.item import Item, Track
from syncify.abstract.misc import Result
from syncify.processors.match import ItemMatcher
from syncify.remote.api.api import RemoteAPI
from syncify.remote.enums import RemoteItemType, RemoteIDType
from syncify.remote.processors.wrangle import RemoteDataWrangler
from syncify.remote.types import RemoteObjectClasses
from syncify.utils.helpers import get_user_input
from syncify.utils.logger import REPORT


@dataclass(frozen=True)
class ItemCheckResult(Result):
    """
    Stores the results of the checking proces

    :ivar switched: Sequence of Items that had URIs switched during the check.
    :ivar unavailable: Sequence of Items that were marked as unavailable.
    :ivar unchanged: Sequence of Items that were unchanged from the check.
    """
    switched: Sequence[Item] = field(default=tuple())
    unavailable: Sequence[Item] = field(default=tuple())
    unchanged: Sequence[Item] = field(default=tuple())


class RemoteItemChecker(RemoteDataWrangler, ItemMatcher, metaclass=ABCMeta):
    """
    Runs operations for checking the URIs associated with a collection of items.
    When running :py:func:`check`, the object will do the following:

    * Make temporary playlists for each collection up to a ``interval`` limit of playlists.
        At which point, playlist creation pauses.
    * User can then check and modify the temporary playlists to match items to correct items or otherwise.
    * When operations resume at the user's behest, the program will search each playlist to find changes and
        attempt to match any new items to a source item.
    * If no matches are found for certain items, the program will prompt the user
        to determine how they wish to deal with these items.
    * Operation completes once user exists or all items have an associated URI.

    :param api: An API object with authorised access to a remote User to create playlists for.
    :param allow_karaoke: When True, items determined to be karaoke are allowed when matching added items.
        Skip karaoke results otherwise.
    """

    _default_name = "check"

    @property
    @abstractmethod
    def _remote_types(self) -> RemoteObjectClasses:
        raise NotImplementedError

    def __init__(self, api: RemoteAPI, allow_karaoke: bool = False):
        ItemMatcher.__init__(self, allow_karaoke=allow_karaoke)

        self.api = api
        self.playlist_name_urls = {}
        self.playlist_name_collection = {}

        self.skip = False  # when true, skip the current loop
        self.quit = False  # when true, quit ItemChecker

        self.remaining: list[Track] = []
        self.switched: list[Track] = []

        self.final_switched: list[Track] = []
        self.final_unavailable: list[Track] = []
        self.final_unchanged: list[Track] = []

    def _make_temp_playlist(self, name: str, collection: ItemCollection) -> None:
        """Create a temporary playlist, store its URL for later unfollowing, and add all given URIs."""
        try:
            uris = [item.uri for item in collection if item.has_uri]
            if not uris:
                return

            url = self.api.create_playlist(name, public=False)
            self.playlist_name_urls[name] = url
            self.playlist_name_collection[name] = collection

            self.api.add_to_playlist(url, items=uris, skip_dupes=False)
        except KeyboardInterrupt:
            self.quit = True
        except BaseException:  # TODO: too broad an exception clause
            self.logger.error(traceback.format_exc())
            self.quit = True

    def _get_user_input(self, text: str | None = None) -> str:
        """Print dialog with optional text and get the user's input."""
        inp = get_user_input(text)
        self.logger.debug(f"User input: {inp}")
        return inp.strip()

    def _format_help_text(self, options: Mapping[str, str], header: MutableSequence[str] | None = None) -> str:
        """Format help text with a given mapping of options. Add an option header to include before options."""
        max_width = self.get_max_width(options)

        help_text = header if header else []
        help_text.append("\n\t\33[96mEnter one of the following: \33[0m\n\t")
        help_text.extend(
            f"{self.align_and_truncate(k, max_width=max_width)}{': ' + v if v else ''}" for k, v in options.items()
        )

        return "\n\t".join(help_text) + '\n'

    def _delete_temp_playlists(self) -> None:
        """Delete all temporary playlists stored and clear stored playlists and collections"""
        if not self.api.test():  # check if token has expired
            self.logger.info_extra("\33[93mAPI token has expired, re-authorising... \33[0m")
            self.api.auth()

        self.logger.info_extra(f"\33[93mDeleting {len(self.playlist_name_urls)} temporary playlists... \33[0m")
        for url in self.playlist_name_urls.values():  # delete playlists
            self.api.delete_playlist(url.removesuffix("tracks"))

        self.playlist_name_urls.clear()
        self.playlist_name_collection.clear()

    def check(self, collections: Collection[ItemCollection], interval: int = 10) -> ItemCheckResult | None:
        """
        Run the following operations to check a list of ItemCollections on the remote application.

        * Make temporary playlists for each collection up to a ``interval`` limit of playlists.
            At which point, playlist creation pauses.
        * User can then check and modify the temporary playlists to match items to correct items or otherwise.
        * When operations resume at the user's behest, the program will search each playlist to find changes and
            attempt to match any new items to a source item.
        * If no matches are found for certain items, the program will prompt the user
            to determine how they wish to deal with these items.
        * Operation completes once user exists or all items have an associated URI.

        :param collections: A list of collections to check.
        :param interval: Stop creating playlists after this many playlists have been created and pause for user input.
        :return: A :py:class:`ItemCheckResult` object containing the remapped items created during the check.
            Return None when the user opted to quit (not skip) the checker before completion.
        """
        if len(collections) == 0 or all(not collection.items for collection in collections):
            self.logger.debug("\33[93mNo items to check. \33[0m")
            return

        self.logger.debug("Checking items: START")
        self.logger.info(
            f"\33[1;95m ->\33[1;97m Checking items by creating temporary {self.remote_source} playlists "
            f"for the current user: {self.api.user_name} \33[0m"
        )

        bar = self.get_progress_bar(iterable=collections, desc="Creating temp playlists", unit="playlists")
        interval_total = (len(collections) // interval) + (len(collections) % interval > 0)
        self.skip = False
        self.quit = False

        for i, collection in enumerate(bar):
            self._make_temp_playlist(name=collection.name, collection=collection)
            if self.quit:  # quit check
                self._delete_temp_playlists()
                break

            # skip loop if pause amount has not been reached and not finished making all playlists i.e. not last loop
            if len(self.playlist_name_urls) % interval != 0 and i + 1 != len(collections):
                continue

            try:
                self._check_pause(page=i, page_size=interval, page_total=interval_total)
                if not self.quit:
                    self._check_uri()
            except (KeyboardInterrupt, ConnectionError):
                self.quit = True

            self._delete_temp_playlists()
            if self.quit or self.skip:  # quit check
                if i + 1 != len(collections):
                    bar.leave = False
                break

        result = self._finalise() if not self.quit else None
        self.logger.debug("Checking items: DONE\n")
        return result

    def _finalise(self) -> ItemCheckResult:
        """Log results and prepare the :py:class:`ItemCheckResult` object"""
        self.print_line()
        self.logger.report(
            f"\33[1;96mCHECK TOTALS \33[0m| "
            f"\33[94m{len(self.final_switched):>5} switched  \33[0m| "
            f"\33[91m{len(self.final_unavailable):>5} unavailable \33[0m| "
            f"\33[93m{len(self.final_unchanged):>5} unchanged \33[0m"
        )
        self.print_line(REPORT)

        result = ItemCheckResult(
            switched=self.final_switched, unavailable=self.final_unavailable, unchanged=self.final_unchanged
        )

        self.skip = True
        self.remaining.clear()
        self.switched.clear()
        self.final_switched = []
        self.final_unavailable = []
        self.final_unchanged = []

        return result

    ###########################################################################
    ## Pause to check items in current temp playlists
    ###########################################################################
    def _check_pause(self, page: int, page_size: int, page_total: int) -> None:
        """
        Initial pause after the ``interval`` limit of playlists have been created.

        :param page: The current number of stops that have happened so far.
        :param page_size: The number of created playlists needed for each pause to be triggered.
        :param page_total: The total number of pauses that will occur in this run.
        """
        options = {
            "Return": "Once all playlist's items are checked, continue on and check for any switches by the user",
            "Name of playlist":
                "Print position, item name, URI, and URL from given link of items as originally added to temp playlist",
            f"{self.remote_source} link/URI":
                "Print position, item name, URI, and URL from given link (useful to check current status of playlist)",
            "s": "Check for changes on current playlists, but skip any remaining checks",
            "q": "Delete current temporary playlists and quit check",
            "h": "Show this dialogue again",
        }

        current_input = "START"
        help_text = self._format_help_text(options=options)
        progress_text = f"{(page // page_size) + 1}/{page_total}"

        print("\n" + help_text)
        while current_input != '':  # while user has not hit return only
            current_input = self._get_user_input(f"Enter ({progress_text})")
            pl_names = [name for name in self.playlist_name_collection if current_input.casefold() in name.casefold()]

            if current_input == "":  # user entered no option, break loop and return
                break
            elif current_input.casefold() == 's' or current_input.casefold() == 'q':  # quit/skip
                self.quit = current_input.casefold() == 'q' or self.quit
                self.skip = current_input.casefold() == 's' or self.skip
                break
            elif current_input.casefold() == "h":  # print help text
                print(help_text)
            elif pl_names:  # print originally added items
                name = pl_names[0]
                items = [item for item in self.playlist_name_collection[name] if item.has_uri]
                max_width = self.get_max_width(items)

                print(f"\n\t\33[96mShowing items originally added to \33[94m{name}\33[0m:\n")
                for i, item in enumerate(items, 1):
                    length = getattr(item, "length", 0)
                    formatted_item_data = self.api.format_item_data(
                        i=i, name=item.name, uri=item.uri, length=length, total=len(items), max_width=max_width
                    )
                    print(formatted_item_data)
                print()
            elif self.validate_id_type(current_input):  # print URL/URI/ID result
                if not self.api.test():
                    self.api.auth()
                self.api.pretty_print_uris(current_input)

            else:
                self.logger.warning("Input not recognised.")

    ###########################################################################
    ## Match items user has added or removed
    ###########################################################################
    def _check_uri(self) -> None:
        """Run operations to check that URIs are assigned to all the items in the current list of collections."""
        skip_hold = self.quit or self.skip
        self.skip = False
        for name, collection in self.playlist_name_collection.items():
            if not self.api.test():  # check if token has expired
                self.logger.info_extra("\33[93mAPI token has expired, re-authorising... \33[0m")
                self.api.auth()

            name: str = collection.name if isinstance(collection, ItemCollection) else self._default_name
            items: list[Item] = collection.items if isinstance(collection, ItemCollection) else collection
            self._log_padded([name, f"{len(items):>6} total items"], pad='>')

            while True:
                self._match_to_remote(name=name)
                self._match_to_input(name=name)
                if not self.remaining:
                    break

            unavailable = tuple(item for item in collection if item.has_uri is False)
            unchanged = tuple(item for item in collection if item.has_uri is None)

            self._log_padded([name, f"{len(unavailable):>6} items unavailable"])
            self._log_padded([name, f"{len(unchanged):>6} items unchanged"])
            self._log_padded([name, f"{len(self.switched):>6} items switched"], pad='<')

            self.final_switched += self.switched
            self.final_unavailable += unavailable
            self.final_unchanged += unchanged
            self.switched.clear()

            if self.quit or self.skip:
                break

        self.skip = skip_hold

    def _match_to_remote(self, name: str) -> None:
        """
        Check the current temporary playlist given by ``name`` and attempt to match the source list of items
        to any modifications the user has made.
        """
        self.logger.info(
            "\33[1;95m ->\33[1;97m Checking for changes to items in "
            f"{self.remote_source} playlist: \33[94m{name}\33[0m..."
        )

        pl_processor = self._remote_types.playlist

        source = self.playlist_name_collection[name]
        remote = pl_processor(self.api.get_collections(self.playlist_name_urls[name], use_cache=False)[0]).tracks
        source_valid = [item for item in source if item.has_uri]
        remote_valid = [item for item in remote if item.has_uri]

        added = [item for item in remote_valid if item not in source]
        removed = [item for item in source_valid if item not in remote]
        missing = [item for item in source if item.has_uri is None]

        if len(added) + len(removed) + len(missing) == 0:
            if len(source_valid) == len(remote_valid):
                self._log_padded([name, f"Playlist unchanged and no missing URIs, skipping match"])
                return

            # if item collection originally contained duplicate URIS and one or more of the duplicates were removed,
            # find missing items by looking for changes in counts
            remote_counts = Counter(item.uri for item in remote_valid)
            for uri, count in Counter(item.uri for item in source_valid).items():
                if remote_counts.get(uri) != count:
                    missing.extend([item for item in source_valid if item.uri == uri])

        self._log_padded([name, f"{len(added):>6} items added"])
        self._log_padded([name, f"{len(removed):>6} items removed"])
        self._log_padded([name, f"{len(missing):>6} items in source missing URI"])
        self._log_padded([name, f"{len(source_valid) - len(remote_valid):>6} total difference"])

        remaining = removed + missing
        count_start = len(remaining)
        for item in remaining:
            if not added:
                break

            result = self.score_match(item, results=added, match_on=[FieldCombined.TITLE])
            if not result:
                continue

            item.uri = result.uri

            added.remove(result)
            removed.remove(item) if item in removed else missing.remove(item)
            self.switched.append(result)

        self.remaining = removed + missing
        count_final = len(self.remaining)
        self._log_padded([name, f"{count_start - count_final:>6} items switched"])
        self._log_padded([name, f"{count_final:>6} items still not found"])

    def _match_to_input(self, name: str) -> None:
        """Get the user's input for any items in the collection given by ``name`` that are still missing URIs."""
        if not self.remaining:
            return

        header = ["\t\33[1;94m{name}:\33[91m The following items were removed and/or matches were not found. \33[0m"]
        options = {
            "u": f"Mark item as 'Unavailable on {self.remote_source}'",
            "n": f"Leave item with no URI. ({PROGRAM_NAME} will still attempt to find this item at the next run)",
            "a": "Add in addition to 'u' or 'n' options to apply this setting to all items in this playlist",
            "r": "Recheck playlist for all items in the album",
            "p": "Print the local path of the current item if available",
            "s": "Skip checking process for all current playlists",
            "q": "Skip checking process for all current playlists and quit check",
            "h": "Show this dialogue again",
        }

        current_input = ""
        help_text = self._format_help_text(options=options, header=header).format(name=name)
        help_text += "OR enter a custom URI/URL/ID for this item\n"

        self._log_padded([name, f"Getting user input for {len(self.remaining)} items"])
        max_width = self.get_max_width({item.name for item in self.remaining})

        print("\n" + help_text)
        for item in self.remaining.copy():
            while item in self.remaining:  # while item not matched or skipped
                self._log_padded([name, f"{len(self.remaining):>6} remaining items"])
                if 'a' not in current_input:
                    current_input = self._get_user_input(self.align_and_truncate(item.name, max_width=max_width))

                if current_input.casefold().replace('a', '') == 'u':  # mark item as unavailable
                    self._log_padded([name, "Marking as unavailable"], pad="<")
                    item.uri = self.unavailable_uri_dummy
                    self.remaining.remove(item)
                elif current_input.casefold().replace('a', '') == 'n':  # leave item without URI and unprocessed
                    self._log_padded([name, "Skipping"], pad="<")
                    item.uri = None
                    self.remaining.remove(item)
                elif current_input.casefold() == 'r':  # return to former 'while' loop
                    self._log_padded([name, "Refreshing playlist metadata and restarting loop"])
                    return
                elif current_input.casefold() == 's' or current_input.casefold() == 'q':  # quit/skip
                    self._log_padded([name, "Skipping all loops"], pad="<")
                    self.quit = current_input.casefold() == 'q' or self.quit
                    self.skip = current_input.casefold() == 's' or self.skip
                    self.remaining.clear()
                    return
                elif current_input.casefold() == 'h':  # print help
                    print("\n" + help_text)
                elif current_input.casefold() == 'p' and hasattr(item, "path"):  # print item path
                    print(f"\33[96m{item.path}\33[0m")
                elif self.validate_id_type(current_input):  # update URI and add item to switched list
                    uri = self.convert(current_input, kind=RemoteItemType.TRACK, type_out=RemoteIDType.URI)

                    self._log_padded([name, f"Updating URI: {item.uri} -> {uri}"], pad="<")
                    item.uri = uri

                    self.switched.append(item)
                    self.remaining.remove(item)
                    current_input = ""
                else:  # invalid input
                    current_input = ""

            if not self.remaining:
                break
