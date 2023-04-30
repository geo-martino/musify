
import argparse
import json
import os
import sys
from ast import literal_eval
from copy import deepcopy
from os.path import basename, dirname, exists, join, normpath, splitext

import yaml

from syncify.local.library import LocalIO
from syncify.spotify.search import Search


def jprint(data):
    print(json.dumps(data, indent=2))


AUTH_ARGS_BASIC = {
    "auth_args": {
        "url": "{base_auth}/api/token",
        "data": {
            "grant_type": "client_credentials",
            "client_id": "{client_id}",
            "client_secret": "{client_secret}",
        },
    },
    "user_args": None,
    "refresh_args": {
        "url": "{base_auth}/api/token",
        "data": {
            "grant_type": "refresh_token",
            "refresh_token": None,
            "client_id": "{client_id}",
            "client_secret": "{client_secret}",
        },
    },
    "test_expiry": 600,
    "token_path": "{token_path}",
    "extra_headers": {"Accept": "application/json", "Content-Type": "application/json"},
}

AUTH_ARGS_USER = {
    "auth_args": {
        "url": "{base_auth}/api/token",
        "data": {
            "grant_type": "authorization_code",
            "code": None,
            "client_id": "{client_id}",
            "client_secret": "{client_secret}",
            "redirect_uri": "http://localhost/",
        },
    },
    "user_args": {
        "url": "{base_auth}/authorize",
        "params": {
            "response_type": "code",
            "client_id": "{client_id}",
            "scope": " ".join(
                [
                    "playlist-modify-public",
                    "playlist-modify-private",
                    "playlist-read-collaborative",
                ]
            ),
            "redirect_uri": "http://localhost/",
            "state": "syncify",
        },
    },
    "refresh_args": {
        "url": "{base_auth}/api/token",
        "data": {
            "grant_type": "refresh_token",
            "refresh_token": None,
            "client_id": "{client_id}",
            "client_secret": "{client_secret}",
        },
    },
    "test_expiry": 600,
    "token_path": "{token_path}",
    "extra_headers": {"Accept": "application/json", "Content-Type": "application/json"},
}

def _update(d, u, overwrite: bool = False):
    for k, v in u.items():
        if isinstance(v, dict) and isinstance(d.get(k, {}), dict):
            d[k] = _update(d.get(k, {}), v)
        elif d.get(k) is None or overwrite:
            d[k] = v
    return d

def _format_dict(data, format_map: dict):
    if isinstance(data, dict):
        for k, v in data.items():
            data[k] = _format_dict(v, format_map)
    elif isinstance(data, str):
        data = data.format_map(format_map)
    return data

class Environment:

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
        "clean_playlists" : {"clean_playlists": []},
        "clean": {"clean_up_env": ['days', 'keep']},
        "sync": {"sync_playlists": ["export_alias", "ext_playlists_path", "ext_path_prefix"]},
        # endpoints
        "create": {"create_playlist": ['playlist_name', 'public', 'collaborative']},
        "get": {"get_data": ['name']},
        "delete": {"delete_playlist": ['playlist']},
        "clear": {"clear_from_playlist": ['playlist']},
    }

    def __init__(self, config_path: str = None):
        
        self._empty_settings =  {
            "_spotify_api": {}, 
            "base_api": None,
            "open_url": None,
            "data_path": None, 
            "music_path": None, 
            "musicbee_path": None, 
            "playlists_path": None, 
            "other_paths": [], 
            "kwargs": {}, 
            "android": {}
            }
        self.cfg_general = {
            "_spotify_api": {
                "base_api": "https://api.spotify.com/v1",
                "base_auth": "https://accounts.spotify.com",
                "open_url": "https://open.spotify.com",
                "token_filename": "token"
            },
            "data_path": join(dirname(dirname(__file__)), "_data")
        }
        
        self.raw_config = self._load_config(config_path)
        self.runtime_settings = None

    def _load_config(self, config_path: str):
        if config_path is None:
            config_path = join(dirname(dirname(__file__)), "config.yml")
        
        check = splitext(config_path.lower())[1]
        if check not in ['.yml', '.yaml'] and check:
            config_path += '.yml'

        if exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.full_load(f)
            return config
        else:
            raise FileNotFoundError(f"Config path invalid: {config_path}")

    def get_kwargs(self):
        function_kwargs = {}
        self.cfg_general = self._update_from_config(self.cfg_general, self.raw_config['general'], 'general')
        
        for func_name, cfg_raw in self.raw_config['functions'].items():
            func_config = self._update_from_config(deepcopy(self.cfg_general), cfg_raw, func_name)
            self._verify(func_config, func_name)
            function_kwargs[func_name] = func_config
        self.runtime_settings = function_kwargs
        return self.runtime_settings

    def _update_from_config(self, cfg_general: dict, cfg_raw: dict, func_name: str) -> dict:
        if not cfg_raw:
            return {}
        cfg_processed = deepcopy(self._empty_settings)

        for setting_key, settings in cfg_raw.items():
            if setting_key == "spotify_api":
                [settings.pop(k) for k, v in settings.copy().items() if v is None]
                api = settings
                if "token_filename" in api:
                    api["token_filename"] = normpath(api["token_filename"])
                cfg_processed["_spotify_api"] = api

            elif setting_key == "paths":
                [settings.pop(k) for k, v in settings.copy().items() if v is None]
                
                paths = {}
                paths["music_path"] = settings.pop(self._platform_map[sys.platform])
                paths["other_paths"] = []
                for k, v in self._platform_map.items():
                    if k != sys.platform and settings.get(v):
                        paths["other_paths"].append(settings.pop(v))
                
                for k, v in settings.items():
                    if isinstance(v, str):
                        split_path = normpath(v.replace("\\", "/")).split("/")
                        paths[k + "_path"] = join(*split_path)
                
                paths["playlists_path"] = join(paths["music_path"], paths["playlists_path"])
                if "musicbee_path" in paths:
                    paths["musicbee_path"] = join(paths["music_path"], paths["musicbee_path"])

                cfg_processed.update(paths)

            elif setting_key == "algorithm":
                [settings.pop(k) for k, v in settings.copy().items() if v is None]
                algo_values = list(Search._settings.keys())
                clamp = lambda n: max(min(max(algo_values), n), -max(algo_values))
                cfg_processed["kwargs"]["algorithm_track"] = clamp(settings.get("track", 3))
                cfg_processed["kwargs"]["algorithm_album"] = clamp(settings.get("album", 2))

            elif setting_key == "playlists":
                cfg_processed["kwargs"]["in_playlists"] = settings.get("include")
                cfg_processed["kwargs"]["ex_playlists"] = settings.get("exclude")
                cfg_processed["kwargs"]["filter_tags"] = settings.get("filter")
                cfg_processed["kwargs"]["clear"] = settings.get("clear")

            elif setting_key == "android":  # remove any settings already defined in general
                [settings.pop(k) for k, v in settings.copy().items() if v is None]
                cfg_processed["android"] = settings

            elif isinstance(settings, dict):  # destructively replace general
                cfg_processed["kwargs"] = _update(cfg_processed["kwargs"] , settings)
        
        general_kwargs = cfg_general.get("kwargs", {})
        cfg_processed["args"] = cfg_raw.get("args")
        cfg_processed["verbose"] = int(cfg_raw.get("verbose", cfg_general.get('verbose', 0)))
        if "output" in cfg_raw:
            cfg_processed["kwargs"]["no_output"] = not cfg_raw["output"]
        else:
            cfg_processed["kwargs"]["no_output"] = general_kwargs.get('no_output', True)
        if "execute" in cfg_raw:
            cfg_processed["kwargs"]["dry_run"] = not cfg_raw["execute"]
        else:
            cfg_processed["kwargs"]["dry_run"] = general_kwargs.get('dry_run', True)

        cfg_processed = _update(cfg_processed, cfg_general, overwrite=False)
        return self._configure(func_name, cfg_processed)

    def _configure(self, func_name: str, cfg_processed: dict) -> None:
        data_path = cfg_processed["data_path"]

        # elevate values to main settings for main Syncify object
        cfg_processed["base_api"] = cfg_processed["_spotify_api"]["base_api"]
        cfg_processed["open_url"] = cfg_processed["_spotify_api"]["open_url"]
        
        # token filename and spotify api settings
        token_filename = cfg_processed["_spotify_api"]["token_filename"]
        if not token_filename.endswith(".json"):
            token_filename += ".json"
        
        cfg_processed["_spotify_api"]["token_path"] = join(data_path, token_filename)
        cfg_processed["spotify_api"] = _format_dict(AUTH_ARGS_USER, cfg_processed["_spotify_api"])

        # quickload
        if cfg_processed.get("kwargs", {}).get("quickload"):
            quickload = cfg_processed["kwargs"]["quickload"]
            last_runs = sorted([basename(rd[0]) for rd in os.walk(data_path)][1:])
            if isinstance(quickload, str):
                quickload = [r for r in last_runs if r.startswith(quickload)]
                quickload = False if len(quickload) == 0 else quickload[0]
            elif quickload and len(last_runs) > 0:
                quickload = last_runs[-1]
            else:
                quickload = False
            cfg_processed["kwargs"]["quickload"] = quickload
        
        cfg_processed["kwargs"]["compilation_check"] = not cfg_processed["kwargs"].get("compilation")
        
        cfg_processed = self._parse_args(func_name, cfg_processed)
        return cfg_processed

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

    def _verify(self, cfg_processed: dict, func_name: str) -> None:
        mandatory_api_keys = ['client_id', 'client_secret']
        if any(m not in cfg_processed["_spotify_api"] for m in mandatory_api_keys):
            raise RuntimeError(f"{func_name} | You must define {mandatory_api_keys} in the 'spotify_api' key")
        elif cfg_processed["music_path"] is None:
            key = self._platform_map[sys.platform].replace('_path', '')
            raise RuntimeError(f"{func_name} | You must define a '{key}' path in the 'paths' key for this OS")
        elif 'playlists_path' not in cfg_processed:
            raise RuntimeError(f"{func_name} | You must define a 'playlists' path in the 'paths' key")

    def parse_from_bash(self):
        parser = self.get_parser()
        parsed = parser.parse_known_args()
        kwargs = vars(parsed[0])
        args = parsed[1]
        func_name = kwargs.pop('function')

        if kwargs.pop('use_config'):
            if func_name in self.runtime_settings or func_name in self._functions:
                self.runtime_settings = {func_name: self.runtime_settings.get(func_name, self.cfg_general)}
                if len(args) > 0:
                    self.runtime_settings[func_name]["args"] = args
                    self.runtime_settings[func_name] = self._parse_args(func_name,  self.runtime_settings[func_name])
            
            return self.runtime_settings
        if kwargs['filter_tags']:
            del kwargs['filter_tags']
        
        cfg_processed = {"kwargs": kwargs, "args": args}
        cfg_processed = _update(deepcopy(self.cfg_general), cfg_processed)

        _update(self.runtime_settings[func_name], cfg_processed)
        self.runtime_settings = self._configure(func_name, self.runtime_settings[func_name])
        return self.runtime_settings


    def get_parser(self):
        parser = argparse.ArgumentParser(
        description="Sync your local library to Spotify.", prog="syncify",
        usage='%(prog)s [function] [options]')
        parser._positionals.title = 'Functions'
        parser._optionals.title = 'Optional arguments'

        # cli function aliases and expected args in order user should give them
        parser.add_argument('-cfg', '--use-config', action='store_true',
                            help=f"Use saved config in config.yml instead of cli settings.")
        parser.add_argument('function', nargs='?', choices=list(self._functions.keys()),
                            help=f"Syncify function to run.")


        local = parser.add_argument_group("Local library filters and options")
        local.add_argument('-q', '--quickload', required=False, nargs='?', default=False, const=True,
                        help="Skip search/update tags sections of main function. If set, use last run's data for these sections or enter a date to define which run to load from.")
        local.add_argument('-s', '--start', type=str, required=False, nargs='*', dest='prefix_start', metavar='',
                        help='Start processing from the folder with this prefix i.e. <folder>:<END>')
        local.add_argument('-e', '--end', type=str, required=False, nargs='*', dest='prefix_stop', metavar='',
                        help='Stop processing from the folder with this prefix i.e. <START>:<folder>')
        local.add_argument('-l', '--limit', type=str, required=False, nargs='*', dest='prefix_limit', metavar='',
                        help="Only process albums that start with this prefix")
        local.add_argument('-c', '--compilation', action='store_const', const=True,
                        help="Only process albums that are compilations")

        spotify = parser.add_argument_group("Spotify metadata extraction options")
        spotify.add_argument('-ag', '--add-genre', action='store_true',
                            help="Get genres when extracting track metadata from Spotify")
        spotify.add_argument('-af', '--add-features', action='store_true',
                            help="Get audio features when extracting track metadata from Spotify")
        spotify.add_argument('-aa', '--add-analysis', action='store_true',
                            help="Get audio analysis when extracting track metadata from Spotify (long runtime)")
        spotify.add_argument('-ar', '--add-raw', action='store_true',
                            help="Keep raw API data back when extracting track metadata from Spotify")

        playlists = parser.add_argument_group("Playlist processing options")
        playlists.add_argument('-in', '--in-playlists', required=False, nargs='*', metavar='',
                            help=f"Playlist names to include in any playlist processing")
        playlists.add_argument('-ex', '--ex-playlists', required=False, nargs='*', metavar='',
                            help=f"Playlist names to exclude in any playlist processing")
        playlists.add_argument('-f', '--filter-tags', action='store_true',
                            help=f"Enable tag filtering from playlists based on values in the config file.")
        playlists.add_argument('-ce', '--clear-extra', action='store_const', dest='clear', default=False, const='extra',
                            help="Clear songs not present locally first when updating current Spotify playlists")
        playlists.add_argument('-ca', '--clear-all', action='store_const', dest='clear', default=False, const='all',
                            help="Clear all songs first when updating current Spotify playlists")

        tags = parser.add_argument_group("Local library tag update options")
        tag_options = list(LocalIO._tag_ids['.flac'].keys()) + ["uri"]
        tags.add_argument('-t', '--tags', required=False, nargs='*', metavar='',
                        choices=tag_options,
                        help=f"List of tags to update from Spotify to local files' metadata. Allowed values: {', '.join(tag_options)}.")
        tags.add_argument('-r', '--replace', action='store_true',
                        help="If set, destructively replace tags when updating local file tags")

        runtime = parser.add_argument_group("Runtime options")
        runtime.add_argument('-o', '--no-output', action='store_true',
                            help="Suppress all json file output, apart from files saved to the parent folder i.e. API token file and URIs.json")
        runtime.add_argument('-v', '--verbose', action='count', default=0,
                            help="Add additional stats on library to terminal throughout the run")
        runtime.add_argument('-x', '--execute', action='store_false', dest='dry_run',
                            help="Modify users files and playlist. Otherwise, do not affect files and append '_dry' to data folder path.")

        return parser
