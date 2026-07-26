from qntoolkit.utils import simulator
from qiskit_aer import AerSimulator


def test_simulator_returns_aer_backend():
    backend = simulator()

    assert backend is not None
    assert isinstance(backend, AerSimulator)
    assert backend.name == "aer_simulator"