import traceback
from dataclasses import dataclass
from typing import List, Mapping, Optional

from syncify.abstract.item import Item
from syncify.abstract.collection import ItemCollection
from syncify.spotify import check_spotify_type, ItemType, IDType
from syncify.spotify.api import API
from syncify.spotify.library.library import SpotifyPlaylist
from syncify.spotify.processor.match import ItemMatcher
from syncify.utils.logger import Logger


@dataclass
class CheckResult:
    switched: List[Item]
    unavailable: List[Item]
    unchanged: List[Item]


class ItemChecker(ItemMatcher):

    _default_name = "check"

    @property
    def exit(self) -> bool:
        return self._exit

    @exit.setter
    def exit(self, value: bool):
        self.done = value if value else self.done
        self._exit = value

    def __init__(self, api: API):
        Logger.__init__(self)

        self.api = api
        self.playlist_name_urls = {}
        self.playlist_name_collection = {}

        self.done = False
        self.exit = False

        self.remaining: List[Item] = []
        self.switched: List[Item] = []

        self.final_switched: List[Item] = []
        self.final_unavailable: List[Item] = []
        self.final_unchanged: List[Item] = []

    def _log_padded(self, log: List[str], pad: str = ' '):
        log[0] = pad * 3 + ' ' + log[0]
        self._logger.debug(" | ".join(log))

    def _make_temp_playlist(self, name: str, collection: ItemCollection) -> None:
        """Create a temporary playlist, store its URL for later unfollowing, and add all given URIs."""
        try:
            url = f'{self.api.create_playlist(name, public=False)}/tracks'
            uris = [item.uri for item in collection if item.has_uri]
            self.playlist_name_urls[name] = url
            self.playlist_name_collection[name] = collection

            self.api.add_to_playlist(url, items=uris, skip_dupes=False)
        except (KeyboardInterrupt, BaseException):
            self._logger.error(traceback.format_exc())
            self.exit = True

    def _get_user_input(self, text: Optional[str] = None) -> str:
        """Print dialog with optional text and get the user's input."""
        inp = input(f"\33[93m{text}\33[0m | ")
        self._logger.debug(f"User input: {inp}")
        return inp.strip()

    def _help_text_formatter(self, options: Mapping[str, str], header: Optional[List[str]] = None) -> str:
        max_width = self._get_max_width(options, 50)

        help_text = header if header else []
        help_text.append("\n\t\33[96mEnter one of the following: \33[0m\n\t")
        help_text.extend(f"{self._truncate_align_str(k, max_width=max_width)}{': ' + v if v else ''}"
                         for k, v in options.items())

        return '\n\t'.join(help_text) + '\n'

    def check_items(self, collections: List[ItemCollection], interval: int = 10) -> CheckResult:
        self._logger.debug('Checking items: START')

        self._logger.info(f"\33[1;95m ->\33[1;97m Checking items by creating temporary Spotify playlists "
                          f"for the current user: {self.api.user_name} \33[0m")

        bar = self._get_progress_bar(total=len(collections), desc="Creating temp playlists", unit="playlists")
        interval_total = (len(collections) // interval) + (len(collections) % interval > 0)
        self.done = False
        self.exit = False

        for i in bar:
            collection: ItemCollection = collections[i]
            self._make_temp_playlist(name=collection.name, collection=collection)

            # skip loop if pause amount has not been reached and not finished making all playlists i.e. not last loop
            if len(self.playlist_name_urls) % interval != 0 and i != len(collections) - 1:
                continue

            try:
                self._check_pause(page=i, page_size=interval, page_total=interval_total)
                if not self.done:
                    self._check_uri()
            except (KeyboardInterrupt, ConnectionError):
                self.exit = True

            if not self.api.test():  # check if token has expired
                self._logger.info('\33[93mAPI token has expired, re-authorising... \33[0m')
                self.api.auth()

            self._logger.info(f'\33[93mDeleting {len(self.playlist_name_urls)} temporary playlists... \33[0m')
            for url in self.playlist_name_urls.values():  # delete playlists
                self.api.delete_playlist(url.replace("tracks", "followers"))
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

        self.done = True
        self.remaining.clear()
        self.switched.clear()
        self.final_switched = []
        self.final_unavailable = []
        self.final_unchanged = []

        self._logger.debug('Checking items: DONE\n')
        return result

    ###########################################################################
    ## Pause to check tracks in current temp playlists
    ###########################################################################
    def _check_pause(self, page: int, page_size: int, page_total: int) -> None:
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
        help_text = self._help_text_formatter(options=options)
        progress_text = f"{page // page_size}/{page_total}"

        print(help_text)
        while current_input != '':  # while user has not hit return only
            current_input = self._get_user_input(f"Enter ({progress_text})")
            pl_names = [name for name in self.playlist_name_collection
                        if name.lower().startswith(current_input.lower())]

            if current_input == "":  # user entered no option, break loop and return
                break
            elif pl_names:  # print originally added tracks
                name = pl_names[0]
                items = self.playlist_name_collection[name]

                print(f"\n\t\33[96mShowing tracks originally added to {name}:\33[0m\n")
                for i, item in enumerate(items, 1):
                    print(self.api.format_item_data(i=i, name=item.name, uri=item.uri, total=len(items)))
            elif current_input.lower() == 's' or current_input.lower() == 'q':  # quit/skip
                self.exit = current_input.lower() == 'q'
                self.done = True
                break
            elif current_input.lower() == "h":  # print help text
                print(help_text)
            elif check_spotify_type(current_input) is not None:  # print URL/URI/ID result
                if not self.api.test():
                    self.api.auth()
                self.api.pretty_print_uris(current_input)

            else:
                print("Input not recognised.")

    ###########################################################################
    ## Match tracks user has added or removed
    ###########################################################################
    def _check_uri(self) -> None:
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

            self._log_padded([name, f"{len(self.switched):>4} tracks switched"])
            self._log_padded([name, f"{len(unavailable):>4} tracks unavailable"])
            self._log_padded([name, f"{len(unchanged):>4} tracks unchanged"])
            self._log_padded([name, f"{updated:>4} tracks updated"], pad='<')

            self.final_switched += self.switched
            self.final_unavailable += unavailable
            self.final_unchanged += unchanged
            self.switched.clear()

    def _match_to_remote(self, name: str) -> None:
        self._logger.info(f'\33[1;95m ->\33[1;97m '
                          f'Attempting to find URIs for items in Spotify playlist: \33[94m{name}\33[0m...')

        source = self.playlist_name_collection[name]
        remote = SpotifyPlaylist(self.api.get_collections(self.playlist_name_urls[name])[0]).tracks

        added = [track for track in remote if track not in source and track.has_uri]
        removed = [track for track in source if track not in remote and track.has_uri]
        missing = [track for track in source if not track.has_uri]

        if len(added) + len(removed) + len(missing) == 0:
            self._log_padded([name, f"Playlist unchanged and no missing URIs, skipping match"], pad='< >')
            return

        self._log_padded([name, f"{len(added):>6} items added"], pad=' ')
        self._log_padded([name, f"{len(removed):>6} items removed"], pad=' ')
        self._log_padded([name, f"{len(missing):>6} items in source missing URI"], pad=' ')

        remaining = removed + missing
        count_start = len(remaining)
        for track in remaining:
            result = self.score_match(track, results=added, max_score=1.5)
            if not result:
                continue

            removed.remove(result) if result in removed else missing.remove(result)
            self.switched.append(result)

        self.remaining = removed + missing
        count_final = len(remaining)
        self._log_padded([name, f"{count_start - count_final:>4} tracks switched"])
        self._log_padded([name, f"{count_final:>4} tracks still not found"])

    def _match_to_input(self, name: str):
        if not self.remaining:
            return

        header = ["\n\t\33[1;94m{name}:\33[91m The following tracks were removed and/or matches were not found. \33[0m"]
        options = {
            "u": "Mark track as 'Unavailable on Spotify'",
            "n": "Leave track with no URI. (Syncify will still attempt to find this track at the next run)",
            "a": "Add in addition to 'u' or 's' options to apply this setting to all tracks in this playlist",
            "r": "Recheck playlist for all tracks in the album",
            "s": "Skip checking process for all playlists",
            "q": "Skip checking process, delete current temporary playlists, and quit Syncify",
            "h": "Show this dialogue again",
        }

        current_input = ""
        help_text = self._help_text_formatter(options=options, header=header).format(name=name)
        help_text += "OR enter a custom URI/URL/ID for this track\n"

        self._log_padded([name, f"Getting user input for {len(self.remaining)} tracks"])
        max_width = self._get_max_width([item.name for item in self.remaining], max_width=50)

        print(help_text)
        for item in self.remaining.copy():
            while item in self.remaining:  # while item not matched or skipped
                if 'a' not in current_input:
                    current_input = self._get_user_input(self._truncate_align_str(item.name, max_width=max_width))

                if current_input.lower().replace('a', '') == 'u':  # mark track as unavailable
                    self._logger.debug([name, "Marking as unavailable"])
                    item.uri = None
                    item.has_uri = False
                    self.remaining.remove(item)
                elif current_input.lower().replace('a', '') == 'n':  # leave track without URI and unprocessed
                    self._logger.debug([name, "Skipping"])
                    item.uri = None
                    item.has_uri = None
                    self.remaining.remove(item)
                elif current_input.lower() == 'r':  # return to former 'while' loop
                    self._logger.debug([name, "Refreshing playlist metadata and restarting loop"])
                    self.remaining.clear()
                    return
                elif current_input.lower() == 's' or current_input.lower() == 'q':  # quit/skip
                    self._log_padded([name, "Skipping all loops"])
                    self.exit = current_input.lower() == 'q'
                    self.done = True
                    self.remaining.clear()
                    return
                elif current_input.lower() == 'h':  # print help
                    print(help_text)
                elif check_spotify_type(current_input) is not None:  # update URI and add track to switched list
                    uri = self.api.convert(current_input, kind=ItemType.TRACK, type_out=IDType.URI)

                    self._logger.debug([name, f"Updating URI: {item.uri} -> {uri}"])
                    item.uri = uri
                    item.has_uri = uri

                    self.switched.append(item)
                    self.remaining.remove(item)
                else:  # invalid input
                    current_input = ""

            if not self.remaining:
                break
