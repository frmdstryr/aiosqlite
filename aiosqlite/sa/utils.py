from types import TracebackType
from typing import Any, Generic, Optional, Type, TypeVar
from collections.abc import Coroutine

T = TypeVar("T")

class ContextManager(Coroutine, Generic[T]):
    """ A context manager which allows using either:

        obj = await ctx()

    or
        async with ctx() as obj:
            pass

    """
    __slots__ = ("_coro", "_obj")

    def __init__(self, coro):
        self._coro = coro
        self._obj: Optional[T] = None

    def send(self, value: Any) -> Any:
        return self._coro.send(value)

    def throw(
        self,
        typ: Optional[Type[BaseException]],
        val: Optional[BaseException] = None,
        tb: Optional[TracebackType] = None
    ):
        return self._coro.throw(typ, val, tb)

    def close(self):
        return self._coro.close()

    @property
    def gi_frame(self):
        return self._coro.gi_frame

    @property
    def gi_running(self):
        return self._coro.gi_running

    @property
    def gi_code(self):
        return self._coro.gi_code

    def __next__(self):
        return self.send(None)

    def __await__(self) -> T:
        return self._coro.__await__()

    async def __aenter__(self) -> T:
        self._obj = await self._coro
        return self._obj

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType]
    ):
        await self._obj.close()
        self._obj = None
