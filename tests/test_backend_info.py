import pytest

from qntoolkit.backend import (
    get_backend_configuration,
    get_backend_info,
    get_backend_properties,
    get_backend_status,
    get_backend_target,
    get_coupling_map,
    get_num_qubits,
    get_operation_names,
    get_supported_operations,
)

from .conftest import IBM_BACKEND

pytestmark = pytest.mark.ibm


def test_backend_info(ibm_service):
    info = get_backend_info(ibm_service, IBM_BACKEND)

    assert isinstance(info, dict)
    assert info["name"] == IBM_BACKEND
    assert info["num_qubits"] > 0


def test_backend_target(ibm_service):
    target = get_backend_target(
        ibm_service,
        IBM_BACKEND,
    )

    assert target is not None


def test_backend_properties(ibm_service):
    properties = get_backend_properties(
        ibm_service,
        IBM_BACKEND,
    )

    assert properties is not None


def test_backend_configuration(ibm_service):
    configuration = get_backend_configuration(
        ibm_service,
        IBM_BACKEND,
    )

    assert configuration is not None


def test_backend_status(ibm_service):
    status = get_backend_status(
        ibm_service,
        IBM_BACKEND,
    )

    assert status is not None


def test_num_qubits(ibm_service):
    qubits = get_num_qubits(
        ibm_service,
        IBM_BACKEND,
    )

    assert qubits > 0


def test_operation_names(ibm_service):
    operations = get_operation_names(
        ibm_service,
        IBM_BACKEND,
    )

    assert isinstance(operations, list)
    assert "measure" in operations


def test_supported_operations(ibm_service):
    operations = get_supported_operations(
        ibm_service,
        IBM_BACKEND,
    )

    assert "measure" in operations


def test_coupling_map(ibm_service):
    coupling = get_coupling_map(
        ibm_service,
        IBM_BACKEND,
    )

    assert coupling is not None
