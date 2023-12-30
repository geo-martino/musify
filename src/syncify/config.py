from __future__ import annotations

import base64
import os
import sys
from abc import ABC, abstractmethod
from collections.abc import Mapping, Generator
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from os.path import isabs, join, dirname, splitext, exists
from typing import Any, Self, get_args

import yaml

from syncify.abstract.enums import TagField
from syncify.abstract.misc import PrettyPrinter
from syncify.abstract.object import Library
from syncify.exception import ConfigError
from syncify.fields import LocalTrackField
from syncify.local.exception import InvalidFileType
from syncify.local.library import MusicBee, LocalLibrary
from syncify.remote.api import RemoteAPI
from syncify.remote.library import RemoteObject
from syncify.remote.library.library import RemoteLibrary
from syncify.remote.library.object import PLAYLIST_SYNC_KINDS
from syncify.remote.processors.check import RemoteItemChecker, ALLOW_KARAOKE_DEFAULT
from syncify.remote.processors.search import RemoteItemSearcher
from syncify.remote.processors.wrangle import RemoteDataWrangler
from syncify.spotify import SPOTIFY_SOURCE_NAME
from syncify.spotify.api import SpotifyAPI, SPOTIFY_API_AUTH_USER, SPOTIFY_API_AUTH_BASIC
from syncify.spotify.library import SpotifyObject
from syncify.spotify.library.library import SpotifyLibrary
from syncify.spotify.processors.processors import SpotifyItemChecker, SpotifyItemSearcher
from syncify.spotify.processors.wrangle import SpotifyDataWrangler
from syncify.utils.helpers import to_collection, safe_format_map
from syncify.utils.logger import LOGGING_DT_FORMAT


@dataclass
class RemoteClasses:
    """Stores the key classes for a remote source"""
    name: str
    api: type[RemoteAPI]
    wrangler: type[RemoteDataWrangler]
    object: type[RemoteObject]
    library: type[RemoteLibrary]
    checker: type[RemoteItemChecker]
    searcher: type[RemoteItemSearcher]


# map of the names of all supported remote sources and their associated implementations
REMOTE_CONFIG: Mapping[str, RemoteClasses] = {
    SPOTIFY_SOURCE_NAME: RemoteClasses(
        name=SPOTIFY_SOURCE_NAME,
        api=SpotifyAPI,
        wrangler=SpotifyDataWrangler,
        object=SpotifyObject,
        library=SpotifyLibrary,
        checker=SpotifyItemChecker,
        searcher=SpotifyItemSearcher,
    )
}


def _get_local_track_tags(tags: Any) -> tuple[LocalTrackField, ...]:
    values = to_collection(tags, tuple)
    return tuple(LocalTrackField.from_name(*values) if values else LocalTrackField.all())


class Config(PrettyPrinter):
    """
    Set up config and provide framework for initialising various objects
    needed for the main functionality of the program from a given config file at ``path``.

    The following options are in place for configuration values:

    - `DEFAULT`: When a value is not found, a default value will be used.
    - `REQUIRED`: The configuration will fail if this value is not given. Only applies when the key is called.
    - `OPTIONAL`: This value does not need to be set and ``None`` will be set when this is the case.
        The configuration will not fail if this value is not given.

    Sub-configs have ``override`` parameter that can be set using ``override`` key in initial config block.
    When override is True and ``config`` given, override loaded config from the file with
    values in ``config`` only using loaded values when values are not present in given ``config``.
    When override is False, loaded config takes priority and given ``config`` values are only used
    when values are not present in the file.

    :param name: Name of this config.
        Used as the parent key to use to pull the required configuration from the config file.
    :param path: Path of the config file to use.
    :param config: When given, use values from this config. Priority is set by ``force_new``.
        The following values are always overriden and ignore any ``override`` setting:
        - ``start_time`` i.e. the time at which the config was instantiated.
        - ``module_folder``
    """

    def __init__(self, name: str = "general", path: str = "config.yml", config: Self | None = None):
        self.start_time = config.start_time if config else datetime.now()
        self._package_root = config.package_root if config else dirname(dirname(dirname(__file__)))
        self.config_path = self._make_path_absolute(path)
        self._cfg = self._load_config(name)
        override = self._cfg.get("override", False)

        self._output_folder: str | None = config.output_folder if config and override else None
        self._dry_run: bool | None = config.dry_run if config and override else None

        self.local: dict[str, ConfigLocal] = {}
        for name, settings in self._cfg.get("local", {}).items():
            local_config = config.local.get(name) if config else None

            match settings["kind"]:
                case "musicbee":
                    library = ConfigMusicBee(file=settings, config=local_config, override=override)
                case _:
                    library = ConfigLocal(file=settings, config=local_config, override=override)

            self.local[name] = library

        self.remote: dict[str, ConfigRemote] = {}
        for name, settings in self._cfg.get("remote", {}).items():
            remote_config = config.remote.get(name) if config else None
            library = ConfigRemote(file=settings, config=remote_config, override=override)

            if not exists(library.api.token_path) and not isabs(library.api.token_path):
                # noinspection PyProtectedMember
                assert library.api._api is None  # ensure api has not already been instantiated
                library.api._token_path = join(dirname(self.output_folder), library.api.token_path)

            self.remote[name] = library

        # operation specific settings
        self.filter = ConfigFilter(file=self._cfg, config=config.filter if config else None, override=override)
        self.pause_message = self._cfg.get("message")
        self.reports = ConfigReports(file=self._cfg, config=self)

    def _make_path_absolute(self, path: str) -> str:
        """Append the package root to any relative path to make it an absolute path. Do nothing if path is absolute."""
        if not isabs(path):
            path = join(self._package_root, path)
        return path

    def _load_config(self, name: str) -> dict[Any, Any]:
        """
        Load the config file

        :return: The config file.
        :raise InvalidFileType: When the given config file is not of the correct type.
        """
        if splitext(self.config_path)[1].casefold() not in [".yml", ".yaml"]:
            raise InvalidFileType(f"Unrecognised file type: {self.config_path}")
        elif not exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as file:
            config = yaml.full_load(file)
        if name not in config:
            raise ConfigError("Unrecognised config name: {key} | Available: {value}", key=name, value=config)

        return config[name]

    ###########################################################################
    ## General
    ###########################################################################
    @property
    def output_folder(self) -> str:
        """`DEFAULT` | The output folder for saving diagnostic data"""
        if self._output_folder is not None:
            return self._output_folder

        parent_folder = self._make_path_absolute(self._cfg.get("output", "_data"))
        self._output_folder = join(parent_folder, self.start_time.strftime(LOGGING_DT_FORMAT))
        os.makedirs(self._output_folder, exist_ok=True)
        return self._output_folder

    @property
    def dry_run(self) -> bool:
        """`DEFAULT` | Whether this run is a dry run i.e. don't write out where possible"""
        if self._dry_run is not None:
            return self._dry_run

        self._dry_run = self._cfg.get("dry_run", True)
        return self._dry_run

    def as_dict(self) -> dict[str, Any]:
        return {
            "start_time": self.start_time,
            "config_path": self.config_path,
            "output_folder": self.output_folder,
            "dry_run": self.dry_run,
            "local": {name: config for name, config in self.local.items()},
            "remote": {name: config for name, config in self.remote.items()},
            "filter": self.filter,
            "pause_message": self.pause_message,
            "reports": self.reports,
        }


###########################################################################
## Shared
###########################################################################
class ConfigLibrary(PrettyPrinter, ABC):
    """Set the settings for a library from a config file and terminal arguments."""
    @property
    @abstractmethod
    def library(self) -> Library:
        """An initialised library"""
        raise NotImplementedError

    def as_dict(self) -> dict[str, Any]:
        return {"library": self.library}


class ConfigPlaylists(PrettyPrinter):
    """
    Set the settings for the playlists from a config file and terminal arguments.
    See :py:class:`Config` for more documentation regarding initialisation and operation.

    :param file: The loaded config from the config file.
    """

    def __init__(self, file: dict[Any, Any], config: Self | None = None, override: bool = False):
        self._cfg = file.get("playlists", {})

        self._include: tuple[str] | None = config.include if config and override else None
        self._exclude: tuple[str] | None = config.exclude if config and override else None
        self._filter: dict[str, tuple[str]] | None = config.filter if config and override else None

    @property
    def include(self) -> tuple[str]:
        """`OPTIONAL` | The playlists to include when loading the remote library."""
        if self._include is not None:
            return self._include
        self._include = to_collection(self._cfg.get("include"), tuple) or ()
        return self._include

    @property
    def exclude(self) -> tuple[str]:
        """`OPTIONAL` | The playlists to exclude when loading the remote library."""
        if self._exclude is not None:
            return self._exclude
        self._exclude = to_collection(self._cfg.get("exclude"), tuple) or ()
        return self._exclude

    @property
    def filter(self) -> dict[str, tuple[str]]:
        """`OPTIONAL` | Tags and values of items to filter out of every playlist when loading"""
        if self._filter is not None:
            return self._filter

        self._filter = {}
        for tag, values in self._cfg.get("filter", {}).items():
            if tag not in TagField.__tags__ or not values:
                continue
            self._filter[tag] = to_collection(values, tuple)

        return self._filter

    def as_dict(self) -> dict[str, Any]:
        return {
            "include": self.include,
            "exclude": self.exclude,
            "filter": self.filter,
        }


class ConfigFilter(PrettyPrinter):
    """
    Set the settings for granular filtering from a config file and terminal arguments.
    See :py:class:`Config` for more documentation regarding initialisation and operation.

    :param file: The loaded config from the config file.
    """

    def __init__(self, file: dict[Any, Any], config: Self | None = None, override: bool = False):
        self._cfg = file.get("filter", {})

        self.include = config.include if config and override else None
        if not self.include:
            self.include = self.ConfigFilterOptions(
                name="include", file=self._cfg, config=config.include if config else None, override=override
            )

        self.exclude = config.exclude if config and override else None
        if not self.exclude:
            self.exclude = self.ConfigFilterOptions(
                name="exclude", file=self._cfg, config=config.exclude if config else None, override=override
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "include": self.include,
            "exclude": self.exclude,
        }

    class ConfigFilterOptions(PrettyPrinter):
        """
        Set the settings for filter options from a config file and terminal arguments.
        See :py:class:`Config` for more documentation regarding initialisation and operation.

        :param name: The key to load filter options for.
            Used as the parent key to use to pull the required configuration from the config file.
        :param file: The loaded config from the config file.
        """

        def __init__(self, name: str, file: dict[Any, Any], config: Self | None = None, override: bool = False):
            self._cfg = file.get(name, {})

            self._prefix: str | None = config.prefix if config and override else None
            self._start: str | None = config.start if config and override else None
            self._stop: str | None = config.stop if config and override else None

        @property
        def prefix(self) -> str | None:
            """`OPTIONAL` | The prefix of the items to match on."""
            if self._prefix is not None:
                return self._prefix
            self._prefix = self._cfg.get("prefix")
            return self._prefix

        @property
        def start(self) -> str | None:
            """`OPTIONAL` | The exact name for the first item to match on."""
            if self._start is not None:
                return self._start
            self._start = self._cfg.get("start")
            return self._start

        @property
        def stop(self) -> str | None:
            """`OPTIONAL` | The exact name for the last item to match on."""
            if self._stop is not None:
                return self._stop

            self._stop = self._cfg.get("stop")
            return self._stop

        def as_dict(self) -> dict[str, Any]:
            return {
                "prefix": self.prefix,
                "start": self.start,
                "stop": self.stop,
            }


class ConfigReports(PrettyPrinter):
    """
    Set the settings for all reports from a config file and terminal arguments.
    See :py:class:`Config` for more documentation regarding initialisation and operation.

    :param file: The loaded config from the config file.
    """
    def __init__(self, file: dict[Any, Any], config: Config):
        self._cfg = file.get("reports", {})

        self.library_differences = self.ConfigLibraryDifferences(file=self._cfg, config=config)
        self.missing_tags = self.ConfigMissingTags(file=self._cfg, config=config)

        self.all = (self.library_differences, self.missing_tags)

    def __iter__(self) -> Generator[[ConfigReportBase], None, None]:
        return (report for report in self.all)

    def as_dict(self) -> dict[str, Any]:
        return {report.name: report for report in self.all}

    class ConfigReportBase(PrettyPrinter):
        """
        Base class for settings reports settings.

        :param file: The loaded config from the config file.
        """
        def __init__(self, name: str, file: dict[Any, Any]):
            self._cfg = file.get(name, {})
            self.name = name
            self.enabled = self._cfg.get("enabled", True)

        def as_dict(self) -> dict[str, Any]:
            return {"enabled": self.enabled}

    class ConfigLibraryDifferences(ConfigReportBase):
        """
        Set the settings for the library differences report from a config file and terminal arguments.

        :param file: The loaded config from the config file.
        :param config: The fully processed :py:class:`Config` to apply settings from.
        """
        def __init__(self, file: dict[Any, Any], config: Config):
            super().__init__(name="library_differences", file=file)

            source = self._cfg.get("source")
            self.source: Library | None = None
            if not source:
                pass
            elif source in config.remote:
                self.source = config.remote[source].library
            elif source in config.local:
                self.source = config.local[source].library

            reference = self._cfg.get("reference")
            self.reference: Library | None = None
            if not reference:
                pass
            elif reference in config.remote:
                self.reference = config.remote[source].library
            elif reference in config.local:
                self.reference = config.local[source].library

        def as_dict(self) -> dict[str, Any]:
            return super().as_dict() | {
                "source": self.source if self.source else None,
                "reference": self.reference if self.reference else None,
            }

    class ConfigMissingTags(ConfigReportBase):
        """
        Set the settings for the missing tags report from a config file and terminal arguments.

        :param file: The loaded config from the config file.
        :param config: The fully processed :py:class:`Config` to apply settings from.
        """

        def __init__(self, file: dict[Any, Any], config: Config):
            super().__init__(name="missing_tags", file=file)

            source = self._cfg.get("source")
            self.source: Library | None = config.local[source].library if source in config.local else None
            self.tags = _get_local_track_tags(self._cfg.get("tags"))
            self.match_all = self._cfg.get("match_all", True)

        def as_dict(self) -> dict[str, Any]:
            return super().as_dict() | {
                "source": self.source if self.source else None,
                "tags": [t for tag in self.tags for t in tag.to_tag()],
                "match_all": self.match_all,
            }


###########################################################################
## Local
###########################################################################
class ConfigLocal(ConfigLibrary):
    """
    Set the settings for the local functionality of the program from a config file and terminal arguments.
    See :py:class:`Config` for more documentation regarding initialisation and operation.

    :param file: The loaded config from the config file.
    """

    @property
    def _platform_key(self) -> str:
        platform_map = {"win32": "win", "linux": "lin", "darwin": "mac"}
        return platform_map[sys.platform]

    def __init__(self, file: dict[Any, Any], config: Self | None = None, override: bool = False):
        self._cfg = file

        self._library_folder: str | None = config.library_folder if config and override else None
        self._playlist_folder: str | None = config.playlist_folder if config and override else None
        self._other_folders: tuple[str] | None = config.other_folders if config and override else None

        valid_library = config and isinstance(config.library, LocalLibrary)
        self._library = config.library if override and valid_library else None

        self.playlists: ConfigPlaylists = config.playlists if config and override else None
        if not self.playlists:
            self.playlists = ConfigPlaylists(
                file=self._cfg, config=config.playlists if config else None, override=override
            )

        self.update = config.update if config and override else None
        if not self.update:
            self.update = self.ConfigUpdateTags(
                file=self._cfg, config=config.update if config else None, override=override
            )

    @property
    def library(self) -> LocalLibrary:
        if self._library is not None and isinstance(self._library, LocalLibrary):
            return self._library

        self._library = LocalLibrary(
            library_folder=self.library_folder,
            playlist_folder=self.playlist_folder,
            other_folders=self.other_folders,
            include=self.playlists.include,
            exclude=self.playlists.exclude,
        )
        return self._library

    @property
    def _cfg_paths(self) -> dict[Any, Any]:
        return self._cfg.get("paths", {})

    @property
    def library_folder(self) -> str:
        """`REQUIRED` | The path of the local library folder"""
        if self._library_folder is not None:
            return self._library_folder

        if isinstance(self._cfg_paths.get("library"), str):
            self._library_folder = self._cfg_paths["library"]
            return self._library_folder
        elif not isinstance(self._cfg_paths.get("library"), dict):
            raise ConfigError("Config not found", key=["local", "paths", "library"], value=self._cfg_paths)

        # assume platform sub-keys
        value = self._cfg_paths["library"].get(self._platform_key)
        if not value:
            raise ConfigError(
                "Library folder for the current platform not given",
                key=["local", "paths", "library", self._platform_key],
                value=self._cfg_paths["library"]
            )

        self._library_folder = value
        return self._library_folder

    @property
    def playlist_folder(self) -> str | None:
        """`OPTIONAL` | The path of the playlist folder."""
        if self._playlist_folder is not None:
            return self._playlist_folder
        self._playlist_folder = self._cfg_paths.get("playlists")
        return self._playlist_folder

    @property
    def other_folders(self) -> tuple[str]:
        """`OPTIONAL` | The paths of other folder to use for replacement when processing local libraries"""
        if self._other_folders is not None:
            return self._other_folders
        self._other_folders = to_collection(self._cfg_paths.get("other"), tuple) or ()
        return self._other_folders

    def as_dict(self) -> dict[str, Any]:
        return {
            "library_folder": self.library_folder,
            "playlist_folder": self.playlist_folder,
            "other_folders": self.other_folders,
            "playlists": self.playlists,
            "update": self.update,
        } | super().as_dict()

    class ConfigUpdateTags(PrettyPrinter):
        """
        Set the settings for the playlists from a config file and terminal arguments.
        See :py:class:`Config` for more documentation regarding initialisation and operation.

        :param file: The loaded config from the config file.
        """

        def __init__(self, file: dict[Any, Any], config: Self | None = None, override: bool = False):
            self._cfg = file.get("update", {})
            self._tags: tuple[LocalTrackField, ...] | None = config.tags if config and override else None
            self._replace: bool | None = config.replace if config and override else None

        @property
        def tags(self) -> tuple[LocalTrackField, ...]:
            """`OPTIONAL` | The tags to be updated."""
            if self._tags is not None:
                return self._tags
            self._tags = _get_local_track_tags(self._cfg.get("tags"))
            return self._tags

        @property
        def replace(self) -> bool:
            """`OPTIONAL` | Destructively replace tags in each file."""
            if self._replace is not None:
                return self._replace
            self._replace = self._cfg.get("replace")
            return self._replace

        def as_dict(self) -> dict[str, Any]:
            return {
                "tags": [t for tag in self.tags for t in tag.to_tag()],
                "replace": self.replace,
            }


class ConfigMusicBee(ConfigLocal):
    def __init__(self, file: dict[Any, Any], config: Self | None = None, override: bool = False):
        super().__init__(file=file, config=config, override=override)

        self._musicbee_folder: str | None = config.musicbee_folder if config and override else None

        valid_library = config and isinstance(config.library, MusicBee)
        self._library = config.library if override and valid_library else None

    @property
    def library(self) -> LocalLibrary:
        if self._library is not None and isinstance(self._library, MusicBee):
            return self._library

        self._library = MusicBee(
            musicbee_folder=self.musicbee_folder,
            library_folder=self.library_folder,
            playlist_folder=self.playlist_folder,
            other_folders=self.other_folders,
            include=self.playlists.include,
            exclude=self.playlists.exclude,
        )
        return self._library

    @property
    def musicbee_folder(self) -> str | None:
        """`OPTIONAL` | The path of the MusicBee library folder."""
        if self._musicbee_folder is not None:
            return self._musicbee_folder
        self._musicbee_folder = self._cfg_paths.get("musicbee")
        return self._musicbee_folder

    def as_dict(self) -> dict[str, Any]:
        return {"musicbee_folder": self.musicbee_folder} | super().as_dict()


###########################################################################
## Remote
###########################################################################
class ConfigRemote(ConfigLibrary):
    """
    Set the settings for the remote functionality of the program from a config file and terminal arguments.
    See :py:class:`Config` for more documentation regarding initialisation and operation.

    :param file: The loaded config from the config file.
    """

    def __init__(self, file: dict[Any, Any], config: Self | None = None, override: bool = False):
        self._cfg = file

        self.api = config.api if config and override else None
        if not self.api:
            if self._cfg["kind"] == "spotify" or self._cfg["kind"] == SPOTIFY_SOURCE_NAME:
                self.name = SPOTIFY_SOURCE_NAME
                config_api = config.api if config and isinstance(config.api, self.ConfigSpotify) else None
                self.api = self.ConfigSpotify(file=self._cfg, config=config_api, override=override)
            else:
                raise ConfigError(
                    "No configuration found for this remote source type '{key}'. Available: {value}",
                    key=self._cfg["kind"], value=file,
                )

        valid_library = config and isinstance(config.library, REMOTE_CONFIG[self.name].library)
        self._library = config.library if override and valid_library else None
        valid_wrangler = config and isinstance(config.wrangler, REMOTE_CONFIG[self.name].wrangler)
        self._wrangler = config.wrangler if override and valid_wrangler else None
        valid_checker = config and isinstance(config.checker, REMOTE_CONFIG[self.name].checker)
        self._checker = config.checker if override and valid_checker else None
        valid_searcher = config and isinstance(config.searcher, REMOTE_CONFIG[self.name].searcher)
        self._searcher = config.searcher if override and valid_searcher else None

        self.playlists = config.checker if config and override else None
        if not self.playlists:
            self.playlists = self.ConfigPlaylists(
                file=self._cfg, config=config.playlists if config else None, override=override
            )

    @property
    def library(self) -> RemoteLibrary:
        if self._library is not None and isinstance(self._library, REMOTE_CONFIG[self.name].library):
            return self._library

        self._library = REMOTE_CONFIG[self.name].library(
            api=self.api.api,
            include=self.playlists.include,
            exclude=self.playlists.exclude,
            use_cache=self.api.use_cache,
        )
        return self._library

    @property
    def wrangler(self) -> RemoteDataWrangler:
        """An initialised remote wrangler"""
        if self._wrangler is not None and isinstance(self._wrangler, REMOTE_CONFIG[self.name].wrangler):
            return self._wrangler
        self._wrangler = REMOTE_CONFIG[self.name].wrangler()
        return self._wrangler

    @property
    def checker(self) -> RemoteItemChecker:
        """An initialised remote wrangler"""
        if self._checker is not None and isinstance(self._checker, REMOTE_CONFIG[self.name].checker):
            return self._checker

        interval = self._cfg.get("interval", 10)
        allow_karaoke = self._cfg.get("allow_karaoke", ALLOW_KARAOKE_DEFAULT)
        self._checker = REMOTE_CONFIG[self.name].checker(
            api=self.api.api, interval=interval, allow_karaoke=allow_karaoke
        )
        return self._checker

    @property
    def searcher(self) -> RemoteItemSearcher:
        """An initialised remote wrangler"""
        if self._searcher is not None and isinstance(self._checker, REMOTE_CONFIG[self.name].searcher):
            return self._searcher

        self._searcher = REMOTE_CONFIG[self.name].searcher(api=self.api.api, use_cache=self.api.use_cache)
        return self._searcher

    def as_dict(self) -> dict[str, Any]:
        return {
            "api": self.api,
            "wrangler": bool(self.wrangler.remote_source),  # just check it loaded
            "checker": self.checker,
            "searcher": self.searcher,
        } | super().as_dict()

    class ConfigPlaylists(ConfigPlaylists):
        """
        Set the settings for processing remote playlists from a config file and terminal arguments.
        See :py:class:`Config` for more documentation regarding initialisation and operation.

        :param file: The loaded config from the config file.
        """

        def __init__(self, file: dict[Any, Any], config: Self | None = None, override: bool = False):
            super().__init__(file=file, config=config, override=override)

            self.sync = config.sync if config and override else None
            if not self.sync:
                self.sync = self.ConfigPlaylistsSync(
                    file=self._cfg, config=config.sync if config else None, override=override
                )

        def as_dict(self) -> dict[str, Any]:
            return super().as_dict() | {"sync": self.sync}

        class ConfigPlaylistsSync(PrettyPrinter):
            """
            Set the settings for synchronising remote playlists from a config file and terminal arguments.
            See :py:class:`Config` for more documentation regarding initialisation and operation.

            :param file: The loaded config from the config file.
            """

            def __init__(self, file: dict[Any, Any], config: Self | None = None, override: bool = False):
                self._cfg = file.get("sync", {})

                self._kind: str | None = config.kind if config and override else None
                self._reload: bool | None = config.reload if config and override else None

            @property
            def kind(self) -> str:
                """`OPTIONAL` | Sync option for the remote playlist."""
                if self._kind is not None:
                    return self._kind

                valid = get_args(PLAYLIST_SYNC_KINDS)
                kind = self._cfg.get("kind", "new")
                if kind not in valid:
                    raise ConfigError("Invalid kind given: {key}. Allowed values: {value}", key=kind, value=valid)

                self._kind = kind
                return self._kind

            @property
            def reload(self) -> bool:
                """`OPTIONAL` | Reload playlists after synchronisation."""
                if self._reload is not None:
                    return self._reload
                self._reload = self._cfg.get("reload", True)
                return self._reload

            def as_dict(self) -> dict[str, Any]:
                return {
                    "kind": self.kind,
                    "reload": self.reload,
                }

    class ConfigAPI(PrettyPrinter, ABC):
        """
        Set the settings for the remote API from a config file and terminal arguments.
        See :py:class:`Config` for more documentation regarding initialisation and operation.

        :param file: The loaded config from the config file.
        """

        def __init__(self, file: dict[Any, Any], config: Self | None = None, override: bool = False):
            self._cfg = file.get("api", {})

            self._api: RemoteAPI | None = config.api if config and override else None
            self._token_path: str | None = config.token_path if config and override else None
            self._use_cache: bool | None = config.use_cache if config and override else None

        @property
        @abstractmethod
        def api(self) -> RemoteAPI:
            """Set up and return a valid API session for this remote source type."""
            raise NotImplementedError

        @property
        def token_path(self) -> str:
            """`DEFAULT` | The client secret to use when authorising access to the API."""
            if self._token_path is not None:
                return self._token_path
            self._token_path = self._cfg.get("token_path", "token.json")
            return self._token_path

        @property
        def use_cache(self) -> bool:
            """
            `DEFAULT` | When True, use requests cache where possible when making API calls.
            When False, always make calls to the API, refreshing any cached data in the process.
            """
            if self._use_cache is not None:
                return self._use_cache
            self._use_cache = self._cfg.get("use_cache", True)
            return self._use_cache

        def as_dict(self) -> dict[str, Any]:
            return super().as_dict() | {
                "token_path": self.token_path,
                "use_cache": self.use_cache,
            }

    class ConfigSpotify(ConfigAPI):

        def __init__(self, file: dict[Any, Any], config: Self | None = None, override: bool = False):
            super().__init__(file=file, config=config, override=override)

            self._client_id: str | None = config.client_id if config and override else None
            self._client_secret: str | None = config.client_secret if config and override else None
            self._scopes: tuple[str] | None = config.scopes if config and override else None
            self._user_auth: bool | None = config.user_auth if config and override else None

        @property
        def client_id(self) -> str | None:
            """`OPTIONAL` | The client ID to use when authorising access to the API."""
            if self._client_id is not None:
                return self._client_id
            self._client_id = self._cfg.get("client_id")
            return self._client_id

        @property
        def client_secret(self) -> str | None:
            """`OPTIONAL` | The client secret to use when authorising access to the API."""
            if self._client_secret is not None:
                return self._client_secret
            self._client_secret = self._cfg.get("client_secret")
            return self._client_secret

        @property
        def scopes(self) -> tuple[str]:
            """`DEFAULT` | The scopes to use when authorising access to the API."""
            if self._scopes is not None:
                return self._scopes
            self._scopes = to_collection(self._cfg.get("scopes"), tuple) or ()
            return self._scopes

        @property
        def user_auth(self) -> bool:
            """`DEFAULT` | When True, authorise user access to the API. When False, only authorise basic access."""
            if self._user_auth is not None:
                return self._user_auth
            self._user_auth = self._cfg.get("user_auth", False)
            return self._user_auth

        @property
        def api(self) -> SpotifyAPI:
            if self._api is not None:
                # noinspection PyTypeChecker
                return self._api

            args = deepcopy(SPOTIFY_API_AUTH_USER if self.user_auth else SPOTIFY_API_AUTH_BASIC)
            format_map = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "client_base64": base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode(),
                "token_file_path": self.token_path,
                "scopes": " ".join(self.scopes),
            }
            safe_format_map(args, format_map=format_map)

            self._api = SpotifyAPI(**args, cache_path=None)
            return self._api

        def as_dict(self) -> dict[str, Any]:
            return {
                "client_id": "<OBFUSCATED>" if self.client_id else None,
                "client_secret": "<OBFUSCATED>" if self.client_secret else None,
                "scopes": self.scopes,
                "user_auth": self.user_auth,
            }


if __name__ == "__main__":
    import logging.config
    import json

    from syncify.utils.logger import SyncifyLogger

    conf = Config()

    # noinspection PyProtectedMember
    config_file = join(conf._package_root, "logging.yml")
    with open(config_file, "r") as f:
        log_config = yaml.full_load(f)
    SyncifyLogger.compact = log_config.pop("compact", False)

    for formatter in log_config["formatters"].values():  # ensure ANSI colour codes in format are recognised
        formatter["format"] = formatter["format"].replace(r"\33", "\33")

    logging.config.dictConfig(log_config)

    conf.remote["spotify"].api.api.authorise()
    print(conf)
    print(json.dumps(conf.json(), indent=2))
