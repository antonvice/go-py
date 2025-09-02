import asyncio
import collections
import time

import pytest

from pygoroutine import (
    GET,
    Case,
    GoroutineManager,
    Once,
    TimeoutError,
    WaitGroup,
    defer,
)


def cpu_intensive_task(x):
    """A simple, verifiable CPU-bound function for testing."""
    return sum(i * i for i in range(x))


async def async_io_task(duration):
    """An awaitable I/O-bound function for testing."""
    await asyncio.sleep(duration)
    return f"Slept for {duration}"


def sync_io_task(duration):
    """A blocking I/O-bound function for testing."""
    time.sleep(duration)
    return f"Slept for {duration}"


def test_manager_lifecycle():
    """Tests that the manager starts and shuts down cleanly."""
    manager = GoroutineManager()
    assert not manager._is_running
    with manager as app:
        assert app._is_running
        future = app.go(sync_io_task, 0.01)
        assert future.result() == "Slept for 0.01"
    assert not manager._is_running


@pytest.fixture(scope="module")
def app_manager():
    """A shared manager for all tests in this module."""
    with GoroutineManager() as manager:
        yield manager


def test_go_with_sync_function(app_manager):
    """Tests submitting a standard blocking function."""
    future = app_manager.go(sync_io_task, 0.1)
    assert future.result(timeout=1) == "Slept for 0.1"


def test_go_with_async_function(app_manager):
    """Tests submitting an async coroutine function."""
    future = app_manager.go(async_io_task, 0.1)
    assert future.result(timeout=1) == "Slept for 0.1"


def test_go_with_multiprocessing(app_manager):
    """Tests submitting a function to the process pool."""
    future = app_manager.go(cpu_intensive_task, 1000, process=True)
    assert future.result(timeout=5) == 332833500


def test_channels_with_operators(app_manager):
    """Tests channel send/receive via operators and iteration."""
    channel = app_manager.nc()

    def producer():
        time.sleep(0.1)
        channel << "hello"
        channel.close()

    app_manager.go(producer)

    items = [item for item in channel]
    assert items == ["hello"]


# --- Tests for new Go-inspired concepts ---


def test_select_statement(app_manager):
    """Tests that select picks the first available channel."""
    ch1 = app_manager.nc()
    ch2 = app_manager.nc()

    def worker(ch, delay, msg):
        time.sleep(delay)
        ch << msg

    app_manager.go(worker, ch1, 0.2, "slow")
    app_manager.go(worker, ch2, 0.05, "fast")

    # Use the fixture's manager for select
    ready_case = app_manager.select([Case(ch1, GET), Case(ch2, GET)])

    assert ready_case.channel is ch2
    assert ready_case.value == "fast"


def test_select_non_blocking(app_manager):
    """Tests that a non-blocking select returns None immediately if no case is ready."""
    ch1 = app_manager.nc()
    # Use the fixture's manager for select
    result = app_manager.select([Case(ch1, GET)], non_blocking=True)
    assert result is None


def test_waitgroup(app_manager):
    """Tests that WaitGroup blocks until all tasks are done."""
    # Associate the WaitGroup with the fixture's manager
    wg = WaitGroup(manager=app_manager)
    results = collections.deque()

    def worker(worker_id):
        with defer(wg.done):
            time.sleep(0.01 * worker_id)
            results.append(worker_id)

    num_workers = 5
    wg.add(num_workers)
    for i in range(num_workers):
        app_manager.go(worker, i)

    wg.wait()  # This should block until all 5 workers call done()
    assert len(results) == num_workers
    assert set(results) == set(range(num_workers))


def test_context_with_timeout(app_manager):
    """Tests that a task is cancelled when its context times out."""
    # Use the fixture's manager to create the context
    ctx = app_manager.new_context_with_timeout(0.1)

    def long_running_worker(context):
        for _ in range(10):
            if context.is_done():
                return "cancelled"
            time.sleep(0.05)
        return "finished"

    future = app_manager.go(long_running_worker, ctx, ctx=ctx)

    # The fix is to call the blocking .result() method inside the context manager.
    # This is the operation that is expected to time out and raise the error.
    with pytest.raises(TimeoutError):
        future.result()

    # Optional: You can also add an assertion to ensure the context was marked as done.
    assert ctx.is_done()


def test_sync_once(app_manager):
    """Tests that a function is executed exactly once, even with concurrent callers."""
    once = Once()
    # Associate the WaitGroup with the fixture's manager
    wg = WaitGroup(manager=app_manager)
    run_count = []  # Use a list to have a mutable counter

    def initialize():
        run_count.append(1)
        time.sleep(0.1)  # Simulate initialization work

    def worker():
        with defer(wg.done):
            once.do(initialize)

    num_workers = 10
    wg.add(num_workers)
    for _ in range(num_workers):
        app_manager.go(worker)

    wg.wait()
    assert len(run_count) == 1
