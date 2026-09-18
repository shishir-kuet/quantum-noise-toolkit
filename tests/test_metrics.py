import numpy as np
import pytest
from qiskit.circuit.library import XGate
from qiskit.quantum_info import DensityMatrix, Operator

from qntoolkit.metrics import (
    gate_error,
    gate_fidelity,
    hellinger_fidelity,
    process_fidelity,
    purity,
    state_fidelity,
    total_variation_distance,
    trace_distance,
)
from qntoolkit.noise_models import BitFlip, DepolarizingNoise

ZERO = np.array([1, 0])
ONE = np.array([0, 1])
PLUS = np.array([1, 1]) / np.sqrt(2)


def test_state_fidelity():
    assert state_fidelity(ZERO, ZERO) == pytest.approx(1.0)
    assert state_fidelity(ZERO, ONE) == pytest.approx(0.0)
    assert state_fidelity(ZERO, PLUS) == pytest.approx(0.5)


def test_purity():
    assert purity(ZERO) == pytest.approx(1.0)
    assert purity(DensityMatrix(np.eye(2) / 2)) == pytest.approx(0.5)


def test_trace_distance():
    assert trace_distance(ZERO, ONE) == pytest.approx(1.0)
    assert trace_distance(ZERO, ZERO) == pytest.approx(0.0)
    assert trace_distance(ZERO, PLUS) == pytest.approx(np.sqrt(0.5))


def test_channel_fidelities():
    # Bit flip with probability p: process fidelity = 1 - p.
    assert process_fidelity(BitFlip(0.1)) == pytest.approx(0.9)

    # Depolarizing with probability p on one qubit: F_avg = 1 - p / 2.
    assert gate_fidelity(DepolarizingNoise(0.1)) == pytest.approx(0.95)
    assert gate_error(DepolarizingNoise(0.1)) == pytest.approx(0.05)


def test_gate_fidelity_with_target():
    assert gate_fidelity(Operator(XGate()), target=Operator(XGate())) == pytest.approx(1.0)


def test_count_metrics():
    ideal = {"00": 500, "11": 500}

    assert hellinger_fidelity(ideal, ideal) == pytest.approx(1.0)
    assert total_variation_distance(ideal, ideal) == pytest.approx(0.0)
    assert total_variation_distance({"0": 10}, {"1": 10}) == pytest.approx(1.0)
    assert total_variation_distance(ideal, {"00": 400, "11": 400, "01": 200}) == pytest.approx(0.2)

    with pytest.raises(ValueError):
        total_variation_distance({}, ideal)
