# Contributing to Quantum Noise Toolkit

Thanks for your interest in contributing! Bug fixes, new noise models, analysis techniques,
visualizations, examples and documentation are all welcome.

## Development setup

```bash
git clone https://github.com/shishir-kuet/quantum-noise-toolkit.git
cd quantum-noise-toolkit
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

## Running the tests

```bash
pytest -m "not ibm"   # offline suite, uses Qiskit fake backends
pytest                # everything, including live IBM Quantum tests
```

Tests marked `ibm` need saved IBM Quantum credentials
(`QiskitRuntimeService.save_account(...)`) and are skipped automatically when none are
available. New features should be tested offline with fake backends such as `fake_manila`
(5 qubits) or `fake_fez` (156 qubits).

## Code style

```bash
ruff check src tests examples
black src tests examples
```

Or install the git hooks once and let them run on every commit:

```bash
pip install pre-commit
pre-commit install
```

CI runs ruff, black and the offline test suite (with coverage) on Python 3.11–3.13 for every
pull request.

- Type hints on public functions
- A docstring on every public function and class, stating units where relevant
  (T1/T2 in µs, durations in ns, frequencies in GHz, errors as probabilities)
- Functions take any Qiskit `BackendV2` (or `Target`) and read calibration data from its
  `Target`

## Branching and pull requests

This project follows a Git Flow-inspired workflow:

1. Fork the repository and create a branch from `develop`
   (`feature/<name>`, `fix/<name>`, `docs/<name>`).
2. Make your changes, with tests.
3. Make sure `pytest -m "not ibm"`, `ruff` and `black --check` pass.
4. Open a pull request against `develop`.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add crosstalk analysis
fix: correct readout error averaging
docs: improve installation guide
test: add noise model tests
```

## Adding a noise model

Subclass `qntoolkit.noise_models.NoiseChannel`, implement `to_quantum_error()` and
`_parameters()`, export it from `qntoolkit/noise_models/__init__.py`, and add tests that check
its action on known states (see `tests/test_noise_models.py`).
