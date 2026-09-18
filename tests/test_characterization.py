import math

import pytest

from qntoolkit.characterization import (
    BackendSummary,
    backend_summary,
    compare_backends,
    gate_durations,
    gate_errors,
    gate_names,
    qubit_properties,
    readout_errors,
    single_qubit_gate,
    t1_times,
    t2_times,
    two_qubit_gate,
    two_qubit_gate_properties,
)
from qntoolkit.utils.exceptions import CalibrationDataError


def test_native_gates(manila, fez):
    assert single_qubit_gate(manila) == "sx"
    assert two_qubit_gate(manila) == "cx"
    assert two_qubit_gate(fez) == "cz"
    assert "rz" in gate_names(manila, num_qubits=1)
    assert "measure" not in gate_names(manila)


def test_coherence_times_in_microseconds(manila):
    t1 = t1_times(manila)
    t2 = t2_times(manila)

    assert set(t1) == set(range(5))
    # Manila's T1 is ~130 us in the calibration snapshot.
    assert 131 < t1[0] < 132
    assert all(value > 0 for value in t2.values())


def test_readout_and_gate_errors(manila):
    readout = readout_errors(manila)

    assert readout[0] == pytest.approx(0.0353)

    cx = gate_errors(manila, "cx")
    assert (0, 1) in cx
    assert 0 < cx[(0, 1)] < 0.05

    everything = gate_errors(manila)
    assert {"cx", "sx", "x", "rz"} <= set(everything)

    durations = gate_durations(manila, "sx")
    assert durations[(0,)] == pytest.approx(35.56, abs=0.01)


def test_unknown_gate_raises(manila):
    with pytest.raises(CalibrationDataError):
        gate_errors(manila, "not_a_gate")


def test_qubit_properties_table(fez):
    table = qubit_properties(fez)

    assert len(table) == 156
    assert list(table.columns) == [
        "t1_us",
        "t2_us",
        "frequency_ghz",
        "readout_error",
        "readout_duration_ns",
        "single_qubit_error",
        "two_qubit_error",
    ]
    # Disabled couplers (error 1.0) never leak into per-qubit averages.
    assert table["two_qubit_error"].max() < 1.0


def test_two_qubit_gate_properties(manila):
    table = two_qubit_gate_properties(manila)

    assert len(table) == 8  # 4 couplers x 2 directions
    assert set(table["gate"]) == {"cx"}


def test_backend_summary(manila, fez):
    summary = backend_summary(manila)

    assert isinstance(summary, BackendSummary)
    assert summary.name == "fake_manila"
    assert summary.num_qubits == 5
    assert summary.num_couplers == 4
    assert summary.num_faulty_couplers == 0
    assert 100 < summary.mean_t1_us < 200
    assert "fake_manila" in str(summary)

    fez_summary = backend_summary(fez)
    assert fez_summary.num_faulty_couplers == 7
    assert fez_summary.mean_two_qubit_error < 0.01


def test_summary_of_ideal_simulator(aer):
    summary = backend_summary(aer)

    assert summary.mean_t1_us is None
    assert summary.two_qubit_gate is None
    assert "n/a" in str(summary)


def test_compare_backends(manila, fez):
    table = compare_backends([manila, fez])

    assert list(table.index) == ["fake_manila", "fake_fez"]
    assert not math.isnan(table.loc["fake_fez", "mean_readout_error"])
