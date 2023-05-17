import argparse
import json
import os
import sys
from abc import ABCMeta, abstractmethod
from ast import literal_eval
from copy import deepcopy
from datetime import datetime
from os.path import dirname, exists, join, splitext, isabs
from typing import Any, MutableMapping, List

import yaml

from syncify.local.track import TagMap
from syncify.spotify.api.api import AUTH_ARGS_BASIC, AUTH_ARGS_USER
from syncify.spotify.processor.search import AlgorithmSettings
from syncify.utils.logger import Logger


def _update_map(source: MutableMapping, new: MutableMapping, extend: bool = True, overwrite: bool = False):
    for k, v in new.items():
        if isinstance(v, dict) and isinstance(source.get(k, {}), dict):
            source[k] = _update_map(source.get(k, {}), v)
        elif extend and isinstance(v, list) and isinstance(source.get(k, []), list):
            source[k] = v + source.get(k, [])
        elif overwrite or source.get(k) is None:
            source[k] = v
    return source


def _format_map(data, format_map: dict):
    if isinstance(data, dict):
        for k, v in data.items():
            data[k] = _format_map(v, format_map)
    elif isinstance(data, str):
        data = data.format_map(format_map)
    return data


class Settings(metaclass=ABCMeta):
    _platform_map = {"win32": "win", "linux": "lin", "darwin": "mac"}
    _functions = {
        "main": {"main": []},
        "auth": {"auth": []},
        # individual main steps
        'search': {'search': []},
        'check': {'check': []},
        'update_tags': {'update_tags': []},
        'update_spotify': {'update_spotify': []},
        # reports/maintenance/utilities
        'report': {'report': []},
        'missing_tags': {'missing_tags': ["match"]},
        'backup': {'backup': []},
        'restore': {'restore': ['kind', 'mod']},
        'extract': {'extract': ['kind', 'playlists']},
        "clean_playlists": {"clean_playlists": []},
        "clean": {"clean_up_env": ['days', 'keep']},
        "sync": {"sync_playlists": ["export_alias", "ext_playlists_path", "ext_path_prefix"]},
        # endpoints
        "create": {"create_playlist": ['playlist_name', 'public', 'collaborative']},
        "get": {"get_data": ['name']},
        "delete": {"delete_playlist": ['playlist']},
        "clear": {"clear_from_playlist": ['playlist']},
    }

    @property
    @abstractmethod
    def allowed_functions(self) -> List[str]:
        raise NotImplementedError

    def __init__(self, config_path: str = "config.yml"):
        self.run_dt = datetime.now()
        self.module_folder = dirname(dirname(__file__))
        config_path = self._append_module_folder(config_path)

        self.cfg = self._load_config(config_path)
        self.cfg_general = deepcopy(self.cfg.get("general", {}))
        self.cfg_functions = deepcopy(self.cfg.get("functions", {}))

        self.cfg_logging = self.cfg_general.pop("logging", {})
        self.cfg_output = self.cfg_general.pop("output", {})

        self.dry_run = self.cfg_general.get("dry_run", True)
        self.output_folder = None

        self.functions: List[str] = [self.allowed_functions[0]]

        self.set_env()

    def _append_module_folder(self, path: str) -> str:
        if not isabs(path):
            path = join(self.module_folder, path)
        return path

    @staticmethod
    def _load_config(config_path: str) -> MutableMapping[Any, Any]:
        if splitext(config_path)[1].lower() not in ['.yml', '.yaml']:
            raise ValueError(f"Unrecognised file type: {config_path}")
        elif not exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, 'r') as f:
            config = yaml.full_load(f)
        return config

    ###########################################################################
    ## Wrangle general settings
    ###########################################################################
    def set_logger(self):
        log_folder = self._append_module_folder(self.cfg_logging.get("path", "_logs"))
        Logger.set_log_folder(log_folder, run_dt=self.run_dt)

        verbosity = self.cfg_logging.get("verbosity", 0)
        Logger.set_verbosity(verbosity)

    def set_output(self):
        parent_folder = self._append_module_folder(self.cfg_output.get("path", "_data"))
        self.output_folder = join(parent_folder, self.run_dt.strftime(Logger.dt_format))
        if not exists(self.output_folder):
            os.makedirs(self.output_folder)

    ###########################################################################
    ## Wrangle local settings
    ###########################################################################
    def set_platform_paths(self) -> None:
        for cfg in [self.cfg_general] + list(self.cfg_functions.values()):
            paths = cfg.get("local", {}).get("paths", {})
            if not paths:
                continue

            paths["library"] = paths.pop(f"library_{self._platform_map[sys.platform]}", None)
            if not paths["library"]:
                raise KeyError(f"No library path given for this platform: {sys.platform}")

            paths["other"] = []
            for key in paths.copy():
                if key.startswith("library_"):
                    paths["other"].append(paths.pop(key))

    def set_search_algorithm(self) -> None:
        settings = list(AlgorithmSettings.__annotations__.keys())

        for cfg in [self.cfg_general] + list(self.cfg_functions.values()):
            search = cfg.get("spotify", {}).get("search", {})
            algorithm = search.get("algorithm")
            if algorithm is None:
                continue
            if algorithm.upper().strip() not in settings:
                raise ValueError(f"'{algorithm}' search algorithm is invalid, use one of the following algorithms: " +
                                 ', '.join(settings))
            search["algorithm"] = getattr(AlgorithmSettings, algorithm.strip().upper())

    ###########################################################################
    ## Wrangle Spotify settings
    ###########################################################################
    def set_api_settings(self) -> None:
        for cfg in [self.cfg_general] + list(self.cfg_functions.values()):
            settings = cfg.get("spotify", {}).get("api", {})
            if not settings:
                continue

            template = AUTH_ARGS_USER if settings.get("user_auth", False) else AUTH_ARGS_BASIC
            token_file_path = settings.pop("token_file_path", "token.json")
            if not isabs(token_file_path):
                token_file_path = join(dirname(self.output_folder), token_file_path)

            format_map = {
                "client_id": settings.pop("client_id"),
                "client_secret": settings.pop("client_secret"),
                "token_file_path": token_file_path,
                "scopes": " ".join(settings.pop("scopes", [])),
            }

            _format_map(template, format_map=format_map)
            settings["settings"] = template

    ###########################################################################
    ## Finalise
    ###########################################################################
    def merge_general_to_functions(self) -> None:
        if not self.cfg_general or not self.cfg_functions:
            return

        for cfg in self.cfg_functions.values():
            _update_map(cfg, self.cfg_general, extend=True, overwrite=False)

    def set_env(self):
        self.set_output()
        self.set_logger()
        self.set_platform_paths()
        self.set_search_algorithm()
        self.set_api_settings()
        self.merge_general_to_functions()

    ###########################################################################
    ## Parse prompt args
    ###########################################################################
    def _parse_args(self, func_name: str, cfg_processed: dict):
        # parse function specific arguments
        if func_name in self._functions and cfg_processed["args"]:
            func_args = list(self._functions[func_name].values())[0]
            for k, v in zip(func_args, cfg_processed["args"]):
                try:
                    cfg_processed["kwargs"][k] = literal_eval(v)
                except (ValueError, SyntaxError):
                    cfg_processed["kwargs"][k] = v
        elif func_name not in self._functions and func_name != 'general':
            raise NotImplementedError(f"Function name '{func_name}' not recognised")
        cfg_processed.pop("args")
        return cfg_processed

    def parse_from_prompt(self):
        parser = self.get_parser()
        parsed = parser.parse_known_args()
        kwargs = vars(parsed[0])
        args = parsed[1]
        self.functions = kwargs.pop('functions')

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

    # noinspection PyProtectedMember
    def get_parser(self):
        parser = argparse.ArgumentParser(description="Sync your local library to Spotify.",
                                         prog="syncify",
                                         usage='%(prog)s [options] [function]')
        parser._positionals.title = 'Functions'
        parser._optionals.title = 'Optional arguments'

        # cli function aliases and expected args in order user should give them
        parser.add_argument('-cfg', '--use-config',
                            action='store_true',
                            help=f"Use saved config in config.yml instead of cli settings.")
        parser.add_argument('functions',
                            nargs='*', choices=self.allowed_functions,
                            help=f"Syncify function to run.")

        local = parser.add_argument_group("Local library filters and options")
        local.add_argument('-q', '--quickload',
                           required=False, nargs='?', default=False, const=True,
                           help="Skip search/update tags sections of main function. "
                                "If set, use last run's data for these sections or enter "
                                "a date to define which run to load from.")
        local.add_argument('-s', '--start',
                           type=str, required=False, nargs='*', dest='prefix_start', metavar='',
                           help='Start processing from the folder with this prefix i.e. <folder>:<END>')
        local.add_argument('-e', '--end',
                           type=str, required=False, nargs='*', dest='prefix_stop', metavar='',
                           help='Stop processing from the folder with this prefix i.e. <START>:<folder>')
        local.add_argument('-l', '--limit',
                           type=str, required=False, nargs='*', dest='prefix_limit', metavar='',
                           help="Only process albums that start with this prefix")
        local.add_argument('-c', '--compilation',
                           action='store_const', const=True,
                           help="Only process albums that are compilations")

        spotify = parser.add_argument_group("Spotify metadata extraction options")
        spotify.add_argument('-ag', '--add-genre',
                             action='store_true',
                             help="Get genres when extracting track metadata from Spotify")
        spotify.add_argument('-af', '--add-features',
                             action='store_true',
                             help="Get audio features when extracting track metadata from Spotify")
        spotify.add_argument('-aa', '--add-analysis',
                             action='store_true',
                             help="Get audio analysis when extracting track metadata from Spotify (long runtime)")
        spotify.add_argument('-ar', '--add-raw',
                             action='store_true',
                             help="Keep raw API data back when extracting track metadata from Spotify")

        playlists = parser.add_argument_group("Playlist processing options")
        playlists.add_argument('-in', '--in-playlists',
                               required=False, nargs='*', metavar='',
                               help=f"Playlist names to include in any playlist processing")
        playlists.add_argument('-ex', '--ex-playlists',
                               required=False, nargs='*', metavar='',
                               help=f"Playlist names to exclude in any playlist processing")
        playlists.add_argument('-f', '--filter-tags',
                               action='store_true',
                               help=f"Enable tag filtering from playlists based on values in the config file.")
        playlists.add_argument('-ce', '--clear-extra',
                               action='store_const', dest='clear', default=False, const='extra',
                               help="Clear songs not present locally first when updating current Spotify playlists")
        playlists.add_argument('-ca', '--clear-all',
                               action='store_const', dest='clear', default=False, const='all',
                               help="Clear all songs first when updating current Spotify playlists")

        tags = parser.add_argument_group("Local library tag update options")
        tag_options = list(TagMap.__annotations__.keys()) + ["uri"]
        tags.add_argument('-t', '--tags',
                          required=False, nargs='*', metavar='', choices=tag_options,
                          help=f"List of tags to update from Spotify to local files' metadata. "
                               f"Allowed values: {', '.join(tag_options)}.")
        tags.add_argument('-r', '--replace',
                          action='store_true',
                          help="If set, destructively replace tags when updating local file tags")

        runtime = parser.add_argument_group("Runtime options")
        runtime.add_argument('-o', '--no-output',
                             action='store_true',
                             help="Suppress all json file output, apart from files saved to the parent folder "
                                  "i.e. API token file and URIs.json")
        runtime.add_argument('-v', '--verbose',
                             action='count', default=0,
                             help="Add additional stats on library to terminal throughout the run")
        runtime.add_argument('-x', '--execute',
                             action='store_false', dest='dry_run',
                             help="Modify users files and playlist. Otherwise, do not affect files "
                                  "and append '_dry' to data folder path.")

        return parser


if __name__ == "__main__":
    env = Settings()
    print(env.get_parser().print_help())
    env.cfg_general["spotify"]["api"]["settings"].pop('test_condition')
    print(json.dumps(env.cfg_general, indent=2))
    print(json.dumps(env.cfg_functions["main"], indent=2))
