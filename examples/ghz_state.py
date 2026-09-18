"""
GHZ states of growing size: how does noise accumulate?

For n = 2 .. N qubits the script builds a GHZ state, estimates its success
probability from calibration data, and checks the estimate against a noisy
simulation using the device noise model.

Usage:
    python examples/ghz_state.py                  # offline, fake_brisbane
    python examples/ghz_state.py ibm_fez 10       # real calibration, up to 10 qubits
"""

import sys

from qiskit import QuantumCircuit, transpile

from qntoolkit import load_backend
from qntoolkit.analysis import analyse_circuit, best_qubits
from qntoolkit.noise_models import noisy_simulator

SHOTS = 10_000
SEED = 7

backend_name = sys.argv[1] if len(sys.argv) > 1 else "fake_brisbane"
max_qubits = int(sys.argv[2]) if len(sys.argv) > 2 else 8

backend = load_backend(backend_name)
simulator = noisy_simulator(backend)


def ghz_circuit(num_qubits: int) -> QuantumCircuit:
    circuit = QuantumCircuit(num_qubits, name=f"ghz_{num_qubits}")
    circuit.h(0)

    for qubit in range(num_qubits - 1):
        circuit.cx(qubit, qubit + 1)

    circuit.measure_all()

    return circuit


print(f"Backend: {backend.name}   (best qubits: {best_qubits(backend, 5)})")
print()
print(" n   depth  2Q gates  estimated  simulated  reliability")

for num_qubits in range(2, max_qubits + 1):
    mapped = transpile(ghz_circuit(num_qubits), backend, optimization_level=3, seed_transpiler=SEED)
    analysis = analyse_circuit(mapped, backend)

    counts = simulator.run(mapped, shots=SHOTS, seed_simulator=SEED).result().get_counts()
    simulated = (counts.get("0" * num_qubits, 0) + counts.get("1" * num_qubits, 0)) / SHOTS

    print(
        f"{num_qubits:2d}   {analysis.depth:5d}  {analysis.num_two_qubit_gates:8d}"
        f"  {analysis.success_probability:9.3f}  {simulated:9.3f}  {analysis.reliability}"
    )

print()
print(
    "'estimated' is the calibration-based success probability; 'simulated' is the\n"
    "fraction of shots landing in |0...0> or |1...1> under the device noise model.\n"
    "The estimate ignores idle decoherence, so it is typically a little optimistic."
)
