"""
Custom exceptions used throughout Quantum Noise Toolkit.
"""


class BackendNotFoundError(Exception):
    """Raised when a requested backend cannot be found."""
    pass


class BackendConnectionError(Exception):
    """Raised when a backend connection fails."""
    pass