"""
Shared colors and axis styling for all toolkit figures.

Colors follow one rule per job: magnitudes use a single-hue sequential
ramp (light = low, dark = high), series identity uses a fixed categorical
order, and the "critical" status color is reserved for faulty hardware.
"""

from __future__ import annotations

from matplotlib.axes import Axes
from matplotlib.colors import LinearSegmentedColormap

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
EDGE_NEUTRAL = "#b9b8b2"
MISSING = "#d9d8d3"

CRITICAL = "#d03b3b"

# Fixed categorical order - assigned in sequence, never cycled.
CATEGORICAL = (
    "#2a78d6",
    "#eb6834",
    "#1baf7a",
    "#eda100",
    "#e87ba4",
    "#008300",
    "#4a3aa7",
    "#e34948",
)

SEQUENTIAL_BLUE = (
    "#cde2fb",
    "#b7d3f6",
    "#9ec5f4",
    "#86b6ef",
    "#6da7ec",
    "#5598e7",
    "#3987e5",
    "#2a78d6",
    "#256abf",
    "#1c5cab",
    "#184f95",
    "#104281",
    "#0d366b",
)

SEQUENTIAL_CMAP = LinearSegmentedColormap.from_list("qnt_blue", SEQUENTIAL_BLUE)

METRIC_LABELS = {
    "t1_us": "T1 (µs)",
    "t2_us": "T2 (µs)",
    "frequency_ghz": "Frequency (GHz)",
    "readout_error": "Readout error",
    "readout_duration_ns": "Readout duration (ns)",
    "single_qubit_error": "Single-qubit gate error",
    "two_qubit_error": "Two-qubit gate error",
    "score": "Qubit score",
}


def metric_label(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric.replace("_", " ").capitalize())


def categorical_color(index: int) -> str:
    if index >= len(CATEGORICAL):
        raise ValueError(
            f"Only {len(CATEGORICAL)} categorical colors are available; "
            "group extra series or use small multiples."
        )

    return CATEGORICAL[index]


def style_axes(ax: Axes, grid_axis: str | None = "y") -> Axes:
    """Apply recessive axes: no top/right spines, light grid, muted ticks."""

    ax.set_facecolor(SURFACE)

    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    for side in ("left", "bottom"):
        ax.spines[side].set_color(EDGE_NEUTRAL)

    ax.tick_params(colors=TEXT_SECONDARY, labelsize=9)
    ax.xaxis.label.set_color(TEXT_SECONDARY)
    ax.yaxis.label.set_color(TEXT_SECONDARY)
    ax.title.set_color(TEXT_PRIMARY)

    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)

    return ax


def hide_axes(ax: Axes) -> Axes:
    ax.set_facecolor(SURFACE)
    ax.set_xticks([])
    ax.set_yticks([])

    for spine in ax.spines.values():
        spine.set_visible(False)

    return ax
