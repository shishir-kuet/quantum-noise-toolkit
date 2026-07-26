"""
Custom exceptions used throughout Quantum Noise Toolkit.
"""

class QNToolkitError(Exception):
    pass

class BackendNotFoundError(QNToolkitError):
    """Raised when a requested backend cannot be found."""
    pass

class ServiceNotInitializedError(QNToolkitError):
    """Raised when the runtime service is not initialized."""
    pass

class BackendConnectionError(QNToolkitError):
    """Raised when a backend connection fails."""
    pass