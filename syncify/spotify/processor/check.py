import traceback
from dataclasses import dataclass
from typing import List, Mapping, Optional

from syncify.abstract.collection import ItemCollection
from syncify.abstract.item import Item
from syncify.abstract.misc import Result
from syncify.local.track import TagName
from syncify.spotify import check_spotify_type, ItemType, IDType
from syncify.spotify.api import API
from syncify.spotify.library.library import SpotifyPlaylist
from syncify.spotify.processor.match import Matcher
from syncify.utils.helpers import get_user_input


@dataclass
class CheckResult(Result):
    """Stores the results of the checking process"""
    switched: List[Item]
    unavailable: List[Item]
    unchanged: List[Item]


class Checker(Matcher):
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

    :param api: An API object with authorised access to a Spotify User to create playlists for.
    :param allow_karaoke: When True, items determined to be karaoke are allowed when matching added items.
    """

    _default_name = "check"

    @property
    def exit(self) -> bool:
        return self._exit

    @exit.setter
    def exit(self, value: bool):
        self.done = value if value else self.done
        self._exit = value

    def __init__(self, api: API, allow_karaoke: bool = False):
        Matcher.__init__(self, allow_karaoke=allow_karaoke)

        self.api = api
        self.playlist_name_urls = {}
        self.playlist_name_collection = {}

        self.done = False  # when true, exit ItemChecker
        self.exit = False  # when true, exit Syncify

        self.remaining: List[Item] = []
        self.switched: List[Item] = []

        self.final_switched: List[Item] = []
        self.final_unavailable: List[Item] = []
        self.final_unchanged: List[Item] = []

    def _make_temp_playlist(self, name: str, collection: ItemCollection) -> None:
        """Create a temporary playlist, store its URL for later unfollowing, and add all given URIs."""
        try:
            url = self.api.create_playlist(name, public=False)
            uris = [item.uri for item in collection if item.has_uri]
            self.playlist_name_urls[name] = url
            self.playlist_name_collection[name] = collection

            self.api.add_to_playlist(url, items=uris, skip_dupes=False)
        except (KeyboardInterrupt, BaseException):
            self.logger.error(traceback.format_exc())
            self.exit = True

    def _get_user_input(self, text: Optional[str] = None) -> str:
        """Print dialog with optional text and get the user's input."""
        inp = get_user_input(text)
        self.logger.debug(f"User input: {inp}")
        return inp.strip()

    def _format_help_text(self, options: Mapping[str, str], header: Optional[List[str]] = None) -> str:
        """Format help text with a given mapping of options. Add an option header to include before options."""
        max_width = self.get_max_width(options, 50)

        help_text = header if header else []
        help_text.append("\n\t\33[96mEnter one of the following: \33[0m\n\t")
        help_text.extend(f"{self.truncate_align_str(k, max_width=max_width)}{': ' + v if v else ''}"
                         for k, v in options.items())

        return '\n\t'.join(help_text) + '\n'

    def check(self, collections: List[ItemCollection], interval: int = 10) -> Optional[CheckResult]:
        """
        Run the following operations to check a list of ItemCollections on Spotify.

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
        :return: A result object containing the remapped items created during the check.
        """
        if len(collections) == 0 or all(not collection.items for collection in collections):
            self.logger.debug("\33[93mNo items to check. \33[0m")
            return

        self.logger.debug('Checking items: START')
        self.logger.info(f"\33[1;95m ->\33[1;97m Checking items by creating temporary Spotify playlists "
                         f"for the current user: {self.api.user_name} \33[0m")

        bar = self.get_progress_bar(iterable=collections, desc="Creating temp playlists", unit="playlists")
        interval_total = (len(collections) // interval) + (len(collections) % interval > 0)
        self.done = False
        self.exit = False

        for i, collection in enumerate(bar):
            self._make_temp_playlist(name=collection.name, collection=collection)

            # skip loop if pause amount has not been reached and not finished making all playlists i.e. not last loop
            if len(self.playlist_name_urls) % interval != 0 and i + 1 != len(collections):
                continue

            try:
                self._check_pause(page=i, page_size=interval, page_total=interval_total)
                if not self.done:
                    self._check_uri()
            except (KeyboardInterrupt, ConnectionError):
                self.exit = True

            if not self.api.test():  # check if token has expired
                self.logger.info('\33[93mAPI token has expired, re-authorising... \33[0m')
                self.api.auth()

            self.logger.info(f'\33[93mDeleting {len(self.playlist_name_urls)} temporary playlists... \33[0m')
            for url in self.playlist_name_urls.values():  # delete playlists
                self.api.delete_playlist(url.removesuffix("tracks"))

            self.playlist_name_urls.clear()
            self.playlist_name_collection.clear()

            if self.exit:  # quit syncify
                exit("User terminated program or critical failure occurred.")
            elif self.done:
                bar.leave = False
                break

        result = CheckResult(
            switched=self.final_switched, unavailable=self.final_unavailable, unchanged=self.final_unchanged
        )
        self.print_line()
        self.logger.info(f"\33[1;96mCHECK TOTALS \33[0m| "
                         f"\33[94m{len(self.final_switched):>5} switched  \33[0m| "
                         f"\33[91m{len(self.final_unavailable):>5} unavailable \33[0m| "
                         f"\33[93m{len(self.final_unchanged):>5} unchanged \33[0m")

        self.done = True
        self.remaining.clear()
        self.switched.clear()
        self.final_switched = []
        self.final_unavailable = []
        self.final_unchanged = []

        self.logger.debug('Checking items: DONE\n')
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
            "Name of playlist": "Print position, item name, URI, and URL from given link "
                                "of items as originally added to temp playlist",
            "Spotify link/URI": "Print position, item name, URI, and URL from given link "
                                "(useful to check current status of playlist)",
            "s": "Delete current temporary playlists and skip remaining checks",
            "q": "Delete current temporary playlists and quit Syncify",
            "h": "Show this dialogue again",
        }

        current_input = "START"
        help_text = self._format_help_text(options=options)
        progress_text = f"{page // page_size}/{page_total}"

        print("\n" + help_text)
        while current_input != '':  # while user has not hit return only
            current_input = self._get_user_input(f"Enter ({progress_text})")
            pl_names = [name for name in self.playlist_name_collection
                        if name.casefold().startswith(current_input.casefold())]

            if current_input == "":  # user entered no option, break loop and return
                break
            elif pl_names:  # print originally added items
                name = pl_names[0]
                items = self.playlist_name_collection[name]

                print(f"\n\t\33[96mShowing items originally added to {name}:\33[0m\n")
                for i, item in enumerate(items, 1):
                    print(self.api.format_item_data(i=i, name=item.name, uri=item.uri, total=len(items)))
                print()
            elif current_input.casefold() == 's' or current_input.casefold() == 'q':  # quit/skip
                self.exit = current_input.casefold() == 'q'
                self.done = True
                break
            elif current_input.casefold() == "h":  # print help text
                print(help_text)
            elif check_spotify_type(current_input) is not None:  # print URL/URI/ID result
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
        for name, collection in self.playlist_name_collection.items():
            name: str = self._default_name if isinstance(collection, list) else collection.name
            items: List[Item] = collection if isinstance(collection, list) else collection.items
            self._log_padded([name, f"{len(items):>6} total items"], pad='>')

            while True:
                self._match_to_remote(name=name)
                self._match_to_input(name=name)
                if not self.remaining:
                    break

            unavailable = [item for item in collection if item.has_uri is False]
            unchanged = [item for item in collection if item.has_uri is None]
            updated = len(self.switched) + len(unavailable)

            self._log_padded([name, f"{len(self.switched):>4} items switched"])
            self._log_padded([name, f"{len(unavailable):>4} items unavailable"])
            self._log_padded([name, f"{len(unchanged):>4} items unchanged"])
            self._log_padded([name, f"{updated:>4} items updated"], pad='<')

            self.final_switched += self.switched
            self.final_unavailable += unavailable
            self.final_unchanged += unchanged
            self.switched.clear()

    def _match_to_remote(self, name: str) -> None:
        """
        Check the current temporary playlist given by ``name`` and attempt to match the source list of items
        to any modifications the user has made.
        """
        self.logger.info(f'\33[1;95m ->\33[1;97m '
                         f'Attempting to find URIs for items in Spotify playlist: \33[94m{name}\33[0m...')

        source = self.playlist_name_collection[name]
        remote = SpotifyPlaylist(self.api.get_collections(self.playlist_name_urls[name], use_cache=False)[0]).tracks

        added = [item for item in remote if item not in source and item.has_uri]
        removed = [item for item in source if item not in remote and item.has_uri]
        missing = [item for item in source if not item.has_uri]

        if len(added) + len(removed) + len(missing) == 0:
            self._log_padded([name, f"Playlist unchanged and no missing URIs, skipping match"], pad=' ')
            return

        self._log_padded([name, f"{len(added):>6} items added"], pad=' ')
        self._log_padded([name, f"{len(removed):>6} items removed"], pad=' ')
        self._log_padded([name, f"{len(missing):>6} items in source missing URI"], pad=' ')

        remaining = removed + missing
        count_start = len(remaining)
        for item in remaining:
            if not added:
                break

            result = self.score_match(item, results=added, match_on=[TagName.TITLE], max_score=0.8)
            if not result:
                continue

            item.uri = result.uri
            item.has_uri = result.has_uri

            added.remove(result)
            removed.remove(item) if item in removed else missing.remove(item)
            self.switched.append(result)

        self.remaining = removed + missing
        count_final = len(self.remaining)
        self._log_padded([name, f"{count_start - count_final:>4} items switched"])
        self._log_padded([name, f"{count_final:>4} items still not found"])

    def _match_to_input(self, name: str):
        """Get the user's input for any items in the collection given by ``name`` that are still missing URIs."""
        if not self.remaining:
            return

        header = ["\t\33[1;94m{name}:\33[91m The following items were removed and/or matches were not found. \33[0m"]
        options = {
            "u": "Mark item as 'Unavailable on Spotify'",
            "n": "Leave item with no URI. (Syncify will still attempt to find this item at the next run)",
            "a": "Add in addition to 'u' or 'n' options to apply this setting to all items in this playlist",
            "r": "Recheck playlist for all items in the album",
            "s": "Skip checking process for all playlists",
            "q": "Skip checking process, delete current temporary playlists, and quit Syncify",
            "h": "Show this dialogue again",
        }

        current_input = ""
        help_text = self._format_help_text(options=options, header=header).format(name=name)
        help_text += "OR enter a custom URI/URL/ID for this item\n"

        self._log_padded([name, f"Getting user input for {len(self.remaining)} items"])
        max_width = self.get_max_width([item.name for item in self.remaining], max_width=50)

        print("\n" + help_text)
        for item in self.remaining.copy():
            while item in self.remaining:  # while item not matched or skipped
                self._log_padded([name, f"{len(self.remaining)} remaining items"])
                if 'a' not in current_input:
                    current_input = self._get_user_input(self.truncate_align_str(item.name, max_width=max_width))

                if current_input.casefold().replace('a', '') == 'u':  # mark item as unavailable
                    self._log_padded([name, "Marking as unavailable"], pad="<")
                    item.uri = None
                    item.has_uri = False
                    self.remaining.remove(item)
                elif current_input.casefold().replace('a', '') == 'n':  # leave item without URI and unprocessed
                    self._log_padded([name, "Skipping"], pad="<")
                    item.uri = None
                    item.has_uri = None
                    self.remaining.remove(item)
                elif current_input.casefold() == 'r':  # return to former 'while' loop
                    self._log_padded([name, "Refreshing playlist metadata and restarting loop"])
                    return
                elif current_input.casefold() == 's' or current_input.casefold() == 'q':  # quit/skip
                    self._log_padded([name, "Skipping all loops"], pad="<")
                    self.exit = current_input.casefold() == 'q'
                    self.done = True
                    self.remaining.clear()
                    return
                elif current_input.casefold() == 'h':  # print help
                    print("\n" + help_text)
                elif check_spotify_type(current_input) is not None:  # update URI and add item to switched list
                    uri = self.api.convert(current_input, kind=ItemType.TRACK, type_out=IDType.URI)

                    self._log_padded([name, f"Updating URI: {item.uri} -> {uri}"], pad="<")
                    item.uri = uri
                    item.has_uri = uri

                    self.switched.append(item)
                    self.remaining.remove(item)
                    current_input = ""
                else:  # invalid input
                    current_input = ""

            if not self.remaining:
                break
