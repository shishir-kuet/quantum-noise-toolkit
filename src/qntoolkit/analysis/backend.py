"""
Analyse and compare quantum backends using their calibration data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from qiskit import QuantumCircuit

from qntoolkit.characterization.calibration import (
    FAULTY_ERROR_THRESHOLD,
    backend_name,
    backend_summary,
    compare_backends,
    gate_errors,
    gate_names,
    get_target,
    qubit_properties,
    two_qubit_gate_properties,
)

from .circuit import analyse_circuit

# Metrics where a *larger* value is worse.
ERROR_METRICS = ("readout_error", "single_qubit_error")
# Metrics where a *smaller* value is worse.
COHERENCE_METRICS = ("t1_us", "t2_us")


def _one_minus(value) -> float:
    return 1.0 if value is None or np.isnan(value) else 1.0 - float(value)


def backend_score(backend) -> float:
    """Return a 0-100 backend reliability score.

    The score is the success probability of a reference layer consisting of
    one single-qubit gate, one native two-qubit gate and one measurement,
    each with the backend's *average* error::

        score = 100 * (1 - e_1q) * (1 - e_2q) * (1 - e_readout)

    Missing error data counts as zero error, so ideal simulators score 100.
    """

    summary = backend_summary(backend)

    return 100.0 * (
        _one_minus(summary.mean_single_qubit_error)
        * _one_minus(summary.mean_two_qubit_error)
        * _one_minus(summary.mean_readout_error)
    )


def rank_qubits(backend) -> pd.DataFrame:
    """Rank qubits from best to worst.

    Each qubit's ``score`` is ``(1 - readout_error) * (1 - single_qubit_error)
    * (1 - two_qubit_error)``, where ``two_qubit_error`` is the mean error of
    the native two-qubit gates acting on it.
    """

    table = qubit_properties(backend)

    score = (
        (1.0 - table["readout_error"].fillna(0.0))
        * (1.0 - table["single_qubit_error"].fillna(0.0))
        * (1.0 - table["two_qubit_error"].fillna(0.0))
    )

    table = table.assign(score=score).sort_values("score", ascending=False)
    table.insert(0, "rank", range(1, len(table) + 1))

    return table


def best_qubits(backend, count: int = 5) -> list[int]:
    """Return the ``count`` best qubits according to :func:`rank_qubits`."""

    return [int(qubit) for qubit in rank_qubits(backend).index[:count]]


def worst_qubits(backend, count: int = 5) -> list[int]:
    """Return the ``count`` worst qubits, worst first."""

    return [int(qubit) for qubit in rank_qubits(backend).index[::-1][:count]]


def _robust_z_scores(values: pd.Series) -> pd.Series:
    """Modified z-score (Iglewicz & Hoaglin) based on the median absolute
    deviation, which is not skewed by the outliers we are looking for."""

    values = values.dropna().astype(float)

    if values.empty:
        return values

    median = values.median()
    mad = (values - median).abs().median()

    if mad == 0:
        std = values.std(ddof=0)

        if std == 0 or np.isnan(std):
            return values * 0.0

        return (values - values.mean()) / std

    return 0.6745 * (values - median) / mad


def error_hotspots(backend, threshold: float = 3.5) -> pd.DataFrame:
    """Find qubits and couplers whose calibration is anomalously bad.

    A value is flagged when its robust (MAD-based) z-score exceeds
    ``threshold`` in the bad direction: high errors, or low T1/T2.
    The result is sorted from most to least anomalous.
    """

    table = qubit_properties(backend)
    rows = []

    for metric in ERROR_METRICS + COHERENCE_METRICS:
        scores = _robust_z_scores(table[metric])
        sign = 1.0 if metric in ERROR_METRICS else -1.0

        for qubit, z_score in scores.items():
            if sign * z_score > threshold:
                rows.append(
                    {
                        "kind": "qubit",
                        "location": (int(qubit),),
                        "metric": metric,
                        "value": float(table.at[qubit, metric]),
                        "z_score": float(z_score),
                    }
                )

    couplers = two_qubit_gate_properties(backend)

    if not couplers.empty:
        # One row per undirected pair.
        couplers = (
            couplers.assign(
                pair=[
                    tuple(sorted(pair))
                    for pair in zip(couplers["qubit_0"], couplers["qubit_1"], strict=True)
                ]
            )
            .drop_duplicates("pair")
            .set_index("pair")
        )

        for pair, z_score in _robust_z_scores(couplers["error"]).items():
            if z_score > threshold:
                rows.append(
                    {
                        "kind": "coupler",
                        "location": pair,
                        "metric": f"{couplers.at[pair, 'gate']}_error",
                        "value": float(couplers.at[pair, "error"]),
                        "z_score": float(z_score),
                    }
                )

    columns = ["kind", "location", "metric", "value", "z_score"]
    result = pd.DataFrame(rows, columns=columns)

    if result.empty:
        return result

    return result.reindex(result["z_score"].abs().sort_values(ascending=False).index).reset_index(
        drop=True
    )


def calibration_statistics(backend) -> pd.DataFrame:
    """Return mean, std, min, median and max of each per-qubit metric."""

    table = qubit_properties(backend)
    statistics = table.agg(["count", "mean", "std", "min", "median", "max"]).T
    statistics.index.name = "metric"

    return statistics


def average_gate_fidelities(backend) -> dict[str, float]:
    """Return ``1 - mean error`` for every calibrated gate (disabled
    couplers with error 1.0 are excluded)."""

    target = get_target(backend)
    fidelities = {}

    for name in gate_names(target):
        errors = [
            error
            for error in gate_errors(target, name).values()
            if error is not None and error < FAULTY_ERROR_THRESHOLD
        ]

        if errors:
            fidelities[name] = 1.0 - float(np.mean(errors))

    return fidelities


def rank_backends(backends) -> pd.DataFrame:
    """Compare backends and rank them by :func:`backend_score`."""

    backends = list(backends)
    table = compare_backends(backends)
    table["score"] = [backend_score(backend) for backend in backends]
    table = table.sort_values("score", ascending=False)
    table.insert(0, "rank", range(1, len(table) + 1))

    return table


def backend_suitability(
    circuit: QuantumCircuit,
    backends,
    optimization_level: int = 1,
    seed_transpiler: int | None = None,
) -> pd.DataFrame:
    """Rank backends by the estimated success probability of ``circuit``."""

    rows = []

    for backend in backends:
        analysis = analyse_circuit(
            circuit,
            backend,
            optimization_level=optimization_level,
            seed_transpiler=seed_transpiler,
        )

        rows.append(
            {
                "backend": backend_name(backend),
                "depth": analysis.depth,
                "two_qubit_gates": analysis.num_two_qubit_gates,
                "estimated_fidelity": analysis.estimated_fidelity,
                "success_probability": analysis.success_probability,
                "reliability": analysis.reliability,
            }
        )

    table = pd.DataFrame(rows).sort_values("success_probability", ascending=False)
    table.insert(0, "rank", range(1, len(table) + 1))

    return table.set_index("backend")
