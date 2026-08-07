from qntoolkit.utils import get_simulator
from qntoolkit.utils import get_backend
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import QiskitRuntimeService

from qntoolkit.utils import backend_exists

from qntoolkit.utils import list_backends
from qntoolkit.utils.exceptions import BackendNotFoundError
import pytest

def test_list_backends():
    service = QiskitRuntimeService()

    backends = list_backends(service)

    assert isinstance(backends, list)
    assert len(backends) > 0
    assert "ibm_fez" in backends


def test_backend_exists():
    service = QiskitRuntimeService()

    assert backend_exists(service, "ibm_fez")


def test_simulator_returns_aer_backend():
    backend = get_simulator()

    assert backend is not None
    assert isinstance(backend, AerSimulator)
    assert backend.name == "aer_simulator"


def test_get_backend():
    service = QiskitRuntimeService()

    backend = get_backend(service, "ibm_fez")

    assert backend.name == "ibm_fez"    


def test_get_backend_invalid():
    service = QiskitRuntimeService()

    with pytest.raises(BackendNotFoundError):
        get_backend(service, "ibm_this_backend_does_not_exist")    