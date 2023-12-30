import argparse

from syncify import PROGRAM_NAME


class Settings:
    ###########################################################################
    ## Parse prompt args
    ###########################################################################
    def parse_from_prompt(self) -> None:
        """Parse user input from the terminal"""
        parser = self.get_parser()
        parsed = parser.parse_known_args()
        kwargs = vars(parsed[0])
        # args = parsed[1]
        self.functions = tuple(kwargs.pop("functions"))

        # if kwargs.pop('use_config'):
        #     if func_name in self.runtime_settings or func_name in self._functions:
        #         self.runtime_settings = {func_name: self.runtime_settings.get(func_name, self.cfg_general)}
        #         if len(args) > 0:
        #             self.runtime_settings[func_name]["args"] = args
        #             self.runtime_settings[func_name] = self._parse_args(func_name, self.runtime_settings[func_name])
        #
        #     return self.runtime_settings
        # if kwargs['filter_tags']:
        #     del kwargs['filter_tags']
        #
        # cfg_processed = {"kwargs": kwargs, "args": args}
        # cfg_processed = _update_map(deepcopy(self.cfg_general), cfg_processed)
        #
        # _update_map(self.runtime_settings[func_name], cfg_processed)
        # self.runtime_settings = self._configure(func_name, self.runtime_settings[func_name])
        # return self.runtime_settings

    # noinspection PyProtectedMember,SpellCheckingInspection
    def get_parser(self) -> argparse.ArgumentParser:
        """Get the terminal input parser"""
        parser = argparse.ArgumentParser(
            description="Sync your local library to Spotify.",
            prog=PROGRAM_NAME,
            usage="%(prog)s [options] [function]"
        )
        parser._positionals.title = "Functions"
        parser._optionals.title = "Optional arguments"

        # cli function aliases and expected args in order user should give them
        # parser.add_argument('-cfg', '--use-config',
        #                     action='store_true',
        #                     help=f"Use saved config in config.yml instead of cli settings.")
        parser.add_argument(
            "functions", nargs='*', choices=self.allowed_functions, help=f"{PROGRAM_NAME} function to run."
        )

        # local = parser.add_argument_group("Local library filters and options")
        # local.add_argument('-q', '--quickload',
        #                    required=False, nargs='?', default=False, const=True,
        #                    help="Skip search/update tags sections of main function. "
        #                         "If set, use last run's data for these sections or enter "
        #                         "a date to define which run to load from.")
        # local.add_argument('-s', '--start',
        #                    type=str, required=False, nargs='*', dest='prefix_start', metavar='',
        #                    help='Start processing from the folder with this prefix i.e. <folder>:<END>')
        # local.add_argument('-e', '--end',
        #                    type=str, required=False, nargs='*', dest='prefix_stop', metavar='',
        #                    help='Stop processing from the folder with this prefix i.e. <START>:<folder>')
        # local.add_argument('-l', '--limit',
        #                    type=str, required=False, nargs='*', dest='prefix_limit', metavar='',
        #                    help="Only process albums that start with this prefix")
        # local.add_argument('-c', '--compilation',
        #                    action='store_const', const=True,
        #                    help="Only process albums that are compilations")
        #
        # spotify = parser.add_argument_group("Spotify metadata extraction options")
        # spotify.add_argument('-ag', '--add-genre',
        #                      action='store_true',
        #                      help="Get genres when extracting track metadata from Spotify")
        # spotify.add_argument('-af', '--add-features',
        #                      action='store_true',
        #                      help="Get audio features when extracting track metadata from Spotify")
        # spotify.add_argument('-aa', '--add-analysis',
        #                      action='store_true',
        #                      help="Get audio analysis when extracting track metadata from Spotify (long runtime)")
        # spotify.add_argument('-ar', '--add-raw',
        #                      action='store_true',
        #                      help="Keep raw API data back when extracting track metadata from Spotify")
        #
        # playlists = parser.add_argument_group("Playlist processing options")
        # playlists.add_argument('-in', '--in-playlists',
        #                        required=False, nargs='*', metavar='',
        #                        help=f"Playlist names to include in any playlist processing")
        # playlists.add_argument('-ex', '--ex-playlists',
        #                        required=False, nargs='*', metavar='',
        #                        help=f"Playlist names to exclude in any playlist processing")
        # playlists.add_argument('-f', '--filter-tags',
        #                        action='store_true',
        #                        help=f"Enable tag filtering from playlists based on values in the config file.")
        # playlists.add_argument('-ce', '--clear-extra',
        #                        action='store_const', dest='clear', default=False, const='extra',
        #                        help="Clear songs not present locally first when updating current Spotify playlists")
        # playlists.add_argument('-ca', '--clear-all',
        #                        action='store_const', dest='clear', default=False, const='all',
        #                        help="Clear all songs first when updating current Spotify playlists")
        #
        # tags = parser.add_argument_group("Local library tag update options")
        # tag_options = list(TagMap.__annotations__.keys()) + ["uri"]
        # tags.add_argument('-t', '--tags',
        #                   required=False, nargs='*', metavar='', choices=tag_options,
        #                   help=f"List of tags to update from Spotify to local files' metadata. "
        #                        f"Allowed values: {', '.join(tag_options)}.")
        # tags.add_argument('-r', '--replace',
        #                   action='store_true',
        #                   help="If set, destructively replace tags when updating local file tags")
        #
        # runtime = parser.add_argument_group("Runtime options")
        # runtime.add_argument('-o', '--no-output',
        #                      action='store_true',
        #                      help="Suppress all JSON file output, apart from files saved to the parent folder "
        #                           "i.e. API token file and URIs.json")
        # runtime.add_argument('-v', '--verbose',
        #                      action='count', default=0,
        #                      help="Add additional stats on library to terminal throughout the run")
        # runtime.add_argument('-x', '--execute',
        #                      action='store_false', dest='dry_run',
        #                      help="Modify users files and playlist. Otherwise, do not affect files "
        #                           "and append '_dry' to data folder path.")

        return parser
