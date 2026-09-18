# Architecture

Quantum Noise Toolkit is a set of small, independent modules layered on top of Qiskit. Every
module that needs hardware data reads it from a backend's **`Target`**, so the same code works
for real IBM backends, offline fake backends and the Aer simulator.

## Module layers

```
                 ┌──────────────┐
                 │   reports    │  Markdown / HTML / JSON / CSV
                 └──────┬───────┘
          ┌─────────────┼──────────────┐
   ┌──────┴──────┐ ┌────┴─────┐ ┌──────┴───────┐
   │visualization│ │ analysis │ │   metrics    │
   └──────┬──────┘ └────┬─────┘ └──────┬───────┘
          └──────┬──────┘              │
        ┌────────┴─────────┐   ┌───────┴──────┐
        │ characterization │   │ noise_models │
        └────────┬─────────┘   └───────┬──────┘
                 └──────────┬──────────┘
                      ┌─────┴─────┐
                      │   utils   │  backend loading, exceptions
                      └─────┬─────┘
                            │
             Qiskit · Qiskit Aer · Qiskit IBM Runtime
```

Dependencies point downward only; a lower layer never imports a higher one.

| Module | Responsibility |
|---|---|
| `utils` | Load backends by name (`load_backend`), fake backends, custom exceptions |
| `backend` | Name-based access to IBM backend information (service + backend name) |
| `characterization` | Extract T1, T2, frequencies, gate/readout errors and durations from a `Target` |
| `noise_models` | Noise channels, channel composition and Aer `NoiseModel` construction |
| `metrics` | Fidelities and distances between states, channels and count distributions |
| `analysis` | Circuit fidelity estimation, backend scoring, qubit ranking, hotspot detection |
| `visualization` | Matplotlib figures and Plotly interactive maps |
| `reports` | A format-independent `Report` model rendered to Markdown, HTML, JSON or CSV |

## Design decisions

**Target-based.** `BackendV2.target` is the modern, provider-independent source of
calibration data. Functions accept either a backend or a bare `Target`.

**Consistent units.** T1/T2 in microseconds, durations in nanoseconds, frequencies in GHz,
errors as probabilities. Units are part of every column name (`t1_us`, `duration_ns`).

**Tables as DataFrames.** Per-qubit and per-coupler data are returned as pandas DataFrames,
so they can be filtered, joined, plotted and exported directly.

**Faulty hardware is explicit.** IBM reports an error of `1.0` for disabled qubits and
couplers. These are counted separately (`num_faulty_qubits`, `num_faulty_couplers`) and
excluded from averages, so a single dead coupler does not distort a device's statistics. They
still appear in hotspot detection and on error maps (dashed red).

**Robust outlier detection.** Error hotspots use the modified z-score based on the median
absolute deviation, which the outliers being searched for cannot inflate.

**Deterministic layouts without Graphviz.** Device maps are laid out by classical MDS on
graph distances refined with stress majorization, which reproduces heavy-hex and square
lattices cleanly with only NumPy and rustworkx.

**Channels wrap Aer.** Every `NoiseChannel` converts to an Aer `QuantumError`, so the
toolkit's channels plug straight into Aer simulations and Qiskit's `quantum_info`.

## Extending the toolkit

- **New noise channel:** subclass `NoiseChannel` and implement `to_quantum_error()`.
- **New per-qubit metric:** add a column in `characterization.qubit_properties()`; it becomes
  available to `plot_qubit_heatmap(backend, "<column>")`, histograms and reports.
- **New report:** build a `Report`, add sections (facts and/or DataFrames) and call `save()`.
