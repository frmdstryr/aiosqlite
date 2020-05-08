# Copyright 2022 Amethyst Reese
# Licensed under the MIT license

"""asyncio bridge to the standard sqlite3 module"""

from sqlite3 import (  # pylint: disable=redefined-builtin
    DatabaseError,
    Error,
    IntegrityError,
    NotSupportedError,
    OperationalError,
    paramstyle,
    ProgrammingError,
    register_adapter,
    register_converter,
    Row,
    sqlite_version,
    sqlite_version_info,
    Warning,
)

__author__ = "Amethyst Reese"
from .__version__ import __version__
from .core import connect, Connection, Cursor
from .pool import create_pool, Pool

__all__ = [
    "__version__",
    "paramstyle",
    "create_pool",
    "register_adapter",
    "register_converter",
    "sqlite_version",
    "sqlite_version_info",
    "connect",
    "Connection",
    "Cursor",
    "Pool",
    "Row",
    "Warning",
    "Error",
    "DatabaseError",
    "IntegrityError",
    "ProgrammingError",
    "OperationalError",
    "NotSupportedError",
]
