"""
Validate the toolkit's fidelity estimates against real quantum hardware.

Submits ONE job (Bell, GHZ-3 and GHZ-5 circuits) to an IBM Quantum backend,
then compares, for each circuit:

- the calibration-based success probability from ``analyse_circuit``
  (with and without idle-qubit decoherence),
- a noisy Aer simulation using the device noise model,
- the measured probability of the ideal outcomes (all zeros / all ones).

For circuits with 3+ qubits it also diagnoses each measured qubit: how often
it alone flipped away from the ideal outcome on hardware, compared with the
same rate in the calibrated noisy simulation. A qubit that fails far more often
than its calibration predicts points to drift, such as a T1 fluctuation.

This consumes QPU time on your IBM Quantum account (about 6 seconds).

Usage:
    python examples/hardware_validation.py                   # submit to ibm_fez
    python examples/hardware_validation.py ibm_torino        # another device
    python examples/hardware_validation.py --job-id <ID>     # re-analyse an earlier job
    python examples/hardware_validation.py --dry-run         # no submission

With --job-id the exact circuits of the job are re-analysed, but with the
device's current calibration, which may have changed since the job ran.
"""

import argparse
import json
from pathlib import Path

from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

from qntoolkit.analysis import analyse_circuit
from qntoolkit.metrics import hellinger_fidelity
from qntoolkit.noise_models import noisy_simulator

SHOTS = 4000
SIMULATION_SHOTS = 50_000
SEED = 11


def ghz_circuit(num_qubits: int) -> QuantumCircuit:
    name = "bell" if num_qubits == 2 else f"ghz_{num_qubits}"
    circuit = QuantumCircuit(num_qubits, name=name)
    circuit.h(0)

    for qubit in range(num_qubits - 1):
        circuit.cx(qubit, qubit + 1)

    circuit.measure_all()

    return circuit


def ideal_fraction(counts: dict, num_bits: int) -> float:
    total = sum(counts.values())
    good = counts.get("0" * num_bits, 0) + counts.get("1" * num_bits, 0)
    return good / total


def measured_qubits(circuit: QuantumCircuit) -> dict[int, int]:
    """Map each classical bit to the physical qubit measured into it."""

    mapping = {}

    for instruction in circuit.data:
        if instruction.operation.name == "measure":
            clbit = circuit.find_bit(instruction.clbits[0]).index
            mapping[clbit] = circuit.find_bit(instruction.qubits[0]).index

    return mapping


def single_flip_rate(counts: dict, num_bits: int, clbit: int) -> float:
    """Fraction of shots where only ``clbit`` deviates from 00..0 or 11..1."""

    total = sum(counts.values())
    position = num_bits - 1 - clbit  # bitstrings are little-endian

    flipped = 0
    for ideal in ("0" * num_bits, "1" * num_bits):
        other = "1" if ideal[0] == "0" else "0"
        flipped += counts.get(ideal[:position] + other + ideal[position + 1 :], 0)

    return flipped / total


parser = argparse.ArgumentParser()
parser.add_argument("backend", nargs="?", default="ibm_fez")
parser.add_argument("--job-id", help="re-analyse an earlier job")
parser.add_argument("--dry-run", action="store_true", help="estimate and simulate only")
args = parser.parse_args()

service = QiskitRuntimeService()

if args.job_id:
    job = service.job(args.job_id)
    backend = job.backend()
    mapped = [pub[0] for pub in job.inputs["pubs"]]
else:
    backend = service.backend(args.backend)
    circuits = [ghz_circuit(n) for n in (2, 3, 5)]
    mapped = transpile(circuits, backend, optimization_level=3, seed_transpiler=SEED)

analyses = [analyse_circuit(circuit, backend) for circuit in mapped]
idle_analyses = [analyse_circuit(circuit, backend, include_idle=True) for circuit in mapped]
simulator = noisy_simulator(backend)

if args.dry_run:
    for circuit, analysis in zip(mapped, analyses, strict=True):
        counts = simulator.run(circuit, shots=SHOTS, seed_simulator=SEED).result().get_counts()
        print(
            f"{circuit.name:8} qubits={analysis.physical_qubits} "
            f"estimated={analysis.success_probability:.3f} "
            f"simulated={ideal_fraction(counts, len(circuit.clbits)):.3f}"
        )

    raise SystemExit(0)

if not args.job_id:
    job = SamplerV2(mode=backend).run(mapped, shots=SHOTS)
    print(f"Submitted job {job.job_id()} to {backend.name}; waiting for results...")

result = job.result()
print(f"Job {job.job_id()} on {backend.name}\n")

rows = []

for circuit, analysis, idle_analysis, pub_result in zip(
    mapped, analyses, idle_analyses, result, strict=True
):
    num_bits = len(circuit.clbits)  # the mapped circuit spans the whole device
    hardware_counts = pub_result.data.meas.get_counts()
    simulated_counts = (
        simulator.run(circuit, shots=SIMULATION_SHOTS, seed_simulator=SEED).result().get_counts()
    )

    # With 2 qubits a single flip (01 / 10) cannot be attributed to one qubit.
    diagnosis = [
        {
            "clbit": clbit,
            "qubit": qubit,
            "hardware_flip_rate": single_flip_rate(hardware_counts, num_bits, clbit),
            "simulated_flip_rate": single_flip_rate(simulated_counts, num_bits, clbit),
        }
        for clbit, qubit in sorted(measured_qubits(circuit).items())
        if num_bits >= 3
    ]

    rows.append(
        {
            "circuit": circuit.name,
            "physical_qubits": analysis.physical_qubits,
            "two_qubit_gates": analysis.num_two_qubit_gates,
            "estimated": analysis.success_probability,
            "estimated_with_idle": idle_analysis.success_probability,
            "simulated": ideal_fraction(simulated_counts, num_bits),
            "hardware": ideal_fraction(hardware_counts, num_bits),
            "hellinger_sim_vs_hw": hellinger_fidelity(simulated_counts, hardware_counts),
            "diagnosis": diagnosis,
            "hardware_counts": hardware_counts,
        }
    )

print(
    f"{'circuit':8} {'physical qubits':>26} {'2Q':>3} {'estimate':>9} {'+idle':>7}"
    f" {'simulated':>10} {'hardware':>9}"
)

for row in rows:
    print(
        f"{row['circuit']:8} {row['physical_qubits']!s:>26} {row['two_qubit_gates']:>3}"
        f" {row['estimated']:>9.3f} {row['estimated_with_idle']:>7.3f}"
        f" {row['simulated']:>10.3f} {row['hardware']:>9.3f}"
    )

print("\nPer-qubit diagnosis: share of shots where only this qubit was wrong")

for row in [row for row in rows if row["diagnosis"]]:
    print(f"  {row['circuit']}")

    for item in row["diagnosis"]:
        hardware_rate = item["hardware_flip_rate"]
        simulated_rate = item["simulated_flip_rate"]
        worse = hardware_rate > 1.5 * simulated_rate and hardware_rate - simulated_rate > 0.005
        flag = "  <-- worse than calibration predicts" if worse else ""
        print(
            f"    Q{item['qubit']:<4} hardware {hardware_rate:.4f}"
            f"   calibrated simulation {simulated_rate:.4f}{flag}"
        )

output = Path(__file__).parent / "output" / "hardware"
output.mkdir(parents=True, exist_ok=True)
path = output / f"{job.job_id()}.json"
path.write_text(
    json.dumps(
        {
            "backend": backend.name,
            "job_id": job.job_id(),
            "shots": SHOTS,
            "ran_at": str(job.metrics().get("timestamps", {}).get("running")),
            "results": rows,
        },
        indent=2,
    ),
    encoding="utf-8",
)
print(f"\nSaved to {path}")
