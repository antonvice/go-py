"""
go-py: Go-like concurrency in Python.

This library provides a simple, powerful API for concurrent programming,
inspired by the concurrency model of the Go language.
"""

__author__ = "Anton Vice"
__version__ = "0.1.7"

from .app import (
    GET,
    PUT,
    CancellationError,
    Case,
    Channel,
    Context,
    GoroutineManager,
    Once,
    TimeoutError,
    WaitGroup,
    defer,
    go,
    nc,
    new_context_with_timeout,
    select,
)

__all__ = [
    "go",
    "nc",
    "GoroutineManager",
    "Channel",
    "select",
    "Case",
    "GET",
    "PUT",
    "WaitGroup",
    "defer",
    "Context",
    "new_context_with_timeout",
    "CancellationError",
    "TimeoutError",
    "Once",
]
