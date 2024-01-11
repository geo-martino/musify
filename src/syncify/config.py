from __future__ import annotations

import inspect
import json
import logging.config
import os
import sys
from abc import ABCMeta, abstractmethod
from collections.abc import Mapping, Callable, Iterable
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from os.path import isabs, join, dirname, splitext, exists
from typing import Any, Self, get_args

import yaml

from syncify import PACKAGE_ROOT, MODULE_ROOT
from syncify.local.exception import InvalidFileType, FileDoesNotExistError
from syncify.local.file import PathStemMapper
from syncify.local.library import MusicBee, LocalLibrary
from syncify.local.track.field import LocalTrackField
from syncify.processors.compare import Comparer
from syncify.processors.filter import FilterComparers
from syncify.report import report_missing_tags
from syncify.shared.api.authorise import APIAuthoriser
from syncify.shared.api.request import RequestHandler
from syncify.shared.core.base import Nameable
from syncify.shared.core.enum import TagField
from syncify.shared.core.misc import PrettyPrinter
from syncify.shared.core.object import Library
from syncify.shared.exception import ConfigError, SyncifyError
from syncify.shared.logger import LOGGING_DT_FORMAT, SyncifyLogger
from syncify.shared.remote.api import RemoteAPI
from syncify.shared.remote.base import RemoteObject
from syncify.shared.remote.library import RemoteLibrary
from syncify.shared.remote.object import PLAYLIST_SYNC_KINDS, RemotePlaylist
from syncify.shared.remote.processors.check import RemoteItemChecker
from syncify.shared.remote.processors.search import RemoteItemSearcher
from syncify.shared.remote.processors.wrangle import RemoteDataWrangler
from syncify.shared.utils import to_collection
from syncify.spotify import SPOTIFY_NAME
from syncify.spotify.api import SpotifyAPI
from syncify.spotify.base import SpotifyObject
from syncify.spotify.library import SpotifyLibrary
from syncify.spotify.object import SpotifyPlaylist
from syncify.spotify.processors.processors import SpotifyItemChecker, SpotifyItemSearcher
from syncify.spotify.processors.wrangle import SpotifyDataWrangler


def _get_local_track_tags(tags: Any) -> tuple[LocalTrackField, ...]:
    values = to_collection(tags, tuple)
    if not values:
        return tuple(LocalTrackField.all(only_tags=True))

    tags = LocalTrackField.to_tags(LocalTrackField.from_name(*values))
    order = LocalTrackField.all()
    return tuple(sorted(LocalTrackField.from_name(*tags), key=lambda x: order.index(x)))


def _get_default_args(func: Callable):
    signature = inspect.signature(func)
    return {
        k: v.default
        for k, v in signature.parameters.items()
        if v.default is not inspect.Parameter.empty
    }


class BaseConfig(PrettyPrinter, metaclass=ABCMeta):
    """Base config section representing a config block from the file"""

    __override__: tuple[str] = ()
    __reset__: tuple[str] = ()

    def __init__(self, settings: dict[Any, Any], key: Any | None = None):
        super().__init__()
        self._file: dict[Any, Any] = settings.get(key, {}) if key else settings

    def merge(self, other: Self | None, override: bool = False) -> None:
        """
        Merge the currently stored config values with the config from a given ``other`` configured config object
        When ``override`` is True, force overwrite any values in ``self`` with ``other``.
        """
        if other is None:
            return

        for k in to_collection(self.__override__) + tuple(key for key in dir(self) if key not in self.__override__):
            if k in self.__override__:
                pass
            elif not k.startswith("_") or k.startswith("__") or k.lstrip("_") not in dir(self):
                try:
                    if not isinstance(getattr(self, k), BaseConfig):
                        continue
                except SyncifyError:
                    continue
            elif k in self.__reset__:
                setattr(self, k, None)
                continue

            try:
                v_self = getattr(self, k.lstrip("_"))
            except SyncifyError:
                v_self = None

            force = False
            try:
                force = not override and k in self.__override__ and getattr(other, k) is not None
                v_other = getattr(other, k.lstrip("_"))
            except SyncifyError:
                v_other = None

            if isinstance(v_self, BaseConfig) and isinstance(v_other, v_self.__class__):
                # merge value of self when values are matching types of config objects
                v_self.merge(v_other, override=override)

            elif isinstance(v_self, dict) and isinstance(v_other, dict):
                for k_sub, v_self_sub in v_self.items():
                    v_other_sub = v_other.get(k_sub)
                    if isinstance(v_self_sub, BaseConfig) and v_other_sub.__class__ == v_self_sub.__class__:
                        # override any matching types of config objects
                        v_self_sub.merge(v_other_sub, override=override)
                    elif override:    # just replace the current value
                        v_self[k_sub] = v_other_sub

                for k_sub, v_other_sub in v_other.items():  # add missing keys from self found in other
                    if k_sub not in v_self:
                        v_self[k_sub] = v_other_sub
            else:
                if override and v_other is not None:  # if value from other exists, replace self value
                    if isinstance(v_other, tuple) and len(v_other) == 0:
                        continue
                    setattr(self, k, v_other)
                elif v_self is None or force or (isinstance(v_self, tuple) and len(v_self) == 0):
                    setattr(self, k, v_other)

        if isinstance(self, ConfigLibrary) and isinstance(other, ConfigLibrary):
            # noinspection PyAttributeOutsideInit
            self.library_loaded = other.library_loaded


###########################################################################
## Reports
###########################################################################
class ConfigReportBase(BaseConfig):
    """
    Base class for settings reports settings.
    See :py:class:`Config` for more documentation regarding operation.

    :param settings: The loaded config from the config file.
    """
    def __init__(self, settings: dict[Any, Any], key: str):
        super().__init__(settings=settings, key=key)
        self.name = key
        self.enabled = self._file.get("enabled", True)
        self.filter = ConfigFilter(settings=self._file)

    def as_dict(self) -> dict[str, Any]:
        return {"enabled": self.enabled}


class ConfigReports(BaseConfig, Iterable[ConfigReportBase]):
    """
    Set the settings for all reports from a config file.
    See :py:class:`Config` for more documentation regarding operation.

    :param settings: The loaded config from the config file.
    """
    def __init__(self, settings: dict[Any, Any]):
        super().__init__(settings=settings, key="reports")

        self.library_differences = ConfigLibraryDifferences(settings=self._file)
        self.missing_tags = ConfigMissingTags(settings=self._file)

    @property
    def enabled(self) -> bool:
        """Are any reports configured enabled"""
        return len(self) > 0

    def __iter__(self):
        return (value for value in self.__dict__.values() if isinstance(value, ConfigReportBase) and value.enabled)

    def __len__(self):
        return len([value for value in self])

    def as_dict(self) -> dict[str, Any]:
        return {report.name: report for report in self}


class ConfigLibraryDifferences(ConfigReportBase):
    """
    Set the settings for the library differences report from a config file.
    See :py:class:`Config` for more documentation regarding operation.

    :param settings: The loaded config from the config file.
    """
    def __init__(self, settings: dict[Any, Any]):
        super().__init__(settings=settings, key="library_differences")


class ConfigMissingTags(ConfigReportBase):
    """
    Set the settings for the missing tags report from a config file.
    See :py:class:`Config` for more documentation regarding operation.

    :param settings: The loaded config from the config file.
    """

    def __init__(self, settings: dict[Any, Any]):
        super().__init__(settings=settings, key="missing_tags")

        self._tags: tuple[LocalTrackField, ...] | None = None
        self._match_all: bool | None = None

    @property
    def tags(self) -> tuple[LocalTrackField, ...]:
        """`DEFAULT = (<all LocalTrackFields>)` | The tags to be updated."""
        if self._tags is not None:
            return self._tags

        default = to_collection(_get_default_args(report_missing_tags)["tags"])
        self._tags = _get_local_track_tags(self._file["tags"]) if "tags" in self._file else default
        return self._tags

    @property
    def match_all(self) -> bool:
        """
        `DEFAULT = True` | When True, consider a track as having missing tags only if it is missing all the given tags.
        """
        if self._match_all is not None:
            return self._match_all

        defaults = _get_default_args(report_missing_tags)
        self._match_all = self._file.get("match_all", defaults["match_all"])
        return self._match_all

    def as_dict(self) -> dict[str, Any]:
        order = [field.name.lower() for field in LocalTrackField.all(only_tags=True)]
        return super().as_dict() | {
            "tags": list(sorted([t for tag in self.tags for t in tag.to_tag()], key=lambda x: order.index(x))),
            "match_all": self.match_all,
        }


###########################################################################
## Shared
###########################################################################
class ConfigLibrary(BaseConfig):
    """
    Set the settings for a library from a config file.
    See :py:class:`Config` for more documentation regarding operation.

    :param settings: The loaded config from the config file.
    :param key: The key to load filter options for.
        Used as the parent key to use to pull the required configuration from the config file.
    """

    __override__ = ("_library",)

    def __init__(self, settings: dict[Any, Any], key: Any | None = None):
        super().__init__(settings=settings, key=key)

        self._library: Library | None = None
        self.playlists: ConfigPlaylists | None = None

        self.library_loaded: bool = False  # marks whether initial loading of the library has happened

    @property
    def kind(self) -> str:
        """The config identifier that gives the type of library being configured"""
        return self._file["type"]

    @property
    @abstractmethod
    def source(self) -> str:
        """The name of the source currently being used for this library"""
        raise NotImplementedError

    @property
    @abstractmethod
    def library(self) -> Library:
        """An initialised library"""
        raise NotImplementedError

    def as_dict(self) -> dict[str, Any]:
        try:
            library = self.library
        except SyncifyError:
            library = None
        return {"library": library, "playlists": self.playlists}

    def __deepcopy__(self, _: dict = None):
        obj = self.__class__.__new__(self.__class__)
        obj.__dict__ = {k: deepcopy(v) if not isinstance(v, Library) else v for k, v in self.__dict__.items()}
        return obj


class ConfigFilter[T: str | Nameable](BaseConfig, FilterComparers[T]):
    """
    Set the settings for granular filtering from a config file.
    See :py:class:`Config` for more documentation regarding operation.

    :param settings: The loaded config from the config file.
    """

    def __init__(self, settings: dict[Any, Any]):
        super().__init__(settings=settings, key="filter")

        if isinstance(self._file, str):
            self.comparers = (Comparer(condition="is", expected=self._file),)
            return
        elif isinstance(self._file, list):
            self.comparers = (Comparer(condition="is in", expected=self._file),)
            return

        self.match_all = self._file.pop("match_all", self.match_all)
        self.comparers = tuple(Comparer(condition=cond, expected=exp) for cond, exp in self._file.items())

        self.transform = lambda value: value.name if isinstance(value, Nameable) else value


class ConfigPlaylists(BaseConfig):
    """
    Set the settings for the playlists from a config file.
    See :py:class:`Config` for more documentation regarding operation.

    :param settings: The loaded config from the config file.
    """

    def __init__(self, settings: dict[Any, Any]):
        super().__init__(settings=settings, key="playlists")
        self.filter = ConfigFilter(settings=self._file)

    def as_dict(self) -> dict[str, Any]:
        return {"filter": self.filter}


###########################################################################
## Local
###########################################################################
class ConfigLocalBase(ConfigLibrary, metaclass=ABCMeta):
    """
    Set the settings for the local functionality of the program from a config file.
    See :py:class:`Config` for more documentation regarding operation.

    :param settings: The loaded config from the config file.
    """

    @property
    def _platform_key(self) -> str:
        platform_map = {"win32": "win", "linux": "lin", "darwin": "mac"}
        return platform_map[sys.platform]

    def __init__(self, settings: dict[Any, Any]):
        super().__init__(settings=settings)
        self._defaults = _get_default_args(LocalLibrary)

        self._stems: dict[str, str] | None = None
        self._remote_wrangler: RemoteDataWrangler | None = self._defaults["remote_wrangler"]

        self.playlists = ConfigPlaylists(settings=self._file)
        self.update = self.ConfigUpdateTags(settings=self._file)

    @property
    @abstractmethod
    def library(self) -> LocalLibrary:
        raise NotImplementedError

    @property
    def source(self):
        return LocalLibrary.source

    @property
    def remote_wrangler(self) -> RemoteDataWrangler:
        """The remote wrangler to apply when initialising a library"""
        return self._remote_wrangler

    @remote_wrangler.setter
    def remote_wrangler(self, value: RemoteDataWrangler):
        if self._library is not None:
            raise ConfigError("Cannot set the remote wrangler after the library has been initialised")
        self._remote_wrangler = value

    ###########################################################################
    ## Paths
    ###########################################################################
    @property
    def _paths(self) -> dict[Any, Any]:
        return self._file.get("paths", {})

    @property
    def stems(self) -> dict[str, str]:
        """`DEFAULT = {}` | The mapped paths of other folders to use for replacement when processing local libraries"""
        if self._stems is not None:
            return self._stems

        self._stems = self._paths.get("map") or {}
        return self._stems

    def as_dict(self) -> dict[str, Any]:
        return {"stems": self.stems, "update": self.update} | super().as_dict()

    class ConfigUpdateTags(BaseConfig):
        """
        Set the settings for the playlists from a config file.
        See :py:class:`Config` for more documentation regarding operation.

        :param settings: The loaded config from the config file.
        """

        def __init__(self, settings: dict[Any, Any]):
            super().__init__(settings=settings, key="update")
            self._defaults = _get_default_args(LocalLibrary.save_tracks)

            self._tags: tuple[LocalTrackField, ...] | None = None
            self._replace: bool | None = None

        @property
        def tags(self) -> tuple[LocalTrackField, ...]:
            """`DEFAULT = (<all LocalTrackFields>)` | The tags to be updated."""
            if self._tags is not None:
                return self._tags

            default = to_collection(self._defaults["tags"])
            self._tags = _get_local_track_tags(self._file["tags"]) if "tags" in self._file else default
            return self._tags

        @property
        def replace(self) -> bool:
            """`DEFAULT = False` | Destructively replace tags in each file."""
            if self._replace is not None:
                return self._replace

            self._replace = self._file.get("replace", self._defaults["replace"])
            return self._replace

        def as_dict(self) -> dict[str, Any]:
            order = [field.name.lower() for field in LocalTrackField.all(only_tags=True)]
            return {
                "tags": list(sorted([t for tag in self.tags for t in tag.to_tag()], key=lambda x: order.index(x))),
                "replace": self.replace,
            }


class ConfigLocalLibrary(ConfigLocalBase):
    """
    Set the settings for the local functionality of the program for a generic LocalLibrary from a config file.
    See :py:class:`Config` for more documentation regarding operation.

    :param settings: The loaded config from the config file.
    """

    def __init__(self, settings: dict[Any, Any]):
        super().__init__(settings=settings)
        self._defaults = _get_default_args(LocalLibrary)

        self._library_folders: tuple[str, ...] | None = None
        self._playlist_folder: str | None = None

    @property
    def library(self) -> LocalLibrary:
        if self._library is not None and isinstance(self._library, LocalLibrary):
            return self._library

        self._library = LocalLibrary(
            library_folders=self.library_folders,
            playlist_folder=self.playlist_folder,
            playlist_filter=self.playlists.filter,
            path_mapper=PathStemMapper(stem_map=self.stems),
            remote_wrangler=self.remote_wrangler
        )
        return self._library

    @property
    def library_folders(self) -> tuple[str, ...]:
        """`REQUIRED` | The path of the local library folder"""
        if self._library_folders is not None:
            return self._library_folders

        if isinstance(self._paths.get("library"), (str, list)):
            folder = self._paths["library"]
        elif isinstance(self._paths.get("library"), dict):  # assume platform sub-keys
            folder = self._paths["library"].get(self._platform_key)
            self.stems.update(
                {path: folder for key, path in self._paths["library"].items() if path and key != self._platform_key}
            )
        else:
            raise ConfigError("Config not found", key=["local", "paths", "library"], value=self._paths)

        if not folder:
            raise ConfigError(
                "Library folder for the current platform not given",
                key=["local", "paths", "library", self._platform_key],
                value=self._paths["library"]
            )

        self._library_folders = to_collection(folder)
        return self._library_folders

    @property
    def playlist_folder(self) -> str:
        """`DEFAULT = 'Playlists'` | The path of the playlist folder."""
        if self._playlist_folder is not None:
            return self._playlist_folder
        self._playlist_folder = self._paths.get("playlists", self._defaults["playlist_folder"])
        return self._playlist_folder

    def as_dict(self) -> dict[str, Any]:
        try:
            library_folders = self.library_folders
        except ConfigError:
            library_folders = None

        return {"library_folders": library_folders, "playlist_folder": self.playlist_folder} | super().as_dict()


class ConfigMusicBee(ConfigLocalBase):
    """
    Set the settings for the local functionality of the program for a MusicBee from a config file.
    See :py:class:`Config` for more documentation regarding operation.

    :param settings: The loaded config from the config file.
    """
    def __init__(self, settings: dict[Any, Any]):
        super().__init__(settings=settings)
        self._defaults = _get_default_args(MusicBee)

        self._musicbee_folder: str | None = None

    @property
    def source(self):
        return MusicBee.source

    @property
    def library(self) -> MusicBee:
        if self._library is not None and isinstance(self._library, MusicBee):
            return self._library

        self._library = MusicBee(
            musicbee_folder=self.musicbee_folder,
            playlist_filter=self.playlists.filter,
            path_mapper=PathStemMapper(stem_map=self.stems),
            remote_wrangler=self.remote_wrangler,
        )
        return self._library

    @property
    def musicbee_folder(self) -> str | None:
        """`REQUIRED` | The path of the MusicBee library folder."""
        if self._musicbee_folder is not None:
            return self._musicbee_folder

        if isinstance(self._paths.get("library"), str):
            folder = self._paths["library"]
        elif isinstance(self._paths.get("library"), dict):  # assume platform sub-keys
            folder = self._paths["library"].get(self._platform_key)
        else:
            raise ConfigError("Config not found/invalid", key=["local", "paths", "library"], value=self._paths)

        if not folder:
            raise ConfigError(
                "MusicBee Library folder for the current platform not given",
                key=["local", "paths", "library", self._platform_key],
                value=self._paths["library"]
            )

        self._musicbee_folder = folder
        return self._musicbee_folder

    def as_dict(self) -> dict[str, Any]:
        try:
            musicbee_folder = self.musicbee_folder
        except ConfigError:
            musicbee_folder = None

        return {"musicbee_folder": musicbee_folder} | super().as_dict()


###########################################################################
## Remote
###########################################################################
class ConfigRemote(ConfigLibrary):
    """
    Set the settings for the remote functionality of the program from a config file.
    See :py:class:`Config` for more documentation regarding operation.

    :param settings: The loaded config from the config file.
    """

    __override__ = ("api", "_library")

    def __init__(self, settings: dict[Any, Any]):
        super().__init__(settings=settings)

        if self.kind not in REMOTE_CONFIG:
            raise ConfigError(
                "No remote configuration found for this remote source type '{key}'. Available: {value}. "
                f"Valid source types: {", ".join(REMOTE_CONFIG)}",
                key=self.kind, value=settings,
            )

        self.api: ConfigAPI = self._classes.api(settings=self._file)
        self.playlists = self.ConfigPlaylists(settings=self._file)

        self._wrangler: RemoteDataWrangler | None = None
        self._checker: RemoteItemChecker | None = None
        self._searcher: RemoteItemSearcher | None = None

    @property
    def _classes(self) -> RemoteClasses:
        return REMOTE_CONFIG[self.kind]

    @property
    def source(self) -> str:
        return self._classes.source
    
    @property
    def library(self) -> RemoteLibrary:
        if self._library is not None and isinstance(self._library, self._classes.library):
            return self._library

        self._library = self._classes.library(
            api=self.api.api,
            use_cache=self.api.use_cache,
            playlist_filter=self.playlists.filter,
        )
        return self._library

    @property
    def playlist(self) -> type[RemotePlaylist]:
        """The :py:class:`RemotePlaylist` class for this remote library type"""
        return self._classes.playlist

    @property
    def wrangler(self) -> RemoteDataWrangler:
        """An initialised remote wrangler"""
        if self._wrangler is not None and isinstance(self._wrangler, self._classes.wrangler):
            return self._wrangler
        self._wrangler = self._classes.wrangler()
        return self._wrangler

    @property
    def checker(self) -> RemoteItemChecker:
        """An initialised remote wrangler"""
        if self._checker is not None and isinstance(self._checker, self._classes.checker):
            return self._checker

        defaults = _get_default_args(self._classes.checker)
        settings = self._file.get("check", {})
        self._checker = self._classes.checker(
            api=self.api.api,
            interval=settings.get("interval", defaults["interval"]),
            allow_karaoke=settings.get("allow_karaoke", defaults["allow_karaoke"])
        )
        return self._checker

    @property
    def searcher(self) -> RemoteItemSearcher:
        """An initialised remote wrangler"""
        if self._searcher is not None and isinstance(self._checker, self._classes.searcher):
            return self._searcher

        self._searcher = self._classes.searcher(api=self.api.api, use_cache=self.api.use_cache)
        return self._searcher

    def as_dict(self) -> dict[str, Any]:
        try:
            return {
                "api": self.api,
                "wrangler": bool(self.wrangler.source),  # just check it loaded
                "checker": self.checker,
                "searcher": self.searcher,
            } | super().as_dict()
        except SyncifyError:
            return {
                "api": None,
                "wrangler": bool(self.wrangler.source),  # just check it loaded
                "checker": None,
                "searcher": None,
            } | super().as_dict()

    class ConfigPlaylists(ConfigPlaylists):
        """
        Set the settings for processing remote playlists from a config file.
        See :py:class:`Config` for more documentation regarding operation.

        :param settings: The loaded config from the config file.
        """

        def __init__(self, settings: dict[Any, Any]):
            super().__init__(settings=settings)
            
            self.sync = self.ConfigPlaylistsSync(settings=self._file)

        def as_dict(self) -> dict[str, Any]:
            return super().as_dict() | {"sync": self.sync}

        class ConfigPlaylistsSync(BaseConfig):
            """
            Set the settings for synchronising remote playlists from a config file.
            See :py:class:`Config` for more documentation regarding operation.

            :param settings: The loaded config from the config file.
            """

            def __init__(self, settings: dict[Any, Any]):
                super().__init__(settings=settings, key="sync")
                self._defaults = _get_default_args(RemotePlaylist.sync)

                self._kind: str | None = None
                self._reload: bool | None = None
                self._filter: dict[str, tuple[Any, ...]] | None = None

            def merge(self, other: Self | None, override: bool = False) -> None:
                if override:
                    self._kind = other.kind
                    self._reload = other.reload
                    self._filter = other.filter
                else:
                    self._kind = other.kind if self.kind is None else self.kind
                    self._reload = other.reload if self.reload is None else self.reload
                    self._filter = other.filter if self.filter is None else self.filter

            @property
            def kind(self) -> str:
                """`DEFAULT = 'new'` | Sync option for the remote playlist."""
                if self._kind is not None:
                    return self._kind

                valid = get_args(PLAYLIST_SYNC_KINDS)
                kind = self._file.get("kind", self._defaults["kind"])
                if kind not in valid:
                    raise ConfigError("Invalid kind given: {key}. Allowed values: {value}", key=kind, value=valid)

                self._kind = kind
                return self._kind

            @property
            def reload(self) -> bool:
                """`DEFAULT = True` | Reload playlists after synchronisation."""
                if self._reload is not None:
                    return self._reload
                self._reload = self._file.get("reload", self._defaults["reload"])
                return self._reload

            @property
            def filter(self) -> dict[str, tuple[str, ...]]:
                """`DEFAULT = {}` | Tags and values of items to filter out of every playlist when synchronising"""
                if self._filter is not None:
                    return self._filter

                self._filter = {}
                for tag, values in self._file.get("filter", {}).items():
                    if tag not in TagField.__tags__ or not values:
                        continue
                    self._filter[tag] = to_collection(values, tuple)

                return self._filter

            def as_dict(self) -> dict[str, Any]:
                return {
                    "kind": self.kind,
                    "reload": self.reload,
                }


class ConfigAPI(BaseConfig, metaclass=ABCMeta):
    """
    Set the settings for the remote API from a config file.
    See :py:class:`Config` for more documentation regarding operation.

    :param settings: The loaded config from the config file.
    """

    __override__ = ("_api",)

    def __init__(self, settings: dict[Any, Any]):
        super().__init__(settings=settings, key="api")

        self._api: RemoteAPI | None = None
        self._token_path: str | None = None
        self._cache_path: str | None = None
        self._use_cache: bool | None = None

    @property
    @abstractmethod
    def api(self) -> RemoteAPI:
        """Set up and return a valid API session for this remote source type."""
        raise NotImplementedError

    @property
    def token_path(self) -> str:
        """`OPTIONAL` | The client secret to use when authorising access to the API."""
        if self._token_path is not None:
            return self._token_path

        defaults = _get_default_args(APIAuthoriser)
        self._token_path = self._file.get("token_path", defaults["token_file_path"])
        return self._token_path

    @property
    def cache_path(self) -> str:
        """`DEFAULT = '.api_cache'` | The path of the cache to use when using cached requests for the API"""
        if self._cache_path is not None:
            return self._cache_path

        defaults = _get_default_args(RequestHandler)
        self._cache_path = self._file.get("cache_path", defaults["cache_path"])
        return self._cache_path

    @property
    def use_cache(self) -> bool:
        """
        `DEFAULT = True` | When True, use requests cache where possible when making API calls.
        When False, always make calls to the API, refreshing any cached data in the process.
        """
        if self._use_cache is not None:
            return self._use_cache
        self._use_cache = self._file.get("use_cache", True)
        return self._use_cache

    def as_dict(self) -> dict[str, Any]:
        return super().as_dict() | {
            "token_path": self.token_path,
            "use_cache": self.use_cache,
        }

    def __deepcopy__(self, _: dict = None):
        obj = self.__class__.__new__(self.__class__)
        obj.__dict__ = {k: deepcopy(v) if not isinstance(v, RemoteAPI) else v for k, v in self.__dict__.items()}
        return obj


class ConfigSpotify(ConfigAPI):

    def __init__(self, settings: dict[Any, Any]):
        super().__init__(settings=settings)
        self._defaults = _get_default_args(SpotifyAPI)

        self._client_id: str | None = None
        self._client_secret: str | None = None
        self._scopes: tuple[str, ...] | None = None

    @property
    def client_id(self) -> str | None:
        """`OPTIONAL` | The client ID to use when authorising access to the API."""
        if self._client_id is not None:
            return self._client_id
        self._client_id = self._file.get("client_id", self._defaults["client_id"])
        return self._client_id

    @property
    def client_secret(self) -> str | None:
        """`OPTIONAL` | The client secret to use when authorising access to the API."""
        if self._client_secret is not None:
            return self._client_secret
        self._client_secret = self._file.get("client_secret", self._defaults["client_secret"])
        return self._client_secret

    @property
    def scopes(self) -> tuple[str, ...]:
        """`DEFAULT = ()` | The scopes to use when authorising access to the API."""
        if self._scopes is not None:
            return self._scopes

        self._scopes = to_collection(self._file.get("scopes"), tuple) or self._defaults["scopes"]
        return self._scopes

    @property
    def api(self) -> SpotifyAPI:
        if self._api is not None:
            # noinspection PyTypeChecker
            return self._api
        
        if not self.client_id or not self.client_secret:
            raise ConfigError("Cannot create API object without client ID and client secret")

        self._api = SpotifyAPI(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.scopes,
            token_file_path=self.token_path,
            cache_path=self.cache_path,
        )
        return self._api

    def as_dict(self) -> dict[str, Any]:
        return {
            "client_id": "<OBFUSCATED>" if self.client_id else None,
            "client_secret": "<OBFUSCATED>" if self.client_secret else None,
            "scopes": self.scopes,
        }


###########################################################################
## Main config
###########################################################################
@dataclass
class RemoteClasses:
    """Stores the key classes for a remote source"""
    source: str
    api: type[ConfigAPI]
    wrangler: type[RemoteDataWrangler]
    object: type[RemoteObject]
    checker: type[RemoteItemChecker]
    searcher: type[RemoteItemSearcher]
    library: type[RemoteLibrary]
    playlist: type[RemotePlaylist]


SPOTIFY_CLASSES = RemoteClasses(
    source=SPOTIFY_NAME,
    api=ConfigSpotify,
    wrangler=SpotifyDataWrangler,
    object=SpotifyObject,
    checker=SpotifyItemChecker,
    searcher=SpotifyItemSearcher,
    library=SpotifyLibrary,
    playlist=SpotifyPlaylist,
)

# map of the names of all supported library sources and their associated config
REMOTE_CONFIG: Mapping[str, RemoteClasses] = {
    SPOTIFY_NAME: SPOTIFY_CLASSES,
    "spotify": SPOTIFY_CLASSES,
}

LOCAL_CONFIG: Mapping[str, type[ConfigLocalBase]] = {
    "local": ConfigLocalLibrary,
    "musicbee": ConfigMusicBee,
}


class Config(BaseConfig):
    """
    Set up config and provide framework for initialising various objects
    needed for the main functionality of the program from a given config file at ``path``.

    The following options are in place for configuration values:

    - `DEFAULT`: When a value is not found, a default value will be used.
    - `REQUIRED`: The configuration will fail if this value is not given. Only applies when the key is called.
    - `OPTIONAL`: This value does not need to be set and ``None`` will be set when this is the case.
        The configuration will not fail if this value is not given.

    Sub-configs have an ``override`` parameter that can be set using the ``override`` key in initial config block.
    When override is True and ``config`` given, override loaded config from the file with values in ``config``
    only using loaded values when values are not present in given ``config``.
    When override is False and ``config`` given, loaded config takes priority
    and given ``config`` values are only used when values are not present in the file.
    By default, always keep the current settings.

    :param path: Path of the config file to use. If relative path given, appends package root path.
    """

    __override__ = "libraries"
    __reset__ = ("_reload", "_pause")

    def __init__(self, path: str = "config.yml"):
        super().__init__({})
        self.dt = datetime.now()
        self._root_path: str = PACKAGE_ROOT
        self.path = self._make_path_absolute(path)
        self.loaded: bool = False  # marked as True after the first load, prevents excessive overriding

        # general operation settings
        self.dry_run: bool | None = None
        self._output_folder: str | None = None
        self._reload: dict[str, tuple[str, ...]] | None = None
        self._pause: str | None = None

        self.libraries: dict[str, ConfigLibrary] = {}
        self.filter: ConfigFilter | None = None
        self.reports: ConfigReports | None = None

    def load(self, key: str | None = None):
        """
        Load config from the config file at the given ``key`` respecting ``override`` rules.

        :param key: The key to pull config from within the file.
            Used as the parent key to use to pull the required configuration from the config file.
            If not given, use the root values in the config file.
        """
        previous = deepcopy(self) if self.loaded else None
        try:
            self._file = self._load_config(key)
        except ConfigError as ex:
            if previous:  # keep the same config
                return
            raise ex

        self.filter = ConfigFilter(settings=self._file)
        self.reports = ConfigReports(settings=self._file)

        for name, settings in self._file.get("libraries", {}).items():
            if "type" not in settings and name in self.libraries:
                settings["type"] = self.libraries[name].kind

            if settings["type"] not in LOCAL_CONFIG:
                library = ConfigRemote(settings=settings)
                # noinspection PyProtectedMember
                assert library.api._api is None  # ensure api has not already been instantiated

                if library.api.token_path and not exists(library.api.token_path) and not isabs(library.api.token_path):
                    library.api._token_path = join(dirname(self.output_folder), library.api.token_path)
                if library.api.cache_path and not exists(library.api.cache_path) and not isabs(library.api.cache_path):
                    library.api._cache_path = join(dirname(self.output_folder), library.api.cache_path)
            else:
                library = LOCAL_CONFIG[settings["type"]](settings=settings)

            self.libraries[name] = library

        if previous:  # override or enrich as needed
            override = self._file.get("override", True)

            if self.filter.ready:
                previous.filter = None
            self.merge(previous, override=not override)

        self.loaded = True
        return

    def _make_path_absolute(self, path: str) -> str:
        """Append the root path to any relative path to make it an absolute path. Do nothing if path is absolute."""
        if not isabs(path):
            path = join(self._root_path, path)
        return path

    def _load_config(self, key: str | None = None) -> dict[Any, Any]:
        """
        Load the config file

        :param key: The key to pull config from within the file.
        :return: The config file.
        :raise InvalidFileType: When the given config file is not of the correct type.
        :raise FileDoesNotExistError: When the given path to the config file does not exist
        :raise ConfigError: When the given key cannot be found.
        """
        if splitext(self.path)[1].casefold() not in [".yml", ".yaml"]:
            raise InvalidFileType(f"Unrecognised file type: {self.path}")
        elif not exists(self.path):
            raise FileDoesNotExistError(f"Config file not found: {self.path}")

        with open(self.path, 'r') as file:
            config = yaml.full_load(file)
        if key and key not in config:
            raise ConfigError("Unrecognised config name: {key} | Available: {value}", key=key, value=config)

        return config.get(key, config)

    def load_log_config(self, path: str = "logging.yml", name: str | None = None, *names: str) -> None:
        """
        Load logging config from the JSON or YAML file at the given ``path`` using logging.config.dictConfig.
        If relative path given, appends package root path.

        :param path: The path to the logger config
        :param name: If the given name is a valid logger name in the config,
            assign this logger's config to the module root logger.
        :param names: When given, also apply the config from ``name`` to loggers with these ``names``.
        """
        path = self._make_path_absolute(path)
        ext = splitext(path)[1].casefold()

        allowed = {".yml", ".yaml", ".json"}
        if ext not in allowed:
            raise ConfigError(
                "Unrecognised log config file type: {key}. Valid: {value}", key=ext, value=allowed
            )

        with open(path, "r") as file:
            if ext in {".yml", ".yaml"}:
                log_config = yaml.full_load(file)
            elif ext in {".json"}:
                log_config = json.load(file)

        SyncifyLogger.compact = log_config.pop("compact", False)

        for formatter in log_config["formatters"].values():  # ensure ANSI colour codes in format are recognised
            formatter["format"] = formatter["format"].replace(r"\33", "\33")

        if name and name in log_config.get("loggers", {}):
            log_config["loggers"][MODULE_ROOT] = log_config["loggers"][name]
            for n in names:
                log_config["loggers"][n] = log_config["loggers"][name]

        logging.config.dictConfig(log_config)

        if name and name in log_config.get("loggers", {}):
            logging.getLogger(MODULE_ROOT).debug(f"Logging config set to: {name}")

    ###########################################################################
    ## General
    ###########################################################################
    @property
    def output_folder(self) -> str:
        """`DEFAULT = '<package_root>/_data'` | The output folder for saving diagnostic data"""
        if self._output_folder is not None:
            return self._output_folder

        parent_folder = self._make_path_absolute(self._file.get("output", "_data"))
        self._output_folder = join(parent_folder, self.dt.strftime(LOGGING_DT_FORMAT))
        os.makedirs(self._output_folder, exist_ok=True)
        return self._output_folder

    @property
    def reload(self) -> dict[str, tuple[str, ...]]:
        """
        `DEFAULT = <map of all libraries to empty tuples>` |
        The keys of libraries as found in either 'local' or 'remote' maps to reload
        mapped to the types of data to reload for each library.
        """
        if self._reload is not None:
            return self._reload

        self._reload = {}
        if "reload" not in self._file:  # reload nothing
            return {}
        if self._file["reload"] is None:  # no settings given, reload all data for all libraries
            # empty tuple should be interpreted as reload all
            self._reload = {name: tuple() for name in self.libraries}
            return self._reload

        for name in self._file["reload"]:  # reload only the data specified in the config
            if isinstance(self._file["reload"], dict) and self._file["reload"][name] is not None:
                self._reload[name] = to_collection(self._file["reload"][name])
            else:
                self._reload[name] = tuple()

        return self._reload

    @property
    def pause(self) -> str | None:
        """`OPTIONAL` | A message to display when pausing"""
        if self._pause is not None or "pause" not in self._file:
            return self._pause

        default = "Pausing, hit return to continue..."
        self._pause = (self._file.get("pause", default) or default).strip()
        return self._pause

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_time": self.dt,
            "path": self.path,
            "output_folder": self.output_folder,
            "dry_run": self.dry_run,
            "reload": self.reload,
            "pause_message": self.pause,
            "libraries": {name: config for name, config in self.libraries.items()},
            "filter": self.filter,
            "reports": self.reports,
        }


if __name__ == "__main__":
    conf = Config()
    conf.load_log_config("logging.yml")
    conf.load("general")

    print(conf)
    print(json.dumps(conf.json(), indent=2))
