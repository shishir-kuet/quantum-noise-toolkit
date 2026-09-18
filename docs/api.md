# API Reference

All functions that take a `backend` accept any Qiskit `BackendV2` (IBM, fake, Aer) or a
`Target`. Units: T1/T2 in µs, durations in ns, frequencies in GHz, errors as probabilities.

---

## `qntoolkit.utils`

| Function | Description |
|---|---|
| `load_backend(name, service=None)` | `"aer_simulator"`, `"fake_<device>"` or an IBM backend name. Creates a `QiskitRuntimeService` from saved credentials if `service` is omitted |
| `get_fake_backend(name)` | Offline fake backend, e.g. `"fake_fez"` |
| `list_fake_backends()` | Names of all fake backends |
| `get_simulator()` | Ideal `AerSimulator` |
| `get_backend(service, name)` | IBM backend; raises `BackendNotFoundError` |
| `list_backends(service)` / `backend_exists(service, name)` | IBM backend discovery |

Exceptions: `QNToolkitError` (base), `BackendNotFoundError`, `ServiceNotInitializedError`,
`BackendConnectionError`, `CalibrationDataError`.

## `qntoolkit.backend`

Name-based helpers taking `(service, backend_name)`: `get_backend_info`, `get_backend_target`,
`get_backend_properties`, `get_backend_configuration`, `get_backend_status`, `get_num_qubits`,
`get_operation_names`, `get_supported_operations`, `get_coupling_map`.

---

## `qntoolkit.characterization`

| Function | Returns |
|---|---|
| `t1_times(backend)` / `t2_times(backend)` | `{qubit: µs}` |
| `qubit_frequencies(backend)` | `{qubit: GHz}` |
| `readout_errors(backend)` / `readout_durations(backend)` | `{qubit: error}` / `{qubit: ns}` |
| `gate_errors(backend, gate=None)` | `{qargs: error}` for one gate, or `{gate: {qargs: error}}` |
| `gate_durations(backend, gate=None)` | Same shape, in ns |
| `gate_names(backend, num_qubits=None)` | Calibrated gate names |
| `single_qubit_gate(backend)` / `two_qubit_gate(backend)` | Reference gates, e.g. `"sx"`, `"cz"` |
| `qubit_properties(backend)` | DataFrame indexed by qubit: `t1_us`, `t2_us`, `frequency_ghz`, `readout_error`, `readout_duration_ns`, `single_qubit_error`, `two_qubit_error` |
| `two_qubit_gate_properties(backend)` | DataFrame: `gate`, `qubit_0`, `qubit_1`, `error`, `duration_ns` |
| `backend_summary(backend)` | `BackendSummary` dataclass (means/medians, faulty counts); `print()`-able |
| `compare_backends(backends)` | DataFrame of summaries indexed by backend name |

---

## `qntoolkit.noise_models`

### Channels

| Class | Parameters |
|---|---|
| `DepolarizingNoise(probability, num_qubits=1)` | Replaces the state by I/d with probability p |
| `BitFlip(probability)` / `PhaseFlip(probability)` | X / Z error with probability p |
| `AmplitudeDamping(gamma, excited_state_population=0)` | Energy relaxation |
| `PhaseDamping(gamma)` | Pure dephasing |
| `ThermalRelaxation(t1, t2, gate_time, excited_state_population=0)` | T1/T2 decay over `gate_time` (same units) |
| `ResetNoise(prob_0, prob_1=0)` | Reset to \|0> or \|1> |
| `CustomNoise(kraus_operators or QuantumError, name="custom")` | User-defined channel |
| `ReadoutNoise(p1_given0, p0_given1=None)` | Classical measurement error |

Every `NoiseChannel` provides:

- `to_quantum_error()` → Aer `QuantumError`
- `kraus_operators()` → list of NumPy arrays
- `apply(state)` → `DensityMatrix`
- `compose(other)` → `ComposedNoise` (apply `self`, then `other`)
- `to_noise_model(gates=None, qubits=None)` / `add_to(noise_model, gates=None, qubits=None)`

### Noise models

| Function | Description |
|---|---|
| `NoiseModelBuilder().add(channel, gates, qubits).add_readout(readout).build()` | Fluent builder |
| `noise_model_from_backend(backend, gate_error=True, readout_error=True, thermal_relaxation=True)` | Realistic model from calibration |
| `noisy_simulator(source=None)` | `AerSimulator` from a `NoiseModel`, channel, or backend (ideal if `None`) |
| `noise_model_summary(noise_model)` | JSON-friendly description |

---

## `qntoolkit.metrics`

| Function | Description |
|---|---|
| `state_fidelity(a, b)` | (Tr √(√ρ σ √ρ))² |
| `process_fidelity(channel, target=None)` | Entanglement fidelity (identity target by default) |
| `gate_fidelity(channel, target=None)` / `gate_error(...)` | Average gate fidelity / 1 − fidelity |
| `purity(state)` | Tr ρ² |
| `trace_distance(a, b)` | ½‖ρ − σ‖₁ |
| `hellinger_fidelity(counts_a, counts_b)` | Between measurement distributions |
| `total_variation_distance(counts_a, counts_b)` | Between measurement distributions |

Channel arguments accept toolkit channels, Aer errors and any `quantum_info` channel.

---

## `qntoolkit.analysis`

### Circuits

| Function | Description |
|---|---|
| `analyse_circuit(circuit, backend, transpile_circuit=None, optimization_level=1, seed_transpiler=None, include_idle=False)` | Returns `CircuitAnalysis` (alias `analyze_circuit`) |
| `estimate_fidelity(circuit, backend, include_idle=False, **options)` | Π(1 − gate error) (× idle factor), excluding measurement |
| `estimate_success_probability(circuit, backend, include_idle=False, **options)` | Including readout errors |
| `error_budget(mapped_circuit, backend, include_idle=False)` | Fidelity factor and count per category (`single_qubit`, `two_qubit`, `multi_qubit`, `idle`, `readout`) |
| `idle_budget(mapped_circuit, backend)` | ALAP-schedules the circuit and charges T1/T2 decay to idle windows |
| `idle_error(duration, t1, t2)` | 1 − (3 + e^(−t/T1) + 2e^(−t/T2)) / 6 |
| `circuit_statistics(circuit)` | Depth, two-qubit depth, gate counts, ... |
| `prepare_circuit(circuit, backend, ...)` | Transpile unless already mapped |

`CircuitAnalysis` fields: `depth`, `two_qubit_depth`, `gate_counts`, `num_two_qubit_gates`
(`cx_count`), `physical_qubits`, `duration_ns`, `estimated_fidelity`, `estimated_error`,
`success_probability`, `reliability_score` (0–100), `reliability`
(`excellent` ≥ 0.9, `good` ≥ 0.7, `fair` ≥ 0.5, else `poor`), `error_budget`.

### Backends

| Function | Description |
|---|---|
| `backend_score(backend)` | 100 × (1 − ē₁q)(1 − ē₂q)(1 − ē_readout) |
| `rank_qubits(backend)` | DataFrame with `rank` and `score` = (1 − readout)(1 − 1Q)(1 − 2Q) |
| `best_qubits(backend, count=5)` / `worst_qubits(...)` | Qubit indices |
| `error_hotspots(backend, threshold=3.5)` | Outlier qubits/couplers by robust z-score |
| `calibration_statistics(backend)` | count/mean/std/min/median/max per metric |
| `average_gate_fidelities(backend)` | `{gate: 1 − mean error}` |
| `rank_backends(backends)` | Summaries ranked by `backend_score` |
| `backend_suitability(circuit, backends)` | Backends ranked by the circuit's success probability |

---

## `qntoolkit.visualization`

All return a Matplotlib `Figure`, accept `ax=` to draw into existing axes and `filename=` to
save.

| Function | Figure |
|---|---|
| `plot_backend_topology(backend, qubit_metric=None, edge_metric=False)` | Device coupling map |
| `plot_qubit_heatmap(backend, metric)` | Qubits colored by any `qubit_properties` column |
| `plot_t1_heatmap`, `plot_t2_heatmap`, `plot_readout_error_map` | Shortcuts |
| `plot_cx_error_map(backend)` | Couplers colored by two-qubit error; faulty couplers dashed red |
| `plot_error_histogram(backend, metric="readout_error")` | Distribution (`"coupler_error"` for 2Q) |
| `plot_gate_errors(backend, gate=None, top=40)` | Worst gate errors |
| `plot_qubit_ranking(backend, top=20)` | Best qubits |
| `plot_calibration_dashboard(backend)` | Six-panel overview |
| `plot_backend_comparison(backends)` | Mean metrics, one panel per metric |
| `plot_interactive_topology(backend, qubit_metric)` | Plotly figure with hover tooltips |

---

## `qntoolkit.reports`

| Function | Description |
|---|---|
| `generate_backend_report(backend, output=None, fmt=None)` | Summary, statistics, hotspots, ranking, calibration tables |
| `generate_circuit_report(circuit, backend, output=None, fmt=None, **options)` | Circuit analysis |
| `generate_noise_summary(noise, output=None, fmt=None)` | `NoiseModel` or list of channels |

The format is inferred from the `output` extension: `.md`, `.html`, `.json`, `.csv`. Each
generator returns a `Report` with `to_markdown()`, `to_html()`, `to_json()`, `to_csv()`,
`to_dict()` and `save(path)`.

---

## Command line (`qntoolkit` or `python -m qntoolkit`)

| Command | Description |
|---|---|
| `qntoolkit backends [--fake]` | List IBM (or offline fake) backends |
| `qntoolkit summary BACKEND [--top N]` | Calibration summary, score, best/worst qubits |
| `qntoolkit hotspots BACKEND [--threshold Z] [--limit N]` | Anomalous qubits and couplers |
| `qntoolkit analyze CIRCUIT.qasm BACKEND [--idle] [--seed S]` | Circuit reliability estimate (OpenQASM 2 or 3) |
| `qntoolkit report BACKEND -o report.html` | Backend report (`.md`, `.html`, `.json`, `.csv`) |
| `qntoolkit dashboard BACKEND -o dashboard.png` | Calibration dashboard image |
