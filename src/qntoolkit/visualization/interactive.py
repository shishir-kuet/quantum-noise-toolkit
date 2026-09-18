"""
Interactive (Plotly) device maps with per-qubit hover tooltips.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from qntoolkit.characterization.calibration import (
    FAULTY_ERROR_THRESHOLD,
    backend_name,
    qubit_properties,
    two_qubit_gate,
    two_qubit_gate_properties,
)

from .layout import coupling_edges, topology_layout
from .style import (
    CRITICAL,
    EDGE_NEUTRAL,
    SEQUENTIAL_BLUE,
    SURFACE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    metric_label,
)


def _format(value: float, spec: str) -> str:
    return "n/a" if value is None or not np.isfinite(value) else format(value, spec)


def plot_interactive_topology(backend, qubit_metric: str = "readout_error") -> go.Figure:
    """Return a Plotly device map; hover a qubit to see all its calibration data.

    Save it with ``fig.write_html("map.html")`` or show it with ``fig.show()``.
    """

    positions = topology_layout(backend)
    edges = coupling_edges(backend)
    table = qubit_properties(backend)

    if qubit_metric not in table.columns:
        raise ValueError(f"Unknown qubit metric '{qubit_metric}'.")

    couplers = two_qubit_gate_properties(backend)
    faulty_pairs = {
        tuple(sorted((row.qubit_0, row.qubit_1)))
        for row in couplers.itertuples()
        if row.error >= FAULTY_ERROR_THRESHOLD
    }

    figure = go.Figure()

    for faulty in (False, True):
        xs, ys = [], []

        for a, b in edges:
            if ((a, b) in faulty_pairs) != faulty:
                continue

            xs += [positions[a, 0], positions[b, 0], None]
            ys += [positions[a, 1], positions[b, 1], None]

        if xs:
            figure.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines",
                    line={
                        "color": CRITICAL if faulty else EDGE_NEUTRAL,
                        "width": 2,
                        "dash": "dash" if faulty else "solid",
                    },
                    hoverinfo="skip",
                    name="Faulty coupler" if faulty else "Coupler",
                    showlegend=faulty,
                )
            )

    hover = [
        (
            f"<b>Qubit {qubit}</b><br>"
            f"T1: {_format(row.t1_us, '.1f')} µs<br>"
            f"T2: {_format(row.t2_us, '.1f')} µs<br>"
            f"Readout error: {_format(row.readout_error, '.2e')}<br>"
            f"1Q error: {_format(row.single_qubit_error, '.2e')}<br>"
            f"2Q error (mean): {_format(row.two_qubit_error, '.2e')}"
        )
        for qubit, row in table.iterrows()
    ]

    values = table[qubit_metric].to_numpy(dtype=float)
    fill = np.nanmin(values) if np.isfinite(values).any() else 0.0
    colorscale = [
        [index / (len(SEQUENTIAL_BLUE) - 1), color] for index, color in enumerate(SEQUENTIAL_BLUE)
    ]

    figure.add_trace(
        go.Scatter(
            x=positions[:, 0],
            y=positions[:, 1],
            mode="markers+text" if len(positions) <= 64 else "markers",
            text=[str(qubit) for qubit in table.index],
            textfont={"size": 9, "color": TEXT_PRIMARY},
            textposition="top center",
            marker={
                "size": 16 if len(positions) <= 64 else 10,
                "color": np.nan_to_num(values, nan=fill),
                "colorscale": colorscale,
                "line": {"color": SURFACE, "width": 2},
                "colorbar": {"title": {"text": metric_label(qubit_metric)}},
            },
            hovertext=hover,
            hoverinfo="text",
            name="Qubit",
            showlegend=False,
        )
    )

    gate = two_qubit_gate(backend)
    figure.update_layout(
        title={
            "text": f"{backend_name(backend)} - {metric_label(qubit_metric)}"
            + (f" (native 2Q gate: {gate})" if gate else ""),
            "x": 0.01,
        },
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        font={"color": TEXT_SECONDARY},
        xaxis={"visible": False},
        yaxis={"visible": False, "scaleanchor": "x"},
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
        legend={"orientation": "h", "y": -0.02},
        hoverlabel={"bgcolor": "white"},
    )

    return figure
