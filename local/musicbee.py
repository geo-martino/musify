import re
import sys
import urllib
from copy import deepcopy
from datetime import datetime as dt
from datetime import timedelta
from functools import reduce
from glob import glob
from operator import mul
from os.path import basename, dirname, isdir, join, normpath, sep, splitext
from random import shuffle

from dateutil.relativedelta import relativedelta
from tqdm.auto import tqdm

from local.library import LocalIO


class Compare:

    def __init__(self, value, condition: dict, last_played: str = None) -> None:
        self.value = value
        self.expected = [val for k, val in condition.items() if k.startswith("@Value")]
        if self.expected[0] == '[playing track]' and last_played is not None:
            self.expected = [last_played]

        self.check_type()

        compare_str = condition["@Comparison"]
        compare_str = re.sub('([A-Z])', lambda m: f"_{m.group(0).lower()}", compare_str)
        self.method = getattr(self, compare_str)


    def match(self) -> bool:
        return self.method()

    def check_type(self) -> None:
        if isinstance(self.value, str):
            if re.match("\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{1,2}:\d{1,2}", self.value):
                self.value = dt.strptime(self.value, "%d/%m/%Y %H:%M:%S")
        
        if isinstance(self.value, int):
            self.convert_expected_to_int()
        elif isinstance(self.value, float):
            self.convert_expected_to_float()
        elif isinstance(self.value, bool):
            self.expected = None
        elif isinstance(self.value, dt):
            self.convert_expected_to_dt()

    def convert_expected_to_int(self) -> None:
        converted = []
        for exp in self.expected:
            if ":" in exp:
                exp = self._get_seconds(exp)
            converted.append(int(exp))
        self.expected = converted

    def convert_expected_to_float(self) -> None:
        converted = []
        for exp in self.expected:
            if ":" in exp:
                exp = self._get_seconds(exp)
            converted.append(float(exp))
        self.expected = converted
    
    def convert_expected_to_dt(self) -> None:
        td_str_mapper = {
            "h": lambda x: timedelta(hours=int(x)),
            "d": lambda x: timedelta(days=int(x)),
            "w": lambda x: timedelta(weeks=int(x)), 
            "m": lambda x: relativedelta(months=int(x))
            }
        
        converted = []
        for exp in self.expected:
            if re.match("\d{1,2}/\d{1,2}/\d{4}", exp):
                converted.append(dt.strptime(exp, "%d/%m/%Y"))
            elif re.match("\d{1,2}/\d{1,2}/\d{2}", exp):
                converted.append(dt.strptime(exp, "%d/%m/%y"))
            else:
                digit = int(re.sub("[^\d]+", "", exp))
                mapper_key = re.sub("[^\w]+", "", exp)
                converted.append(dt.now() - td_str_mapper[mapper_key](digit))
        self.expected = converted

    @staticmethod
    def _get_seconds(time_str: str) -> int:
        factors = [24, 60, 60, 1]
        digits_split = time_str.split(":")
        digits = [int(n.split(",")[0]) for n in digits_split]
        seconds = int(digits_split[-1].split(",")[1]) / 1000
        for i, digit in enumerate(digits, 1):
            seconds += digit * reduce(mul, factors[-i:], 1)

        return seconds      

    def _is(self) -> bool:
        return self.value == self.expected[0]

    def _is_not(self) -> bool:
        return not self._is()

    def _is_after(self) -> bool:
        return self.value > self.expected[0]

    def _is_before(self) -> bool:
        return self.value < self.expected[0]

    def _is_in_the_last(self) -> bool:
        return self._is_after()

    def _is_not_in_the_last(self) -> bool:
        return self._is_before()

    def _is_in(self) -> bool:
        return self.value in self.expected

    def _is_not_in(self) -> bool:
        return not self._is_in()

    def _greater_than(self) -> bool:
        return self.value > self.expected[0]

    def _less_than(self) -> bool:
        return self.value < self.expected[0]

    def _in_range(self) -> bool:
        return self.value > self.expected[0] and self.value < self.expected[1]

    def _not_in_range(self) -> bool:
        return not self._in_range()

    def _is_not_null(self) -> bool:
        return self.value is not None or self.value is True

    def _is_null(self) -> bool:
        return self.value is None or self.value is False

    def _starts_with(self) -> bool:
        return self.value.startswith(self.expected[0])

    def _ends_with(self) -> bool:
        return self.value.endswith(self.expected[0])

    def _contains(self) -> bool:
        return self.expected[0] in self.value

    def _does_not_contain(self) -> bool:
        return not self._contains()

    def _in_tag_hierarchy(self) -> bool:
        # TODO: what even is this
        return

    def _matches_reg_ex(self) -> bool:
        return bool(re.search(self.expected[0], self.value))

    def _matches_reg_ex_ignore_case(self) -> bool:
        return bool(re.search(self.expected[0], self.value, flags=re.IGNORECASE))



class MusicBee(LocalIO):
    _field_code_map = {
        0: None,
        65: "title",
        32: "artist",
        78: "album",  # album including articles like 'the' and 'a' etc.
        30: "album",  # album ignoring articles like 'the' and 'a' etc.
        86: "track",
        59: "genre",
        35: "year",
        85: "bpm",
        3: "disc",
        31: "album_artist",
        44: "comment",
        16: "length",
        106: "path",
        179: "folder",
        52: "filename",
        100: "ext",
        11: "date_modified",
        12: "date_added",
        13: "last_played",
        14: "play_count",
        75: "rating",
        6: {78: False, 3: False, 86: False, 52: False},
    }

    _field_map = {
        "None": None,
        "Title": "title",
        "ArtistPeople": "artist",
        "Album": "album",  # album including articles like 'the' and 'a' etc.
        "TrackNo": "track",
        "GenreSplits": "genre",
        "Year": "year",
        "Tempo": "bpm",
        "DiscNo": "disc",
        "AlbumArtist": "album_artist",
        "Comment": "comment",
        "FileDuration": "length",
        "FolderName": "folder",
        "FilePath": "path",
        "FileName": "filename",
        "FileExtension": "ext",
        "FileDateAdded": "date_added",
        "FilePlayCount": "play_count",
    }

    _musicbee_library_path = join("MusicBee", "iTunes Music Library.xml")

    def __init__(self) -> None:
        self._select_by_func = {
            "Random": lambda pl: self._simple_sort(pl, 0),
            "HighestRating": lambda pl: self._simple_sort(pl, 75, reverse=True),
            "LowestRating": lambda pl: self._simple_sort(pl, 75, reverse=False),
            "MostRecentlyPlayed": lambda pl: self._simple_sort(pl, 13, reverse=True),
            "LeastRecentlyPlayed": lambda pl: self._simple_sort(pl, 13, reverse=False),
            "MostOftenPlayed": lambda pl: self._simple_sort(pl, 14, reverse=True),
            "LeastOftenPlayed": lambda pl: self._simple_sort(pl, 14, reverse=False),
            "MostRecentlyAdded": lambda pl: self._simple_sort(pl, 12, reverse=True),
            "LeastRecentlyAdded": lambda pl: self._simple_sort(pl, 12, reverse=False),
        }

        LocalIO.__init__(self)

    @staticmethod
    def _xml_ts_to_str(timestamp_str: str) -> str:
        if timestamp_str:
            timestamp = dt.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
            return timestamp.strftime("%d/%m/%Y %H:%M:%S")


    def _get_tracks(self, tracks: dict, combine_method: str, conditions: list, include: list = None, exclude: list = None) -> list:
        matches = []
        combine = lambda x: any(x) if combine_method == "Any" else all(x)
        last_played = self._simple_sort(tracks.values(), field="last_played", reverse=True)[0]

        for path, track in tracks.items():
            if include and path in include:
                matches.append(track)
                continue
            elif exclude and path in exclude:
                continue

            match_results = []
            for condition in conditions:
                field = self._field_map.get(condition["@Field"])
                if field is None:
                    match_results.append(True)
                    continue
                elif field not in track:
                   match_results.append(None)
                   continue
                match_results.append(Compare(track[field], condition, last_played[field]).match())

            if combine(match_results):
                matches.append(track)
        
        return matches

    def _limit_playlist(self, playlist: list, conditions: dict) -> list:
        sorted_playlist = self._select_by_func[conditions["@SelectedBy"]](playlist)
        limit = int(conditions["@Count"])
        kind = conditions["@Type"]

        type_convert_func = {
            "Minutes": lambda track: track["length"] / 60,
            "Hours": lambda track: track["length"] / (60 * 60),
            "Megabytes": lambda track: track["size"] / (1000 ** 2),
            "Gigabytes": lambda track: track["size"] / (1000 ** 3),
        }

        count = 0
        limited_playlist = []
        if kind == "Items":
            limited_playlist = sorted_playlist[:limit]
        elif kind == "Albums":
            seen_albums = []
            for track in sorted_playlist:
                limited_playlist.append(track)
                if track['album'] not in seen_albums:
                    seen_albums.append(track['album'])
                
                if len(seen_albums) >= limit:
                    break
        else:
            for track in sorted_playlist:
                if count + type_convert_func[kind](track) <= limit * 1.25:
                    limited_playlist.append(track)
                    count += type_convert_func[kind](track)
                if count > limit:
                    break
        return limited_playlist

    def _sort_playlist(self, playlist: list, source: dict, shuffle_mode: str = None):
        if "SortBy" in source:
            sort = source["SortBy"]
            reverse = sort["@Order"] == "Descending"
            if int(sort["@Field"]) in self._field_code_map:
                sort_fields = {int(sort["@Field"]): reverse}
            else:
                sort_fields = self._field_code_map[6]
        elif "DefinedSort" in source:
            sort_fields = self._field_code_map.get(int(source["DefinedSort"]["@Id"]))    

        if shuffle_mode == "None":
            fields = [self._field_code_map[field] for field in sort_fields.keys()]
            reverse = list(sort_fields.values())
            nested_playlist = self._recursive_sort({None: playlist}, fields, reverse)
            playlist = self._deconstruct_nested_playlist(nested_playlist)
        else:  # only random sort supported
            playlist = self._simple_sort(playlist)
        
        return playlist

    def _simple_sort(self, playlist: list, field=None, reverse: bool = False) -> list:
        if isinstance(field, int):
            field = self._field_code_map[field]
        
        if field in ["date_added", "date_modified", "last_played"]:
            sort_value = lambda track: self._str_ts_to_int(track[field])
            return sorted(playlist, key=sort_value, reverse=reverse)
        elif field:
            sort_value = lambda track: self._strip_ignore_words(track[field])
            return sorted(playlist, key=sort_value, reverse=reverse)
        else:
            shuffle(playlist)
            return playlist

    def _recursive_sort(self, nested_struct: dict, fields: list, reverse: list) -> list:
        for key, tracks in nested_struct.items():
            nested_struct[key] = self.convert_metadata(tracks, key=fields[0], out="tracks", sort_keys=True, reverse=reverse[0])
        
        if len(fields) > 1 and len(reverse) > 1:
            for key, tracks in nested_struct.items():
                nested_struct[key] = self._recursive_sort(tracks, fields[1:], reverse[1:])
        return nested_struct

    def _deconstruct_nested_playlist(self, sort_struct: dict, tracks: list = None) -> list:
        if tracks is None:
            tracks = []
        
        if isinstance(sort_struct, dict):
            for value in sort_struct.values():
                self._deconstruct_nested_playlist(value, tracks)
        elif isinstance(sort_struct, list):
            tracks.extend(sort_struct)
        
        return tracks
        
        
    def get_tracks_from_autoplaylist(self, tracks: dict, playlist_path: str) -> list:
        """
        Get metadata on all tracks found in xautopf playlists

        :param tracks: dict. <path>: <track metadata>
        :param playlist_path: str. .autopf playlist path to load from.
        :return: list. list of track paths in the playlist
        """
        raw_xml = self.load_autoplaylist(playlist_path)
        source = raw_xml["SmartPlaylist"]["Source"]

        combine_method = source["Conditions"]["@CombineMethod"]
        conditions = self._make_list(source["Conditions"]["Condition"])
        include = source.get("ExceptionsInclude")
        exclude = source.get("Exceptions")
        if isinstance(include, str):
            include = include.split("|")
        if isinstance(exclude, str):
            exclude = exclude.split("|")

        playlist = self._get_tracks(tracks=tracks, combine_method=combine_method, conditions=conditions, include=include, exclude=exclude)

        limit = source["Limit"]
        if eval(limit["@Enabled"]):
            playlist = self._limit_playlist(playlist, conditions=limit)

        shuffle_mode = raw_xml["SmartPlaylist"]["@ShuffleMode"]
        playlist = self._sort_playlist(playlist, source=source, shuffle_mode=shuffle_mode)

        description = source["Description"]

        return playlist

    def get_local_playlists_metadata(self, tracks: dict, in_playlists: list = None, ex_playlists: list = None, **kwargs) -> dict:
        """
        Get metadata on all tracks found in xautopf playlists

        :param tracks: dict. <path>: <track metadata>
        :param in_playlists: list, default=None. Limit playlists to those in this list.
        :param ex_playlists: list, default=None. Don't process playlists in this list.
        :return: dict. <name>: <list of dicts of track's metadata>
        """
        # list of paths of .m3u files in playlists path
        playlist_paths = glob(join(self._playlists_path, '**', '*.xautopf'), recursive=True)
        playlist_paths += glob(join(self._playlists_path, '**', '*.m3u'), recursive=True)
        playlist_paths = sorted(playlist_paths, key=lambda x: splitext(basename(x))[0].lower())
        playlist_metadata = {}

        playlists_filtered = []
        for path in playlist_paths:
            name = splitext(basename(path))[0]
            if in_playlists is not None and name.lower() not in [p.lower() for p in in_playlists]:
                continue
            elif ex_playlists is not None and name.lower() in [p.lower() for p in ex_playlists]:
                continue
            playlists_filtered.append(path)

        self._logger.debug(
            f"Filtered out {len(playlist_paths) - len(playlists_filtered)} playlists "
            f"from {len(playlist_paths)} local playlists \33[0m")
        playlist_paths = playlists_filtered

        print()
        self._logger.info(
            f"\33[1;95m -> \33[1;97mFiltering track metadata for {len(playlist_paths)} playlists \33[0m")

        # progress bar
        playlist_bar = tqdm(
            playlist_paths,
            desc="Loading m3u playlists",
            unit="playlists",
            leave=self._verbose > 0,
            disable=self._verbose > 2 and self._verbose < 2,
            file=sys.stdout,
        )

        for playlist_path in playlist_bar:
            split_filename = splitext(basename(playlist_path))
            name = split_filename[0]
            ext = split_filename[1]
            if ext == ".xautopf":
                playlist = self.get_tracks_from_autoplaylist(tracks, playlist_path)
            else:
                paths = self.load_m3u(playlist_path)
                playlist = [tracks[self._get_case_sensitive_path(path)] for path in paths]
            
            playlist = deepcopy(playlist)
            for i, track in enumerate(playlist, 1):
                track["position"] = i
            playlist_metadata[name] = playlist

        # get verbose level appropriate logger and appropriately align formatting
        logger = self._logger.info if self._verbose > 0 else self._logger.debug
        max_width = len(max(playlist_metadata, key=len)) + 1 if len(max(playlist_metadata, key=len)) + 1 < 50 else 50

        # sort playlists in alphabetical order and print
        if self._verbose > 0:
            print()
        logger("\33[1;96mFound the following Local playlists: \33[0m")
        for name, playlist in sorted(playlist_metadata.items(), key=lambda x: x[0].lower()):
            logger(
                f"{name if len(name) < 50 else name[:47] + '...':<{max_width}} |"
                f"\33[92m{len([t for t in playlist if isinstance(t['uri'], str)]):>4} available \33[0m|"
                f"\33[91m{len([t for t in playlist if t['uri'] is None]):>4} missing \33[0m|"
                f"\33[93m{len([t for t in playlist if t['uri'] is False]):>4} unavailable \33[0m|"
                f"\33[1m {len(playlist):>4} total \33[0m"
            )

        self._logger.debug("Extrating track metadata: Done")
        return playlist_metadata
    
    def enrich_metadata(self, tracks: dict) -> None:
        path = join(self._music_path, self._musicbee_library_path)
        raw_xml = self.load_xml(path)
        
        if not raw_xml:
            return

        # progress bar
        track_bar = tqdm(
            raw_xml['Tracks'].values(),
            desc="Enriching metadata",
            unit="tracks",
            leave=False,
            disable=self._verbose > 2 and self._verbose < 2,
            file=sys.stdout,
        )

        for track in track_bar:
            if not track['Location'].startswith('file://localhost/'):
                continue
                
            path = urllib.parse.unquote(track['Location'].replace("file://localhost/", ""))
            path = normpath(path)
            if path not in tracks:
                path = self._get_case_sensitive_path(path)
            
            if path is None or path not in tracks:
                continue
                
            date_added = self._xml_ts_to_str(track.get('Date Added'))
            last_played = self._xml_ts_to_str(track.get('Play Date UTC'))
            play_count = int(track.get('Play Count', 0))
            rating = track.get('Rating')
            if rating is not None:
                rating = int(rating)
            
            tracks[path]["date_added"] = date_added
            tracks[path]["last_played"] = last_played
            tracks[path]["play_count"] = play_count
            tracks[path]["rating"] = rating
    
    #############################################################
    ## Load metadata from m3u path lists
    #############################################################
    def load_m3u_metadata(self, in_playlists: list = None,
                         ex_playlists: list = None, **kwargs) -> dict:
        """
        Load metadata on all tracks found in m3u playlists

        :param in_playlists: list, default=None. Limit playlists to those in this list.
        :param ex_playlists: list, default=None. Don't process playlists in this list.
        :return: dict. <name>: <list of dicts of track's metadata>
        """
        # list of paths of .m3u files in playlists path
        playlist_paths = glob(join(self._playlists_path, '**', '*.m3u'), recursive=True)
        playlist_metadata = {}

        playlists_filtered = []
        for path in playlist_paths:
            name = splitext(basename(path))[0]
            if in_playlists is not None and name.lower() not in [p.lower() for p in in_playlists]:
                continue
            elif ex_playlists is not None and name.lower() in [p.lower() for p in ex_playlists]:
                continue
            playlists_filtered.append(path)

        self._logger.debug(
            f"Filtered out {len(playlist_paths) - len(playlists_filtered)} playlists "
            f"from {len(playlist_paths)} local playlists \33[0m")
        playlist_paths = playlists_filtered

        print()
        self._logger.info(
            f"\33[1;95m -> \33[1;97mExtracting track metadata for {len(playlist_paths)} playlists \33[0m")
        
        if len(playlist_paths) == 0:
            return playlist_metadata

        # progress bar
        playlist_bar = tqdm(
            playlist_paths,
            desc="Loading m3u playlists",
            unit="playlists",
            leave=self._verbose > 0,
            disable=self._verbose > 2 and self._verbose < 2,
            file=sys.stdout,
        )

        names = [splitext(basename(path))[0] for path in playlist_paths]
        max_width = len(max(names, key=len)) + 1 if len(max(names, key=len)) + 1 < 50 else 50

        load_errors = []
        for playlist_path in playlist_bar:
            # extract filename only process if playlists not defined or in playlists list
            name = splitext(basename(playlist_path))[0]

            # get list of tracks in playlist
            track_paths = self.load_m3u(playlist_path)

            if len(track_paths) == 0:
                continue

            # replace filepath stems related to other operating systems
            if any(path in track_paths[0] for path in self._other_paths):
                # determine part of filepath to replace and replace
                sub = (
                    self._other_paths[0]
                    if track_paths[0].startswith(self._other_paths[0])
                    else self._other_paths[1]
                )
                track_paths = [file.replace(sub, self._music_path) for file in track_paths]

                # sanitise path separators
                if "/" in self._music_path:
                    track_paths = [file.replace("\\", "/") for file in track_paths]
                else:
                    track_paths = [file.replace("/", "\\") for file in track_paths]

            self._logger.debug(
                f"{name if len(name) < 50 else name[:47] + '...':<{max_width}} |"
                f"{len(track_paths):>4} tracks"
            )

            if len(track_paths) > 100:  # show progress bar for large playlists
                track_paths = tqdm(
                    track_paths,
                    desc=name,
                    unit="tracks",
                    leave=False,
                    file=sys.stdout,
                )

            # extract metadata for track path in playlist and add to dict of playlists
            playlist_metadata[name] = []
            for i, path in enumerate(track_paths):
                metadata = self.extract_local_track_metadata(path, i, **kwargs)
                if metadata is None or metadata == path:
                    load_errors.append(path)
                elif metadata is not None:
                    playlist_metadata[name].append(metadata)

        # get verbose level appropriate logger and appropriately align formatting
        logger = self._logger.info if self._verbose > 0 else self._logger.debug
        max_width = len(max(playlist_metadata, key=len)) + 1 if len(max(playlist_metadata, key=len)) + 1 < 50 else 50

        # sort playlists in alphabetical order and print
        if self._verbose > 0:
            print()
        logger("\33[1;96mFound the following Local playlists: \33[0m")
        for name, playlist in sorted(playlist_metadata.items(), key=lambda x: x[0].lower()):
            logger(
                f"{name if len(name) < 50 else name[:47] + '...':<{max_width}} |"
                f"\33[92m{len([t for t in playlist if isinstance(t['uri'], str)]):>4} available \33[0m|"
                f"\33[91m{len([t for t in playlist if t['uri'] is None]):>4} missing \33[0m|"
                f"\33[93m{len([t for t in playlist if t['uri'] is False]):>4} unavailable \33[0m|"
                f"\33[1m {len(playlist):>4} total \33[0m"
            )

        if len(load_errors) > 0:
            print()
            load_errors = "\n".join(load_errors)
            logger(f"Could not load: \33[91m\n{load_errors} \33[0m")

        self._logger.debug("Extrating track metadata: Done")
        return playlist_metadata
