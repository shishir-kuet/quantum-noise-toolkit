"""End-to-end checks of the toolkit against a live IBM Quantum backend."""

import pytest

from qntoolkit.analysis import analyse_circuit, backend_score, error_hotspots
from qntoolkit.characterization import backend_summary, qubit_properties
from qntoolkit.reports import generate_backend_report
from qntoolkit.utils import load_backend

from .conftest import IBM_BACKEND

pytestmark = pytest.mark.ibm


@pytest.fixture(scope="module")
def ibm_backend(ibm_service):
    return load_backend(IBM_BACKEND, service=ibm_service)


def test_live_calibration(ibm_backend):
    summary = backend_summary(ibm_backend)
    table = qubit_properties(ibm_backend)

    assert summary.num_qubits == ibm_backend.num_qubits
    assert summary.mean_t1_us and summary.mean_t1_us > 0
    assert table["readout_error"].notna().sum() > 0


def test_live_analysis(ibm_backend, ghz):
    analysis = analyse_circuit(ghz, ibm_backend, seed_transpiler=1)

    assert 0 < analysis.success_probability <= 1
    assert 0 < backend_score(ibm_backend) <= 100
    assert error_hotspots(ibm_backend) is not None


def test_live_report(ibm_backend):
    assert IBM_BACKEND in generate_backend_report(ibm_backend).to_markdown()
