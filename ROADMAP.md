# Roadmap

Each milestone adds one layer of capability on top of a stable, modular core.

| Version | Milestone | Status |
|---|---|---|
| 0.1 | Foundation: package structure, backend loader, backend information | ✅ Done |
| 0.2 | Noise characterization: T1/T2, readout and gate errors, calibration parser, backend comparison | ✅ Implemented |
| 0.3 | Noise models: depolarizing, amplitude/phase damping, thermal relaxation, readout, custom | ✅ Implemented |
| 0.4 | Circuit analysis: statistics, fidelity estimation, reliability scoring, backend suitability | ✅ Implemented |
| 0.5 | Visualization: topology maps, heatmaps, dashboards, histograms, interactive maps | ✅ Implemented |
| 0.6 | Reporting: backend, circuit and noise reports in Markdown, HTML, JSON and CSV | ✅ Implemented |
| 1.0 | Stable release | 🚧 In progress |

## Toward 1.0

- [x] Continuous integration (ruff, black, tests with coverage on Python 3.11–3.13)
- [x] Command-line interface
- [x] Validation against real hardware (`docs/hardware_validation.md`)
- [x] Quickstart notebook
- [x] `CITATION.cff`
- [ ] PyPI package
- [ ] More notebooks: backend comparison, readout error, noise channels
- [ ] Algorithm examples: QAOA, VQE, MaxCut, QFT, Grover
- [ ] Validation on more devices and deeper circuits
- [ ] API stability review and deprecation policy

## Future scope

- Drift detection: compare calibration snapshots over time and flag qubits that change
- Crosstalk analysis
- Readout error mitigation helpers built on the characterization data
- Noise-aware qubit recommendation and layout selection
- Machine-learning-based noise prediction
- Multi-provider backend support
- PDF reports
