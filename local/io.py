import re
import sys
from glob import glob
from os.path import basename, dirname, isdir, join, splitext

import mutagen
from tqdm.auto import tqdm

from utils.process import Process


class LocalIO(Process):

    # tag name which holds track URI
    _uri_tag = "comment"
    # placeholder URI for tracks which aren't on Spotify
    _unavailable_uri_value = "spotify:track:unavailable"

    # tag type formats
    _int_tags = ["track", "year", "disc"]
    _float_tags = ["bpm", "length"]

    # tags used for each metadata type for flac, mp3, m4a, and wma file types
    # also generic image file type for mp3, m4a, and wma file types
    _tag_ids = {
        ".flac": {
            "title": ["title"],
            "artist": ["artist"],
            "album": ["album"],
            "track": ["tracknumber"],
            "genre": ["genre"],
            "year": ["year", "date"],
            "bpm": ["bpm"],
            "key": ["initialkey"],
            "disc": ["discnumber"],
            "compilation": ["compilation"],
            "album_artist": ["albumartist"],
            "comment": ["comment"],
            "image": [],
        },
        ".mp3": {
            "title": ["TIT2"],
            "artist": ["TPE1"],
            "album": ["TALB"],
            "track": ["TRCK"],
            "genre": ["TCON"],
            "year": ["TDRC", "TYER", "TDAT"],
            "bpm": ["TBPM"],
            "key": ["TKEY"],
            "disc": ["TPOS"],
            "compilation": ["TCMP"],
            "album_artist": ["TPE2"],
            "comment": ["COMM"],
            "image": ["APIC"],
        },
        ".m4a": {
            "title": ["©nam"],
            "artist": ["©ART", "aART"],
            "album": ["©alb"],
            "track": ["trkn"],
            "genre": ["©gen"],
            "year": ["©day"],
            "bpm": ["tmpo"],
            "key": ["----:com.apple.iTunes:INITIALKEY"],
            "disc": ["discnumber"],
            "compilation": ["cpil"],
            "album_artist": [],
            "comment": ["©cmt"],
            "image": ["covr"],
        },
        ".wma": {
            "title": ["Title"],
            "artist": ["Author"],
            "album": ["WM/AlbumTitle"],
            "track": ["WM/TrackNumber"],
            "genre": ["WM/Genre"],
            "year": ["WM/Year"],
            "bpm": ["WM/BeatsPerMinute"],
            "key": ["WM/InitialKey"],
            "disc": ["WM/PartOfSet"],
            "compilation": ["COMPILATION"],
            "album_artist": ["WM/AlbumArtist"],
            "comment": ["Description"],
            "image": ["WM/Picture"],
        },
    }

    def __init__(self):

        Process.__init__(self)

        # get list of all accepted types of audio files in music path
        self._all_files = []
        for ext in self._tag_ids:
            # first glob doesn't get filenames that start with a period
            # second glob only picks up filenames that start with a period
            self._all_files += glob(join(self.MUSIC_PATH, "*", "**", f"*{ext}"), recursive=True)
            self._all_files += glob(join(self.MUSIC_PATH, "*", "**", f".*{ext}"), recursive=True)
        self._all_files = sorted(self._all_files)

    #############################################################
    ## Inidividual track functions
    #############################################################
    def load_file(self, track, **kwargs) -> tuple:
        """
        Load local file using mutagen and extract file extension as string.

        :param track: str/dict. A string of the track's path or a dict containing 'path' as key
        :return: (mutagen.File, str). Mutagen file object and file extension as string OR track path/None and None if load error.
        """
        # extract track path
        if isinstance(track, dict) and "path" in track:
            path = track["path"]
        elif isinstance(track, str):
            path = track
        else:
            return None, None

        # extract file extension and confirm file type is listed in self.filetype_tags dict
        ext = splitext(path)[1].lower()
        if ext not in self._tag_ids:
            self._logger.warning(
                f"{ext} not an accepted extension."
                f"Use only: {', '.join(list(self._tag_ids.keys()))}")
            return path, ext

        try:  # load filepath and get file extension
            raw_data = mutagen.File(path)
        except mutagen.MutagenError:
            # check if given path is case-insensitive, replace with case-sensitive path
            for file_path in self._all_files:
                if file_path.lower() == path.lower():
                    path = file_path
                    break

            try:  # load case-sensitive path
                raw_data = mutagen.File(path)
            except mutagen.MutagenError:  # give up
                self._logger.error(f"File not found | {path}")
                return path, ext

        return raw_data, ext

    def extract_local_track_metadata(self, path: str, position: int = None, **kwargs) -> dict:
        """
        Extract metadata for a track.

        :param path: str. Path to the track (may be case-insensitive)
        :param position: int, default=None. Position of track in a playlist.
        :return: dict or str. Processed metadata. If load failed, return path string
        """
        # load file as mutagen object
        raw_data, ext = self.load_file(path, **kwargs)
        if raw_data is None or raw_data == path:
            return path

        metadata, uri = self._extract(raw_data=raw_data, ext=ext, position=position)
        metadata = self._process(metadata=metadata, uri=uri, path=path)

        return metadata

    def _extract(self, raw_data, ext: str, position: int = None) -> tuple:
        """Extension based tag extraction logic. INTERNAL USE ONLY"""
        # record given track position
        uri = None
        metadata = {"position": position}

        # extract all tags found in _tag_ids for this filetype
        for tag_name, _tag_ids in self._tag_ids.get(ext, {"": []}).items():
            for tag_id in _tag_ids:
                # each filetype has a different way of extracting tags within mutagen
                if ext == ".mp3":
                    # some tags start with the given tag_id,
                    # but often have multiple tags with extra suffixes
                    # loop through each tag in raw_data to find all tags
                    metadata[tag_name] = []
                    for tag in raw_data:
                        if tag_id in tag and raw_data[tag] is not None:
                            if tag_name == 'image': 
                                metadata[tag_name].append(raw_data[tag].data)
                            elif tag_name == "year" and hasattr(raw_data[tag], "year"):
                                metadata[tag_name].append(raw_data[tag].year)
                            else:
                                metadata[tag_name].append(raw_data[tag][0])

                            
                    for i, value in enumerate(metadata[tag_name]):  # find valid URI
                        if self.check_spotify_valid(value, kind="uri") or value == self._unavailable_uri_value:
                            metadata[tag_name] = value
                            uri = value
                            break

                elif ext == ".m4a" and tag_name in ["track", "disc", "compilation", "key"]:
                    if tag_name in ["track", "disc"]:
                        metadata[tag_name] = raw_data.get(tag_id, [[None]])[0][0]
                    elif tag_name == "compilation":
                        metadata[tag_name] = raw_data.get(tag_id, "")
                    elif tag_name == "key":
                        metadata[tag_name] = raw_data.get(tag_id, [b''])[0][:].decode("utf-8")
                elif ext == ".wma":
                    metadata[tag_name] = raw_data.get(
                        tag_id, [mutagen.asf.ASFUnicodeAttribute(None)]
                    )[0].value
                else:
                    metadata[tag_name] = raw_data.get(tag_id, [None])[0]


                # if no tag found, replace with null
                if len(str(metadata[tag_name]).strip()) == 0:
                    metadata[tag_name] = None
                
                if isinstance(metadata[tag_name], list):  # remove lists
                    if len(metadata[tag_name]) == 0:  # no tags left
                        metadata[tag_name] = None
                    else:  # only keep first tag
                        metadata[tag_name] = metadata[tag_name][0]

                if metadata[tag_name] is not None:  # type based conversion
                    # strip whitespaces from string based tags
                    if isinstance(metadata[tag_name], str):
                        metadata[tag_name] = metadata[tag_name].strip()

                    # convert to int or float
                    if tag_name in self._int_tags:
                        metadata[tag_name] = int(re.sub('[^0-9]', '', str(metadata[tag_name])))
                    elif tag_name in self._float_tags:
                        metadata[tag_name] = float(re.sub('[^0-9.]', '', str(metadata[tag_name])))

        # determine if track has image embedded
        if ext == ".flac":
            metadata["has_image"] = bool(raw_data.pictures)
        else:
            metadata["has_image"] = metadata["image"] is not None
        metadata["image"] = None

        # add track length
        metadata["length"] = raw_data.info.length

        return metadata, uri

    def _process(self, metadata: dict, uri: str, path: str) -> dict:
        """Process file metadata. INTERNAL USE ONLY"""
        if metadata["compilation"] is not None:  # convert compilation tag to bool
            metadata["compilation"] = int(metadata["compilation"])

        try:  # convert release date tags to year only
            metadata["year"] = int(re.sub("[^0-9]", "", str(metadata.get("year", "")))[:4])
        except (ValueError, TypeError):
            metadata["year"] = None

        # URI handling conditions
        metadata["uri"] = None
        uri = metadata.get(self._uri_tag) if uri is None else uri
        if uri is not None:
            if uri == self._unavailable_uri_value:
                metadata["uri"] = False
            elif self.check_spotify_valid(uri, kind="uri"):
                metadata["uri"] = uri

        # add track path and folder name to metadata
        metadata["folder"] = basename(dirname(path))
        metadata["path"] = path

        return metadata

    #############################################################
    ## Multiple files functions
    #############################################################
    def get_local_metadata(self, prefix_start: str = None, prefix_stop: str = None,
                           prefix_limit: str = None, compilation: bool = None, **kwargs) -> dict:
        """
        Get metadata on all audio files in music folder.

        :param prefix_start: str, default=None. Start processing from the folder
            with this prefix i.e. <start_folder>:<END>.
        :param prefix_stop: str, default=None. Stop processing from the folder
            with this prefix i.e. <START>:<stop_folder>.
        :param prefix_limit: str, default=None. Only process albums that start
            with this prefix.
        :param compilation: bool, default=None. Only return compilation albums.
        :return: dict. <folder name>: <list of dicts of track's metadata>
        """
        # get all folders in music path
        folders = [basename(f) for f in glob(join(self.MUSIC_PATH, "**"), recursive=True) if isdir(f)]

        # filter folders to use in extraction
        if prefix_start:
            for i, folder in enumerate(folders):
                if folder.lower().strip().startswith(prefix_start.strip().lower()):
                    self._logger.debug(f"Folder start: {folder}")
                    folders = folders[i:]
                    break
        if prefix_stop:
            for i, folder in enumerate(folders):
                if folder.lower().strip().startswith(prefix_stop.strip().lower()):
                    self._logger.debug(f"Folder end: {folder}")
                    folders = folders[:i + 1]
                    break
        if prefix_limit:
            folders_reduced = []
            for folder in folders:
                if folder.lower().strip().startswith(prefix_limit.strip().lower()):
                    folders_reduced.append(folder)
            folders = folders_reduced
            self._logger.debug(f"Folder prefixes: {folder}")

        # filter files
        paths = [path for path in self._all_files if basename(dirname(path)) in folders]

        print()
        self._logger.info(
            f"\33[1;95m -> \33[1;97mExtracting track metadata for {len(paths)} audio paths in {len(folders)} folders \33[0m")

        # progress bar and empty dict to fill with metadata
        folder_metadata = {}
        path_bar = tqdm(
            paths,
            desc="Loading library",
            unit="tracks",
            leave=self._verbose,
            file=sys.stdout,
        )

        load_errors = []
        for path in path_bar:
            # get folder name and metadata for each track
            folder = basename(dirname(path))
            metadata = self.extract_local_track_metadata(path, **kwargs)

            if metadata is None or metadata == path:
                # extract_local_track_metadata returns path if load is unsuccesful
                load_errors.append(path)
            elif metadata:
                # if metadata successfully extracted, update metadata folder
                folder_metadata[folder] = folder_metadata.get(folder, []) + [metadata]

        if compilation:
            count = 0
            for folder, tracks in folder_metadata.copy().items():
                if not self.check_compilation(tracks):
                    del folder_metadata[folder]
                    count += 1
            self._logger.debug(
                f"Removed {count} non-compilation folders."
                f"{len(folder_metadata)} folders remaining."
            )

        # get verbose level appropriate logger and appropriately align formatting
        logger = self._logger.info if self._verbose else self._logger.debug

        # sort playlists in alphabetical order and print
        if self._verbose:
            print()
        available = len([t for f in folder_metadata.values() for t in f if isinstance(t['uri'], str)])
        missing = len([t for f in folder_metadata.values() for t in f if t['uri'] is None])
        unavailable = len([t for f in folder_metadata.values() for t in f if t['uri'] is False])
        logger(
            f"\33[1;96mLIBRARY TOTALS       \33[1;0m|"
            f"\33[92m{available:>6} available \33[0m|"
            f"\33[91m{missing:>6} missing \33[0m|"
            f"\33[93m{unavailable:>6} unavailable \33[0m|"
            f"\33[1m{len(paths):>6} total \33[0m"
        )

        if len(load_errors) > 0:
            load_errors = "\n".join(load_errors)
            self._logger.error(f"Could not load: \33[91m\n{load_errors} \33[0m")

        self._logger.debug('Extracting track metadata: Done')
        return folder_metadata

    def get_m3u_metadata(self, in_playlists: list = None,
                         ex_playlists: list = None, **kwargs) -> dict:
        """
        Get metadata on all tracks found in m3u playlists

        :param in_playlists: list, default=None. Limit playlists to those in this list.
        :param ex_playlists: list, default=None. Don't process playlists in this list.
        :return: dict. <name>: <list of dicts of track's metadata>
        """
        # list of paths of .m3u files in playlists path
        playlist_paths = glob(join(self._playlists_PATH, "*.m3u"))
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

        # progress bar
        playlist_bar = tqdm(
            playlist_paths,
            desc="Loading m3u playlists",
            unit="playlists",
            leave=self._verbose,
            file=sys.stdout,
        )

        names = [splitext(basename(path))[0] for path in playlist_paths]
        max_width = len(max(names, key=len)) if len(max(names, key=len)) < 50 else 50

        load_errors = []
        for playlist_path in playlist_bar:
            # extract filename only process if playlists not defined or in playlists list
            name = splitext(basename(playlist_path))[0]

            # get list of tracks in playlist
            with open(playlist_path, "r", encoding="utf-8") as m3u:
                track_paths = [line.rstrip() for line in m3u]

            # replace filepath stems related to other operating systems
            if any(path in track_paths[0] for path in self.OTHER_PATHS):
                # determine part of filepath to replace and replace
                sub = (
                    self.OTHER_PATHS[0]
                    if track_paths[0].startswith(self.OTHER_PATHS[0])
                    else self.OTHER_PATHS[1]
                )
                track_paths = [file.replace(sub, self.MUSIC_PATH) for file in track_paths]

                # sanitise path separators
                if "/" in self.MUSIC_PATH:
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
        logger = self._logger.info if self._verbose else self._logger.debug
        max_width = len(max(playlist_metadata, key=len)) if len(max(playlist_metadata, key=len)) < 50 else 50

        # sort playlists in alphabetical order and print
        if self._verbose:
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
            load_errors = "\n".join(load_errors)
            logger(f"Could not load: \33[91m\n{load_errors} \33[0m")

        self._logger.debug("Extrating track metadata: Done")
        return playlist_metadata

    def restore_local_uris(self, playlists: dict, backup: str, **kwargs) -> dict:
        """
        Restore loaded metadata URIs from backup dict.

        :param playlists: dict. Metadata in form <name>: <list of dicts of track's metadata>
        :param backup: str. Filename of backup json in form <path>: <uri>.
        :return: dict. <name>: <list of dicts of track's metadata>
        """
        self._logger.info(f"Restoring URIs from backup file: {backup}")

        backup = self.load_json(backup, **kwargs)
        if not backup:
            return

        for tracks in playlists.values():
            for track in tracks:  # loop through all tracks
                if track['path'] in backup:
                    track['uri'] = backup[track['path']]

        return playlists
