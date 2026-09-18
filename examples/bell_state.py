"""
Bell state under noise.

1. Prepares |Phi+> = (|00> + |11>) / sqrt(2).
2. Simulates it ideally and with the noise model of a real device.
3. Compares the toolkit's calibration-based estimate with the simulation.
4. Shows how the state fidelity decays under increasing depolarizing noise.

Usage:
    python examples/bell_state.py                 # offline, fake_manila
    python examples/bell_state.py ibm_fez         # real IBM calibration data
"""

import sys

from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import DensityMatrix, Statevector

from qntoolkit import load_backend
from qntoolkit.analysis import analyse_circuit
from qntoolkit.metrics import hellinger_fidelity, purity, state_fidelity, total_variation_distance
from qntoolkit.noise_models import DepolarizingNoise, noisy_simulator

SHOTS = 20_000
SEED = 1234

backend_name = sys.argv[1] if len(sys.argv) > 1 else "fake_manila"
backend = load_backend(backend_name)

bell = QuantumCircuit(2, name="bell")
bell.h(0)
bell.cx(0, 1)

measured = bell.measure_all(inplace=False)

# ----------------------------------------------------------------------
# Ideal vs noisy simulation
# ----------------------------------------------------------------------

ideal_simulator = noisy_simulator()
ideal_counts = (
    ideal_simulator.run(transpile(measured, ideal_simulator), shots=SHOTS, seed_simulator=SEED)
    .result()
    .get_counts()
)

device_simulator = noisy_simulator(backend)
mapped = transpile(measured, backend, optimization_level=3, seed_transpiler=SEED)
noisy_counts = device_simulator.run(mapped, shots=SHOTS, seed_simulator=SEED).result().get_counts()

print(f"Backend: {backend.name}")
print(f"Ideal counts : {dict(sorted(ideal_counts.items()))}")
print(f"Noisy counts : {dict(sorted(noisy_counts.items()))}")
print(f"Hellinger fidelity       : {hellinger_fidelity(ideal_counts, noisy_counts):.4f}")
print(f"Total variation distance : {total_variation_distance(ideal_counts, noisy_counts):.4f}")

# Fraction of shots in the correct outcomes 00 / 11.
simulated_success = (noisy_counts.get("00", 0) + noisy_counts.get("11", 0)) / SHOTS

analysis = analyse_circuit(mapped, backend)
print()
print(analysis)
print()
print(f"Simulated P(00 or 11)    : {simulated_success:.4f}")
print(f"Estimated success prob.  : {analysis.success_probability:.4f}")

# ----------------------------------------------------------------------
# Depolarizing noise sweep on the Bell state
# ----------------------------------------------------------------------

ideal_state = Statevector(bell)

print()
print(" p     fidelity   purity")

for probability in (0.0, 0.05, 0.1, 0.2, 0.4, 0.8):
    noisy_state = DensityMatrix(ideal_state).evolve(
        DepolarizingNoise(probability, num_qubits=2).to_quantum_error().to_quantumchannel()
    )
    print(
        f"{probability:4.2f}   {state_fidelity(ideal_state, noisy_state):.4f}"
        f"     {purity(noisy_state):.4f}"
    )
