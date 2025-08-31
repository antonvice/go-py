import asyncio
import functools
import random
import sys
import threading
from concurrent.futures import Future, ProcessPoolExecutor
from contextlib import contextmanager
from threading import Thread
from typing import Any, Callable, List, Optional

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


# --- New Go-inspired Concepts ---

# 1. Select Statement
GET = "get"
PUT = "put"


class Case:
    """Defines a single channel operation for use in a `select` statement."""

    def __init__(self, channel: "Channel", operation: str, value: Any = None):
        if operation not in (GET, PUT):
            raise ValueError(f"operation must be GET or PUT, not {operation}")
        if operation == PUT and value is None:
            raise ValueError("PUT operation requires a value")
        self.channel = channel
        self.operation = operation
        self.value = value

    @property
    def _coro(self):
        """Internal property to get the awaitable for this case."""
        if self.operation == GET:
            return self.channel.get_async()
        return self.channel.put_async(self.value)

    def __repr__(self) -> str:
        if self.operation == PUT:
            return f"Case(channel={self.channel}, operation={self.operation}, value={self.value})"
        return f"Case(channel={self.channel}, operation={self.operation})"


# 2. WaitGroup & Defer
class WaitGroup:
    """Waits for a collection of goroutines to finish."""

    def __init__(self, manager: Optional["GoroutineManager"] = None):
        self._manager = manager or _default_manager
        self._loop = self._manager._loop
        self._counter = 0
        self._lock = threading.Lock()

        fut = asyncio.run_coroutine_threadsafe(self._create_event(), self._loop)
        self._event: asyncio.Event = fut.result()

    async def _create_event(self) -> asyncio.Event:
        return asyncio.Event()

    def add(self, delta: int) -> None:
        """Adds a delta to the WaitGroup counter."""
        with self._lock:
            if self._counter <= 0 and delta > 0:
                self._loop.call_soon_threadsafe(self._event.clear)
            self._counter += delta
            if self._counter < 0:
                self._counter = 0  # Counter cannot be negative
            if self._counter == 0:
                self._loop.call_soon_threadsafe(self._event.set)

    def done(self) -> None:
        """Decrements the WaitGroup counter by one."""
        self.add(-1)

    def wait(self) -> None:
        """Blocks until the WaitGroup counter is zero."""
        with self._lock:
            if self._counter <= 0:
                return
        future = asyncio.run_coroutine_threadsafe(self._event.wait(), self._loop)
        future.result()


@contextmanager
def defer(cleanup_func: Callable, *args, **kwargs):
    """A context manager to ensure a function is called on exit, mimicking Go's defer."""
    try:
        yield
    finally:
        cleanup_func(*args, **kwargs)


# 3. Context
class CancellationError(Exception):
    """Raised when an operation is cancelled."""

    pass


class TimeoutError(CancellationError):
    """Raised when a context times out."""

    pass


class Context:
    """Manages cancellation signals and deadlines for goroutines."""

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        self._done_event = asyncio.Event()
        self._error = None
        self._lock = threading.Lock()

    def is_done(self) -> bool:
        """Returns True if the context has been cancelled."""
        return self._done_event.is_set()

    def err(self) -> Optional[Exception]:
        """Returns the reason for the context's cancellation."""
        with self._lock:
            return self._error

    def _cancel(self, err: Exception) -> None:
        with self._lock:
            if self.is_done():
                return
            self._error = err
        self._loop.call_soon_threadsafe(self._done_event.set)

    async def _wait_for_done(self):
        await self._done_event.wait()


# 4. Once
class Once:
    """Ensures a function is executed exactly one time."""

    def __init__(self):
        self._done = False
        self._lock = threading.Lock()

    def do(self, func: Callable, *args, **kwargs) -> None:
        """Executes the function func, with arguments, only if it has not been called before."""
        if self._done:
            return
        with self._lock:
            if self._done:
                return
            func(*args, **kwargs)
            self._done = True


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

    def go(
        self,
        obj: Callable,
        *args,
        process: bool = False,
        ctx: Optional["Context"] = None,
        **kwargs,
    ) -> Future:
        """Submits a callable to run concurrently.

        Args:
            obj: The callable to execute (sync function or async coroutine).
            *args: Positional arguments to pass to the callable.
            process: If True, run in a separate process for CPU-bound tasks.
                     The callable and its arguments must be pickleable.
            ctx: An optional Context for cancellation and timeouts.
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
            user_awaitable = awaitable
            if ctx is None:
                return await user_awaitable

            # Race the user task against the context's done event
            user_task = asyncio.create_task(user_awaitable)
            done_task = asyncio.create_task(ctx._wait_for_done())

            done, pending = await asyncio.wait(
                {user_task, done_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            for p in pending:
                p.cancel()

            if user_task in done:
                return await user_task
            else:
                raise ctx.err()

        return asyncio.run_coroutine_threadsafe(_wrapper(), self._loop)

    def nc(self, maxsize: int = 0) -> Channel:
        """Creates a new channel for communication between goroutines."""
        return Channel(self._loop, maxsize)

    async def _async_select(
        self, cases: List["Case"], non_blocking: bool
    ) -> Optional["Case"]:
        if not cases:
            if non_blocking:
                return None
            await asyncio.Future()  # Block forever

        # Shuffle to provide pseudorandom selection on multiple ready channels
        tasks = {asyncio.create_task(case._coro): case for case in cases}
        task_list = list(tasks.keys())
        random.shuffle(task_list)

        timeout = 0 if non_blocking else None
        done, pending = await asyncio.wait(
            task_list, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

        if not done:
            return None  # Non-blocking and nothing was ready

        winner = done.pop()
        completed_case = tasks[winner]

        # Populate the completed case with the result value
        result = winner.result()  # This will re-raise exceptions if any
        if completed_case.operation == GET:
            completed_case.value = result

        return completed_case

    def select(
        self, cases: List["Case"], *, non_blocking: bool = False
    ) -> Optional["Case"]:
        """Blocks until one of the channel operations in `cases` is ready."""
        if not cases and not non_blocking:
            raise ValueError("blocking select call with no cases will block forever")

        future = asyncio.run_coroutine_threadsafe(
            self._async_select(cases, non_blocking), self._loop
        )
        return future.result()

    def new_context_with_timeout(self, timeout: float) -> "Context":
        """Creates a new Context that is automatically cancelled after a timeout."""
        ctx = Context(self._loop)

        def _cancel_callback():
            ctx._cancel(TimeoutError("Context timed out"))

        self._loop.call_later(timeout, _cancel_callback)
        return ctx

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
nc = _default_manager.nc
select = _default_manager.select
new_context_with_timeout = _default_manager.new_context_with_timeout
