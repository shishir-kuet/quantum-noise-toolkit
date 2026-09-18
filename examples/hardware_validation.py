"""
Validate the toolkit's fidelity estimates against real quantum hardware.

Submits ONE job (Bell, GHZ-3 and GHZ-5 circuits) to an IBM Quantum backend,
then compares, for each circuit:

- the calibration-based success probability from ``analyse_circuit``,
- a noisy Aer simulation using the device noise model,
- the measured probability of the ideal outcomes (all zeros / all ones).

This consumes QPU time on your IBM Quantum account.

Usage:
    python examples/hardware_validation.py                   # submit to ibm_fez
    python examples/hardware_validation.py ibm_torino        # another device
    python examples/hardware_validation.py --job-id <ID>     # fetch an earlier job
    python examples/hardware_validation.py --dry-run         # no submission

With --job-id, estimates use the device's current calibration, which may have
changed since the job ran.
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
SEED = 11


def ghz_circuit(num_qubits: int) -> QuantumCircuit:
    name = "bell" if num_qubits == 2 else f"ghz_{num_qubits}"
    circuit = QuantumCircuit(num_qubits, name=name)
    circuit.h(0)

    for qubit in range(num_qubits - 1):
        circuit.cx(qubit, qubit + 1)

    circuit.measure_all()

    return circuit


def ideal_fraction(counts: dict, num_qubits: int) -> float:
    total = sum(counts.values())
    good = counts.get("0" * num_qubits, 0) + counts.get("1" * num_qubits, 0)
    return good / total


parser = argparse.ArgumentParser()
parser.add_argument("backend", nargs="?", default="ibm_fez")
parser.add_argument("--job-id", help="retrieve the results of an earlier job")
parser.add_argument("--dry-run", action="store_true", help="estimate and simulate only")
args = parser.parse_args()

service = QiskitRuntimeService()

if args.job_id:
    job = service.job(args.job_id)
    backend = job.backend()
else:
    backend = service.backend(args.backend)

circuits = [ghz_circuit(n) for n in (2, 3, 5)]
mapped = transpile(circuits, backend, optimization_level=3, seed_transpiler=SEED)
analyses = [analyse_circuit(circuit, backend) for circuit in mapped]

if args.dry_run:
    simulator = noisy_simulator(backend)

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
print(f"Job {job.job_id()} finished on {backend.name}\n")

simulator = noisy_simulator(backend)
rows = []

for circuit, analysis, pub_result in zip(mapped, analyses, result, strict=True):
    n = len(circuit.clbits)  # logical qubits; the mapped circuit spans the whole device
    hardware_counts = pub_result.data.meas.get_counts()
    simulated_counts = (
        simulator.run(circuit, shots=SHOTS, seed_simulator=SEED).result().get_counts()
    )

    rows.append(
        {
            "circuit": circuit.name,
            "physical_qubits": analysis.physical_qubits,
            "two_qubit_gates": analysis.num_two_qubit_gates,
            "estimated": analysis.success_probability,
            "simulated": ideal_fraction(simulated_counts, n),
            "hardware": ideal_fraction(hardware_counts, n),
            "hellinger_sim_vs_hw": hellinger_fidelity(simulated_counts, hardware_counts),
            "hardware_counts": hardware_counts,
        }
    )

print(f"{'circuit':8} {'qubits':>26} {'2Q':>3} {'estimated':>10} {'simulated':>10} {'hardware':>9}")

for row in rows:
    print(
        f"{row['circuit']:8} {row['physical_qubits']!s:>26} {row['two_qubit_gates']:>3}"
        f" {row['estimated']:>10.3f} {row['simulated']:>10.3f} {row['hardware']:>9.3f}"
    )

output = Path(__file__).parent / "output" / "hardware"
output.mkdir(parents=True, exist_ok=True)
path = output / f"{job.job_id()}.json"
path.write_text(
    json.dumps({"backend": backend.name, "job_id": job.job_id(), "results": rows}, indent=2),
    encoding="utf-8",
)
print(f"\nSaved to {path}")
