# TODO: write tests
from os.path import join, dirname

import pytest
from pytest_lazyfixture import lazy_fixture

from syncify import PACKAGE_ROOT
from syncify.abstract.enums import TagFields
from syncify.config import Config, LOCAL_CONFIG, REMOTE_CONFIG, ConfigRemote, ConfigLocal, ConfigMusicBee, \
    ConfigSpotify, ConfigFilter, ConfigPlaylists, ConfigReports
from syncify.exception import ConfigError, SyncifyError
from syncify.fields import LocalTrackField
from tests.abstract.misc import PrettyPrinterTester
from tests.utils import path_resources

path_config = join(path_resources, "config_test.yml")


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

    def test_load_empty(self, config_empty: Config, tmp_path: str):
        assert config_empty.output_folder.startswith(join(tmp_path, "_data"))
        assert config_empty.dry_run
        assert config_empty.reload == {}
        assert config_empty.pause is None

        for name, conf_library in config_empty.libraries.items():
            self.assert_empty_config_filter(conf_library.playlists)
            assert conf_library.playlists.filter == {}

            if isinstance(conf_library, ConfigLocal):
                self.assert_empty_config_local(conf_library, name=name)
            elif isinstance(conf_library, ConfigRemote):
                self.assert_empty_config_remote(conf_library)

        self.assert_empty_config_filter(config_empty.filter)

        for report in config_empty.reports:
            assert report.enabled
        assert config_empty.reports.missing_tags.tags == (TagFields.ALL,)
        assert not config_empty.reports.missing_tags.match_all

    @staticmethod
    def assert_empty_config_local(config: ConfigLocal, name: str):
        assert config.kind == name
        assert config._library is None
        assert config.remote_wrangler is None

        # paths tests
        with pytest.raises(ConfigError):
            assert config.library_folder

        bad_platform = next(key for key in {"win", "lin", "mac"} if key != config._platform_key)
        config._file["paths"] = {}
        config._paths["library"] = {}
        config._paths["library"][bad_platform] = "/path/to/library/on/other/platform"
        with pytest.raises(ConfigError):
            assert config.library_folder

        config._paths["library"][config._platform_key] = "/path/to/library/on/this/platform"
        assert config.library_folder == config._paths["library"][config._platform_key]

        assert config.other_folders == ()

        assert config.update.tags == (LocalTrackField.ALL,)
        assert not config.update.replace

        if isinstance(config, ConfigMusicBee):
            assert config.playlist_folder == "Playlists"
            assert config.musicbee_folder == "MusicBee"

            with pytest.raises(SyncifyError):
                assert config.library
        else:
            assert config.playlist_folder is None

    @staticmethod
    def assert_empty_config_remote(config: ConfigRemote):
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
        assert config.api.cache_path == ".api_cache"
        assert config.api.use_cache

        if isinstance(config.api, ConfigSpotify):
            assert config.api.client_id is None
            assert config.api.client_secret is None
            assert config.api.scopes == ()

            with pytest.raises(ConfigError):
                assert config.api.api

    def assert_empty_config_playlists(self, config: ConfigPlaylists):
        self.assert_empty_config_filter(config)
        assert config.filter == {}

    @staticmethod
    def assert_empty_config_filter(config: ConfigFilter):
        def assert_empty_config_options(options: ConfigFilter.ConfigFilterOptions):
            assert options.available is None
            assert options.values == ()
            assert options.prefix is None
            assert options.start is None
            assert options.stop is None

            assert options.process(values) == tuple(values)  # no filter happens
            assert len(options) == 0

        values = ["please", "keep", "all", "of", "these"]
        assert_empty_config_options(config.include)
        assert_empty_config_options(config.exclude)
        assert config.process(values)

    ###########################################################################
    ## Valid load test
    ###########################################################################
    @pytest.fixture
    def config_valid(self, config: Config) -> Config:
        """Yields :py:class:`Config` with config loaded from a file to test as a pytest.fixture"""
        config.load("valid")
        return config

    def test_load(self, config_valid: Config, tmp_path: str):
        assert config_valid.output_folder.startswith(join(tmp_path, "test_folder"))
        assert not config_valid.dry_run
        assert config_valid.reload == {"main": tuple(), "spotify": tuple()}
        assert config_valid.pause == "this is a test message"

        for name, conf_library in config_valid.libraries.items():
            self.assert_valid_config_filter(conf_library.playlists)
            assert conf_library.playlists.filter == {}

            if isinstance(conf_library, ConfigLocal):
                self.assert_valid_config_local(conf_library, name=name)
            elif isinstance(conf_library, ConfigRemote):
                self.assert_valid_config_remote(conf_library)

        self.assert_valid_config_filter(config_valid.filter)

        assert config_valid.reports.library_differences.enabled

        assert not config_valid.reports.missing_tags.enabled
        assert config_valid.reports.missing_tags.match_all
        tags = (
            LocalTrackField.TITLE,
            LocalTrackField.ARTIST,
            LocalTrackField.ALBUM,
            LocalTrackField.TRACK_NUMBER,
            LocalTrackField.TRACK_TOTAL,
        )
        assert config_valid.reports.missing_tags.tags == tags

    @staticmethod
    def assert_valid_config_local(config: ConfigLocal, name: str):
        assert config.kind == name
        assert config._library is None
        assert config.remote_wrangler is None

        # paths tests
        with pytest.raises(ConfigError):
            assert config.library_folder

        bad_platform = next(key for key in {"win", "lin", "mac"} if key != config._platform_key)
        config._file["paths"] = {}
        config._paths["library"] = {}
        config._paths["library"][bad_platform] = "/path/to/library/on/other/platform"
        with pytest.raises(ConfigError):
            assert config.library_folder

        config._paths["library"][config._platform_key] = "/path/to/library/on/this/platform"
        assert config.library_folder == config._paths["library"][config._platform_key]

        assert config.other_folders == ()

        assert config.update.tags == (LocalTrackField.ALL,)
        assert not config.update.replace

        if isinstance(config, ConfigMusicBee):
            assert config.playlist_folder == "Playlists"
            assert config.musicbee_folder == "MusicBee"

            with pytest.raises(SyncifyError):
                assert config.library
        else:
            assert config.playlist_folder is None

    @staticmethod
    def assert_valid_config_remote(config: ConfigRemote):
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
        assert config.api.cache_path == ".api_cache"
        assert config.api.use_cache

        if isinstance(config.api, ConfigSpotify):
            assert config.api.client_id is None
            assert config.api.client_secret is None
            assert config.api.scopes == ()

            with pytest.raises(ConfigError):
                assert config.api.api

    @staticmethod
    def assert_valid_config_filter(config: ConfigFilter):
        def assert_valid_config_options(options: ConfigFilter.ConfigFilterOptions):
            assert options.available is None
            assert options.values == ()
            assert options.prefix is None
            assert options.start is None
            assert options.stop is None

            assert options.process(values) == tuple(values)  # no filter happens
            assert len(options) == 0

        values = ["please", "keep", "all", "of", "these"]
        assert_valid_config_options(config.include)
        assert_valid_config_options(config.exclude)
        assert config.process(values)
