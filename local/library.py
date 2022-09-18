import json
import re
import sys
from glob import glob
from datetime import datetime as dt
from os.path import basename, dirname, isdir, join, sep, splitext, getmtime, getsize

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
            "comment": ["comment", "description"],
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
            self._all_files += glob(join(self._music_path, "**", f"*{ext}"), recursive=True)
            self._all_files += glob(join(self._music_path, "*", "**", f".*{ext}"), recursive=True)
        self._all_files = sorted(self._all_files)
        self._all_files_lower = [path.lower() for path in self._all_files]

    def _get_case_sensitive_path(self, path: str):
        if path in self._all_files:
            return path
        elif path.lower() in self._all_files_lower:
            return self._all_files[self._all_files_lower.index(path.lower())]
        else:
            raise Exception(f"Path not found in library: {path}")

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
            path_cs = self._get_case_sensitive_path(path)

            if path_cs is not None:
                try:  # load case-sensitive path
                    raw_data = mutagen.File(path_cs)
                except mutagen.MutagenError:  # give up
                    self._logger.error(f"File not found | {path}")
                    return path, ext
            else:
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
            metadata[tag_name] = None
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
                
                if metadata.get(tag_name) is not None:  # break if value found
                    break

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
        metadata["path"] = path
        metadata["folder"] = basename(dirname(path))
        metadata["filename"] = basename(path)
        metadata["ext"] = splitext(path)[1].lower()
        metadata["size"] = getsize(path)
        metadata["date_modified"] = dt.fromtimestamp(getmtime(path)).strftime("%d/%m/%Y %H:%M:%S")
        
        # placeholders for musicbee metadata
        metadata["date_added"] = None
        metadata["last_played"] = None
        metadata["play_count"] = None
        metadata["rating"] = None

        return metadata

    #############################################################
    ## Multiple files functions
    #############################################################
    def load_local_metadata(self, prefix_start: str = None, prefix_stop: str = None,
                           prefix_limit: list = None, compilation: bool = None, **kwargs) -> dict:
        """
        Get metadata on all audio files in music folder.

        :param prefix_start: str, default=None. Start processing from the folder
            with this prefix i.e. <start_folder>:<END>.
        :param prefix_stop: str, default=None. Stop processing from the folder
            with this prefix i.e. <START>:<stop_folder>.
        :param prefix_limit: list, default=None. Only process albums that start
            with these prefixes.
        :param compilation: bool, default=None. Only return compilation albums.
        :return: dict. <folder name>: <list of dicts of track's metadata>
        """
        # get all folders in music path
        folders = [basename(f) for f in glob(join(self._music_path, "**"), recursive=True) if isdir(f)]

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
                for prefix in prefix_limit:
                    if folder.lower().strip().startswith(prefix.strip().lower()):
                        folders_reduced.append(folder)
                        break
            folders = folders_reduced
            self._logger.debug(f"Folders matching prefix: {json.dumps(folders, indent=2)}")

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
            leave=self._verbose > 0,
            disable=self._verbose > 2 and self._verbose < 2,
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
                f"Compilation-only mode. Removed {count} non-compilation folders. "
                f"{len(folder_metadata)} folders remaining."
            )

        # get verbose level appropriate logger and appropriately align formatting
        logger = self._logger.info if self._verbose > 0 else self._logger.debug

        # sort playlists in alphabetical order and print
        if self._verbose > 0:
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
            print()
            load_errors = "\n".join(load_errors)
            self._logger.error(f"Could not load: \33[91m\n{load_errors} \33[0m")

        self._logger.debug('Extracting track metadata: Done')
        return folder_metadata

    def restore_local_uris(self, playlists: dict, backup: str, **kwargs) -> dict:
        """
        Restore loaded metadata URIs from backup dict.

        :param playlists: dict. Metadata in form <name>: <list of dicts of track's metadata>
        :param backup: str. Filename of backup json in form <path>: <uri>.
        :return: dict. <name>: <list of dicts of track's metadata>
        """
        print()
        self._logger.info(f"\33[1;95m -> \33[1;97mRestoring URIs from backup file: {backup} \33[0m")

        backup = self.load_json(backup, parent=True, **kwargs)
        if not backup:
            self._logger.info(f"\33[91mBackup file not found.\33[0m")
            return

        for tracks in playlists.values():
            for track in tracks:  # loop through all tracks
                if track['path'] in backup:
                    track['uri'] = backup[track['path']]


        # set clear kwarg to all
        kwargs_mod = kwargs.copy()
        kwargs_mod['tags'] = 'uri'
        self.update_file_tags(playlists, **kwargs_mod)

        tracks_updated = len([t for tracks in playlists.values() for t in tracks])
        self._logger.info(f"\33[92mRestored URIs for {tracks_updated} tracks \33[0m")

        return playlists

