"""
Complete backend analysis workflow:

    Connect backend -> extract calibration -> analyse -> visualize -> report

Usage:
    python examples/backend_analysis.py                 # offline, fake_fez
    python examples/backend_analysis.py ibm_fez         # live IBM Quantum data

Figures and reports are written to examples/output/<backend>/.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from qntoolkit import load_backend
from qntoolkit.analysis import (
    backend_score,
    best_qubits,
    error_hotspots,
    worst_qubits,
)
from qntoolkit.characterization import backend_summary
from qntoolkit.reports import generate_backend_report
from qntoolkit.visualization import (
    plot_calibration_dashboard,
    plot_cx_error_map,
    plot_error_histogram,
    plot_gate_errors,
    plot_interactive_topology,
    plot_qubit_ranking,
    plot_readout_error_map,
    plot_t1_heatmap,
    plot_t2_heatmap,
)

backend_name = sys.argv[1] if len(sys.argv) > 1 else "fake_fez"
backend = load_backend(backend_name)

output = Path(__file__).parent / "output" / backend.name
output.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------
# Calibration summary and analysis
# ----------------------------------------------------------------------

print(backend_summary(backend))
print(f"Backend Score         : {backend_score(backend):.1f}/100")
print()
print(f"Best qubits  : {best_qubits(backend, 10)}")
print(f"Worst qubits : {worst_qubits(backend, 10)}")
print()

hotspots = error_hotspots(backend)
print(f"Error hotspots ({len(hotspots)}):")
print(hotspots.head(15).to_string(index=False) if not hotspots.empty else "none")
print()

# ----------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------

figures = {
    "t1_map.png": plot_t1_heatmap,
    "t2_map.png": plot_t2_heatmap,
    "readout_error_map.png": plot_readout_error_map,
    "two_qubit_error_map.png": plot_cx_error_map,
    "readout_error_histogram.png": plot_error_histogram,
    "gate_errors.png": plot_gate_errors,
    "qubit_ranking.png": plot_qubit_ranking,
    "dashboard.png": plot_calibration_dashboard,
}

for filename, plot in figures.items():
    plot(backend, filename=str(output / filename))

plot_interactive_topology(backend, "readout_error").write_html(output / "interactive_map.html")

# ----------------------------------------------------------------------
# Reports
# ----------------------------------------------------------------------

for extension in ("md", "html", "json", "csv"):
    generate_backend_report(backend, output=output / f"backend_report.{extension}")

print(f"Figures and reports written to {output}")
