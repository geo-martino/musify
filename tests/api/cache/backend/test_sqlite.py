import contextlib
import json
import sqlite3
from datetime import datetime, timedelta
from os.path import join
from pathlib import Path
from random import randrange
from tempfile import gettempdir
from typing import Any
from urllib.parse import urlparse

import aiosqlite
import pytest
from requests import Response, Request

from musify.api.cache.backend.base import RequestSettings, PaginatedRequestSettings
from musify.api.cache.backend.sqlite import SQLiteTable, SQLiteCache
from tests.api.cache.backend.testers import ResponseRepositoryTester, ResponseCacheTester, BaseResponseTester
from tests.utils import random_str


class SQLiteTester(BaseResponseTester):
    """Supplies common functionality expected of all SQLite test suites."""

    @staticmethod
    def generate_connection() -> sqlite3.Connection:
        return aiosqlite.connect(":memory:")

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
            params["size"] = key[3]

        request = Request(method=key[0], url=url, params=params).prepare()

        response = Response()
        response.encoding = "utf-8"
        response._content = json.dumps(value).encode(response.encoding)
        response.status_code = 200
        response.url = request.url
        response.request = request

        return response


class TestSQLiteTable(SQLiteTester, ResponseRepositoryTester):

    @pytest.fixture
    async def repository(
            self, connection: aiosqlite.Connection, settings: RequestSettings, valid_items: dict, invalid_items: dict
    ) -> SQLiteTable:
        expire = timedelta(days=2)

        async with await SQLiteTable.create(connection, settings=settings, expire=expire) as repository:
            columns = (
                *repository._primary_key_columns,
                repository.cached_column,
                repository.expiry_column,
                repository.data_column
            )
            query = "\n".join((
                f"INSERT OR REPLACE INTO {settings.name} (",
                f"\t{", ".join(columns)}",
                ") ",
                f"VALUES ({",".join("?" * len(columns))});",
            ))
            parameters = [
                (*key, datetime.now().isoformat(), repository.expire.isoformat(), repository.serialize(value))
                for key, value in valid_items.items()
            ]
            invalid_expire_dt = datetime.now() - expire  # expiry time in the past, response cache has expired
            parameters.extend(
                (*key, datetime.now().isoformat(), invalid_expire_dt.isoformat(), repository.serialize(value))
                for key, value in invalid_items.items()
            )

            await connection.executemany(query, parameters)
            await connection.commit()

            yield repository

    async def test_init(self, connection: aiosqlite.Connection, settings: RequestSettings):
        async with await SQLiteTable.create(connection, settings=settings) as repository:
            async with connection.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{settings.name}'"
            ) as cur:
                rows = await cur.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == settings.name

            async with connection.execute(f"SELECT name FROM pragma_table_info('{settings.name}');") as cur:
                columns = {row[0] async for row in cur}
            assert {repository.name_column, repository.data_column, repository.expiry_column}.issubset(columns)
            assert set(repository._primary_key_columns).issubset(columns)

    def test_serialize(self, repository: SQLiteTable):
        _, value = self.generate_item(repository.settings)
        value_serialized = repository.serialize(value)

        assert isinstance(value_serialized, str)
        assert repository.serialize(value_serialized) == value_serialized

        assert repository.serialize("I am not a valid JSON") is None

    # noinspection PyTypeChecker
    def test_deserialize(self, repository: SQLiteTable):
        _, value = self.generate_item(repository.settings)
        value_str = json.dumps(value)
        value_deserialized = repository.deserialize(value_str)

        assert isinstance(value_deserialized, dict)
        assert repository.deserialize(value_deserialized) == value

        assert repository.deserialize(None) is None
        assert repository.deserialize(123) is None


class TestSQLiteCache(SQLiteTester, ResponseCacheTester):

    @staticmethod
    def generate_response(settings: RequestSettings) -> Response:
        key, value = TestSQLiteTable.generate_item(settings)
        return TestSQLiteTable.generate_response_from_item(settings, key, value)

    @classmethod
    @contextlib.asynccontextmanager
    async def generate_cache(cls, connection: aiosqlite.Connection) -> SQLiteCache:
        async with SQLiteCache(cache_name="test", connection=connection) as cache:
            cache.repository_getter = cls.get_repository_from_url

            for _ in range(randrange(5, 10)):
                settings = cls.generate_settings()
                items = dict(TestSQLiteTable.generate_item(settings) for _ in range(randrange(3, 6)))

                repository = await SQLiteTable.create(settings=settings, connection=connection)
                for k, v in items.items():
                    await repository._set_item_from_key_value_pair(k, v)
                cache[settings.name] = repository

            yield cache

    @staticmethod
    def get_repository_from_url(cache: SQLiteCache, url: str) -> SQLiteCache | None:
        for name, repository in cache.items():
            if name == urlparse(url).path.split("/")[-2]:
                return repository

    # noinspection PyTestUnpassedFixture
    @staticmethod
    async def get_db_path(cache: SQLiteCache) -> str:
        """Get the DB path from the connection associated with the given ``cache``."""
        async with cache.connection.execute("PRAGMA database_list") as cur:
            rows = await cur.fetchall()

        assert len(rows) == 1
        db_seq, db_name, db_path = rows[0]
        return db_path

    # noinspection PyTestUnpassedFixture
    async def test_connect_with_path(self, tmp_path: Path):
        fake_name = "not my real name"
        path = join(tmp_path, "test")
        expire = timedelta(weeks=42)

        async with SQLiteCache.connect_with_path(path, cache_name=fake_name, expire=expire) as cache:
            assert await self.get_db_path(cache) == path + ".sqlite"
            assert cache.cache_name != fake_name
            assert cache.expire == expire

    # noinspection PyTestUnpassedFixture
    async def test_connect_with_in_memory_db(self):
        fake_name = "not my real name"
        expire = timedelta(weeks=42)

        async with SQLiteCache.connect_with_in_memory_db(cache_name=fake_name, expire=expire) as cache:
            assert await self.get_db_path(cache) == ""
            assert cache.cache_name != fake_name
            assert cache.expire == expire

    # noinspection PyTestUnpassedFixture
    async def test_connect_with_temp_db(self):
        name = "this is my real name"
        path = join(gettempdir(), name)
        expire = timedelta(weeks=42)

        async with SQLiteCache.connect_with_temp_db(name, expire=expire) as cache:
            assert (await self.get_db_path(cache)).endswith(path + ".sqlite")
            assert cache.cache_name == name
            assert cache.expire == expire
