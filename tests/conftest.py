import warnings

import matplotlib
import pytest

# Render figures off-screen during tests.
matplotlib.use("Agg")

IBM_BACKEND = "ibm_fez"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        'ibm: needs IBM Quantum credentials and network access (deselect with -m "not ibm")',
    )


@pytest.fixture(scope="session")
def ibm_service():
    """A live QiskitRuntimeService; tests are skipped if it is unavailable."""

    from qiskit_ibm_runtime import QiskitRuntimeService

    try:
        return QiskitRuntimeService()
    except Exception as error:
        pytest.skip(f"IBM Quantum service unavailable: {error}")


@pytest.fixture(scope="session")
def manila():
    from qntoolkit.utils import get_fake_backend

    return get_fake_backend("fake_manila")


@pytest.fixture(scope="session")
def fez():
    from qntoolkit.utils import get_fake_backend

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return get_fake_backend("fake_fez")


@pytest.fixture(scope="session")
def aer():
    from qntoolkit.utils import get_simulator

    return get_simulator()


@pytest.fixture
def ghz():
    from qiskit import QuantumCircuit

    circuit = QuantumCircuit(3, name="ghz")
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    circuit.measure_all()

    return circuit
