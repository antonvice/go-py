"""
go-py: Go-like concurrency in Python.

This library provides a simple, powerful API for concurrent programming,
inspired by the concurrency model of the Go language.
"""

__author__ = "Anton Vice"
__version__ = "0.1.4"

from .app import Channel, GoroutineManager, go, nc

__all__ = ["go", "nc", "GoroutineManager", "Channel"]
