import asyncio
import time

import pytest

from pygoroutine import GoroutineManager


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
