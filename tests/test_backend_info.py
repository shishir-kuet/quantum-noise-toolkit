from qiskit_ibm_runtime import QiskitRuntimeService

from qntoolkit.backend import (
    get_backend_info,
    get_supported_operations,
)


service = QiskitRuntimeService()


def test_backend_info():

    info = get_backend_info(service, "ibm_fez")

    assert info["name"] == "ibm_fez"
    assert info["num_qubits"] > 0


def test_supported_operations():

    operations = get_supported_operations(
        service,
        "ibm_fez",
    )

    assert "measure" in operations