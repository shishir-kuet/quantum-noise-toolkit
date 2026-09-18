"""
Estimate how hardware noise affects a quantum circuit before running it.

The fidelity model multiplies ``(1 - error)`` over every instruction of the
circuit after it has been mapped onto the backend's physical qubits, using
the calibrated error of each gate on the exact qubits it acts on. This is the
standard "estimated success probability" (ESP) model: it assumes errors are
independent and ignores idle-time decoherence and crosstalk, so it is an
optimistic but fast and widely used first-order estimate.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import Target

from qntoolkit.characterization.calibration import backend_name, get_target
from qntoolkit.utils.exceptions import CalibrationDataError

IGNORED_INSTRUCTIONS = frozenset({"barrier", "delay"})

RELIABILITY_LEVELS = (
    (0.9, "excellent"),
    (0.7, "good"),
    (0.5, "fair"),
    (0.0, "poor"),
)


def reliability_label(success_probability: float) -> str:
    """Map a success probability to ``excellent``/``good``/``fair``/``poor``."""

    for threshold, label in RELIABILITY_LEVELS:
        if success_probability >= threshold:
            return label

    return "poor"


def circuit_statistics(circuit: QuantumCircuit) -> dict:
    """Return structural statistics of a circuit."""

    single_qubit = two_qubit = multi_qubit = measurements = 0

    for instruction in circuit.data:
        name = instruction.operation.name
        size = len(instruction.qubits)

        if name in IGNORED_INSTRUCTIONS:
            continue

        if name == "measure":
            measurements += 1
        elif size == 1:
            single_qubit += 1
        elif size == 2:
            two_qubit += 1
        elif size > 2:
            multi_qubit += 1

    return {
        "num_qubits": circuit.num_qubits,
        "num_clbits": circuit.num_clbits,
        "depth": circuit.depth(),
        "two_qubit_depth": circuit.depth(
            lambda instruction: len(instruction.qubits) == 2
            and instruction.operation.name not in IGNORED_INSTRUCTIONS
        ),
        "size": circuit.size(),
        "gate_counts": dict(circuit.count_ops()),
        "num_single_qubit_gates": single_qubit,
        "num_two_qubit_gates": two_qubit,
        "num_multi_qubit_gates": multi_qubit,
        "num_measurements": measurements,
    }


def prepare_circuit(
    circuit: QuantumCircuit,
    backend,
    transpile_circuit: bool | None = None,
    optimization_level: int = 1,
    seed_transpiler: int | None = None,
) -> QuantumCircuit:
    """Map a circuit onto the backend.

    With ``transpile_circuit=None`` the circuit is transpiled only if it has
    not been transpiled already (i.e. it has no layout).
    """

    if transpile_circuit is None:
        transpile_circuit = circuit.layout is None

    if not transpile_circuit:
        return circuit

    if isinstance(backend, Target):
        return transpile(
            circuit,
            target=backend,
            optimization_level=optimization_level,
            seed_transpiler=seed_transpiler,
        )

    return transpile(
        circuit,
        backend=backend,
        optimization_level=optimization_level,
        seed_transpiler=seed_transpiler,
    )


def _instruction_error(target: Target, name: str, qargs: tuple[int, ...]) -> float:
    if name not in target:
        raise CalibrationDataError(
            f"Instruction '{name}' is not supported by the backend. "
            "Transpile the circuit first or use transpile_circuit=True."
        )

    properties_map = target[name]

    if qargs in properties_map:
        properties = properties_map[qargs]
    elif None in properties_map:
        # Globally defined instruction (e.g. on simulators).
        properties = properties_map[None]
    else:
        raise CalibrationDataError(f"Instruction '{name}' is not calibrated on qubits {qargs}.")

    if properties is None or properties.error is None:
        return 0.0

    return float(properties.error)


def error_budget(circuit: QuantumCircuit, backend) -> dict:
    """Return the fidelity factor and instruction count per error category.

    ``circuit`` must already be mapped onto the backend (see
    :func:`prepare_circuit`). Categories are ``single_qubit``,
    ``two_qubit``, ``multi_qubit`` and ``readout``; each entry holds the
    product of ``(1 - error)`` over the category and the instruction count.
    """

    target = get_target(backend)

    budget = {
        category: {"fidelity": 1.0, "count": 0}
        for category in ("single_qubit", "two_qubit", "multi_qubit", "readout")
    }

    for instruction in circuit.data:
        name = instruction.operation.name

        if name in IGNORED_INSTRUCTIONS:
            continue

        qargs = tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits)
        error = _instruction_error(target, name, qargs)

        if name == "measure":
            category = "readout"
        elif len(qargs) == 1:
            category = "single_qubit"
        elif len(qargs) == 2:
            category = "two_qubit"
        else:
            category = "multi_qubit"

        budget[category]["fidelity"] *= 1.0 - error
        budget[category]["count"] += 1

    return budget


def _gate_fidelity(budget: dict) -> float:
    return (
        budget["single_qubit"]["fidelity"]
        * budget["two_qubit"]["fidelity"]
        * budget["multi_qubit"]["fidelity"]
    )


def estimate_fidelity(circuit: QuantumCircuit, backend, **transpile_options) -> float:
    """Estimate the fidelity of the circuit's gates (excluding measurement)."""

    mapped = prepare_circuit(circuit, backend, **transpile_options)

    return _gate_fidelity(error_budget(mapped, backend))


def estimate_success_probability(circuit: QuantumCircuit, backend, **transpile_options) -> float:
    """Estimate the probability that the circuit runs without any error,
    including readout errors."""

    mapped = prepare_circuit(circuit, backend, **transpile_options)
    budget = error_budget(mapped, backend)

    return _gate_fidelity(budget) * budget["readout"]["fidelity"]


@dataclass
class CircuitAnalysis:
    """Result of :func:`analyse_circuit`."""

    circuit_name: str
    backend: str
    num_qubits: int
    physical_qubits: list[int]
    depth: int
    two_qubit_depth: int
    size: int
    gate_counts: dict[str, int]
    num_single_qubit_gates: int
    num_two_qubit_gates: int
    num_measurements: int
    estimated_fidelity: float
    estimated_error: float
    success_probability: float
    reliability_score: float
    reliability: str
    duration_ns: float | None
    error_budget: dict = field(default_factory=dict)

    @property
    def cx_count(self) -> int:
        """Number of two-qubit gates (CX, ECR or CZ, depending on the device)."""

        return self.num_two_qubit_gates

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        duration = "n/a" if self.duration_ns is None else f"{self.duration_ns:.0f} ns"

        lines = [
            f"Circuit              : {self.circuit_name}",
            f"Backend              : {self.backend}",
            f"Physical Qubits      : {self.physical_qubits}",
            f"Depth                : {self.depth}",
            f"Two-Qubit Depth      : {self.two_qubit_depth}",
            f"Gate Counts          : {self.gate_counts}",
            f"Two-Qubit Gate Count : {self.num_two_qubit_gates}",
            f"Estimated Duration   : {duration}",
            f"Estimated Fidelity   : {self.estimated_fidelity:.4f}",
            f"Estimated Error      : {self.estimated_error:.4f}",
            f"Success Probability  : {self.success_probability:.4f}",
            f"Circuit Reliability  : {self.reliability_score:.1f}/100 ({self.reliability})",
        ]

        return "\n".join(lines)


def _estimate_duration_ns(circuit: QuantumCircuit, backend) -> float | None:
    try:
        return float(circuit.estimate_duration(get_target(backend), unit="s")) * 1e9
    except Exception:
        # Durations are unavailable on ideal simulators and for some instructions.
        return None


def analyse_circuit(
    circuit: QuantumCircuit,
    backend,
    transpile_circuit: bool | None = None,
    optimization_level: int = 1,
    seed_transpiler: int | None = None,
) -> CircuitAnalysis:
    """Analyse a circuit against a backend's calibration data.

    The circuit is transpiled for the backend (unless it already is), then
    circuit statistics, estimated fidelity, success probability and a
    0-100 reliability score are computed on the mapped circuit.
    """

    mapped = prepare_circuit(
        circuit,
        backend,
        transpile_circuit=transpile_circuit,
        optimization_level=optimization_level,
        seed_transpiler=seed_transpiler,
    )

    statistics = circuit_statistics(mapped)
    budget = error_budget(mapped, backend)

    fidelity = _gate_fidelity(budget)
    success = fidelity * budget["readout"]["fidelity"]

    physical_qubits = sorted(
        {
            mapped.find_bit(qubit).index
            for instruction in mapped.data
            if instruction.operation.name not in IGNORED_INSTRUCTIONS
            for qubit in instruction.qubits
        }
    )

    return CircuitAnalysis(
        circuit_name=circuit.name,
        backend=backend_name(backend),
        num_qubits=circuit.num_qubits,
        physical_qubits=physical_qubits,
        depth=statistics["depth"],
        two_qubit_depth=statistics["two_qubit_depth"],
        size=statistics["size"],
        gate_counts=statistics["gate_counts"],
        num_single_qubit_gates=statistics["num_single_qubit_gates"],
        num_two_qubit_gates=statistics["num_two_qubit_gates"],
        num_measurements=statistics["num_measurements"],
        estimated_fidelity=fidelity,
        estimated_error=1.0 - fidelity,
        success_probability=success,
        reliability_score=100.0 * success,
        reliability=reliability_label(success),
        duration_ns=_estimate_duration_ns(mapped, backend),
        error_budget=budget,
    )


# American spelling alias.
analyze_circuit = analyse_circuit
