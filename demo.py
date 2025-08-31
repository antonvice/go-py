import time

from gopy import go, nc


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


if __name__ == "__main__":
    main()
