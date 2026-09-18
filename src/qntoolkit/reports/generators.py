"""
Ready-made reports for backends, circuits and noise models.

Each generator returns a :class:`~qntoolkit.reports.report.Report`; if
``output`` is given, the report is also written to that file, with the
format inferred from its extension (``.md``, ``.html``, ``.json``, ``.csv``).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from qiskit import QuantumCircuit
from qiskit_aer.noise import NoiseModel

from qntoolkit.analysis.backend import (
    average_gate_fidelities,
    backend_score,
    calibration_statistics,
    error_hotspots,
    rank_qubits,
)
from qntoolkit.analysis.circuit import analyse_circuit
from qntoolkit.characterization.calibration import (
    backend_name,
    backend_summary,
    qubit_properties,
    two_qubit_gate_properties,
)
from qntoolkit.noise_models.builder import noise_model_summary
from qntoolkit.noise_models.channels import NoiseChannel, ReadoutNoise

from .report import Report


def _save(report: Report, output: str | Path | None, fmt: str | None) -> Report:
    if output is not None:
        report.save(output, fmt)

    return report


def generate_backend_report(
    backend,
    output: str | Path | None = None,
    fmt: str | None = None,
    top_qubits: int = 10,
) -> Report:
    """Full calibration report: summary, statistics, hotspots, qubit ranking
    and per-qubit / per-coupler calibration tables."""

    name = backend_name(backend)
    summary = backend_summary(backend)

    report = Report(f"Backend report: {name}")

    report.add_section(
        "Summary",
        facts={
            **{
                key.replace("_", " "): value
                for key, value in summary.to_dict().items()
                if key != "name"
            },
            "backend score (0-100)": backend_score(backend),
        },
    )

    fidelities = average_gate_fidelities(backend)
    if fidelities:
        report.add_section("Average gate fidelity", facts=fidelities)

    report.add_section("Calibration statistics", table=calibration_statistics(backend))

    hotspots = error_hotspots(backend)
    report.add_section(
        "Error hotspots",
        text=(
            "Qubits and couplers whose calibration is a statistical outlier "
            "(robust z-score > 3.5)."
            if not hotspots.empty
            else "No calibration outliers detected."
        ),
        table=(
            None
            if hotspots.empty
            else hotspots.assign(
                location=hotspots["location"].map(lambda loc: "-".join(map(str, loc)))
            )
        ),
    )

    report.add_section(
        f"Top {top_qubits} qubits",
        table=rank_qubits(backend).head(top_qubits)[
            [
                "rank",
                "score",
                "readout_error",
                "single_qubit_error",
                "two_qubit_error",
                "t1_us",
                "t2_us",
            ]
        ],
    )

    report.add_section("Qubit calibration", table=qubit_properties(backend), primary=True)

    couplers = two_qubit_gate_properties(backend)
    if not couplers.empty:
        report.add_section("Two-qubit gate calibration", table=couplers)

    return _save(report, output, fmt)


def generate_circuit_report(
    circuit: QuantumCircuit,
    backend,
    output: str | Path | None = None,
    fmt: str | None = None,
    **analysis_options,
) -> Report:
    """Report of :func:`~qntoolkit.analysis.analyse_circuit` for one circuit."""

    analysis = analyse_circuit(circuit, backend, **analysis_options)

    report = Report(f"Circuit report: {analysis.circuit_name} on {analysis.backend}")

    report.add_section(
        "Estimate",
        facts={
            "estimated fidelity": analysis.estimated_fidelity,
            "estimated error": analysis.estimated_error,
            "success probability": analysis.success_probability,
            "reliability score (0-100)": analysis.reliability_score,
            "reliability": analysis.reliability,
            "estimated duration (ns)": analysis.duration_ns,
        },
    )

    report.add_section(
        "Circuit statistics",
        facts={
            "logical qubits": analysis.num_qubits,
            "physical qubits": analysis.physical_qubits,
            "depth": analysis.depth,
            "two-qubit depth": analysis.two_qubit_depth,
            "size": analysis.size,
            "single-qubit gates": analysis.num_single_qubit_gates,
            "two-qubit gates": analysis.num_two_qubit_gates,
            "measurements": analysis.num_measurements,
        },
    )

    report.add_section(
        "Gate counts",
        table=pd.DataFrame(
            sorted(analysis.gate_counts.items(), key=lambda item: -item[1]),
            columns=["gate", "count"],
        ),
    )

    report.add_section(
        "Error budget",
        text="Product of (1 - error) per instruction category.",
        table=pd.DataFrame(
            [
                {"category": category, "count": item["count"], "fidelity": item["fidelity"]}
                for category, item in analysis.error_budget.items()
            ]
        ),
    )

    return _save(report, output, fmt)


def generate_noise_summary(
    noise,
    output: str | Path | None = None,
    fmt: str | None = None,
) -> Report:
    """Summarize an Aer ``NoiseModel`` or a collection of toolkit channels.

    ``noise`` may be a ``NoiseModel``, a single channel, or a list of
    ``NoiseChannel``/``ReadoutNoise`` objects.
    """

    from qntoolkit.metrics import gate_fidelity

    report = Report("Noise summary")

    if isinstance(noise, NoiseModel):
        summary = noise_model_summary(noise)
        report.add_section("Noise model", facts=summary)
        return _save(report, output, fmt)

    channels = [noise] if isinstance(noise, (NoiseChannel, ReadoutNoise)) else list(noise)
    rows = []

    for channel in channels:
        if isinstance(channel, ReadoutNoise):
            rows.append(
                {
                    "channel": repr(channel),
                    "type": "readout",
                    "num_qubits": 1,
                    "average_gate_fidelity": None,
                    "error": channel.error,
                }
            )
        else:
            fidelity = gate_fidelity(channel)
            rows.append(
                {
                    "channel": repr(channel),
                    "type": type(channel).__name__,
                    "num_qubits": channel.num_qubits,
                    "average_gate_fidelity": fidelity,
                    "error": 1.0 - fidelity,
                }
            )

    report.add_section("Channels", table=pd.DataFrame(rows))

    return _save(report, output, fmt)
