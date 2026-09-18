"""
Extract calibration data (T1, T2, gate errors, readout errors) from backends.

All functions accept any Qiskit ``BackendV2`` (real IBM backends, fake
backends, Aer) or a bare :class:`~qiskit.transpiler.Target`. Calibration
values are read from the backend ``Target``.

Units used throughout the toolkit:

- T1, T2 in microseconds (``us``)
- Qubit frequencies in GHz
- Gate and readout durations in nanoseconds (``ns``)
- Errors as probabilities in ``[0, 1]``
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from qiskit.transpiler import Target

from qntoolkit.utils.exceptions import CalibrationDataError

# Operations in a Target that are not gates and have no meaningful gate error.
NON_GATE_OPERATIONS = frozenset(
    {
        "measure",
        "reset",
        "delay",
        "barrier",
        "id",
        "if_else",
        "for_loop",
        "while_loop",
        "switch_case",
        "box",
    }
)

TWO_QUBIT_GATE_PREFERENCE = ("cx", "ecr", "cz")
SINGLE_QUBIT_GATE_PREFERENCE = ("sx", "x")

# IBM reports an error of 1.0 for qubits and couplers that are disabled.
FAULTY_ERROR_THRESHOLD = 1.0


def get_target(backend) -> Target:
    """Return the ``Target`` of a backend (or the target itself)."""

    if isinstance(backend, Target):
        return backend

    target = getattr(backend, "target", None)

    if target is None:
        raise CalibrationDataError(
            "Backend does not expose a Target. A Qiskit BackendV2 is required."
        )

    return target


def backend_name(backend) -> str:
    """Return a readable name for a backend or target."""

    if isinstance(backend, Target):
        return backend.description or "target"

    return getattr(backend, "name", None) or type(backend).__name__


def _num_qubits(backend) -> int:
    return get_target(backend).num_qubits or 0


def _gate_arity(target: Target, name: str) -> int | None:
    operation = target.operation_from_name(name)

    # Control-flow operations are stored as classes, not instances.
    if isinstance(operation, type):
        return None

    return getattr(operation, "num_qubits", None)


def _instruction_properties(target: Target, name: str):
    """Yield ``(qargs, properties)`` for calibrated qargs of an instruction."""

    if name not in target:
        return

    for qargs, properties in target[name].items():
        if qargs is None or properties is None:
            continue
        yield qargs, properties


def _to_micro(value: float | None) -> float | None:
    return None if value is None else value * 1e6


def _to_nano(value: float | None) -> float | None:
    return None if value is None else value * 1e9


def _nan_stat(values, function) -> float | None:
    array = np.array(
        [value for value in values if value is not None],
        dtype=float,
    )

    if array.size == 0 or np.all(np.isnan(array)):
        return None

    return float(function(array[~np.isnan(array)]))


def gate_names(backend, num_qubits: int | None = None) -> list[str]:
    """Return calibrated gate names, optionally filtered by qubit count."""

    target = get_target(backend)
    names = []

    for name in target.operation_names:
        if name in NON_GATE_OPERATIONS:
            continue

        arity = _gate_arity(target, name)

        if arity is None:
            continue

        if num_qubits is not None and arity != num_qubits:
            continue

        names.append(name)

    return sorted(names)


def _select_gate(backend, num_qubits: int, preference: tuple[str, ...]) -> str | None:
    target = get_target(backend)
    candidates = gate_names(target, num_qubits=num_qubits)

    def has_errors(name: str) -> bool:
        return any(
            properties.error is not None for _, properties in _instruction_properties(target, name)
        )

    for name in preference:
        if name in candidates and has_errors(name):
            return name

    # Fall back to the gate with the largest calibrated error (skips
    # virtual gates such as rz, whose error is zero).
    best_name, best_error = None, 0.0

    for name in candidates:
        errors = [
            properties.error
            for _, properties in _instruction_properties(target, name)
            if properties.error is not None
        ]

        if errors and max(errors) > best_error:
            best_name, best_error = name, max(errors)

    return best_name


def single_qubit_gate(backend) -> str | None:
    """Return the reference single-qubit gate (``sx`` on IBM devices)."""

    return _select_gate(backend, 1, SINGLE_QUBIT_GATE_PREFERENCE)


def two_qubit_gate(backend) -> str | None:
    """Return the native two-qubit gate (``cx``, ``ecr`` or ``cz``)."""

    return _select_gate(backend, 2, TWO_QUBIT_GATE_PREFERENCE)


def _qubit_property(backend, attribute: str) -> dict[int, float | None]:
    target = get_target(backend)
    properties = target.qubit_properties
    values: dict[int, float | None] = {}

    for qubit in range(_num_qubits(target)):
        value = None

        if properties is not None and qubit < len(properties):
            value = getattr(properties[qubit], attribute, None)

        values[qubit] = value

    return values


def t1_times(backend) -> dict[int, float | None]:
    """Return T1 relaxation times per qubit, in microseconds."""

    return {qubit: _to_micro(value) for qubit, value in _qubit_property(backend, "t1").items()}


def t2_times(backend) -> dict[int, float | None]:
    """Return T2 dephasing times per qubit, in microseconds."""

    return {qubit: _to_micro(value) for qubit, value in _qubit_property(backend, "t2").items()}


def qubit_frequencies(backend) -> dict[int, float | None]:
    """Return qubit frequencies, in GHz."""

    return {
        qubit: None if value is None else value / 1e9
        for qubit, value in _qubit_property(backend, "frequency").items()
    }


def readout_errors(backend) -> dict[int, float | None]:
    """Return the measurement (readout) error per qubit."""

    target = get_target(backend)
    errors: dict[int, float | None] = dict.fromkeys(range(_num_qubits(target)))

    for qargs, properties in _instruction_properties(target, "measure"):
        errors[qargs[0]] = properties.error

    return errors


def readout_durations(backend) -> dict[int, float | None]:
    """Return the measurement duration per qubit, in nanoseconds."""

    target = get_target(backend)
    durations: dict[int, float | None] = dict.fromkeys(range(_num_qubits(target)))

    for qargs, properties in _instruction_properties(target, "measure"):
        durations[qargs[0]] = _to_nano(properties.duration)

    return durations


def gate_errors(backend, gate: str | None = None) -> dict:
    """Return gate errors.

    With ``gate`` given, returns ``{qargs: error}`` for that gate. Otherwise
    returns ``{gate_name: {qargs: error}}`` for every calibrated gate.
    """

    target = get_target(backend)

    if gate is not None:
        if gate not in target:
            raise CalibrationDataError(f"Gate '{gate}' is not supported by the backend.")

        return {
            qargs: properties.error for qargs, properties in _instruction_properties(target, gate)
        }

    return {name: gate_errors(target, name) for name in gate_names(target)}


def gate_durations(backend, gate: str | None = None) -> dict:
    """Return gate durations in nanoseconds (same shape as :func:`gate_errors`)."""

    target = get_target(backend)

    if gate is not None:
        if gate not in target:
            raise CalibrationDataError(f"Gate '{gate}' is not supported by the backend.")

        return {
            qargs: _to_nano(properties.duration)
            for qargs, properties in _instruction_properties(target, gate)
        }

    return {name: gate_durations(target, name) for name in gate_names(target)}


def two_qubit_gate_properties(backend) -> pd.DataFrame:
    """Return a table of native two-qubit gate calibrations, one row per pair."""

    target = get_target(backend)
    gate = two_qubit_gate(target)
    columns = ["gate", "qubit_0", "qubit_1", "error", "duration_ns"]

    if gate is None:
        return pd.DataFrame(columns=columns)

    rows = [
        {
            "gate": gate,
            "qubit_0": qargs[0],
            "qubit_1": qargs[1],
            "error": properties.error,
            "duration_ns": _to_nano(properties.duration),
        }
        for qargs, properties in _instruction_properties(target, gate)
    ]

    return pd.DataFrame(rows, columns=columns).astype({"error": float, "duration_ns": float})


def qubit_properties(backend) -> pd.DataFrame:
    """Return per-qubit calibration data as a DataFrame indexed by qubit.

    Columns: ``t1_us``, ``t2_us``, ``frequency_ghz``, ``readout_error``,
    ``readout_duration_ns``, ``single_qubit_error`` (reference 1q gate) and
    ``two_qubit_error`` (mean over the operational native 2q gates touching
    the qubit; disabled couplers with error 1.0 are excluded).
    """

    target = get_target(backend)
    num_qubits = _num_qubits(target)

    sq_gate = single_qubit_gate(target)
    sq_errors = gate_errors(target, sq_gate) if sq_gate else {}

    tq_table = two_qubit_gate_properties(target)
    tq_errors: dict[int, list[float]] = {qubit: [] for qubit in range(num_qubits)}

    for row in tq_table.itertuples():
        if not math.isnan(row.error) and row.error < FAULTY_ERROR_THRESHOLD:
            tq_errors[row.qubit_0].append(row.error)
            tq_errors[row.qubit_1].append(row.error)

    t1 = t1_times(target)
    t2 = t2_times(target)
    frequency = qubit_frequencies(target)
    readout = readout_errors(target)
    readout_length = readout_durations(target)

    rows = []

    for qubit in range(num_qubits):
        rows.append(
            {
                "qubit": qubit,
                "t1_us": t1[qubit],
                "t2_us": t2[qubit],
                "frequency_ghz": frequency[qubit],
                "readout_error": readout[qubit],
                "readout_duration_ns": readout_length[qubit],
                "single_qubit_error": sq_errors.get((qubit,)),
                "two_qubit_error": (float(np.mean(tq_errors[qubit])) if tq_errors[qubit] else None),
            }
        )

    columns = [
        "qubit",
        "t1_us",
        "t2_us",
        "frequency_ghz",
        "readout_error",
        "readout_duration_ns",
        "single_qubit_error",
        "two_qubit_error",
    ]

    table = pd.DataFrame(rows, columns=columns).set_index("qubit")

    return table.astype(float)


@dataclass(frozen=True)
class BackendSummary:
    """Aggregate calibration statistics for a backend."""

    name: str
    num_qubits: int
    single_qubit_gate: str | None
    two_qubit_gate: str | None
    num_couplers: int
    num_faulty_qubits: int
    num_faulty_couplers: int
    mean_t1_us: float | None
    median_t1_us: float | None
    mean_t2_us: float | None
    median_t2_us: float | None
    mean_readout_error: float | None
    mean_single_qubit_error: float | None
    mean_two_qubit_error: float | None

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        def fmt(value, spec: str, unit: str = "") -> str:
            return "n/a" if value is None else f"{value:{spec}}{unit}"

        lines = [
            f"Backend               : {self.name}",
            f"Qubits (faulty)       : {self.num_qubits} ({self.num_faulty_qubits})",
            f"Native 1Q / 2Q Gates  : {self.single_qubit_gate or 'n/a'} / "
            f"{self.two_qubit_gate or 'n/a'}",
            f"Couplers (faulty)     : {self.num_couplers} ({self.num_faulty_couplers})",
            f"Average T1            : {fmt(self.mean_t1_us, '.1f', ' us')}",
            f"Average T2            : {fmt(self.mean_t2_us, '.1f', ' us')}",
            f"Average 1Q Error      : {fmt(self.mean_single_qubit_error, '.2e')}",
            f"Average 2Q Error      : {fmt(self.mean_two_qubit_error, '.2e')}",
            f"Average Readout Error : {fmt(self.mean_readout_error, '.2e')}",
        ]

        return "\n".join(lines)


def backend_summary(backend) -> BackendSummary:
    """Return aggregate calibration statistics for a backend.

    Disabled qubits and couplers (gate error 1.0) are counted in
    ``num_faulty_qubits`` / ``num_faulty_couplers`` and excluded from the
    mean gate errors.
    """

    target = get_target(backend)
    qubits = qubit_properties(target)
    couplers = two_qubit_gate_properties(target)
    faulty = couplers["error"] >= FAULTY_ERROR_THRESHOLD
    faulty_qubits = qubits["single_qubit_error"] >= FAULTY_ERROR_THRESHOLD

    def undirected_pairs(table: pd.DataFrame) -> set[tuple[int, int]]:
        return {
            tuple(sorted(pair)) for pair in zip(table["qubit_0"], table["qubit_1"], strict=True)
        }

    return BackendSummary(
        name=backend_name(backend),
        num_qubits=_num_qubits(target),
        single_qubit_gate=single_qubit_gate(target),
        two_qubit_gate=two_qubit_gate(target),
        num_couplers=len(undirected_pairs(couplers)),
        num_faulty_qubits=int(faulty_qubits.sum()),
        num_faulty_couplers=len(undirected_pairs(couplers[faulty])),
        mean_t1_us=_nan_stat(qubits["t1_us"], np.mean),
        median_t1_us=_nan_stat(qubits["t1_us"], np.median),
        mean_t2_us=_nan_stat(qubits["t2_us"], np.mean),
        median_t2_us=_nan_stat(qubits["t2_us"], np.median),
        mean_readout_error=_nan_stat(qubits["readout_error"], np.mean),
        mean_single_qubit_error=_nan_stat(
            qubits.loc[~faulty_qubits, "single_qubit_error"], np.mean
        ),
        mean_two_qubit_error=_nan_stat(couplers.loc[~faulty, "error"], np.mean),
    )


def compare_backends(backends) -> pd.DataFrame:
    """Return a table comparing :func:`backend_summary` across backends."""

    rows = [backend_summary(backend).to_dict() for backend in backends]

    return pd.DataFrame(rows).set_index("name")
