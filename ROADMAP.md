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
| 1.0 | Stable release | 🚧 Planned |

## Toward 1.0

- Continuous integration (GitHub Actions running the offline test suite, ruff and black)
- PyPI package
- Jupyter notebooks (`notebooks/`): noise characterization, backend comparison, readout error,
  visualization
- More algorithm examples: QAOA, VQE, MaxCut, QFT, Grover
- `CITATION.cff` and BibTeX entry
- API stability review and deprecation policy

## Future scope

- Idle-time decoherence in circuit fidelity estimates
- Crosstalk analysis
- Calibration history tracking and drift analysis
- Readout error mitigation helpers built on the characterization data
- Machine-learning-based noise prediction
- Noise-aware qubit recommendation and layout selection
- Multi-provider backend support
- PDF reports
