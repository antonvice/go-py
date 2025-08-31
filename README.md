# pygoroutine 🚀

[![PyPI version](https://badge.fury.io/py/pygoroutine.svg)](https://badge.fury.io/py/pygoroutine)
[![Build Status](https://github.com/antonvice/pygoroutine/actions/workflows/ci.yml/badge.svg)](https://github.com/antonvice/pygoroutine/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Go-like Concurrency in Python.**

`pygoroutine` brings the simplicity and power of Go's concurrency model—goroutines and channels—to Python. It provides a dead-simple API to make concurrent programming feel effortless and intuitive, whether you're dealing with I/O-bound or CPU-bound tasks.

### Key Features

*   **Dead-Simple Concurrency:** Fire-and-forget tasks with a single `go()` call.
*   **Go-style Channels:** Elegant communication using `ch << value` to send and `for item in ch:` to receive.
*   **True Parallelism:** Bypass the GIL for CPU-bound tasks with `process=True`.
*   **Unified API:** Handles `async` and regular functions automatically.
*   **Robust Lifecycle Management:** An optional `GoroutineManager` provides fine-grained control for libraries and complex applications.

## Installation

```bash
pip install pygoroutine
```

## Quick Start: The Go-like Way

This example demonstrates the core features: starting a concurrent task with `go()` and communicating with it over a `channel`.

```python
import time
from pygoroutine import go, nc

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
    ch = nc()
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
from pygoroutine import go
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
from pygoroutine import go

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
from pygoroutine import GoroutineManager
import time

def worker(ch):
    time.sleep(0.1)
    ch << "done"

with GoroutineManager() as app:
    ch = app.nc()
    app.go(worker, ch)
    result = ch.get()
    print(f"Received '{result}' from worker.")

print("Manager has been shut down.")
```

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
