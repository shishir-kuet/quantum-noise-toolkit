"""
Backend loading utilities.

This module provides a unified interface for connecting to IBM Quantum
backends and local simulators.
"""

from qiskit_aer import AerSimulator

def load_backend(name: str):
    """Load a backend by name."""
    raise NotImplementedError


def list_backends():
    """Return all available backends."""
    raise NotImplementedError


def get_backend_info(name: str):
    """Return information about a backend."""
    raise NotImplementedError


def backend_status(name: str):
    """Return backend status."""
    raise NotImplementedError


def get_least_busy_backend():
    """Return the least busy available backend."""
    raise NotImplementedError


def simulator():
    """Return a local Aer simulator."""
    return AerSimulator()