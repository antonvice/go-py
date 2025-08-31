# pygoroutine 🚀

[![PyPI version](https://badge.fury.io/py/pygoroutine.svg)](https://badge.fury.io/py/pygoroutine)
[![Build Status](https://github.com/antonvice/pygoroutine/actions/workflows/python-package.yml/badge.svg)](https://github.com/antonvice/pygoroutine/actions/workflows/python-package.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Go-like Concurrency in Python.**

`pygoroutine` brings the simplicity and power of Go's concurrency model—goroutines and channels—to Python. It provides a dead-simple API to make concurrent programming feel effortless and intuitive, whether you're dealing with I/O-bound or CPU-bound tasks.

### Key Features

*   **Dead-Simple Concurrency:** Fire-and-forget tasks with a single `go()` call.
*   **Go-style Channels:** Elegant communication using `ch << value` to send and `for item in ch:` to receive.
*   **Powerful Concurrency Patterns:** Go-like `select`, `WaitGroup`, `Context`, and `Once` primitives for sophisticated coordination.
*   **True Parallelism:** Bypass the GIL for CPU-bound tasks with `process=True`.
*   **Unified API:** Handles `async` and regular functions automatically.
*   **Robust Lifecycle Management:** An optional `GoroutineManager` provides fine-grained control for libraries and complex applications.

## Installation

```
pip install pygoroutine
```

# Quick Start: The Go-like Way

This example demonstrates the core features: starting a concurrent task with go() and communicating with it over a channel.

```
import time
from gopy import go, nc

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

# Core Concepts
1. The go() Function
The go() function is the heart of the library. It runs any function or coroutine concurrently without blocking and returns a Future object.
```
from gopy import go
import time

def my_sync_task(name):
    time.sleep(1)
    return f"Sync task '{name}' finished."

future = go(my_sync_task, "A")
print("Main thread is not blocked.")

You can optionally wait for the result
result = future.result()
print(result)
```

2. Channels for Communication
Channels provide a safe and elegant way for your concurrent tasks to communicate.
Send: channel << value
Receive (Loop): for item in channel:
Receive (Single): item = channel.get()
Close: channel.close()

3. True Parallelism for CPU-Bound Tasks
Bypass Python's GIL by running CPU-bound tasks in a separate process with the process=True flag.
```
from gopy import go

def sum_squares(n):
    return sum(i * i for i in range(n))
```
# This runs in another process, utilizing another CPU core.
```
future = go(sum_squares, 10_000_000, process=True)
result = future.result()
print(f"Result from process: {result}")
```
# Advanced Go-like Patterns
pygoroutine also includes implementations of Go's most powerful concurrency primitives.
## select: Waiting on Multiple Channels
The select statement waits for several channel operations to be ready and executes the first one that is.
```
from gopy import go, nc, select, Case, GET
import time

ch1 = nc()
ch2 = nc()

def worker(ch, delay, msg):
    time.sleep(delay)
    ch << msg

go(worker, ch1, 0.2, "from ch1")
go(worker, ch2, 0.1, "from ch2")

# select blocks until one of the cases is ready
ready_case = select([
    Case(ch1, GET),
    Case(ch2, GET),
])

# The result is attached to the case object

print(f"Received '{ready_case.value}' from the first ready channel.")
```
# Output: Received 'from ch2' from the first ready channel.
## WaitGroup: Waiting for a Group of Tasks
A WaitGroup blocks until a collection of goroutines has finished.
```
from gopy import go, WaitGroup, defer
import time

wg = WaitGroup()

def worker(id):
    with defer(wg.done): # Ensures wg.done() is called on exit
        print(f"Worker {id} starting...")
        time.sleep(0.5)
        print(f"Worker {id} finished.")

wg.add(3) # Set the counter
for i in range(3):
    go(worker, i)

print("Main thread waiting...")
wg.wait() # Blocks until the counter is zero
print("All workers are done.")
```
## Context: Cancellation and Timeouts
A Context provides a standardized way to signal cancellation or deadlines across multiple goroutines.
```
from gopy import go, new_context_with_timeout, TimeoutError
import time

def slow_worker(ctx):
    print("Worker starting, has 3 seconds to complete.")
    for i in range(3):
        if ctx.is_done():
            print(f"Worker cancelled: {ctx.err()}")
            return
        time.sleep(1)
        print(f"Worker heartbeat {i+1}...")
    print("Worker finished successfully.")

# Create a context that times out after 1.5 seconds
ctx = new_context_with_timeout(1.5)
future = go(slow_worker, ctx=ctx)

try:
    future.result()
except TimeoutError as e:
    print(f"Main thread caught error: {e}")
```

## Once: Do Something Exactly Once
A Once object ensures that a given function is executed only one time, no matter how many concurrent tasks try to call it. It's perfect for thread-safe lazy initialization.

```
from gopy import go, Once, WaitGroup

initializer = Once()

def setup_resource():
    print("--- Initializing shared resource ONCE ---")

def worker(id, wg):
    defer(wg.done)
    print(f"Worker {id} requesting resource.")
    initializer.do(setup_resource)
    print(f"Worker {id} has resource.")

wg = WaitGroup()
wg.add(3)
for i in range(3):
    go(worker, i, wg)
wg.wait()
```
# The "Initializing shared resource" message will only print once.
## Advanced Usage: The GoroutineManager
For libraries or applications needing explicit setup and teardown, use the GoroutineManager. It provides a context manager for clean, predictable lifecycle management.

```
from gopy import GoroutineManager
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

# License
This project is licensed under the MIT License - see the LICENSE file for details.