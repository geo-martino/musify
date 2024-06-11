from __future__ import annotations

import json
import os
from collections.abc import Mapping, Callable, Generator
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Self

from aiohttp import RequestInfo, ClientRequest, ClientResponse
from dateutil.relativedelta import relativedelta
from yarl import URL

from musify import PROGRAM_NAME
from musify.api.cache.backend.base import DEFAULT_EXPIRE, ResponseCache, ResponseRepository, RepositoryRequestType
from musify.api.cache.backend.base import RequestSettings
from musify.api.exception import CacheError
from musify.utils import required_modules_installed

try:
    import aiosqlite
except ImportError:
    aiosqlite = None

REQUIRED_MODULES = [aiosqlite]


class SQLiteTable[K: tuple[Any, ...], V: str](ResponseRepository[K, V]):

    __slots__ = ()

    #: The column under which a response's name is stored in the table
    name_column = "name"
    #: The column under which response data is stored in the table
    data_column = "response"
    #: The column under which the response cache time is stored in the table
    cached_column = "cached_at"
    #: The column under which the response expiry time is stored in the table
    expiry_column = "expires_at"

    async def create(self) -> Self:
        ddl_sep = "\t, "
        ddl = "\n".join((
            f"CREATE TABLE IF NOT EXISTS {self.settings.name} (",
            "\t" + f"\n{ddl_sep}".join(
                f"{key} {data_type} NOT NULL" for key, data_type in self._primary_key_columns.items()
            ),
            f"{ddl_sep}{self.name_column} TEXT",
            f"{ddl_sep}{self.cached_column} TIMESTAMP NOT NULL",
            f"{ddl_sep}{self.expiry_column} TIMESTAMP NOT NULL",
            f"{ddl_sep}{self.data_column} TEXT",
            f"{ddl_sep}PRIMARY KEY ({", ".join(self._primary_key_columns)})",
            ");",
            f"CREATE INDEX IF NOT EXISTS idx_{self.expiry_column} "
            f"ON {self.settings.name}({self.expiry_column});"
        ))

        self.logger.debug(f"Creating {self.settings.name!r} table with the following DDL:\n{ddl}")
        await self.connection.executescript(ddl)
        await self.commit()

        return self

    def __init__(
            self,
            connection: aiosqlite.Connection,
            settings: RequestSettings,
            expire: timedelta | relativedelta = DEFAULT_EXPIRE,
    ):
        required_modules_installed(REQUIRED_MODULES, self)

        super().__init__(settings=settings, expire=expire)

        self.connection = connection

    def __await__(self) -> Generator[Any, None, Self]:
        return self.create().__await__()

    async def commit(self) -> None:
        """Commit the transactions to the database."""
        try:
            await self.connection.commit()
        except ValueError:
            pass

    async def close(self) -> None:
        try:
            await self.commit()
            await self.connection.close()
        except ValueError:
            pass

    @property
    def _primary_key_columns(self) -> Mapping[str, str]:
        """A map of column names to column data types for the primary keys of this repository."""
        expected_columns = self.settings.fields

        keys = {"method": "VARCHAR(10)"}
        if "id" in expected_columns:
            keys["id"] = "VARCHAR(50)"
        if "offset" in expected_columns:
            keys["offset"] = "INT2"
        if "size" in expected_columns:
            keys["size"] = "INT2"

        return keys

    def get_key_from_request(self, request: RepositoryRequestType[K]) -> K | None:
        if isinstance(request, ClientRequest | ClientResponse):
            request = request.request_info
        if not isinstance(request, RequestInfo):
            return request  # `request` is the key

        key = self.settings.get_key(request.url)
        if any(part is None for part in key):
            return

        return str(request.method).upper(), *key

    async def count(self, include_expired: bool = True) -> int:
        query = f"SELECT COUNT(*) FROM {self.settings.name}"
        params = []

        if not include_expired:
            query += f"\nWHERE {self.expiry_column} > ?"
            params.append(datetime.now().isoformat())

        async with self.connection.execute(query, params) as cur:
            row = await cur.fetchone()

        return row[0]

    async def contains(self, request: RepositoryRequestType[K]) -> bool:
        key = self.get_key_from_request(request)
        query = "\n".join((
            f"SELECT COUNT(*) FROM {self.settings.name}",
            f"WHERE {self.expiry_column} > ?",
            f"\tAND {"\n\tAND ".join(f"{key} = ?" for key in self._primary_key_columns)}",
        ))
        async with self.connection.execute(query, (datetime.now().isoformat(), *key)) as cur:
            rows = await cur.fetchone()
        return rows[0] > 0

    async def clear(self, expired_only: bool = False) -> int:
        query = f"DELETE FROM {self.settings.name}"
        params = []

        if expired_only:
            query += f"\nWHERE {self.expiry_column} > ?"
            params.append(datetime.now().isoformat())

        async with self.connection.execute(query, params) as cur:
            count = cur.rowcount
        return count

    async def __aiter__(self):
        query = "\n".join((
            f"SELECT {", ".join(self._primary_key_columns)}, {self.data_column} ",
            f"FROM {self.settings.name}",
            f"WHERE {self.expiry_column} > ?",
        ))
        async with self.connection.execute(query, (datetime.now().isoformat(),)) as cur:
            async for row in cur:
                yield row[:-1], self.deserialize(row[-1])

    async def get_response(self, request: RepositoryRequestType[K]) -> V | None:
        key = self.get_key_from_request(request)
        if not key:
            return

        query = "\n".join((
            f"SELECT {self.data_column} FROM {self.settings.name}",
            f"WHERE {self.data_column} IS NOT NULL",
            f"\tAND {self.expiry_column} > ?",
            f"\tAND {"\n\tAND ".join(f"{key} = ?" for key in self._primary_key_columns)}",
        ))

        async with self.connection.execute(query, (datetime.now().isoformat(), *key)) as cur:
            row = await cur.fetchone()

        if not row:
            return
        return self.deserialize(row[0])

    async def _set_item_from_key_value_pair(self, __key: K, __value: Any) -> None:
        columns = (
            *self._primary_key_columns,
            self.name_column,
            self.cached_column,
            self.expiry_column,
            self.data_column
        )
        query = "\n".join((
            f"INSERT OR REPLACE INTO {self.settings.name} (",
            f"\t{", ".join(columns)}",
            ") ",
            f"VALUES({",".join("?" * len(columns))});",
        ))
        params = (
            *__key,
            self.settings.get_name(self.deserialize(__value)),
            datetime.now().isoformat(),
            self.expire.isoformat(),
            self.serialize(__value)
        )

        await self.connection.execute(query, params)

    async def delete_response(self, request: RepositoryRequestType[K]) -> bool:
        key = self.get_key_from_request(request)
        query = "\n".join((
            f"DELETE FROM {self.settings.name}",
            f"WHERE {"\n\tAND ".join(f"{key} = ?" for key in self._primary_key_columns)}",
        ))

        async with self.connection.execute(query, key) as cur:
            count = cur.rowcount
        return count > 0

    def serialize(self, value: Any) -> V | None:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.decoder.JSONDecodeError:
                return

        return json.dumps(value, indent=2)

    def deserialize(self, value: V | dict) -> Any:
        if isinstance(value, dict):
            return value

        try:
            return json.loads(value)
        except (json.decoder.JSONDecodeError, TypeError):
            return


class SQLiteCache(ResponseCache[SQLiteTable]):

    __slots__ = ("_connector", "connection")

    # noinspection PyPropertyDefinition
    @classmethod
    @property
    def type(cls):
        return "sqlite"

    @property
    def closed(self):
        """Is the stored client session closed."""
        return self.connection is None or not self.connection.is_alive()

    @staticmethod
    def _get_sqlite_path(path: Path) -> Path:
        return path.with_suffix(".sqlite")

    @staticmethod
    def _clean_kwargs[T: dict](kwargs: T) -> T:
        kwargs.pop("cache_name", None)
        kwargs.pop("connection", None)
        return kwargs

    @classmethod
    def connect(cls, value: Any, **kwargs) -> Self:
        return cls.connect_with_path(path=value, **kwargs)

    @classmethod
    def connect_with_path(cls, path: str | Path, **kwargs) -> Self:
        """Connect with an SQLite DB at the given ``path`` and return an instantiated :py:class:`SQLiteResponseCache`"""
        path = cls._get_sqlite_path(Path(path))
        os.makedirs(path.parent, exist_ok=True)

        return cls(
            cache_name=str(path),
            connector=lambda: aiosqlite.connect(database=path),
            **cls._clean_kwargs(kwargs)
        )

    @classmethod
    def connect_with_in_memory_db(cls, **kwargs) -> Self:
        """Connect with an in-memory SQLite DB and return an instantiated :py:class:`SQLiteResponseCache`"""
        return cls(
            cache_name="__IN_MEMORY__",
            connector=lambda: aiosqlite.connect(database="file::memory:?cache=shared", uri=True),
            **cls._clean_kwargs(kwargs)
        )

    @classmethod
    def connect_with_temp_db(cls, name: str = f"{PROGRAM_NAME.lower()}_db.tmp", **kwargs) -> Self:
        """Connect with a temporary SQLite DB and return an instantiated :py:class:`SQLiteResponseCache`"""
        path = cls._get_sqlite_path(Path(gettempdir(), name))
        return cls(
            cache_name=name,
            connector=lambda: aiosqlite.connect(database=path),
            **cls._clean_kwargs(kwargs)
        )

    def __init__(
            self,
            cache_name: str,
            connector: Callable[[], aiosqlite.Connection],
            repository_getter: Callable[[Self, str | URL], SQLiteTable] = None,
            expire: timedelta | relativedelta = DEFAULT_EXPIRE,
    ):
        required_modules_installed(REQUIRED_MODULES, self)

        super().__init__(cache_name=cache_name, repository_getter=repository_getter, expire=expire)

        self._connector = connector
        self.connection: aiosqlite.Connection | None = None

    async def _connect(self) -> Self:
        if self.closed:
            self.connection = self._connector()
            await self.connection

        for repository in self._repositories.values():
            repository.connection = self.connection
            await repository.create()

        return self

    def __await__(self) -> Generator[Any, None, Self]:
        return self._connect().__await__()

    async def __aexit__(self, __exc_type, __exc_value, __traceback) -> None:
        if self.closed:
            return

        await self.commit()
        await self.connection.__aexit__(__exc_type, __exc_value, __traceback)
        self.connection = None

    async def commit(self):
        """Commit the transactions to the database."""
        if self.closed:
            return

        try:
            await self.connection.commit()
        except ValueError:
            pass

    async def close(self):
        if self.closed:
            return

        try:
            await self.commit()
            await self.connection.close()
        except ValueError:
            pass

    def create_repository(self, settings: RequestSettings) -> SQLiteTable:
        if settings.name in self:
            raise CacheError(f"Repository already exists: {settings.name}")

        repository = SQLiteTable(connection=self.connection, settings=settings, expire=self.expire)
        self._repositories[settings.name] = repository
        return repository
