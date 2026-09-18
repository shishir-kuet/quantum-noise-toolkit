"""
Publication-quality figures of backend calibration data.

Every function returns a Matplotlib ``Figure``, draws into ``ax`` when one is
given, and saves the figure when ``filename`` is given.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.cm import ScalarMappable
from matplotlib.collections import LineCollection
from matplotlib.colors import LogNorm, Normalize
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from qntoolkit.analysis.backend import rank_qubits
from qntoolkit.characterization.calibration import (
    FAULTY_ERROR_THRESHOLD,
    backend_name,
    compare_backends,
    gate_errors,
    qubit_properties,
    two_qubit_gate,
    two_qubit_gate_properties,
)
from qntoolkit.utils.exceptions import CalibrationDataError

from .layout import coupling_edges, topology_layout
from .style import (
    CRITICAL,
    EDGE_NEUTRAL,
    MISSING,
    SEQUENTIAL_BLUE,
    SEQUENTIAL_CMAP,
    SURFACE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    categorical_color,
    hide_axes,
    metric_label,
    style_axes,
)

PRIMARY_BAR = SEQUENTIAL_BLUE[7]


def _figure(ax: Axes | None, figsize: tuple[float, float]) -> tuple[Figure, Axes]:
    if ax is not None:
        return ax.figure, ax

    fig, ax = plt.subplots(figsize=figsize, layout="constrained")
    fig.set_facecolor(SURFACE)

    return fig, ax


def _finish(fig: Figure, filename: str | None) -> Figure:
    if filename:
        fig.savefig(filename, dpi=200, facecolor=fig.get_facecolor())

    return fig


def _norm(values: np.ndarray, log: bool) -> Normalize:
    finite = values[np.isfinite(values)]

    if finite.size == 0:
        return Normalize(0.0, 1.0)

    low, high = float(finite.min()), float(finite.max())

    if log and low > 0:
        return LogNorm(low, high if high > low else low * 10)

    return Normalize(low, high if high > low else low + 1.0)


def _colorbar(fig: Figure, ax: Axes, norm: Normalize, label: str) -> None:
    mappable = ScalarMappable(norm=norm, cmap=SEQUENTIAL_CMAP)
    colorbar = fig.colorbar(mappable, ax=ax, shrink=0.7, pad=0.01)
    colorbar.set_label(label, color=TEXT_SECONDARY)
    colorbar.outline.set_visible(False)
    colorbar.ax.tick_params(which="both", colors=TEXT_SECONDARY, labelsize=8)


def _topology_figsize(positions: np.ndarray) -> tuple[float, float]:
    if len(positions) < 2:
        return (4.0, 3.0)

    width = max(float(np.ptp(positions[:, 0])), 1.0)
    height = max(float(np.ptp(positions[:, 1])), 1.0)
    scale = min(12.0 / width, 8.0 / height, 1.2)

    return (max(width * scale + 2.0, 5.0), max(height * scale + 1.5, 3.0))


def _edge_label(backend) -> str:
    return f"{(two_qubit_gate(backend) or 'two-qubit').upper()} error"


def plot_backend_topology(
    backend,
    qubit_metric: str | None = None,
    edge_metric: bool = False,
    label_qubits: bool | None = None,
    log_scale: bool | None = None,
    ax: Axes | None = None,
    filename: str | None = None,
) -> Figure:
    """Draw the coupling map, optionally colored by calibration data.

    Parameters
    ----------
    qubit_metric:
        Column of :func:`~qntoolkit.characterization.qubit_properties`
        used to color qubits (e.g. ``"t1_us"``, ``"readout_error"``).
    edge_metric:
        Color couplers by native two-qubit gate error. Faulty couplers
        (error 1.0) are drawn dashed in the critical color.
    log_scale:
        Use a logarithmic color scale; defaults to ``True`` for errors.
    """

    positions = topology_layout(backend)
    edges = coupling_edges(backend)
    num_qubits = len(positions)

    if num_qubits == 0:
        raise CalibrationDataError("Backend has no qubits to draw.")

    if not edges and num_qubits > 1:
        raise CalibrationDataError(
            f"Backend '{backend_name(backend)}' has no coupling map (all-to-all "
            "simulators cannot be drawn as a topology)."
        )

    fig, ax = _figure(ax, _topology_figsize(positions))
    hide_axes(ax)

    if label_qubits is None:
        label_qubits = num_qubits <= 64

    node_size = 320 if label_qubits else 70

    # Couplers.
    edge_segments = [positions[[a, b]] for a, b in edges]
    faulty_segments = []

    if edge_metric:
        table = two_qubit_gate_properties(backend)
        pair_error: dict[tuple[int, int], float] = {}

        for row in table.itertuples():
            pair = tuple(sorted((row.qubit_0, row.qubit_1)))
            pair_error[pair] = max(pair_error.get(pair, 0.0), row.error)

        errors = np.array([pair_error.get(edge, np.nan) for edge in edges], dtype=float)
        faulty = errors >= FAULTY_ERROR_THRESHOLD
        healthy = ~faulty & np.isfinite(errors)

        edge_log = True if log_scale is None else log_scale
        edge_norm = _norm(errors[healthy], edge_log)

        colors = [
            SEQUENTIAL_CMAP(edge_norm(error)) if ok else MISSING
            for error, ok in zip(errors, healthy, strict=True)
        ]

        normal = [segment for segment, bad in zip(edge_segments, faulty, strict=True) if not bad]
        normal_colors = [color for color, bad in zip(colors, faulty, strict=True) if not bad]
        faulty_segments = [
            segment for segment, bad in zip(edge_segments, faulty, strict=True) if bad
        ]

        ax.add_collection(LineCollection(normal, colors=normal_colors, linewidths=3.5, zorder=1))

        if faulty_segments:
            ax.add_collection(
                LineCollection(
                    faulty_segments,
                    colors=CRITICAL,
                    linewidths=2.0,
                    linestyles="--",
                    zorder=1,
                )
            )

        _colorbar(fig, ax, edge_norm, _edge_label(backend))
    else:
        ax.add_collection(
            LineCollection(edge_segments, colors=EDGE_NEUTRAL, linewidths=2.0, zorder=1)
        )

    # Qubits.
    if qubit_metric:
        table = qubit_properties(backend)

        if qubit_metric not in table.columns:
            raise ValueError(
                f"Unknown qubit metric '{qubit_metric}'. " f"Choose from {list(table.columns)}."
            )

        values = table[qubit_metric].to_numpy(dtype=float)

        if not np.isfinite(values).any():
            raise CalibrationDataError(
                f"Backend '{backend_name(backend)}' has no '{qubit_metric}' data."
            )

        qubit_log = ("error" in qubit_metric) if log_scale is None else log_scale
        qubit_norm = _norm(values, qubit_log)
        colors = [
            SEQUENTIAL_CMAP(qubit_norm(value)) if np.isfinite(value) else MISSING
            for value in values
        ]

        _colorbar(fig, ax, qubit_norm, metric_label(qubit_metric))
    else:
        colors = [SEQUENTIAL_BLUE[7]] * num_qubits

    ax.scatter(
        positions[:, 0],
        positions[:, 1],
        s=node_size,
        c=colors,
        edgecolors=SURFACE,
        linewidths=1.5,
        zorder=2,
    )

    if label_qubits:
        for qubit, (x, y) in enumerate(positions):
            rgba = colors[qubit] if not isinstance(colors[qubit], str) else None
            dark = rgba is None or (0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]) < 0.55
            ax.text(
                x,
                y,
                str(qubit),
                ha="center",
                va="center",
                fontsize=7,
                color="white" if dark else TEXT_PRIMARY,
                zorder=3,
            )

    if faulty_segments:
        ax.legend(
            handles=[Line2D([], [], color=CRITICAL, linestyle="--", label="Faulty coupler")],
            loc="lower left",
            frameon=False,
            fontsize=8,
            labelcolor=TEXT_SECONDARY,
        )

    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.margins(0.08)

    # Linear chains have zero height; give them room.
    if np.ptp(positions[:, 1]) == 0:
        ax.set_ylim(-1.0, 1.0)

    title = backend_name(backend)
    if qubit_metric:
        title += f" - {metric_label(qubit_metric)}"
    elif edge_metric:
        title += f" - {_edge_label(backend)}"
    ax.set_title(title, loc="left", fontsize=12)

    return _finish(fig, filename)


def plot_qubit_heatmap(backend, metric: str, **kwargs) -> Figure:
    """Color each qubit of the device topology by ``metric``."""

    return plot_backend_topology(backend, qubit_metric=metric, **kwargs)


def plot_t1_heatmap(backend, **kwargs) -> Figure:
    """Device map colored by T1 relaxation time."""

    return plot_qubit_heatmap(backend, "t1_us", **kwargs)


def plot_t2_heatmap(backend, **kwargs) -> Figure:
    """Device map colored by T2 dephasing time."""

    return plot_qubit_heatmap(backend, "t2_us", **kwargs)


def plot_readout_error_map(backend, **kwargs) -> Figure:
    """Device map colored by readout error."""

    return plot_qubit_heatmap(backend, "readout_error", **kwargs)


def plot_cx_error_map(backend, **kwargs) -> Figure:
    """Device map with couplers colored by native two-qubit gate error."""

    return plot_backend_topology(backend, edge_metric=True, **kwargs)


def plot_error_histogram(
    backend,
    metric: str = "readout_error",
    bins: int = 30,
    log_x: bool | None = None,
    ax: Axes | None = None,
    filename: str | None = None,
) -> Figure:
    """Histogram of a per-qubit metric, or of coupler errors with
    ``metric="coupler_error"``."""

    if metric == "coupler_error":
        table = two_qubit_gate_properties(backend)
        values = table["error"].to_numpy(dtype=float)
        values = values[values < FAULTY_ERROR_THRESHOLD]
        label = _edge_label(backend)
    else:
        table = qubit_properties(backend)

        if metric not in table.columns:
            raise ValueError(f"Unknown metric '{metric}'.")

        values = table[metric].to_numpy(dtype=float)
        label = metric_label(metric)

    values = values[np.isfinite(values)]

    if values.size == 0:
        raise CalibrationDataError(f"Backend '{backend_name(backend)}' has no '{metric}' data.")

    if log_x is None:
        log_x = "error" in metric and values.min() > 0

    fig, ax = _figure(ax, (6.5, 4.0))
    style_axes(ax)

    # Keep bins meaningful for small devices.
    bins = max(1, min(bins, 2 * int(np.sqrt(values.size))))

    if log_x:
        edges = np.logspace(np.log10(values.min()), np.log10(values.max() * 1.0001), bins + 1)
        ax.set_xscale("log")
    else:
        edges = bins

    ax.hist(values, bins=edges, color=PRIMARY_BAR, edgecolor=SURFACE, linewidth=1.0)

    median = float(np.median(values))
    ax.axvline(median, color=TEXT_PRIMARY, linewidth=1.0, linestyle=":")
    ax.annotate(
        f"median {median:.3g}",
        xy=(median, 1.0),
        xycoords=("data", "axes fraction"),
        xytext=(4, -4),
        textcoords="offset points",
        va="top",
        fontsize=8,
        color=TEXT_SECONDARY,
    )

    ax.set_xlabel(label)
    ax.set_ylabel("Count")
    ax.set_title(f"{backend_name(backend)} - {label} distribution", loc="left", fontsize=12)

    return _finish(fig, filename)


def plot_gate_errors(
    backend,
    gate: str | None = None,
    top: int | None = 40,
    ax: Axes | None = None,
    filename: str | None = None,
) -> Figure:
    """Bar chart of gate errors per qubit (or qubit pair), worst first.

    ``gate`` defaults to the native two-qubit gate. ``top`` limits the chart
    to the worst entries; faulty couplers are marked separately.
    """

    gate = gate or two_qubit_gate(backend)

    if gate is None:
        raise CalibrationDataError(f"Backend '{backend_name(backend)}' has no gate errors.")

    errors: dict[tuple[int, ...], float] = {}

    for qargs, error in gate_errors(backend, gate).items():
        if error is None:
            continue

        key = tuple(sorted(qargs))
        errors[key] = max(errors.get(key, 0.0), error)

    if not errors:
        raise CalibrationDataError(f"Gate '{gate}' has no calibrated errors.")

    series = pd.Series(
        {"-".join(map(str, key)): value for key, value in errors.items()}
    ).sort_values(ascending=False)

    if top is not None:
        series = series.iloc[:top]

    fig, ax = _figure(ax, (max(6.5, 0.22 * len(series) + 2), 4.0))
    style_axes(ax)

    colors = [CRITICAL if value >= FAULTY_ERROR_THRESHOLD else PRIMARY_BAR for value in series]
    ax.bar(
        series.index, series.to_numpy(), color=colors, width=0.8, edgecolor=SURFACE, linewidth=1.0
    )

    ax.set_yscale("log")
    ax.set_ylabel(f"{gate.upper()} error")
    ax.set_xlabel("Qubits" if len(next(iter(errors))) > 1 else "Qubit")
    ax.tick_params(axis="x", rotation=90, labelsize=7)
    ax.margins(x=0.01)

    title = f"{backend_name(backend)} - {gate.upper()} errors"
    if top is not None and len(errors) > top:
        title += f" (worst {top} of {len(errors)})"
    ax.set_title(title, loc="left", fontsize=12)

    if CRITICAL in colors:
        ax.legend(
            handles=[plt.Rectangle((0, 0), 1, 1, color=CRITICAL, label="Faulty (error = 1)")],
            frameon=False,
            fontsize=8,
            labelcolor=TEXT_SECONDARY,
        )

    return _finish(fig, filename)


def plot_qubit_ranking(
    backend,
    top: int = 20,
    ax: Axes | None = None,
    filename: str | None = None,
) -> Figure:
    """Horizontal bar chart of the best qubits by composite score."""

    ranking = rank_qubits(backend).iloc[:top]

    fig, ax = _figure(ax, (6.5, max(3.0, 0.28 * len(ranking) + 1.2)))
    style_axes(ax, grid_axis="x")

    labels = [f"Q{qubit}" for qubit in ranking.index]
    scores = ranking["score"].to_numpy()

    ax.barh(labels[::-1], scores[::-1], color=PRIMARY_BAR, height=0.7, edgecolor=SURFACE)

    low = float(scores.min())
    ax.set_xlim(max(0.0, low - (1.0 - low) * 0.5), 1.0)
    ax.set_xlabel("Score = (1 - readout) x (1 - 1Q error) x (1 - 2Q error)")
    ax.tick_params(axis="y", labelsize=8)
    ax.set_title(f"{backend_name(backend)} - top {len(ranking)} qubits", loc="left", fontsize=12)

    return _finish(fig, filename)


def plot_calibration_dashboard(backend, filename: str | None = None) -> Figure:
    """Six-panel overview: T1, T2, readout and 2Q error maps, readout error
    distribution and best qubits."""

    positions = topology_layout(backend)
    width, height = _topology_figsize(positions)
    map_width = min(width, 9.0)
    map_height = map_width * height / width

    fig = plt.figure(figsize=(2 * map_width, 2 * map_height + 5.0), layout="constrained")
    fig.set_facecolor(SURFACE)

    grid = fig.add_gridspec(3, 2, height_ratios=[map_height, map_height, 5.0])
    label = len(positions) <= 27

    plot_t1_heatmap(backend, ax=fig.add_subplot(grid[0, 0]), label_qubits=label)
    plot_t2_heatmap(backend, ax=fig.add_subplot(grid[0, 1]), label_qubits=label)
    plot_readout_error_map(backend, ax=fig.add_subplot(grid[1, 0]), label_qubits=label)
    plot_cx_error_map(backend, ax=fig.add_subplot(grid[1, 1]), label_qubits=label)
    plot_error_histogram(backend, "readout_error", ax=fig.add_subplot(grid[2, 0]))
    plot_qubit_ranking(backend, top=15, ax=fig.add_subplot(grid[2, 1]))

    fig.suptitle(
        f"{backend_name(backend)} calibration dashboard",
        x=0.01,
        ha="left",
        fontsize=15,
        color=TEXT_PRIMARY,
    )

    return _finish(fig, filename)


DEFAULT_COMPARISON_METRICS = (
    "mean_t1_us",
    "mean_t2_us",
    "mean_single_qubit_error",
    "mean_two_qubit_error",
    "mean_readout_error",
)


def plot_backend_comparison(
    backends,
    metrics=DEFAULT_COMPARISON_METRICS,
    filename: str | None = None,
) -> Figure:
    """Compare backend averages; one small panel per metric (no shared axis)."""

    table = compare_backends(backends)
    metrics = list(metrics)

    columns = min(len(metrics), 3)
    rows = math.ceil(len(metrics) / columns)
    fig, axes = plt.subplots(
        rows,
        columns,
        figsize=(4.2 * columns, 3.2 * rows),
        layout="constrained",
        squeeze=False,
    )
    fig.set_facecolor(SURFACE)

    colors = [categorical_color(index) for index in range(len(table))]

    for ax, metric in zip(axes.flat, metrics, strict=False):
        style_axes(ax)
        values = table[metric].astype(float).fillna(0.0)
        ax.bar(table.index, values, color=colors, width=0.65, edgecolor=SURFACE, linewidth=2)
        ax.set_title(
            metric_label(metric.removeprefix("mean_")) + " (mean)", loc="left", fontsize=10
        )
        ax.tick_params(axis="x", rotation=30, labelsize=8)

        for index, value in enumerate(values):
            ax.annotate(
                f"{value:.3g}",
                (index, value),
                xytext=(0, 2),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=7,
                color=TEXT_SECONDARY,
            )

    for ax in list(axes.flat)[len(metrics) :]:
        ax.set_visible(False)

    fig.suptitle("Backend comparison", x=0.01, ha="left", fontsize=13, color=TEXT_PRIMARY)

    return _finish(fig, filename)
