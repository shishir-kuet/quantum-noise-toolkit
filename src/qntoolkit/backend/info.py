from qiskit_ibm_runtime import QiskitRuntimeService

from qntoolkit.utils import get_backend


def get_backend_info(
    service: QiskitRuntimeService,
    backend_name: str,
) -> dict:
    """Return basic backend information."""

    backend = get_backend(service, backend_name)

    return {
        "name": backend.name,
        "version": backend.backend_version,
        "num_qubits": backend.num_qubits,
        "operations": list(backend.operation_names),
    }


def get_backend_target(
    service: QiskitRuntimeService,
    backend_name: str,
):
    """Return the backend target."""

    backend = get_backend(service, backend_name)

    return backend.target


def get_backend_properties(
    service: QiskitRuntimeService,
    backend_name: str,
):
    """Return backend properties."""

    backend = get_backend(service, backend_name)

    return backend.properties()


def get_backend_configuration(
    service: QiskitRuntimeService,
    backend_name: str,
):
    """Return backend configuration."""

    backend = get_backend(service, backend_name)

    return backend.configuration()


def get_backend_status(
    service: QiskitRuntimeService,
    backend_name: str,
):
    """Return backend status."""

    backend = get_backend(service, backend_name)

    return backend.status()


def get_num_qubits(
    service: QiskitRuntimeService,
    backend_name: str,
) -> int:
    """Return number of physical qubits."""

    backend = get_backend(service, backend_name)

    return backend.num_qubits


def get_operation_names(
    service: QiskitRuntimeService,
    backend_name: str,
) -> list[str]:
    """Return supported operation names."""

    backend = get_backend(service, backend_name)

    return list(backend.operation_names)


def get_coupling_map(
    service: QiskitRuntimeService,
    backend_name: str,
):
    """Return backend coupling map."""

    backend = get_backend(service, backend_name)

    return backend.coupling_map


def get_supported_operations(
    service: QiskitRuntimeService,
    backend_name: str,
) -> list[str]:
    """Return supported operations."""

    return get_operation_names(service, backend_name)