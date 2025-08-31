"""
go-py: Go-like concurrency in Python.

This library provides a simple, powerful API for concurrent programming,
inspired by the concurrency model of the Go language.
"""

__author__ = "anton"
__version__ = "0.1.0"

from .app import Channel, GoroutineManager, go, new_channel

__all__ = ["go", "new_channel", "GoroutineManager", "Channel"]
