"""
Regenerate the figures used in README.md and docs/.

    python scripts/generate_readme_figures.py

Device maps use the offline fake_fez snapshot, so no credentials are needed.
The validation chart reads docs/results/ibm_fez_validation.json, produced by
examples/hardware_validation.py.
"""

import json
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from matplotlib import pyplot as plt

from qntoolkit import load_backend
from qntoolkit.visualization import plot_calibration_dashboard, plot_cx_error_map
from qntoolkit.visualization.style import (
    CATEGORICAL,
    SURFACE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    style_axes,
)

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "docs" / "images"
RESULTS = ROOT / "docs" / "results" / "ibm_fez_validation.json"


def validation_chart(path: Path) -> None:
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    rows = data["results"]

    series = [
        ("estimated", "Toolkit estimate", "o"),
        ("simulated", "Noisy simulation", "s"),
        ("hardware", f"{data['backend']} hardware", "D"),
    ]
    labels = {"bell": "Bell (2 qubits)", "ghz_3": "GHZ-3", "ghz_5": "GHZ-5"}

    fig, ax = plt.subplots(figsize=(7.5, 3.4), layout="constrained")
    fig.set_facecolor(SURFACE)
    style_axes(ax, grid_axis="x")

    names = [labels.get(row["circuit"], row["circuit"]) for row in rows]
    positions = list(range(len(rows)))[::-1]

    for index, (key, label, marker) in enumerate(series):
        offset = (index - 1) * 0.18
        ax.scatter(
            [row[key] for row in rows],
            [position + offset for position in positions],
            s=64,
            marker=marker,
            color=CATEGORICAL[index],
            edgecolors=SURFACE,
            linewidths=1.5,
            label=label,
            zorder=3,
        )

    for row, position in zip(rows, positions, strict=True):
        ax.annotate(
            f"{row['hardware']:.3f}",
            (row["hardware"], position + 0.18),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color=TEXT_SECONDARY,
        )

    ax.set_yticks(positions, names)
    ax.set_xlim(0.9, 1.0)
    ax.set_xlabel("Probability of the ideal outcome (00…0 or 11…1)")
    ax.set_title(
        f"Estimate vs real hardware - {data['backend']}, {data['shots']} shots",
        loc="left",
        fontsize=11,
        color=TEXT_PRIMARY,
    )
    ax.legend(loc="upper left", frameon=False, fontsize=8, labelcolor=TEXT_SECONDARY)

    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        backend = load_backend("fake_fez")

    plt.close(plot_cx_error_map(backend, filename=str(IMAGES / "fez_cz_error_map.png")))
    plt.close(plot_calibration_dashboard(backend, filename=str(IMAGES / "fez_dashboard.png")))
    validation_chart(IMAGES / "hardware_validation.png")

    for path in sorted(IMAGES.glob("*.png")):
        print(f"{path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
