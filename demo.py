import time

from pygoroutine import (
    GET,
    Case,
    Once,
    TimeoutError,
    WaitGroup,
    defer,
    go,
    nc,
    new_context_with_timeout,
    select,
)


# A producer "goroutine"
def number_producer(ch):
    """A producer 'goroutine' that sends messages over a channel."""
    print("Producer starting...")
    for i in range(5):
        message = f"message {i}"
        print(f"-> Sending: {message}")
        ch << message  # So clean!
        time.sleep(0.5)
    ch.close()  # Signal that we're done
    print("Producer finished.")


# A CPU-bound task
def cpu_task():
    """A CPU-bound task that performs a heavy calculation."""
    print("CPU task starting...")
    result = sum(i * i for i in range(10_000_000))
    print("CPU task finished.")
    return result


def advanced_features_demo():
    print("\n" + "=" * 20)
    print(" ADVANCED FEATURES DEMO")
    print("=" * 20 + "\n")

    # --- Select Demo ---
    print("--- 1. Select Demo ---")
    ch1 = nc()
    ch2 = nc()

    def worker(ch, delay, message):
        time.sleep(delay)
        ch << message

    go(worker, ch1, 0.2, "one")
    go(worker, ch2, 0.1, "two")

    ready_case = select([Case(ch1, GET), Case(ch2, GET)])
    print(f"Select received '{ready_case.value}' from the first ready channel.")
    # Clean up the other channel
    if ready_case.channel is ch2:
        ch1.get()
    else:
        ch2.get()
    print("-" * 20 + "\n")

    # --- WaitGroup Demo ---
    print("--- 2. WaitGroup Demo ---")
    wg = WaitGroup()
    results = []

    def wg_worker(worker_id):
        with defer(wg.done):
            print(f"WaitGroup worker {worker_id} starting...")
            time.sleep(0.1)
            results.append(worker_id)
            print(f"WaitGroup worker {worker_id} finished.")

    wg.add(3)
    for i in range(3):
        go(wg_worker, i)

    print("Main thread waiting for WaitGroup...")
    wg.wait()
    print(f"All workers finished. Results: {sorted(results)}")
    print("-" * 20 + "\n")

    # --- Context with Timeout Demo ---
    print("--- 3. Context with Timeout Demo ---")
    # Use a WaitGroup to ensure the worker has fully exited before continuing.
    context_wg = WaitGroup()

    def slow_worker(ctx):
        # Use defer to guarantee the WaitGroup is marked as done on any exit path.
        with defer(context_wg.done):
            print(
                "Slow worker starting, has 5s to work, but context will timeout in 1s."
            )
            for i in range(5):
                if ctx.is_done():
                    # The worker prints its last words before exiting.
                    print(f"Worker cancelled after {i} seconds: {ctx.err()}")
                    return
                time.sleep(1)
            print("Worker finished successfully (should not happen).")

    context_wg.add(1)
    ctx = new_context_with_timeout(1.0)
    future = go(slow_worker, ctx, ctx=ctx)
    try:
        future.result()
    except TimeoutError as e:
        print(f"Main thread correctly caught expected error: {e}")

    # Wait for the worker goroutine to fully finish its cleanup and printing.
    context_wg.wait()

    print("-" * 20 + "\n")

    # --- Once Demo ---
    print("--- 4. Once Demo ---")
    initializer = Once()
    once_wg = WaitGroup()

    def setup_resource():
        print("--- LAZY INITIALIZATION RUNNING ---")
        time.sleep(0.1)  # Simulate work
        print("--- RESOURCE INITIALIZED ---")

    def once_worker(worker_id):
        with defer(once_wg.done):
            print(f"Once worker {worker_id} requesting resource...")
            initializer.do(setup_resource)
            print(f"Once worker {worker_id} has the resource.")

    once_wg.add(3)
    for i in range(3):
        go(once_worker, i)
    once_wg.wait()
    print("--- All workers tried to initialize, but it only ran once. ---")
    print("-" * 20 + "\n")


def main():
    # --- Channel Demo ---
    ch = nc()
    go(number_producer, ch)

    # The main thread becomes the consumer.
    # This loop will block and wait for values, then exit when the channel is closed.
    print("Consumer waiting for messages...")
    for received_message in ch:
        print(f"<- Received: {received_message}")
    print("Consumer finished.")

    print("\n" + "-" * 20 + "\n")

    # --- CPU-Bound Demo ---
    # Fire and forget a CPU-intensive task in another process
    future = go(cpu_task, process=True)
    print("Main thread continues while CPU task runs in the background...")

    # Do other work
    time.sleep(1)
    print("Main thread did some other work.")

    # Now, wait for the result from the process
    result = future.result()
    print(f"Got result from CPU task: {result}")

    # --- Advanced Features Demo ---
    advanced_features_demo()


if __name__ == "__main__":
    main()
