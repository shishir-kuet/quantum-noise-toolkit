import math

import pytest
from qiskit import QuantumCircuit, transpile

from qntoolkit.analysis import (
    CircuitAnalysis,
    analyse_circuit,
    analyze_circuit,
    average_gate_fidelities,
    backend_score,
    backend_suitability,
    best_qubits,
    calibration_statistics,
    circuit_statistics,
    error_budget,
    error_hotspots,
    estimate_fidelity,
    estimate_success_probability,
    idle_budget,
    idle_error,
    rank_backends,
    rank_qubits,
    reliability_label,
    worst_qubits,
)
from qntoolkit.characterization import gate_errors, readout_errors
from qntoolkit.utils.exceptions import CalibrationDataError


def test_circuit_statistics(ghz):
    statistics = circuit_statistics(ghz)

    assert statistics["num_qubits"] == 3
    assert statistics["num_two_qubit_gates"] == 2
    assert statistics["num_single_qubit_gates"] == 1
    assert statistics["num_measurements"] == 3
    assert statistics["two_qubit_depth"] == 2


def test_estimate_matches_manual_product(manila):
    circuit = QuantumCircuit(2)
    circuit.sx(0)
    circuit.cx(0, 1)
    circuit.measure_all()

    # Map trivially onto physical qubits 0 and 1.
    mapped = transpile(circuit, manila, initial_layout=[0, 1], optimization_level=0)

    sx = gate_errors(manila, "sx")[(0,)]
    cx = gate_errors(manila, "cx")[(0, 1)]
    readout = readout_errors(manila)

    expected_fidelity = (1 - sx) * (1 - cx)
    expected_success = expected_fidelity * (1 - readout[0]) * (1 - readout[1])

    assert estimate_fidelity(mapped, manila) == pytest.approx(expected_fidelity)
    assert estimate_success_probability(mapped, manila) == pytest.approx(expected_success)

    budget = error_budget(mapped, manila)
    assert budget["two_qubit"]["count"] == 1
    assert budget["readout"]["count"] == 2


def test_analyse_circuit(ghz, fez):
    analysis = analyse_circuit(ghz, fez, seed_transpiler=1)

    assert isinstance(analysis, CircuitAnalysis)
    assert analysis.backend == "fake_fez"
    assert analysis.num_two_qubit_gates == analysis.cx_count == 2
    assert 0.8 < analysis.success_probability < analysis.estimated_fidelity < 1.0
    assert analysis.estimated_error == pytest.approx(1 - analysis.estimated_fidelity)
    assert analysis.reliability_score == pytest.approx(100 * analysis.success_probability)
    assert len(analysis.physical_qubits) == 3
    assert analysis.duration_ns and analysis.duration_ns > 0
    assert "Circuit Reliability" in str(analysis)
    assert analyze_circuit is analyse_circuit


def test_ideal_simulator_is_perfect(ghz, aer):
    analysis = analyse_circuit(ghz, aer)

    assert analysis.success_probability == pytest.approx(1.0)
    assert analysis.reliability == "excellent"


def test_untranspiled_circuit_without_transpile_raises(manila):
    circuit = QuantumCircuit(1)
    circuit.h(0)

    with pytest.raises(CalibrationDataError):
        estimate_fidelity(circuit, manila, transpile_circuit=False)


def test_reliability_label():
    assert reliability_label(0.95) == "excellent"
    assert reliability_label(0.75) == "good"
    assert reliability_label(0.55) == "fair"
    assert reliability_label(0.1) == "poor"


def test_backend_score(manila, aer):
    assert 90 < backend_score(manila) < 100
    assert backend_score(aer) == pytest.approx(100.0)


def test_qubit_ranking(fez):
    ranking = rank_qubits(fez)

    assert list(ranking["rank"][:3]) == [1, 2, 3]
    assert ranking["score"].is_monotonic_decreasing

    best = best_qubits(fez, 5)
    worst = worst_qubits(fez, 5)

    assert len(best) == len(worst) == 5
    assert not set(best) & set(worst)


def test_error_hotspots_find_faulty_couplers(fez):
    hotspots = error_hotspots(fez)
    couplers = hotspots[(hotspots["kind"] == "coupler") & (hotspots["value"] >= 1.0)]

    assert len(couplers) == 7
    assert hotspots["z_score"].abs().is_monotonic_decreasing


def test_calibration_statistics(manila):
    statistics = calibration_statistics(manila)

    assert "t1_us" in statistics.index
    assert {"mean", "median", "std"} <= set(statistics.columns)


def test_average_gate_fidelities(fez):
    fidelities = average_gate_fidelities(fez)

    assert fidelities["rz"] == pytest.approx(1.0)
    assert 0.99 < fidelities["cz"] < 1.0


def test_rank_backends(manila, fez, aer):
    ranking = rank_backends([manila, fez, aer])

    assert ranking.index[0] == "aer_simulator"
    assert list(ranking["rank"]) == [1, 2, 3]


def test_backend_suitability(ghz, manila, fez):
    table = backend_suitability(ghz, [manila, fez], seed_transpiler=1)

    assert set(table.index) == {"fake_manila", "fake_fez"}
    assert table["success_probability"].is_monotonic_decreasing
    assert not any(math.isnan(value) for value in table["success_probability"])


def test_idle_error_matches_thermal_relaxation_channel():
    from qntoolkit.metrics import gate_error
    from qntoolkit.noise_models import ThermalRelaxation

    for t1, t2, duration in [(100.0, 80.0, 1.0), (50.0, 90.0, 5.0), (120.0, 30.0, 0.3)]:
        expected = gate_error(ThermalRelaxation(t1, t2, duration))
        assert idle_error(duration, t1, t2) == pytest.approx(expected, rel=1e-9)

    assert idle_error(0.0, 100.0, 80.0) == 0.0


def test_idle_budget(fez, aer):
    circuit = QuantumCircuit(5, name="ghz_5")
    circuit.h(0)
    for qubit in range(4):
        circuit.cx(qubit, qubit + 1)
    circuit.measure_all()

    mapped = transpile(circuit, fez, optimization_level=1, seed_transpiler=3)
    budget = idle_budget(mapped, fez)

    assert budget["count"] > 0
    assert budget["duration_ns"] > 0
    assert 0.99 < budget["fidelity"] < 1.0

    # Ideal simulators have no durations, so nothing is charged.
    assert idle_budget(transpile(circuit, aer), aer)["fidelity"] == 1.0

    without_idle = analyse_circuit(mapped, fez)
    with_idle = analyse_circuit(mapped, fez, include_idle=True)

    assert with_idle.error_budget["idle"]["count"] == budget["count"]
    assert with_idle.success_probability == pytest.approx(
        without_idle.success_probability * budget["fidelity"]
    )
