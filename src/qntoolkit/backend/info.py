from qiskit_ibm_runtime import QiskitRuntimeService

from qntoolkit.utils import get_backend


def get_backend_info(
    service: QiskitRuntimeService,
    backend_name: str,
) -> dict:
    """Return basic information about a backend."""

    backend = get_backend(service, backend_name)

    return {
        "name": backend.name,
        "version": backend.backend_version,
        "description": backend.description,
        "num_qubits": backend.num_qubits,
        "online_date": backend.online_date,
        "operations": sorted(backend.operation_names),
    }


def get_backend_status(
    service: QiskitRuntimeService,
    backend_name: str,
) -> dict:
    """Return backend status."""

    backend = get_backend(service, backend_name)
    status = backend.status()

    return {
        "operational": status.operational,
        "pending_jobs": status.pending_jobs,
        "status_msg": status.status_msg,
    }


def get_supported_operations(
    service: QiskitRuntimeService,
    backend_name: str,
) -> list[str]:
    """Return supported quantum operations."""

    backend = get_backend(service, backend_name)

    return sorted(backend.operation_names)


def get_instruction_durations(
    service: QiskitRuntimeService,
    backend_name: str,
):
    """Return instruction durations."""

    backend = get_backend(service, backend_name)

    return backend.instruction_durations


def get_meas_map(
    service: QiskitRuntimeService,
    backend_name: str,
):
    """Return backend measurement map."""

    backend = get_backend(service, backend_name)

    return backend.meas_map


def get_dt(
    service: QiskitRuntimeService,
    backend_name: str,
):
    """Return backend dt."""

    backend = get_backend(service, backend_name)

    return backend.dt