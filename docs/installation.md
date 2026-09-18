# Installation

## Requirements

- Python 3.11 or newer
- pip 23 or newer
- Git

The toolkit builds on Qiskit, Qiskit Aer and Qiskit IBM Runtime. All dependencies are listed in
`pyproject.toml` and installed automatically.

## Install from source

```bash
git clone https://github.com/shishir-kuet/quantum-noise-toolkit.git
cd quantum-noise-toolkit

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

For development tools (pytest, ruff, black):

```bash
pip install -e ".[dev]"
```

## Verify the installation

```bash
python -c "from qntoolkit import load_backend; from qntoolkit.characterization import backend_summary; print(backend_summary(load_backend('fake_manila')))"
```

This uses an offline fake backend and needs no account.

## IBM Quantum access (optional)

Everything in the toolkit works offline with Qiskit's fake backends (`fake_manila`, `fake_fez`,
`fake_brisbane`, ...). To analyse live calibration data from real devices, save your IBM Quantum
credentials once:

```python
from qiskit_ibm_runtime import QiskitRuntimeService

QiskitRuntimeService.save_account(
    channel="ibm_quantum_platform",
    token="<your API key>",
    instance="<your instance CRN>",
    set_as_default=True,
)
```

Afterwards `load_backend("ibm_fez")` connects automatically.

## Running the tests

```bash
pytest -m "not ibm"   # offline tests only
pytest                # includes live IBM Quantum tests (skipped without credentials)
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `ServiceNotInitializedError` | Save IBM Quantum credentials (see above), or use a `fake_*` backend |
| `BackendNotFoundError` for a fake backend | Run `qntoolkit.utils.list_fake_backends()` for valid names |
| Figures do not appear when running a script | Call `matplotlib.pyplot.show()` or pass `filename=` to save them |
