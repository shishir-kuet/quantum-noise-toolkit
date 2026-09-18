"""
Quantum Noise Toolkit - characterize, simulate, analyze and visualize
quantum noise on NISQ devices.

Subpackages:

- :mod:`qntoolkit.utils` - backend loading and exceptions
- :mod:`qntoolkit.backend` - IBM backend information by name
- :mod:`qntoolkit.characterization` - calibration data extraction
- :mod:`qntoolkit.noise_models` - noise channels and Aer noise models
- :mod:`qntoolkit.metrics` - fidelities and distances
- :mod:`qntoolkit.analysis` - circuit and backend analysis
- :mod:`qntoolkit.visualization` - figures and interactive maps
- :mod:`qntoolkit.reports` - Markdown / HTML / JSON / CSV reports
"""

__version__ = "0.1.0"

from qntoolkit.utils import load_backend

__all__ = ["__version__", "load_backend"]
