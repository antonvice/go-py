# go-py 🚀

[![PyPI version](https://badge.fury.io/py/go-py.svg)](https://badge.fury.io/py/go-py)
[![Build Status](https://github.com/antonvice/go-py/actions/workflows/python-package.yml/badge.svg)](https://github.com/antonvice/go-py/actions/workflows/python-package.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Go-like Concurrency in Python.**

`go-py` brings the simplicity and power of Go's concurrency model—goroutines and channels—to Python. It provides a dead-simple API to make concurrent programming feel effortless and intuitive, whether you're dealing with I/O-bound or CPU-bound tasks.

### Key Features

*   **Dead-Simple Concurrency:** Fire-and-forget tasks with a single `go()` call.
*   **Go-style Channels:** Elegant communication using `ch << value` to send and `for item in ch:` to receive.
*   **True Parallelism:** Bypass the GIL for CPU-bound tasks with `process=True`.
*   **Unified API:** Handles `async` and regular functions automatically.
*   **Robust Lifecycle Management:** An optional `GoroutineManager` provides fine-grained control for libraries and complex applications.

## Installation

```bash
pip install go-py
```

## Quick Start: The Go-like Way

This example demonstrates the core features: starting a concurrent task with `go()` and communicating with it over a `channel`.

```python
import time
from gopy import go, new_channel

def producer(ch):
    """A producer "goroutine" that sends numbers over a channel."""
    print("Producer starting...")
    for i in range(5):
        message = f"Message #{i+1}"
        print(f"-> Sending: '{message}'")
        ch << message  # Send a value into the channel
        time.sleep(0.5)
    
    ch.close()
    print("Producer finished.")

def main():
    ch = new_channel()
    go(producer, ch)

    # The main thread becomes the consumer.
    print("Consumer waiting for messages...")
    for received_message in ch:
        print(f"<- Received: '{received_message}'")
    
    print("Consumer finished. All tasks complete.")

if __name__ == "__main__":
    main()
```

## Core Concepts

### 1. The `go()` Function

The `go()` function is the heart of the library. It runs any function or coroutine concurrently without blocking and returns a `Future` object.

```python
from gopy import go
import time

def my_sync_task(name):
    time.sleep(1)
    return f"Sync task '{name}' finished."

future = go(my_sync_task, "A")
print("Main thread is not blocked.")

# You can optionally wait for the result
result = future.result()
print(result)
```

### 2. Channels for Communication

Channels provide a safe and elegant way for your concurrent tasks to communicate.

-   **Send:** `channel << value`
-   **Receive (Loop):** `for item in channel:`
-   **Receive (Single):** `item = channel.get()`
-   **Close:** `channel.close()`

### 3. True Parallelism for CPU-Bound Tasks

Bypass Python's GIL by running CPU-bound tasks in a separate process with the `process=True` flag.

```python
from gopy import go

def sum_squares(n):
    return sum(i * i for i in range(n))

# This runs in another process, utilizing another CPU core.
future = go(sum_squares, 10_000_000, process=True)
result = future.result()
print(f"Result from process: {result}")
```

## Advanced Usage: The `GoroutineManager`

For libraries or applications needing explicit setup and teardown, use the `GoroutineManager`. It provides a context manager for clean, predictable lifecycle management.

```python
from gopy import GoroutineManager
import time

def worker(ch):
    time.sleep(0.1)
    ch << "done"

with GoroutineManager() as app:
    ch = app.new_channel()
    app.go(worker, ch)
    result = ch.get()
    print(f"Received '{result}' from worker.")

print("Manager has been shut down.")
```

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
```

---

### `demo.py`

```python
import time
from gopy import go, new_channel

def number_producer(ch):
    """A producer "goroutine"."""
    print("Producer starting...")
    for i in range(5):
        message = f"message {i}"
        print(f"-> Sending: {message}")
        ch << message
        time.sleep(0.5)
    ch.close()
    print("Producer finished.")

def cpu_task():
    """A CPU-bound task."""
    print("CPU task starting...")
    result = sum(i * i for i in range(10_000_000))
    print("CPU task finished.")
    return result

def main():
    # --- Channel Demo ---
    ch = new_channel()
    go(number_producer, ch)

    print("Consumer waiting for messages...")
    for received_message in ch:
        print(f"<- Received: {received_message}")
    print("Consumer finished.")

    print("\n" + "-"*20 + "\n")

    # --- CPU-Bound Demo ---
    future = go(cpu_task, process=True)
    print("Main thread continues while CPU task runs...")
    
    time.sleep(1)
    print("Main thread did some other work.")

    result = future.result()
    print(f"Got result from CPU task: {result}")


if __name__ == "__main__":
    main()
```

---

### `tests/test_app.py`

```python
import time
import pytest
import asyncio
from gopy import GoroutineManager

def cpu_intensive_task(x):
    return sum(i * i for i in range(x))

async def async_io_task(duration):
    await asyncio.sleep(duration)
    return f"Slept for {duration}"

def sync_io_task(duration):
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
    future = app_manager.go(sync_io_task, 0.1)
    assert future.result(timeout=1) == "Slept for 0.1"

def test_go_with_async_function(app_manager):
    future = app_manager.go(async_io_task, 0.1)
    assert future.result(timeout=1) == "Slept for 0.1"

def test_go_with_multiprocessing(app_manager):
    future = app_manager.go(cpu_intensive_task, 1000, process=True)
    assert future.result(timeout=5) == 332833500

def test_channels_with_operators(app_manager):
    channel = app_manager.new_channel()

    def producer():
        time.sleep(0.1)
        channel << "hello"
        channel.close()

    app_manager.go(producer)

    # Test iteration
    items = [item for item in channel]
    assert items == ["hello"]
