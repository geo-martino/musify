import logging.config
import os
import shutil
from os.path import join, basename, dirname
from pathlib import Path
from typing import Any

import pytest
import yaml
from _pytest.fixtures import SubRequest

from musify import MODULE_ROOT
from musify.shared.api.request import RequestHandler
from musify.shared.logger import MusifyLogger
from musify.spotify.api import SpotifyAPI
from musify.spotify.processors.wrangle import SpotifyDataWrangler
from tests.spotify.api.mock import SpotifyMock


# noinspection PyUnusedLocal
@pytest.hookimpl
def pytest_configure(config: pytest.Config):
    """Loads logging config"""
    config_file = join(dirname(dirname(__file__)), "logging.yml")
    with open(config_file, "r", encoding="utf-8") as file:
        log_config = yaml.full_load(file)

    log_config.pop("compact", False)
    MusifyLogger.disable_bars = True
    MusifyLogger.compact = True

    def remove_file_handler(c: dict[str, Any]) -> None:
        """Remove all config for file handlers"""
        for k, v in c.items():
            if k == "handlers" and isinstance(v, list) and "file" in v:
                v.pop(v.index("file"))
            elif k == "handlers" and isinstance(v, dict) and "file" in v:
                v.pop("file")
            elif isinstance(v, dict):
                remove_file_handler(v)

    remove_file_handler(log_config)

    for formatter in log_config["formatters"].values():  # ensure ANSI colour codes in format are recognised
        formatter["format"] = formatter["format"].replace(r"\33", "\33")

    log_config["loggers"][MODULE_ROOT] = log_config["loggers"]["test"]
    logging.config.dictConfig(log_config)


@pytest.fixture
def path(request: pytest.FixtureRequest | SubRequest, tmp_path: Path) -> str:
    """
    Copy the path of the source file to the test cache for this test and return the cache path.
    Deletes the test folder when test is done.
    """
    if hasattr(request, "param"):
        src_path = request.param
    else:  # assume path is given at the top-level fixture, get param from this request
        # noinspection PyProtectedMember
        src_path = request._pyfuncitem.callspec.params[request._parent_request.fixturename]

    trg_path = join(tmp_path, basename(src_path))

    os.makedirs(dirname(trg_path), exist_ok=True)
    shutil.copyfile(src_path, trg_path)

    yield trg_path

    shutil.rmtree(dirname(trg_path))


@pytest.fixture(scope="session")
def spotify_wrangler():
    """Yields a :py:class:`SpotifyDataWrangler` for testing Spotify data wrangling"""
    return SpotifyDataWrangler()


@pytest.fixture(scope="session")
def spotify_api(spotify_mock: SpotifyMock) -> SpotifyAPI:
    """Yield an authorised :py:class:`SpotifyAPI` object"""
    token = {"access_token": "fake access token", "token_type": "Bearer", "scope": "test-read"}
    api = SpotifyAPI(cache_path=None)
    api.handler = RequestHandler(name=api.source, token=token, cache_path=None)
    return api


@pytest.fixture(scope="session")
def spotify_mock() -> SpotifyMock:
    """Yield an authorised :py:class:`SpotifyMock` object"""
    with SpotifyMock() as m:
        yield m
