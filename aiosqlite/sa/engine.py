# ported from:
# https://github.com/aio-libs/aiopg/blob/master/aiopg/sa/engine.py
import json
import asyncio

import aiosqlite
from pathlib import Path
from typing import Any, Union

from ..core import TIMEOUT
from .connection import SAConnection
from .exc import InvalidRequestError
from .pool import create_pool, PoolAcquireContextManager, PoolContextManager

try:
    from sqlalchemy.dialects.sqlite.pysqlite import SQLiteDialect_pysqlite
except ImportError:  # pragma: no cover
    raise ImportError("aiosqlite.sa requires sqlalchemy")


def get_dialect(json_serializer=json.dumps, json_deserializer=lambda x: x):
    dialect = SQLiteDialect_pysqlite(
        json_serializer=json_serializer, json_deserializer=json_deserializer
    )

    return dialect


_dialect = get_dialect()


def create_engine(
    database: Union[str, Path],
    *,
    minsize: int = 1,
    maxsize: int = 10,
    dialect=_dialect,
    timeout: float = TIMEOUT,
    pool_recycle: int = -1,
    **kwargs: Any
):
    """A coroutine for Engine creation.

    Returns Engine instance with embedded connection pool.

    The pool has *minsize* opened connections to PostgreSQL server.
    """

    coro = _create_engine(
        database=database,
        minsize=minsize,
        maxsize=maxsize,
        dialect=dialect,
        timeout=timeout,
        pool_recycle=pool_recycle,
        **kwargs
    )
    return EngineContextManager(coro)


async def _create_engine(
    database: Union[str, Path],
    *,
    minsize: int,
    maxsize: int,
    dialect,
    timeout: float,
    pool_recycle: int,
    **kwargs: Any
):

    pool = await create_pool(
        database,
        minsize=minsize,
        maxsize=maxsize,
        timeout=timeout,
        pool_recycle=pool_recycle,
        **kwargs
    )
    conn = await pool.acquire()
    try:
        return Engine(dialect, pool, database)
    finally:
        await pool.release(conn)


class Engine:
    """Connects a aiosqlite.Pool and
    sqlalchemy.engine.interfaces.Dialect together to provide a
    source of database connectivity and behavior.

    An Engine object is instantiated publicly using the
    create_engine coroutine.
    """

    def __init__(self, dialect, pool, dsn):
        self._dialect = dialect
        self._pool = pool
        self._dsn = dsn

    @property
    def dialect(self):
        """An dialect for engine."""
        return self._dialect

    @property
    def name(self):
        """A name of the dialect."""
        return self._dialect.name

    @property
    def driver(self):
        """A driver of the dialect."""
        return self._dialect.driver

    @property
    def dsn(self):
        """DSN connection info"""
        return self._dsn

    @property
    def timeout(self):
        return self._pool.timeout

    @property
    def minsize(self):
        return self._pool.minsize

    @property
    def maxsize(self):
        return self._pool.maxsize

    @property
    def size(self):
        return self._pool.size

    @property
    def freesize(self):
        return self._pool.freesize

    @property
    def closed(self):
        return self._pool.closed

    def close(self):
        """Close engine.

        Mark all engine connections to be closed on getting back to pool.
        Closed engine doesn't allow to acquire new connections.
        """
        self._pool.close()

    async def terminate(self):
        """Terminate engine.

        Terminate engine pool with instantly closing all acquired
        connections also.
        """
        await self._pool.terminate()

    async def wait_closed(self):
        """Wait for closing all engine's connections."""
        await self._pool.wait_closed()

    def acquire(self):
        """Get a connection from pool."""
        coro = self._acquire()
        return EngineAcquireContextManager(coro, self)

    async def _acquire(self) -> SAConnection:
        raw = await self._pool.acquire()
        return SAConnection(raw, self)

    def release(self, conn: SAConnection):
        """Revert back connection to pool."""
        if conn.in_transaction:
            raise InvalidRequestError(
                "Cannot release a connection with not finished transaction"
            )
        raw = conn.connection
        return asyncio.create_task(self._pool.release(raw))

    def __enter__(self):
        raise RuntimeError('"await" should be used as context manager expression')

    def __exit__(self, *args):
        # This must exist because __enter__ exists, even though that
        # always raises; that's how the with-statement works.
        pass  # pragma: nocover

    def __await__(self):
        # This is not a coroutine.  It is meant to enable the idiom:
        #
        #     with (await engine) as conn:
        #         <block>
        #
        # as an alternative to:
        #
        #     conn = await engine.acquire()
        #     try:
        #         <block>
        #     finally:
        #         engine.release(conn)
        conn = yield from self._acquire().__await__()
        return ConnectionContextManager(self, conn)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()
        await self.wait_closed()


EngineContextManager = PoolContextManager
EngineAcquireContextManager = PoolAcquireContextManager


class ConnectionContextManager:
    """Context manager.

    This enables the following idiom for acquiring and releasing a
    connection around a block:

        async with engine as conn:
            cur = await conn.cursor()

    while failing loudly when accidentally using:

        with engine:
            <block>
    """

    __slots__ = ("_engine", "_conn")

    def __init__(self, engine, conn):
        self._engine = engine
        self._conn = conn

    def __enter__(self):
        return self._conn

    def __exit__(self, *args):
        try:
            self._engine.release(self._conn)
        finally:
            self._engine = None
            self._conn = None
