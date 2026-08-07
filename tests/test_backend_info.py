from qiskit_ibm_runtime import QiskitRuntimeService

from qntoolkit.backend import (
    get_backend_info,
    get_backend_target,
    get_backend_properties,
    get_backend_configuration,
    get_backend_status,
    get_num_qubits,
    get_operation_names,
    get_coupling_map,
    get_supported_operations,
)

service = QiskitRuntimeService()


def test_backend_info():
    info = get_backend_info(service, "ibm_fez")

    assert isinstance(info, dict)
    assert info["name"] == "ibm_fez"
    assert info["num_qubits"] > 0


def test_backend_target():
    target = get_backend_target(
        service,
        "ibm_fez",
    )

    assert target is not None


def test_backend_properties():
    properties = get_backend_properties(
        service,
        "ibm_fez",
    )

    assert properties is not None


def test_backend_configuration():
    configuration = get_backend_configuration(
        service,
        "ibm_fez",
    )

    assert configuration is not None


def test_backend_status():
    status = get_backend_status(
        service,
        "ibm_fez",
    )

    assert status is not None


def test_num_qubits():
    qubits = get_num_qubits(
        service,
        "ibm_fez",
    )

    assert qubits > 0


def test_operation_names():
    operations = get_operation_names(
        service,
        "ibm_fez",
    )

    assert isinstance(operations, list)
    assert "measure" in operations


def test_supported_operations():
    operations = get_supported_operations(
        service,
        "ibm_fez",
    )

    assert "measure" in operations


def test_coupling_map():
    coupling = get_coupling_map(
        service,
        "ibm_fez",
    )

    assert coupling is not None