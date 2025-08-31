# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Go-like `select` Statement**: Introduced `gopy.select` function and `gopy.Case` class to wait on multiple channel operations simultaneously, mimicking Go's `select`.
- **`WaitGroup` for Synchronization**: Added `gopy.WaitGroup` to allow a goroutine to wait for a collection of other goroutines to complete their execution.
- **`defer` Context Manager**: Implemented `gopy.defer` as a utility for ensuring cleanup functions are called upon exiting a scope, commonly used with `WaitGroup.done()`.
- **Contexts for Cancellation and Timeouts**: Added `gopy.Context` and `gopy.new_context_with_timeout` to enable request-scoped deadlines, cancellation signals, and graceful timeouts across multiple goroutines. Custom exceptions `CancellationError` and `TimeoutError` were also added.
- **`Once` for Singleton Initialization**: Implemented `gopy.Once` to ensure a specific function is executed exactly one time, regardless of concurrent calls, which is ideal for thread-safe lazy initialization of shared resources.

### Changed
- The `gopy.go()` function now accepts an optional `ctx` keyword argument to associate a running task with a `Context` for cancellation management.
- The `gopy.WaitGroup` constructor now accepts an optional `manager` argument to associate it with a specific `GoroutineManager` instance, crucial for isolated testing.

### Fixed
- Refactored `select`, `WaitGroup`, and `new_context_with_timeout` to be methods on the `GoroutineManager` class. This resolves a deadlock that occurred when using a non-global manager (e.g., in tests), ensuring that all asynchronous operations are scheduled on the correct event loop.

## [0.1.3] - 2025-09-02

### Added
- Initial public release of `go-py`.
- Core `go()` function for running synchronous and asynchronous callables concurrently in a background thread pool.
- `nc()` function for creating Go-style `Channel` objects for communication between goroutines.
- Syntactic sugar for channels: `ch << value` for sending and `for item in ch:` for receiving.
- `process=True` flag in the `go()` function to run CPU-bound tasks in a separate process, bypassing the GIL.
- `GoroutineManager` class for explicit, predictable lifecycle management (setup and teardown), ideal for libraries and complex applications.
- A global default `GoroutineManager` instance to power the simple top-level API (`go`, `nc`) without requiring manual setup.