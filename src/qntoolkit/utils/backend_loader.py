from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import QiskitRuntimeService

from qntoolkit.utils.exceptions import (
    BackendNotFoundError,
    ServiceNotInitializedError,
)


def get_simulator() -> AerSimulator:
    """Return the local Aer simulator."""
    return AerSimulator()


def get_backend(
    service: QiskitRuntimeService,
    backend_name: str,
):
    """Return an IBM Quantum backend."""

    if service is None:
        raise ServiceNotInitializedError(
            "Runtime service is not initialized."
        )

    if not backend_exists(service, backend_name):
        raise BackendNotFoundError(
            f"Backend '{backend_name}' not found."
        )

    return service.backend(backend_name)


def list_backends(service: QiskitRuntimeService) -> list[str]:
    """Return available backend names."""

    if service is None:
        raise ServiceNotInitializedError(
            "Runtime service is not initialized."
        )

    return sorted(
        backend.name
        for backend in service.backends()
        if backend.name is not None
    )


def backend_exists(
    service: QiskitRuntimeService,
    backend_name: str,
) -> bool:
    """Check whether a backend exists."""

    return backend_name in list_backends(service)