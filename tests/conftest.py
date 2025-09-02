# tests/conftest.py

import multiprocessing as mp

import pytest

import pygoroutine.app


@pytest.fixture(scope="session", autouse=True)
def manage_global_goroutine_manager():
    """
    A session-scoped fixture to ensure the global GoroutineManager
    is shut down cleanly after all tests have run.
    """
    # The `autouse=True` means this fixture will be used for every test
    # session without needing to be explicitly requested.

    # The code before the 'yield' runs at the beginning of the test session.
    # We don't need to do anything here.

    yield

    # The code after the 'yield' runs at the very end of the test session.
    print("\nShutting down global goroutine manager...")
    if pygoroutine.app._default_manager._is_running:
        pygoroutine.app._default_manager.shutdown()


@pytest.fixture(scope="session", autouse=True)
def set_multiprocessing_context():
    """
    Sets a safer multiprocessing start method for the entire test session
    to avoid potential deadlocks and suppress DeprecationWarnings on Linux.
    """
    try:
        # 'spawn' is safer as it creates a fresh process without inheriting locks.
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        # This can happen if the context is already set.
        pass
