from qiskit_ibm_runtime import QiskitRuntimeService

from .backend_loader import get_backend


def get_backend_info(backend) -> dict:
    """Return basic backend information."""

    return {
        "name": backend.name,
        "version": backend.backend_version,
        "num_qubits": backend.num_qubits,
        "operations": backend.operation_names,
    }


def get_backend_target(backend):
    """Return the backend Target."""

    return backend.target


def get_backend_properties(backend):
    """Return backend properties."""

    return backend.properties()


def get_backend_configuration(backend):
    """Return backend configuration."""

    return backend.configuration()


def get_backend_status(backend):
    """Return backend status."""

    return backend.status()


def get_num_qubits(backend) -> int:
    """Return number of physical qubits."""

    return backend.num_qubits


def get_operation_names(backend) -> list[str]:
    """Return supported operation names."""

    return list(backend.operation_names)


def get_coupling_map(backend):
    """Return backend coupling map."""

    return backend.coupling_map