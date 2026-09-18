import numpy as np
import plotly.graph_objects as go
import pytest
from matplotlib import pyplot as plt
from matplotlib.figure import Figure

from qntoolkit.utils.exceptions import CalibrationDataError
from qntoolkit.visualization import (
    coupling_edges,
    plot_backend_comparison,
    plot_backend_topology,
    plot_calibration_dashboard,
    plot_cx_error_map,
    plot_error_histogram,
    plot_gate_errors,
    plot_interactive_topology,
    plot_qubit_ranking,
    plot_readout_error_map,
    plot_t1_heatmap,
    plot_t2_heatmap,
    topology_layout,
)


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


def test_layout_matches_graph_distance(manila):
    positions = topology_layout(manila)

    assert positions.shape == (5, 2)
    # Manila is a chain: neighbours are equally spaced on a line.
    assert np.allclose(positions[:, 1], 0.0)
    gaps = np.diff(np.sort(positions[:, 0]))
    assert np.allclose(gaps, gaps[0], rtol=0.05)


def test_coupling_edges(manila):
    assert coupling_edges(manila) == [(0, 1), (1, 2), (2, 3), (3, 4)]


@pytest.mark.parametrize(
    "plot",
    [
        plot_backend_topology,
        plot_t1_heatmap,
        plot_t2_heatmap,
        plot_readout_error_map,
        plot_cx_error_map,
        plot_error_histogram,
        plot_gate_errors,
        plot_qubit_ranking,
        plot_calibration_dashboard,
    ],
)
def test_plots_return_figures(plot, manila):
    assert isinstance(plot(manila), Figure)


def test_plots_on_large_backend(fez, tmp_path):
    output = tmp_path / "fez_cx.png"
    plot_cx_error_map(fez, filename=str(output))

    assert output.stat().st_size > 10_000
    assert isinstance(plot_error_histogram(fez, "coupler_error"), Figure)


def test_plot_into_existing_axes(manila):
    fig, ax = plt.subplots()

    assert plot_error_histogram(manila, ax=ax) is fig


def test_backend_comparison(manila, fez):
    assert isinstance(plot_backend_comparison([manila, fez]), Figure)


def test_invalid_metric(manila):
    with pytest.raises(ValueError):
        plot_backend_topology(manila, qubit_metric="not_a_metric")


def test_simulator_has_no_topology(aer):
    with pytest.raises(CalibrationDataError):
        plot_t1_heatmap(aer)


def test_interactive_topology(manila, tmp_path):
    figure = plot_interactive_topology(manila, "t1_us")

    assert isinstance(figure, go.Figure)

    output = tmp_path / "map.html"
    figure.write_html(output)
    assert "Qubit 0" in output.read_text(encoding="utf-8")
