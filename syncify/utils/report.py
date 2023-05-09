
class Report():

    ###########################################################################
    ## Checks
    ###########################################################################
    def check_compilation(self, tracks: list, min_threshold: int = 0.5, **kwargs) -> bool:
        """
        Check if a given set of tracks is a compilation album or not.

        :param track: list. Metadata for locally stored tracks with 'compilation' keys.
        :param min_threshold: int, default=0.5. Min ratio of tracks that need to be
            compilation to return True.
        :return bool. True if compilation, False if not.
        """
        count = [t["compilation"] for t in tracks if isinstance(t["compilation"], int)]
        return sum(count) > len(tracks) * min_threshold

    def check_spotify_valid(self, string: str, kind: list = None, **kwargs) -> bool:
        """
        Check that the given string is of a valid Spotify type.

        :param string: str. URL/URI/ID to check.
        :param kind: str/list, default=None. Types to check for. None checks all.
            Can be 'open', 'api', 'uri', 'id'.
        :return bool. True if valid, False if not.
        """
        if not isinstance(string, str):
            return False
        elif kind is None:
            kind = ['open', 'api', 'uri', 'id']

        if 'open' in kind and self._open_url.lower() in string.lower():
            return True
        elif 'api' in kind and self._base_api.lower() in string.lower():
            return True
        elif 'uri' in kind and len(string.split(":")) == 3:
            uri_list = string.split(":")
            if uri_list[1] != 'user' and len(uri_list[2]) == self._id_len:
                return True
        elif 'id' in kind and len(string) == self._id_len:
            return True

        return False

    ###########################################################################
    ## Reports
    ###########################################################################
    def report_differences(self, local: dict, spotify: dict,
                           report_file: str = None, **kwargs) -> dict:
        """
        Produces a report on the differences between local and spotify playlists.

        :param local: dict. Local playlists in form <name>: <list of dicts of local track's metadata>
        :param spotify: dict. Spotify playlists in form <name>: <list of dicts of spotify track's metadata>
        :param report_file: str, default=None. Name of file to output report to. If None, suppress file output.
        :return: dict. Report on extra, missing, and unavailable tracks from Spotify
        """
        if len(local) == 0 or len(spotify) == 0:
            return False
        
        # prepare for report
        report = {}
        if isinstance(report_file, str):
            self.delete_json(report_file, **kwargs)

        extra_len = 0
        missing_len = 0
        unavailable_len = 0

        # get verbose level appropriate logger and appropriately align formatting
        logger = self._logger.info if self._verbose > 0 else self._logger.debug
        max_width = len(max(local, key=len)) + 1 if len(max(local, key=len)) + 1 < 50 else 50

        print()
        self._logger.info(
            '\33[1;95m -> \33[1;97mReporting on differences between local and Spotify playlists... \33[0m')
        for name, tracks in local.items():  # iterate through local playlists
            # preprocess URIs to lists for local and spotify
            # None and False added to factor in later check: track['uri'] not in spotify_URIs
            local_uris = [track['uri'] for track in tracks if track['uri']]
            spotify_uris = [*[track['uri'] for track in spotify[name]], None, False]

            # get reports
            extra_tracks = [track for track in spotify[name] if track['uri'] not in local_uris]
            missing_tracks = [track for track in tracks if track['uri'] not in spotify_uris]
            unavailable_tracks = [track for track in tracks if track['uri'] is False]

            # update counts and list
            extra = extra_tracks if len(extra_tracks) > 0 else []
            extra_len += len(extra_tracks)

            missing = missing_tracks if len(missing_tracks) > 0 else []
            missing_len += len(missing_tracks)

            unavailable = unavailable_tracks if len(unavailable_tracks) > 0 else []
            unavailable_len += len(unavailable_tracks)

            logger(
                f"{name if len(name) < 50 else name[:47] + '...':<{max_width}} |"
                f"\33[92m{len(extra):>4} extra \33[0m|"
                f"\33[91m{len(missing):>4} missing \33[0m|"
                f"\33[93m{len(unavailable):>4} unavailable \33[0m"
            )

            # incrementally save report
            tmp_out = {
                "Local ✗ | Spotify ✓": {name: extra} if len(extra) > 0 else {},
                "Local ✓ | Spotify ✗": {name: missing} if len(missing) > 0 else {},
                "Tracks not on Spotify": {name: unavailable} if len(unavailable) > 0 else {},
            }
            if len(extra) + len(missing) + len(unavailable) > 0:
                if isinstance(report_file, str):
                    report = self.update_json(tmp_out, report_file, **kwargs)
                else:
                    for k in tmp_out:
                        report[k] = report.get(k, {}) | tmp_out[k]

        # print total stats
        if self._verbose > 0:
            print()
        else:
            max_width = 0
        text = "TOTALS"
        self._logger.info(
            f"\33[1;96m{text:<{len(text) + max_width - len(text)}} \33[0m|"
            f"\33[1;92m{extra_len:>4} extra \33[0m|"
            f"\33[1;91m{missing_len:>4} missing \33[0m|"
            f"\33[1;93m{unavailable_len:>4} unavailable \33[0m\n"
        )

        return report

    def report_missing_tags(self, playlists: dict, tags: list = None,
                            match: str = "any", **kwargs) -> dict:
        """
        Returns lists of dicts of track metadata for tracks with missing tags.

        :param playlists: dict. Metadata in form <name>: <list of dicts of track's metadata>
        :param tags: list, default=None. List of tags to consider missing.
        :param match: str, default="any". Return only if track is missing "any" or "all" tags.
        :return: dict. <name>: <list of dicts of track's metadata that have required missing tags>
        """
        tracks_len = len([t for tracks in playlists.values() for t in tracks])
        self._logger.info(f"Checking {tracks_len} tracks for {match} missing tags: {tags}")
        tags = [t if t != 'image' else 'has_image' for t in tags]

        missing_tags = {}
        for name, tracks in playlists.items():
            missing_tags[name] = []
            for track in tracks:  # loop through all tracks
                if match == "all":  # check if track is missing all tags
                    missing = all(not track.get(tag) for tag in tags)
                else:  # check if track is missing only some tags
                    missing = any(not track.get(tag) for tag in tags)

                if missing:  # if no tag, add to missing_tags dict
                    missing_tags[name].append(track)

            if len(missing_tags[name]) == 0:  # remove entry if no missing tags
                del missing_tags[name]

        tracks_len = len([t for tracks in missing_tags.values() for t in tracks])
        self._logger.info(
            f"\33[93mFound {tracks_len} tracks with {match} missing tags\33[0m: {tags}")

        return missing_tags
