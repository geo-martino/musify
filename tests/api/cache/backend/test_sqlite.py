import json
import sqlite3
from datetime import datetime, timedelta
from random import randrange
from typing import Any
from urllib.parse import urlparse

import pytest
from requests import Response, Request

from musify.api.cache.backend.base import RequestSettings, PaginatedRequestSettings
from musify.api.cache.backend.sqlite import SQLiteTable, SQLiteCache
from tests.api.cache.backend.testers import ResponseRepositoryTester, ResponseCacheTester
from tests.utils import random_str


class SQLiteTester:
    @staticmethod
    @pytest.fixture
    def connection() -> sqlite3.Connection:
        """Yields a valid :py:class:`Connection` to use throughout tests in this suite as a pytest.fixture."""
        return sqlite3.Connection(database="file::memory:")


class TestSQLiteTable(SQLiteTester, ResponseRepositoryTester):

    @pytest.fixture
    def repository(
            self, settings: RequestSettings, connection: sqlite3.Connection, valid_items: dict, invalid_items: dict
    ) -> SQLiteTable:
        expire = timedelta(days=2)
        repository = SQLiteTable(connection=connection, settings=settings, expire=expire)

        query = "\n".join((
            f"INSERT OR REPLACE INTO {settings.name} (",
            f"\t{", ".join(repository._primary_key_columns)}, {repository.expiry_key}, {repository.data_key}",
            ") ",
            f"VALUES ({",".join("?" * len(repository._primary_key_columns))},?,?);",
        ))
        parameters = [
            (*key, repository.expire.isoformat(), repository.serialise(value))
            for key, value in valid_items.items()
        ]
        invalid_expire_dt = datetime.now() - expire  # expiry time in the past, response cache has expired
        parameters.extend(
            (*key, invalid_expire_dt.isoformat(), repository.serialise(value))
            for key, value in invalid_items.items()
        )
        connection.executemany(query, parameters)

        return repository

    @property
    def connection_closed_exception(self) -> type[Exception]:
        return sqlite3.DatabaseError

    @staticmethod
    def generate_item(settings: RequestSettings) -> tuple[tuple, dict[str, Any]]:
        key = ("GET", random_str(30, 50),)
        value = {
            random_str(10, 30): random_str(10, 30),
            random_str(10, 30): randrange(0, 100),
            str(randrange(0, 100)): random_str(10, 30),
            str(randrange(0, 100)): randrange(0, 100),
        }

        if isinstance(settings, PaginatedRequestSettings):
            key = (*key, randrange(0, 100), randrange(1, 50))

        return key, value

    @staticmethod
    def generate_response_from_item(settings: RequestSettings, key: tuple, value: dict[str, Any]) -> Response:
        url = f"http://test.com/{settings.name}/{key[1]}"
        params = {}
        if len(key) == 4:
            params["offset"] = key[2]
            params["page_count"] = key[3]

        request = Request(method=key[0], url=url, params=params).prepare()

        response = Response()
        response.encoding = "utf-8"
        response._content = json.dumps(value).encode(response.encoding)
        response.status_code = 200
        response.url = request.url
        response.request = request

        return response

    def test_init(self, connection: sqlite3.Connection, settings: RequestSettings):
        SQLiteTable(connection=connection, settings=settings)

        cur = connection.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{settings.name}'"
        )
        rows = cur.fetchall()

        assert len(rows) == 1
        assert rows[0][0] == settings.name

    def test_serialise(self, repository: SQLiteTable):
        _, value = self.generate_item(repository.settings)
        value_serialised = repository.serialise(value)

        assert isinstance(value_serialised, str)
        assert repository.serialise(value_serialised) == value_serialised

    def test_deserialise(self, repository: SQLiteTable):
        _, value = self.generate_item(repository.settings)
        value_str = json.dumps(value)
        value_deserialised = repository.deserialise(value_str)

        assert isinstance(value_deserialised, dict)
        assert repository.deserialise(value_deserialised) == value


class TestSQLiteCache(SQLiteTester, ResponseCacheTester):

    @staticmethod
    def generate_response(settings: RequestSettings) -> Response:
        key, value = TestSQLiteTable.generate_item(settings)
        return TestSQLiteTable.generate_response_from_item(settings, key, value)

    @classmethod
    def generate_cache(cls, connection: sqlite3.Connection) -> SQLiteCache:
        cache = SQLiteCache(cache_name="test", connection=connection)
        cache.repository_getter = cls.get_repository_from_url

        for _ in range(randrange(5, 10)):
            settings = cls.generate_settings()
            items = dict(TestSQLiteTable.generate_item(settings) for _ in range(randrange(3, 6)))

            repository = SQLiteTable(settings=settings, connection=connection)
            repository.update(items)
            cache[settings.name] = repository

        return cache

    @staticmethod
    def get_repository_from_url(cache: SQLiteCache, url: str) -> SQLiteCache | None:
        for name, repository in cache.items():
            if name == urlparse(url).path.split("/")[-2]:
                return repository

    @pytest.mark.skip(reason="Not yet implemented")
    def test_connect_with_path(self):
        pass  # TODO

    @pytest.mark.skip(reason="Not yet implemented")
    def test_connect_with_in_memory_db(self):
        pass  # TODO

    @pytest.mark.skip(reason="Not yet implemented")
    def test_connect_with_temp_db(self):
        pass  # TODO
