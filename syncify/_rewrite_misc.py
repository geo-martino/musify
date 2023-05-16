def modify_compilation_tags(
        self, local: dict, compilation_check: bool = True, **kwargs) -> dict:
    """
    Determine if album is compilation and modify metadata:
    - Set compilation to 1
    - Set track number in ascending order by filename
    - Set disc number to 1
    - Set album name to folder name
    - Set album artist to 'Various'

    :param local: dict. <name>: <list of dicts of local track's metadata>.
    :param compilation_check: bool, default=True. If True, determine compilation for each album.
        If False, treat all albums as compilation.
    :return: Modified albums <name>: <list of dicts of local track's metadata>.
    """
    print()
    self._logger.info(
        f"\33[1;95m -> \33[1;97mSetting compilation style tags for {len(local)} albums \33[0m")
    self._logger.debug(f"Compilation check: {compilation_check}")

    modified = {}
    count = 0
    for name, tracks in local.items():
        # check if compilation
        compilation = self.check_compilation(tracks) if compilation_check else True

        if compilation:
            # determine order of tracks by filename
            track_order = sorted(basename(track['path']) for track in tracks)

            for track in tracks:  # set tags
                track["compilation"] = 1
                track['track'] = track_order.index(basename(track['path'])) + 1
                track["disc"] = 1
                track["album"] = track["folder"]
                track["album_artist"] = "Various"
                count += 1

            modified[name] = tracks
        else:
            for track in tracks:  # set tags
                track["compilation"] = 0
                count += 1

    logger = self._logger.info if self._verbose > 0 else self._logger.debug
    logger(f"\33[92mDone | Set metadata for {count} tracks \33[0m")
    return modified


def filter_tracks(self, playlists: dict, filter_tags: dict = None, **kwargs) -> dict:
    """
    Filter tracks to only those with a valid uri and not including a tag in <filter_tags>.

    :param playlists: dict. Local playlists in form <name>: <list of dicts of track's metadata>
    :param filter_tags: dict, default=None. <tag name>: <list of tags to filter out>. If None, skip this filter
    :return: dict. Filtered playlists.
    """
    self._logger.debug(
        f"Filtering tracks in {len(playlists)} playlists | "
        f"Filter out tags: {filter_tags}"
    )

    # for appropriately aligned formatting
    max_width = len(max(playlists, key=len)) + 1 if len(max(playlists, key=len)) + 1 < 50 else 50

    filtered = {}
    for name, tracks in playlists.items():
        # list of all valid tracks to add
        tracks = [track for track in tracks if isinstance(track['uri'], str)]
        filtered[name] = tracks

        if filter_tags is not None and len(filter_tags) > 0:
            # filter out tracks with tags in filter param
            filtered[name] = []
            for track in tracks:
                for tag, values in filter_tags.items():
                    if isinstance(track[tag], str) and all(isinstance(v, str) for v in values):
                        # string processing
                        tag_value = track[tag].strip().lower()
                        values = [v.strip().lower() for v in values]

                        if all(v not in tag_value for v in values):
                            filtered[name].append(track)

        self._logger.debug(
            f"{name if len(name) < 50 else name[:47] + '...':<{max_width}} | "
            f"Filtered out {len(tracks) - len(filtered[name]):>3} tracks"
        )
    return filtered