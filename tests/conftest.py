import asyncio
import copy
import logging.config
import shutil
import types
from collections import defaultdict
from pathlib import Path

import pytest
import yaml
from _pytest.fixtures import SubRequest
# noinspection PyProtectedMember
from _pytest.logging import LogCaptureHandler, _remove_ansi_escape_sequences
from aiorequestful.types import UnitCollection

from musify import MODULE_ROOT
from musify.libraries.remote.core.types import RemoteObjectType
from musify.libraries.remote.spotify.api import SpotifyAPI
from musify.libraries.remote.spotify.wrangle import SpotifyDataWrangler
from musify.logger import MusifyLogger
from musify.utils import to_collection
from tests.libraries.remote.core.utils import ALL_ITEM_TYPES
from tests.libraries.remote.spotify.api.mock import SpotifyMock
from tests.utils import idfn, path_resources


@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# noinspection PyUnusedLocal
@pytest.hookimpl
def pytest_configure(config: pytest.Config):
    """Loads logging config"""
    config_file = path_resources.joinpath("test_logging").with_suffix(".yml")
    if not config_file.is_file():
        return

    with open(config_file, "r", encoding="utf-8") as file:
        log_config = yaml.full_load(file)

    log_config.pop("compact", False)
    MusifyLogger.disable_bars = True
    MusifyLogger.compact = True

    for formatter in log_config["formatters"].values():  # ensure ANSI colour codes in format are recognised
        formatter["format"] = formatter["format"].replace(r"\33", "\33")

    log_config["loggers"][MODULE_ROOT] = log_config["loggers"]["test"]
    logging.config.dictConfig(log_config)


def pytest_collection_modifyitems(items: list[pytest.Function]):
    """Modifies test items in-place, ordering them based on assigned marks."""
    marker_name_order = []  # currently not implemented

    def _get_item_order_index(item: pytest.Function) -> int:
        try:
            name = next(marker.name for marker in item.own_markers if marker.name.casefold() in marker_name_order)
            return marker_name_order.index(name.casefold())
        except (StopIteration, ValueError):
            return len(marker_name_order)

    items.sort(key=_get_item_order_index)


# This is a fork of the pytest-lazy-fixture package
# Fixes applied for issues with pytest >8.0: https://github.com/TvoroG/pytest-lazy-fixture/issues/65
# noinspection PyProtectedMember
@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    if hasattr(item, "_request"):
        item._request._fillfixtures = types.MethodType(
            fillfixtures(item._request._fillfixtures), item._request
        )


def fillfixtures(_fillfixtures):
    # noinspection PyProtectedMember
    def fill(request):
        item = request._pyfuncitem
        fixturenames = getattr(item, "fixturenames", None)
        if fixturenames is None:
            fixturenames = request.fixturenames

        if hasattr(item, "callspec"):
            for param, val in sorted_by_dependency(item.callspec.params, fixturenames):
                if val is not None and is_lazy_fixture(val):
                    item.callspec.params[param] = request.getfixturevalue(val.name)
                elif param not in item.funcargs:
                    item.funcargs[param] = request.getfixturevalue(param)

        _fillfixtures()
    return fill


# noinspection PyUnusedLocal
@pytest.hookimpl(tryfirst=True)
def pytest_fixture_setup(fixturedef, request):
    val = getattr(request, "param", None)
    if is_lazy_fixture(val):
        request.param = request.getfixturevalue(val.name)


# noinspection PyProtectedMember
def pytest_runtest_call(item):
    if hasattr(item, "funcargs"):
        for arg, val in item.funcargs.items():
            if is_lazy_fixture(val):
                item.funcargs[arg] = item._request.getfixturevalue(val.name)


# noinspection PyUnusedLocal
@pytest.hookimpl(hookwrapper=True)
def pytest_pycollect_makeitem(collector, name, obj):
    # noinspection PyGlobalUndefined
    global current_node
    current_node = collector
    yield
    current_node = None


# noinspection PyUnusedLocal
def pytest_make_parametrize_id(config, val, argname):
    if is_lazy_fixture(val):
        return val.name


@pytest.hookimpl(hookwrapper=True)
def pytest_generate_tests(metafunc):
    yield

    normalize_metafunc_calls(metafunc)


# noinspection PyProtectedMember
def normalize_metafunc_calls(metafunc, used_keys=None):
    newcalls = []
    for callspec in metafunc._calls:
        calls = normalize_call(callspec, metafunc, used_keys)
        newcalls.extend(calls)
    metafunc._calls = newcalls


# noinspection PyProtectedMember
def copy_metafunc(metafunc):
    copied = copy.copy(metafunc)
    copied.fixturenames = copy.copy(metafunc.fixturenames)
    copied._calls = []

    try:
        copied._ids = copy.copy(metafunc._ids)
    except AttributeError:
        # pytest>=5.3.0
        pass

    copied._arg2fixturedefs = copy.copy(metafunc._arg2fixturedefs)
    return copied


# noinspection PyProtectedMember
def normalize_call(callspec, metafunc, used_keys):
    fm = metafunc.config.pluginmanager.get_plugin("funcmanage")

    used_keys = used_keys or set()
    keys = set(callspec.params.keys()) - used_keys

    for arg in keys:
        val = callspec.params[arg]
        if is_lazy_fixture(val):
            try:
                if pytest.version_tuple >= (8, 0, 0):
                    fixturenames_closure, arg2fixturedefs = fm.getfixtureclosure(
                        metafunc.definition.parent, [val.name], {}
                    )
                else:
                    _, fixturenames_closure, arg2fixturedefs = fm.getfixtureclosure(
                        [val.name], metafunc.definition.parent
                    )

            except ValueError:
                # 3.6.0 <= pytest < 3.7.0; `FixtureManager.getfixtureclosure` returns 2 values
                fixturenames_closure, arg2fixturedefs = fm.getfixtureclosure([val.name], metafunc.definition.parent)
            except AttributeError:
                # pytest < 3.6.0; `Metafunc` has no `definition` attribute
                fixturenames_closure, arg2fixturedefs = fm.getfixtureclosure([val.name], current_node)

            extra_fixturenames = [fname for fname in fixturenames_closure if fname not in callspec.params]

            newmetafunc = copy_metafunc(metafunc)
            newmetafunc.fixturenames = extra_fixturenames
            newmetafunc._arg2fixturedefs.update(arg2fixturedefs)
            newmetafunc._calls = [callspec]
            fm.pytest_generate_tests(newmetafunc)

            normalize_metafunc_calls(newmetafunc, used_keys | {arg})
            return newmetafunc._calls

        used_keys.add(arg)
    return [callspec]


def sorted_by_dependency(params, fixturenames):
    free_fm = []
    non_free_fm = defaultdict(list)

    for key in _sorted_argnames(params, fixturenames):
        val = params.get(key)

        if key not in params or not is_lazy_fixture(val) or val.name not in params:
            free_fm.append(key)
        else:
            non_free_fm[val.name].append(key)

    non_free_fm_list = []
    for free_key in free_fm:
        non_free_fm_list.extend(
            _tree_to_list(non_free_fm, free_key)
        )

    return [(key, params.get(key)) for key in (free_fm + non_free_fm_list)]


def _sorted_argnames(params, fixturenames):
    argnames = set(params.keys())

    for name in fixturenames:
        if name in argnames:
            argnames.remove(name)
        yield name

    if argnames:
        for name in argnames:
            yield name


def _tree_to_list(trees, leave):
    lst = []
    for ls in trees[leave]:
        lst.append(ls)
        lst.extend(
            _tree_to_list(trees, ls)
        )
    return lst


def lazy_fixture(names):
    if isinstance(names, str):
        return LazyFixture(names)
    else:
        return [LazyFixture(name) for name in names]


pytest.lazy_fixture = lazy_fixture


def is_lazy_fixture(val):
    return isinstance(val, LazyFixture)


class LazyFixture(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<{} "{}">'.format(self.__class__.__name__, self.name)

    def __eq__(self, other):
        return self.name == other.name


class LogCapturer(LogCaptureHandler):
    """
    Fixture to capture logs regardless of the Propagate flag. See
    https://github.com/pytest-dev/pytest/issues/3697 for details.
    """

    @property
    def text(self) -> str:
        return _remove_ansi_escape_sequences(self.stream.getvalue())

    @property
    def messages(self) -> list[str]:
        return [_remove_ansi_escape_sequences(record.getMessage()) for record in self.records]

    def __init__(self):
        super().__init__()
        self._level: int = logging.INFO
        self._loggers: list[logging.Logger] = []

        self._original_levels: dict[logging.Logger, int] = {}
        self._raw_messages: list[str] = []

    def set_level(self, level: int) -> None:
        """Set the level at which to capture logs"""
        self._level = level

    def add_logger(self, logger: logging.Logger) -> None:
        """Set the logger on which to capture logs"""
        self._loggers.append(logger)

    def emit(self, record: logging.LogRecord) -> None:
        if hasattr(record, "message"):
            self._raw_messages.append(record.message)
        super().emit(record)

    def __call__(self, level: int | None = None, loggers: UnitCollection[logging.Logger] | None = None):
        if level is not None:
            self._level = level
        if loggers is not None:
            self._loggers = to_collection(loggers, list)
        return self

    def __enter__(self):
        self.clear()

        for logger in self._loggers:
            self._original_levels[logger] = logger.level
            logger.setLevel(self._level)
            logger.addHandler(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._level = logging.INFO
        self._loggers = []

        for logger, level in self._original_levels.items():
            logger.setLevel(level)
            logger.removeHandler(self)


@pytest.fixture
def log_capturer() -> LogCapturer:
    return LogCapturer()


@pytest.fixture
def path(request: pytest.FixtureRequest | SubRequest, tmp_path: Path) -> Path:
    """
    Copy the path of the source file to the test cache for this test and return the cache path.
    Deletes the test folder when test is done.
    """
    if hasattr(request, "param"):
        src_path = request.param
    else:  # assume path is given at the top-level fixture, get param from this request
        # noinspection PyProtectedMember
        src_path = request._pyfuncitem.callspec.params[request._parent_request.fixturename]

    src_path = Path(src_path)
    trg_path = tmp_path.joinpath(src_path.name)

    trg_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src_path, trg_path)

    yield trg_path

    shutil.rmtree(trg_path.parent)


@pytest.fixture(scope="session", params=ALL_ITEM_TYPES, ids=idfn)
def object_type(request) -> RemoteObjectType:
    """Yields the valid :py:class:`RemoteObjectTypes` to use throughout tests in this suite as a pytest.fixture."""
    return request.param


@pytest.fixture(scope="session")
def spotify_wrangler():
    """Yields a :py:class:`SpotifyDataWrangler` for testing Spotify data wrangling"""
    return SpotifyDataWrangler()


@pytest.fixture(scope="session")
def spotify_mock() -> SpotifyMock:
    """Yield an authorised and configured :py:class:`SpotifyMock` object"""
    with SpotifyMock() as m:
        yield m


@pytest.fixture(scope="session")
async def spotify_api(spotify_mock: SpotifyMock) -> SpotifyAPI:
    """Yield an authorised :py:class:`SpotifyAPI` object"""
    token = {"access_token": "fake access token", "token_type": "Bearer", "scope": "test-read"}
    # disable any token tests by settings test_* kwargs as appropriate
    api = SpotifyAPI()
    api.handler.authoriser.response.replace(token)
    api.handler.authoriser.tester.response_test = None
    api.handler.authoriser.tester.max_expiry = 0

    # force no backoff/wait settings
    api.handler.wait_timer = None
    api.handler.retry_timer = None

    async with api as a:
        spotify_mock.reset()
        yield a
