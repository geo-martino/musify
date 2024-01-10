import logging
from copy import deepcopy
from os.path import join, dirname

import pytest
from pytest_lazyfixture import lazy_fixture
from requests_cache import CachedSession

from syncify import PACKAGE_ROOT, MODULE_ROOT
from syncify.config import ConfigLocalBase, ConfigMusicBee, ConfigLocalLibrary
from syncify.config import ConfigRemote, ConfigSpotify
from syncify.config import LOCAL_CONFIG, REMOTE_CONFIG, Config, ConfigFilter, ConfigReports
from syncify.local.exception import FileDoesNotExistError
from syncify.local.track.field import LocalTrackField
from syncify.shared.core.enum import TagFields
from syncify.shared.exception import ConfigError, SyncifyError
from syncify.shared.logger import SyncifyLogger
from syncify.shared.remote.processors.wrangle import RemoteDataWrangler
from tests.shared.core.misc import PrettyPrinterTester
from tests.utils import path_resources, path_txt

path_config = join(path_resources, "test_config.yml")
path_logging = join(path_resources, "test_logging.yml")


class TestConfig(PrettyPrinterTester):

    @pytest.fixture(params=[
        lazy_fixture("config_empty"),
        lazy_fixture("config_valid"),
    ])
    def obj(self, request) -> Config:
        return request.param

    @pytest.fixture
    def config(self, tmp_path: str) -> Config:
        """Yields an initialised :py:class:`Config` to test as a pytest.fixture"""
        config = Config(path_config)
        config._root_path = tmp_path
        return config

    # noinspection PyTestUnpassedFixture
    def test_init(self):
        filename = "test_file.yml"

        config = Config(filename)
        assert config.path == join(PACKAGE_ROOT, filename)

        config = Config(join(dirname(__file__), filename))
        assert config.path == join(join(dirname(__file__), filename))

    ###########################################################################
    ## Load config
    ###########################################################################
    @pytest.mark.skip(reason="this removes all handlers hence removing ability to see logs for tests that follow this")
    def test_load_log_config(self, config_empty: Config, tmp_path: str):
        with pytest.raises(ConfigError):
            config_empty.load_log_config(path_txt)

        config_empty.load_log_config(path_logging)
        assert SyncifyLogger.compact

        loggers = [logger.name for logger in logging.getLogger().getChildren()]
        assert "__main__" not in loggers

        config_empty.load_log_config(path_logging, "test", "__main__")

        loggers = [logger.name for logger in logging.getLogger().getChildren()]
        assert "test" in loggers
        assert "__main__" in loggers
        assert MODULE_ROOT in loggers

    ###########################################################################
    ## Empty load defaults test
    ###########################################################################
    @pytest.fixture
    def config_empty(self, config: Config) -> Config:
        """Yields an empty :py:class:`Config` to test as a pytest.fixture"""
        config.loaded = True  # force load to pass despite not having loaded any config
        config.load("this key does not exist")

        # add empty config for each library type
        for name, conf in LOCAL_CONFIG.items():
            config.libraries[name] = conf(settings={"type": name})
        for name, conf in REMOTE_CONFIG.items():
            config.libraries[name] = ConfigRemote(settings={"type": conf.source})

        config.filter = ConfigFilter(settings={})
        config.reports = ConfigReports(settings={})

        return config

    def test_empty_core(self, config_empty: Config, tmp_path: str):
        assert config_empty.output_folder.startswith(join(tmp_path, "_data"))
        assert config_empty.reload == {}
        assert config_empty.pause is None

    @pytest.mark.parametrize("name", LOCAL_CONFIG.keys())
    def test_empty_local(self, config_empty: Config, name: str):
        config = config_empty.libraries[name]
        if not isinstance(config, ConfigLocalBase):
            raise TypeError("Config is not a LocalLibrary config")

        assert config._library is None
        assert config.remote_wrangler is None

        # paths tests
        assert config.stems == {}

        assert config.update.tags == (LocalTrackField.ALL,)
        assert not config.update.replace

        if isinstance(config, ConfigLocalLibrary):
            assert config.playlist_folder is None

            with pytest.raises(ConfigError):
                assert config.library_folders
        elif isinstance(config, ConfigMusicBee):
            with pytest.raises(ConfigError):
                assert config.musicbee_folder
            with pytest.raises(SyncifyError):
                assert config.library

    @pytest.mark.parametrize("name", REMOTE_CONFIG.keys())
    def test_empty_remote(self, config_empty: Config, name: str):
        config = config_empty.libraries[name]
        if not isinstance(config, ConfigRemote):
            raise TypeError("Config is not a RemoteLibrary config")

        assert config.kind == config._classes.source
        assert config._library is None
        assert config.wrangler

        # no API config so these should fail at the Config level
        with pytest.raises(ConfigError):
            assert config.searcher
        with pytest.raises(ConfigError):
            assert config.checker
        with pytest.raises(SyncifyError):
            assert config.library

        assert config.playlists.sync.kind == "new"
        assert config.playlists.sync.reload

        assert config.api.token_path is None
        assert config.api.cache_path is None
        assert config.api.use_cache

        if isinstance(config.api, ConfigSpotify):
            assert config.api.client_id is None
            assert config.api.client_secret is None
            assert config.api.scopes == ()

            with pytest.raises(ConfigError):
                assert config.api.api

    def test_empty_filter(self, config_empty: Config):
        values = ("please", "keep", "all", "of", "these")

        assert config_empty.filter(values) == values
        for conf_library in config_empty.libraries.values():
            assert conf_library.playlists.filter(values) == values

    def test_empty_reports(self, config_empty: Config):
        config = config_empty.reports

        for report in config:
            assert report.enabled
        assert config.missing_tags.tags == (TagFields.ALL,)
        assert not config.missing_tags.match_all

    ###########################################################################
    ## Valid load test
    ###########################################################################
    @pytest.fixture
    def config_valid(self, config: Config) -> Config:
        """Yields :py:class:`Config` with config loaded from a file to test as a pytest.fixture"""
        config.load("valid")
        return config

    def test_load_core(self, config_valid: Config, tmp_path: str):
        assert config_valid.output_folder.startswith(join(tmp_path, "test_folder"))
        assert config_valid.reload == {"main": ("tracks", "playlists"), "spotify": tuple()}
        assert config_valid.pause == "this is a test message"

    @pytest.mark.parametrize("name", LOCAL_CONFIG.keys())
    def test_load_local(self, config_valid: Config, name: str, spotify_wrangler: RemoteDataWrangler):
        config = config_valid.libraries[name]
        if not isinstance(config, ConfigLocalBase):
            raise TypeError("Config is not a LocalLibrary config")

        assert config.kind == next(kind for kind, setter in LOCAL_CONFIG.items() if config.__class__ == setter)
        assert config._library is None
        assert config.remote_wrangler is None
        config.remote_wrangler = spotify_wrangler

        playlist_names = ["cool playlist 1", "awesome playlist", "terrible playlist", "other"]
        assert config.playlists.filter(playlist_names) == ["cool playlist 1", "awesome playlist"]

        if isinstance(config, ConfigLocalLibrary):
            assert config.library_folders == ("/path/to/library",)
            assert config.playlist_folder == "/path/to/playlists"
            assert config.stems == {
                "/different/folder": config.library_folders[0],
                "/another/path": config.library_folders[0],
                "/path/to/library": config.library_folders[0],
            }

            assert config.update.tags == (LocalTrackField.TITLE, LocalTrackField.ARTIST, LocalTrackField.ALBUM)
            assert not config.update.replace

            assert not config.library.library_folders  # folders don't exist so not kept
            assert config.library.playlist_folder is None
            assert config.library.playlist_filter == config.playlists.filter
            # noinspection PyUnresolvedReferences
            assert config.library.path_mapper.stem_map == config.stems
            assert config.library.remote_wrangler == spotify_wrangler

        elif isinstance(config, ConfigMusicBee):
            assert config.musicbee_folder == "/path/to/musicbee_folder"
            assert config.stems == {"../": "/path/to/library"}

            assert config.update.tags == (LocalTrackField.TITLE,)
            assert config.update.replace

            with pytest.raises(FileDoesNotExistError):
                assert config.library

        assert not config.library_loaded

    @pytest.mark.parametrize("name", ["spotify"])
    def test_load_remote(self, config_valid: Config, name: str):
        config = config_valid.libraries[name]
        if not isinstance(config, ConfigRemote):
            raise TypeError("Config is not a RemoteLibrary config")

        assert config.library.source == config.source
        assert config.library.api == config.api.api
        assert config.library.use_cache == config.api.use_cache
        assert config.library.playlist_filter == config.playlists.filter

        assert config.wrangler.source == config.source

        assert config.checker.source == config.source
        assert config.checker.api == config.api.api
        assert config.checker.interval == 200
        assert config.checker.allow_karaoke

        assert config.searcher.source == config.source
        assert config.searcher.api == config.api.api
        assert config.searcher.use_cache == config.api.use_cache

        assert config.playlists.sync.kind == "sync"
        assert not config.playlists.sync.reload
        assert config.playlists.sync.filter == {
            "artist": ("bad artist", "nonce"),
            "album": ("unliked album",),
        }

        assert config.api.token_path == "/path/to/token.json"
        assert config.api.token_path == config.api.api.handler.token_file_path
        assert config.api.cache_path == join(dirname(config_valid.output_folder), "cache")
        assert isinstance(config.api.api.handler.session, CachedSession)
        assert not config.api.use_cache

        if isinstance(config.api, ConfigSpotify):
            assert config.api.client_id == "<CLIENT_ID>"
            assert config.api.client_secret == "<CLIENT_SECRET>"
            assert config.api.scopes == ("user-library-read", "user-follow-read")

        assert not config.library_loaded

    def test_load_filter(self, config_valid: Config):
        config = config_valid.filter

        values = ["include me", "exclude me", "don't include me"]
        assert config(values) == ["include me"]
        assert config.process(values) == ["include me"]

    def test_load_reports(self, config_valid: Config):
        config = config_valid.reports

        assert config.library_differences.enabled

        assert not config.missing_tags.enabled
        assert config.missing_tags.match_all
        tags = (
            LocalTrackField.TITLE,
            LocalTrackField.ARTIST,
            LocalTrackField.ALBUM,
            LocalTrackField.TRACK_NUMBER,
            LocalTrackField.TRACK_TOTAL,
        )
        assert config.missing_tags.tags == tags

    ###########################################################################
    ## Specific property process tests
    ###########################################################################
    @pytest.mark.parametrize("name", LOCAL_CONFIG.keys())
    def test_library_folder_conditions(self, config_empty: Config, name: str):
        config = config_empty.libraries[name]
        if not isinstance(config, ConfigLocalBase):
            raise TypeError("Config is not a LocalLibrary config")

        bad_platform = next(key for key in {"win", "lin", "mac"} if key != config._platform_key)
        config._file["paths"] = {}
        config._paths["library"] = {}
        config._paths["library"][bad_platform] = "/path/to/library/on/other/platform"
        with pytest.raises(ConfigError):
            if isinstance(config, ConfigLocalLibrary):
                assert config.library_folders
            elif isinstance(config, ConfigMusicBee):
                assert config.musicbee_folder

        config._paths["library"][config._platform_key] = "/path/to/library/on/this/platform"
        if isinstance(config, ConfigLocalLibrary):
            assert config.library_folders == (config._paths["library"][config._platform_key],)
        elif isinstance(config, ConfigMusicBee):
            assert config.musicbee_folder == config._paths["library"][config._platform_key]

    @pytest.mark.parametrize("name", REMOTE_CONFIG.keys())
    def test_playlists_sync_kind_fails(self, config_empty: Config, name: str):
        config = config_empty.libraries[name]
        if not isinstance(config, ConfigRemote):
            raise TypeError("Config is not a RemoteLibrary config")

        config.playlists.sync._file["kind"] = "invalid kind"
        with pytest.raises(ConfigError):
            assert config.playlists.sync.kind == config._file["kind"]

    ###########################################################################
    ## Merge tests - override
    ###########################################################################
    def test_core_override(self, config_valid: Config, tmp_path: str):
        old = deepcopy(config_valid)
        config_valid.load("core_override")
        new = config_valid

        assert new.output_folder == old.output_folder  # never overwritten
        assert new.reload == {"spotify": ("extend",)}
        assert new.pause is None

        playlist_names = ["cool playlist 1", "awesome playlist", "terrible playlist", "other"]
        assert new.filter.process(playlist_names) == ["cool playlist 1", "awesome playlist"]

        # reports always revert to default values when not defined and override is True
        assert not new.reports.library_differences.enabled
        assert new.reports.missing_tags.enabled
        assert new.reports.missing_tags.tags == (TagFields.ALL,)
        assert not new.reports.missing_tags.match_all

    def test_override_local(self, config_valid: Config):
        name = "local"

        old = config_valid.libraries[name]
        if not isinstance(old, ConfigLocalBase):
            raise TypeError("Config is not a LocalLibrary config")
        old_library = old.library

        config_valid.load("local_override")
        new = config_valid.libraries[name]
        if not isinstance(new, ConfigLocalBase):
            raise TypeError("Config is not a LocalLibrary config")

        assert new != old
        assert new.kind == old.kind == name

        # overriden values
        assert new.playlists.filter.comparers[0].condition == "is_in"
        assert new.playlists.filter.comparers[0].expected == ["new playlist to include", "include me now too"]
        assert new.playlists.filter.comparers[1].condition == "is_not"
        assert new.playlists.filter.comparers[1].expected == ["and don't include me"]

        assert new.update.tags == (LocalTrackField.GENRES,)
        assert new.update.replace

        if isinstance(new, ConfigLocalLibrary):
            assert new.library_folders == ("/new/path/to/library",)
            assert new.playlist_folder == "/new/path/to/playlists"

        # kept values
        assert new.stems == old.stems

        # the library was instantiated already so the new library should be forcibly overriden
        assert id(old_library) == id(new.library)

        assert not new.library_loaded and not old.library_loaded

    def test_override_remote(self, config_valid: Config):
        name = "spotify"

        old = config_valid.libraries[name]
        if not isinstance(old, ConfigRemote):
            raise TypeError("Config is not a RemoteLibrary config")
        old_library = old.library
        old_api = old.api.api
        old.library_loaded = True

        config_valid.load("remote_override")
        new = config_valid.libraries[name]
        if not isinstance(new, ConfigRemote):
            raise TypeError("Config is not a RemoteLibrary config")

        # new values
        assert new.api.use_cache

        assert new.checker.interval == 100
        assert not new.checker.allow_karaoke

        assert new.playlists.filter.comparers[0].condition == "is_not"
        assert new.playlists.filter.comparers[0].expected == ["terrible playlist"]
        assert new.playlists.sync.kind == "refresh"
        assert new.playlists.sync.reload
        assert new.playlists.sync.filter == {
            "title": ("bar title",),
            "artist": ("bad artist", "nonce", "another nonce"),
        }

        assert new.searcher.use_cache

        # old values
        assert new.wrangler.source == old.wrangler.source
        assert new.checker.source == old.checker.source
        assert new.searcher.source == old.searcher.source

        # the library and api were instantiated already so the new library and api should be forcibly overriden
        assert id(old_library) == id(new.library)
        assert id(old_api) == id(new.api.api)
        assert new.checker.api == old.checker.api
        assert new.searcher.api == old.searcher.api

        if isinstance(new.api, ConfigSpotify):
            assert new.api.client_id == "<CLIENT_ID>"
            assert new.api.client_secret == "<CLIENT_SECRET>"
            assert new.api.scopes == ("user-library-read", "user-follow-read")

        assert new.library_loaded and old.library_loaded

    ###########################################################################
    ## Merge tests - no override
    ###########################################################################
    def test_core_enrich(self, config_valid: Config, tmp_path: str):
        old = deepcopy(config_valid)
        config_valid.load("core_enrich")
        new = config_valid

        assert new.output_folder == old.output_folder  # never overwritten
        assert new.reload == {"spotify": ("extend",)}
        assert new.pause is None

        # filter is always overriden
        playlist_names = ["cool playlist 1", "awesome playlist", "terrible playlist", "other"]
        assert new.filter.process(playlist_names) == ["cool playlist 1", "awesome playlist"]

        assert not new.reports.library_differences.enabled
        assert new.reports.missing_tags.enabled
        assert new.reports.missing_tags.match_all
        tags = (
            LocalTrackField.TITLE,
            LocalTrackField.ARTIST,
            LocalTrackField.ALBUM,
            LocalTrackField.TRACK_NUMBER,
            LocalTrackField.TRACK_TOTAL,
        )
        assert new.reports.missing_tags.tags == tags

    def test_local_enrich(self, config_valid: Config):
        name = "local"

        old = config_valid.libraries[name]
        if not isinstance(old, ConfigLocalBase):
            raise TypeError("Config is not a LocalLibrary config")
        old_library = old.library

        config_valid.load("local_enrich")
        new = config_valid.libraries[name]
        if not isinstance(new, ConfigLocalBase):
            raise TypeError("Config is not a LocalLibrary config")

        assert new != old
        assert new.kind == old.kind == name

        # overriden values
        assert new.playlists.filter.comparers[0].condition == "is_in"
        assert new.playlists.filter.comparers[0].expected == ["new playlist to include", "include me now too"]
        assert new.playlists.filter.comparers[1].condition == "is_not"
        assert new.playlists.filter.comparers[1].expected == ["and don't include me"]

        # kept values
        assert new.stems == old.stems

        assert new.update.tags == old.update.tags
        assert new.update.replace == old.update.replace

        if isinstance(new, ConfigLocalLibrary) and isinstance(old, ConfigLocalLibrary):
            assert new.library_folders == old.library_folders
            assert new.playlist_folder == old.playlist_folder

        # the library was instantiated already so the new library should be forcibly overriden
        assert id(old_library) == id(new.library)

        assert not new.library_loaded and not old.library_loaded

    def test_remote_enrich(self, config_valid: Config):
        name = "spotify"

        old = config_valid.libraries[name]
        if not isinstance(old, ConfigRemote):
            raise TypeError("Config is not a RemoteLibrary config")
        old_library = old.library
        old_api = old.api.api

        config_valid.load("remote_enrich")
        new = config_valid.libraries[name]
        if not isinstance(new, ConfigRemote):
            raise TypeError("Config is not a RemoteLibrary config")

        # new values
        assert new.playlists.filter.comparers[0].condition == "is_not"
        assert new.playlists.filter.comparers[0].expected == ["terrible playlist"]

        # kept values
        assert new.api.use_cache == old.api.use_cache

        assert new.wrangler.source == old.wrangler.source

        assert new.checker.source == old.checker.source
        assert new.checker.interval == old.checker.interval
        assert new.checker.allow_karaoke == old.checker.allow_karaoke

        assert new.searcher.source == old.searcher.source
        assert new.searcher.use_cache == old.searcher.use_cache

        assert new.playlists.sync.kind == old.playlists.sync.kind
        assert new.playlists.sync.reload == old.playlists.sync.reload
        assert new.playlists.sync.filter == old.playlists.sync.filter

        # the library and api were instantiated already so the new library and api should be forcibly overriden
        assert id(old_library) == id(new.library)
        assert id(old_api) == id(new.api.api)
        assert new.checker.api == old.checker.api
        assert new.searcher.api == old.searcher.api

        if isinstance(new.api, ConfigSpotify):
            assert new.api.client_id == "<CLIENT_ID>"
            assert new.api.client_secret == "<CLIENT_SECRET>"
            assert new.api.scopes == ("user-library-read", "user-follow-read")

        assert not new.library_loaded and not old.library_loaded
