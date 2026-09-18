## [Unreleased]

### Added

- `load_backend()` loads IBM backends, offline fake backends (`fake_*`) or the Aer simulator by name
- `get_fake_backend()` and `list_fake_backends()` for offline work without credentials
- **Characterization**: T1/T2, qubit frequencies, readout errors and durations, gate errors and
  durations, per-qubit calibration table, coupler table, `backend_summary()`, `compare_backends()`
- **Noise models**: `DepolarizingNoise`, `BitFlip`, `PhaseFlip`, `AmplitudeDamping`,
  `PhaseDamping`, `ThermalRelaxation`, `ResetNoise`, `ReadoutNoise`, `CustomNoise`, channel
  composition, `NoiseModelBuilder`, `noise_model_from_backend()`, `noisy_simulator()`
- **Metrics**: state, process and average gate fidelity, purity, trace distance, Hellinger
  fidelity, total variation distance
- **Circuit analysis**: circuit statistics, estimated fidelity, success probability, error budget,
  reliability score (`analyse_circuit()`)
- **Backend analysis**: backend score, qubit ranking, best/worst qubits, error hotspot detection,
  calibration statistics, average gate fidelities, backend ranking and circuit suitability
- **Visualization**: device maps for T1, T2, readout and two-qubit errors, error histograms,
  gate error bars, qubit ranking, calibration dashboard, backend comparison, interactive Plotly map
- **Reports**: backend, circuit and noise reports in Markdown, HTML, JSON and CSV
- Idle-decoherence-aware estimates: `include_idle=True`, `idle_budget()`, `idle_error()`
- `qntoolkit` command-line interface (`backends`, `summary`, `hotspots`, `analyze`, `report`,
  `dashboard`), also available as `python -m qntoolkit`
- Examples: `bell_state.py`, `ghz_state.py`, `backend_analysis.py`, and `hardware_validation.py`
  (runs Bell/GHZ circuits on real IBM hardware, compares with estimates and simulation, and
  diagnoses per-qubit deviations)
- Hardware validation on `ibm_fez` with results in `docs/hardware_validation.md`
- Executed quickstart notebook (`notebooks/quickstart.ipynb`)
- GitHub Actions CI (ruff, black, tests with coverage on Python 3.11–3.13), pre-commit hooks,
  `CITATION.cff`, `py.typed`
- Offline test suite on fake backends; IBM tests marked `ibm` and skipped without credentials
- Documentation: installation, architecture, API reference, tutorials, theory

### Changed

- Disabled qubits and couplers (reported error 1.0) are counted separately and excluded from
  average error statistics

### Removed

- `qntoolkit.utils.backend_info`, an unused duplicate of `qntoolkit.backend`

## [0.1.0] - 2026-07-27

### Added

- Aer simulator loader
- IBM backend loader
- Backend existence checking
- Backend discovery
- Backend information API
- Backend configuration access
- Backend properties access
- Backend target access
- Coupling map retrieval
- Backend status retrieval
- Unit tests
