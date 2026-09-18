"""
Custom exceptions used throughout Quantum Noise Toolkit.
"""


class QNToolkitError(Exception):
    pass


class BackendNotFoundError(QNToolkitError):
    """Raised when a requested backend cannot be found."""


class ServiceNotInitializedError(QNToolkitError):
    """Raised when the runtime service is not initialized."""


class BackendConnectionError(QNToolkitError):
    """Raised when a backend connection fails."""


class CalibrationDataError(QNToolkitError):
    """Raised when a backend does not provide the required calibration data."""
