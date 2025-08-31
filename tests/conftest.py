# tests/conftest.py

import pytest

import gopy.app


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
    if gopy.app._default_manager._is_running:
        gopy.app._default_manager.shutdown()
