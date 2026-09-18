# Tutorials

All tutorials run offline with fake backends. Replace `"fake_fez"` with a real device name such
as `"ibm_fez"` to use live calibration data.

---

## 1. Characterize a backend

```python
from qntoolkit import load_backend
from qntoolkit.characterization import backend_summary, qubit_properties

backend = load_backend("fake_fez")

print(backend_summary(backend))

table = qubit_properties(backend)
print(table.sort_values("readout_error").head())   # qubits with the best readout
```

---

## 2. Find the best and worst hardware

```python
from qntoolkit.analysis import best_qubits, error_hotspots, rank_qubits, worst_qubits

print(best_qubits(backend, 10))
print(worst_qubits(backend, 10))
print(error_hotspots(backend))      # dead couplers, outlier readout errors, low T1/T2
```

Use the best qubits as an initial layout:

```python
from qiskit import transpile

mapped = transpile(circuit, backend, initial_layout=best_qubits(backend, circuit.num_qubits))
```

---

## 3. Estimate circuit reliability before running it

```python
from qiskit import QuantumCircuit
from qntoolkit.analysis import analyse_circuit

qc = QuantumCircuit(3, name="ghz")
qc.h(0)
qc.cx(0, 1)
qc.cx(1, 2)
qc.measure_all()

report = analyse_circuit(qc, backend, seed_transpiler=1)
print(report)
print(report.error_budget)
```

The estimate multiplies (1 − error) over every gate and measurement on the physical qubits
chosen by the transpiler. `examples/ghz_state.py` shows that it tracks noisy simulations to
within about 1% for GHZ states.

Pick the best device for a circuit:

```python
from qntoolkit.analysis import backend_suitability

backends = [load_backend(name) for name in ("fake_fez", "fake_brisbane", "fake_torino")]
print(backend_suitability(qc, backends))
```

---

## 4. Build and study noise channels

```python
import numpy as np
from qntoolkit.metrics import gate_fidelity, purity
from qntoolkit.noise_models import AmplitudeDamping, PhaseDamping, ThermalRelaxation

one = np.array([0, 1])

print(AmplitudeDamping(0.3).apply(one).probabilities())   # [0.3, 0.7]

decay = AmplitudeDamping(0.1).compose(PhaseDamping(0.2))
print(gate_fidelity(decay), len(decay.kraus_operators()))

# T1 = 100 us, T2 = 80 us, 1 us gate
print(gate_fidelity(ThermalRelaxation(t1=100, t2=80, gate_time=1)))
```

---

## 5. Simulate with noise

```python
from qiskit import transpile
from qntoolkit.noise_models import (
    DepolarizingNoise, NoiseModelBuilder, ReadoutNoise, noisy_simulator,
)

model = (
    NoiseModelBuilder()
    .add(DepolarizingNoise(0.001), gates=["h", "x", "sx"])
    .add(DepolarizingNoise(0.01, num_qubits=2), gates=["cx"])
    .add_readout(ReadoutNoise(0.02, 0.03))
    .build()
)

sim = noisy_simulator(model)
counts = sim.run(transpile(qc, sim), shots=10_000).result().get_counts()

device_sim = noisy_simulator(backend)          # mimic a real device
```

Compare noisy and ideal results:

```python
from qntoolkit.metrics import hellinger_fidelity, total_variation_distance

ideal = noisy_simulator().run(transpile(qc, noisy_simulator()), shots=10_000).result().get_counts()
print(hellinger_fidelity(ideal, counts), total_variation_distance(ideal, counts))
```

---

## 6. Visualize

```python
import matplotlib.pyplot as plt
from qntoolkit.visualization import (
    plot_calibration_dashboard, plot_cx_error_map, plot_interactive_topology, plot_t1_heatmap,
)

plot_t1_heatmap(backend)
plot_cx_error_map(backend, filename="cz_errors.png")
plot_calibration_dashboard(backend, filename="dashboard.png")
plt.show()

plot_interactive_topology(backend, "readout_error").write_html("map.html")
```

---

## 7. Generate reports

```python
from qntoolkit.reports import generate_backend_report, generate_circuit_report

generate_backend_report(backend, output="fez_report.md")
generate_backend_report(backend, output="fez_report.html")
generate_circuit_report(qc, backend, output="ghz_report.json")
```

---

## Example scripts

| Script | What it shows |
|---|---|
| `examples/bell_state.py` | Ideal vs noisy Bell state, estimate vs simulation, depolarizing sweep |
| `examples/ghz_state.py` | Noise accumulation in GHZ states of growing size |
| `examples/backend_analysis.py` | Full workflow: calibration → analysis → figures → reports |

Each script takes an optional backend name, e.g. `python examples/backend_analysis.py ibm_fez`.
