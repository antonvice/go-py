import asyncio
import functools
import sys
from concurrent.futures import Future, ProcessPoolExecutor
from threading import Thread
from typing import Any, Callable

# This project was inspired by the simplicity of goroutine-py.
_SENTINEL = object()


class Channel:
    """A communication channel that mimics Go's channels.

    - Use `ch << value` to send a value.
    - Use `for value in ch:` to receive values until closed.
    - Use `value = ch.get()` for a single, blocking receive.
    - Use `ch.close()` to signal that no more values will be sent.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, maxsize: int = 0):
        """Initializes a new Channel."""
        self._loop = loop

        async def _create_queue():
            return asyncio.Queue(maxsize)

        future = asyncio.run_coroutine_threadsafe(_create_queue(), self._loop)
        self._queue: asyncio.Queue = future.result()

    def put(self, item: Any) -> None:
        """Puts an item into the channel from a synchronous context."""
        asyncio.run_coroutine_threadsafe(self._queue.put(item), self._loop)

    def get(self) -> Any:
        """Gets an item from the channel from a synchronous context. Blocks."""
        future = asyncio.run_coroutine_threadsafe(self._queue.get(), self._loop)
        return future.result()

    def close(self) -> None:
        """Closes the channel, signaling the end of communication."""
        self.put(_SENTINEL)

    def __lshift__(self, item: Any) -> "Channel":
        """Enables the `ch << value` syntax for sending values."""
        self.put(item)
        return self

    def __iter__(self):
        """Allows the channel to be used in `for` loops."""
        return self

    def __next__(self):
        """Retrieves the next item for the `for` loop, blocking if necessary."""
        value = self.get()
        if value is _SENTINEL:
            self.put(_SENTINEL)
            raise StopIteration
        return value

    async def put_async(self, item: Any) -> None:
        """Asynchronously puts an item into the channel from a coroutine."""
        await self._queue.put(item)

    async def get_async(self) -> Any:
        """Asynchronously gets an item from the channel from a coroutine."""
        return await self._queue.get()


class GoroutineManager:
    """Manages a background asyncio event loop for running concurrent tasks."""

    def __init__(self):
        """Initializes the manager, event loop, and executors."""
        self._loop = asyncio.new_event_loop()
        self._thread = Thread(target=self._run, daemon=True)
        self._process_pool = ProcessPoolExecutor()
        self._is_running = False

    def _run(self) -> None:
        """The target for the background thread, runs the event loop forever."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def start(self) -> None:
        """Starts the background event loop thread if not already running."""
        if not self._is_running:
            self._thread.start()
            self._is_running = True

    def go(self, obj: Callable, *args, process: bool = False, **kwargs) -> Future:
        """Submits a callable to run concurrently.

        Args:
            obj: The callable to execute (sync function or async coroutine).
            *args: Positional arguments to pass to the callable.
            process: If True, run in a separate process for CPU-bound tasks.
                     The callable and its arguments must be pickleable.
            **kwargs: Keyword arguments to pass to the callable.

        Returns:
            A concurrent.futures.Future object to track the task's result.
        """
        if not self._is_running:
            self.start()
        if not callable(obj):
            raise TypeError("A callable is required")

        awaitable = None
        if process:
            # 1. Handle process-based tasks first
            awaitable = self._loop.run_in_executor(self._process_pool, obj, *args)
        elif asyncio.iscoroutinefunction(obj):
            # 2. Handle async functions
            awaitable = obj(*args, **kwargs)
        else:
            # 3. Handle all other (sync) functions
            if sys.version_info >= (3, 9):
                awaitable = asyncio.to_thread(obj, *args, **kwargs)
            else:
                p = functools.partial(obj, *args, **kwargs)
                awaitable = self._loop.run_in_executor(None, p)

        async def _wrapper():
            return await awaitable

        return asyncio.run_coroutine_threadsafe(_wrapper(), self._loop)

    def new_channel(self, maxsize: int = 0) -> Channel:
        """Creates a new channel for communication between goroutines."""
        return Channel(self._loop, maxsize)

    def shutdown(self, wait: bool = True) -> None:
        """Stops the event loop, executors, and joins the background thread."""
        if not self._is_running:
            return
        self._process_pool.shutdown(wait=wait)
        self._loop.call_soon_threadsafe(self._loop.stop)
        if wait:
            self._thread.join()
        self._is_running = False

    def __enter__(self):
        """Starts the manager when entering a `with` block."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Shuts down the manager when exiting a `with` block."""
        self.shutdown()


# --- THE GLOBAL API ---
# A single, hidden manager powers the simple API. It starts on import.
# This provides the "no setup required" Go-like feel, with the trade-off
# that a background thread is always running. For library use, an explicit
# `GoroutineManager` instance is recommended for controlled shutdowns.
_default_manager = GoroutineManager()
_default_manager.start()

go = _default_manager.go
new_channel = _default_manager.new_channel
