import json
import os
import sqlite3
from collections.abc import Mapping
from datetime import datetime, timedelta
from os.path import splitext, dirname, join
from tempfile import gettempdir
from typing import Any, Self

from requests import Request, PreparedRequest, Response

from musify import PROGRAM_NAME
from musify.api.cache.backend.base import ResponseCache, ResponseRepository, RequestSettings, PaginatedRequestSettings
from musify.api.cache.backend.base import DEFAULT_EXPIRE
from musify.api.exception import CacheError
from musify.exception import MusifyKeyError


class SQLiteTable[KT: tuple[Any, ...], VT: str](ResponseRepository[sqlite3.Connection, KT, VT]):

    __slots__ = ()

    data_key = "data"
    expiry_key = "expires_at"

    @property
    def _primary_key_columns(self) -> Mapping[str, str]:
        """A map of column names to column data types for the primary keys of this repository."""
        keys = {"method": "VARCHAR(10)", "id": "TEXT"}
        if isinstance(self.settings, PaginatedRequestSettings):
            keys["offset"] = "INT4"
            keys["page_count"] = "INT2"

        return keys

    def get_key_from_request(self, request: Request | PreparedRequest | Response) -> KT:
        if isinstance(request, Response):
            request = request.request

        keys = [str(request.method), self.settings.get_id(request.url)]
        if isinstance(self.settings, PaginatedRequestSettings):
            keys.append(self.settings.get_offset(request.url))
            keys.append(self.settings.get_limit(request.url))

        return tuple(keys)

    def __init__(
            self, connection: sqlite3.Connection, settings: RequestSettings, expire: timedelta = DEFAULT_EXPIRE
    ):
        super().__init__(connection=connection, settings=settings, expire=expire)

        self.create_table()

    def create_table(self):
        """Create the table for this repository type in the backend database if it doesn't already exist."""
        ddl_sep = "\t, "

        ddl = "\n".join((
            f"CREATE TABLE IF NOT EXISTS {self.settings.name} (",
            "\t" + f"\n{ddl_sep}".join(
                f"{key} {data_type} NOT NULL" for key, data_type in self._primary_key_columns.items()
            ),
            f"{ddl_sep}{self.expiry_key} TIMESTAMP",
            f"{ddl_sep}{self.data_key} TEXT",
            f"{ddl_sep}PRIMARY KEY ({", ".join(self._primary_key_columns)})",
            ");\n"
            f"CREATE INDEX IF NOT EXISTS idx_{self.expiry_key} ON {self.settings.name}({self.expiry_key});"
        ))

        self.logger.debug(f"Creating {self.settings.name!r} table with the following DDL:\n{ddl}")
        self.connection.executescript(ddl)

    def commit(self) -> None:
        self.connection.commit()

    def count(self, expired: bool = True) -> int:
        query = f"SELECT COUNT(*) FROM {self.settings.name}"
        if expired:
            cur = self.connection.execute(query)
        else:
            query += f"\nWHERE {self.expiry_key} IS NULL OR {self.expiry_key} > ?"
            cur = self.connection.execute(query, (datetime.now().isoformat(),))

        return cur.fetchone()[0]

    def __repr__(self):
        return repr(dict(self.items()))

    def __str__(self):
        return str(dict(self.items()))

    def __iter__(self):
        query = "\n".join((
            f"SELECT {", ".join(self._primary_key_columns)}, {self.data_key} ",
            f"FROM {self.settings.name}",
            f"WHERE {self.expiry_key} > ?",
        ))
        for row in self.connection.execute(query, (datetime.now().isoformat(),)):
            yield row[:-1]

    def __len__(self):
        return self.count(expired=False)

    def __getitem__(self, __key):
        query = "\n".join((
            f"SELECT {self.data_key} FROM {self.settings.name}",
            f"WHERE {self.expiry_key} > ?",
            f"\tAND {"\n\tAND ".join(f"{key} = ?" for key in self._primary_key_columns)}",
        ))

        cur = self.connection.execute(query, (datetime.now().isoformat(), *__key))
        row = cur.fetchone()
        cur.close()
        if not row:
            raise MusifyKeyError(__key)

        return self.deserialize(row[0])

    def __setitem__(self, __key, __value):
        query = "\n".join((
            f"INSERT OR REPLACE INTO {self.settings.name} (",
            f"\t{", ".join(self._primary_key_columns)}, {self.expiry_key}, {self.data_key}",
            ") ",
            f"VALUES({",".join("?" * len(self._primary_key_columns))},?,?);",
        ))

        data = self.serialize(__value)
        self.connection.execute(query, (*__key, self.expire.isoformat(), data))

    def __delitem__(self, __key):
        query = "\n".join((
            f"DELETE FROM {self.settings.name}",
            f"WHERE {"\n\tAND ".join(f"{key} = ?" for key in self._primary_key_columns)}",
        ))

        cur = self.connection.execute(query, __key)
        if not cur.rowcount:
            raise MusifyKeyError(__key)

    def serialize(self, value: Any) -> VT:
        if isinstance(value, str):
            return value
        return json.dumps(value)

    def deserialize(self, value: VT | dict) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return json.loads(value)


class SQLiteCache(ResponseCache[sqlite3.Connection, SQLiteTable]):

    __slots__ = ()

    # noinspection PyPropertyDefinition
    @classmethod
    @property
    def type(cls):
        return "sqlite"

    @staticmethod
    def _get_sqlite_path(path: str) -> str:
        if not splitext(path)[1] == ".sqlite":  # add/replace extension if not given
            path += ".sqlite"
        return path

    @staticmethod
    def _clean_kwargs[T: dict](kwargs: T) -> T:
        kwargs.pop("cache_name", None)
        kwargs.pop("connection", None)
        return kwargs

    @classmethod
    def connect(cls, value: Any, **kwargs) -> Self:
        return cls.connect_with_path(path=value, **kwargs)

    @classmethod
    def connect_with_path(cls, path: str, **kwargs) -> Self:
        """Connect with an SQLite DB at the given ``path`` and return an instantiated :py:class:`SQLiteResponseCache`"""
        path = cls._get_sqlite_path(path)
        if dirname(path):
            os.makedirs(dirname(path), exist_ok=True)

        connection = sqlite3.Connection(database=path)
        return cls(cache_name=path, connection=connection, **cls._clean_kwargs(kwargs))

    @classmethod
    def connect_with_in_memory_db(cls, **kwargs) -> Self:
        """Connect with an in-memory SQLite DB and return an instantiated :py:class:`SQLiteResponseCache`"""
        connection = sqlite3.Connection(database="file::memory:?cache=shared")
        return cls(cache_name="__IN_MEMORY__", connection=connection, **cls._clean_kwargs(kwargs))

    @classmethod
    def connect_with_temp_db(cls, name: str = f"{PROGRAM_NAME.lower()}_db.tmp", **kwargs) -> Self:
        """Connect with a temporary SQLite DB and return an instantiated :py:class:`SQLiteResponseCache`"""
        path = cls._get_sqlite_path(join(gettempdir(), name))

        connection = sqlite3.Connection(database=path)
        return cls(cache_name=name, connection=connection, **cls._clean_kwargs(kwargs))

    def create_repository(self, settings: RequestSettings) -> SQLiteTable:
        if settings.name in self:
            raise CacheError(f"Repository already exists: {settings.name}")

        repository = SQLiteTable(connection=self.connection, settings=settings, expire=self.expire)
        self._repositories[settings.name] = repository
        return repository
