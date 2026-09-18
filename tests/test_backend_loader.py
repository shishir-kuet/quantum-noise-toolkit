import pytest
from qiskit_aer import AerSimulator

from qntoolkit.utils import (
    backend_exists,
    get_backend,
    get_fake_backend,
    get_simulator,
    list_backends,
    list_fake_backends,
    load_backend,
)
from qntoolkit.utils.exceptions import (
    BackendNotFoundError,
    ServiceNotInitializedError,
)

from .conftest import IBM_BACKEND


def test_simulator_returns_aer_backend():
    backend = get_simulator()

    assert backend is not None
    assert isinstance(backend, AerSimulator)
    assert backend.name == "aer_simulator"


def test_get_backend_without_service():
    with pytest.raises(ServiceNotInitializedError):
        get_backend(None, IBM_BACKEND)


def test_list_backends_without_service():
    with pytest.raises(ServiceNotInitializedError):
        list_backends(None)


def test_fake_backends():
    names = list_fake_backends()

    assert "fake_manila" in names
    assert "fake_fez" in names

    backend = get_fake_backend("fake_manila")

    assert backend.name == "fake_manila"
    assert backend.num_qubits == 5


def test_fake_backend_invalid():
    with pytest.raises(BackendNotFoundError):
        get_fake_backend("fake_this_backend_does_not_exist")


def test_load_backend_offline():
    assert load_backend("aer_simulator").name == "aer_simulator"
    assert load_backend("fake_manila").name == "fake_manila"


@pytest.mark.ibm
def test_list_backends(ibm_service):
    backends = list_backends(ibm_service)

    assert isinstance(backends, list)
    assert len(backends) > 0
    assert IBM_BACKEND in backends


@pytest.mark.ibm
def test_backend_exists(ibm_service):
    assert backend_exists(ibm_service, IBM_BACKEND)


@pytest.mark.ibm
def test_get_backend(ibm_service):
    backend = get_backend(ibm_service, IBM_BACKEND)

    assert backend.name == IBM_BACKEND


@pytest.mark.ibm
def test_get_backend_invalid(ibm_service):
    with pytest.raises(BackendNotFoundError):
        get_backend(ibm_service, "ibm_this_backend_does_not_exist")


@pytest.mark.ibm
def test_load_backend_ibm(ibm_service):
    backend = load_backend(IBM_BACKEND, service=ibm_service)

    assert backend.name == IBM_BACKEND
