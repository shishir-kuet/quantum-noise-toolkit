"""
Deterministic 2D layouts for backend coupling graphs.

Qubits are placed so that Euclidean distances match shortest-path distances
in the coupling graph: classical multidimensional scaling (MDS) provides the
initial positions and stress majorization (SMACOF) refines them. This gives
clean, reproducible drawings of heavy-hex and square lattices without
external tools such as Graphviz.
"""

from __future__ import annotations

import numpy as np
import rustworkx as rx

from qntoolkit.characterization.calibration import get_target


def coupling_edges(backend) -> list[tuple[int, int]]:
    """Return the undirected coupling edges of a backend, sorted."""

    coupling_map = get_target(backend).build_coupling_map()

    if coupling_map is None:
        return []

    return sorted({tuple(sorted(edge)) for edge in coupling_map.get_edges()})


def _graph_distances(num_qubits: int, edges: list[tuple[int, int]]) -> np.ndarray:
    graph = rx.PyGraph()
    graph.add_nodes_from(range(num_qubits))
    graph.add_edges_from_no_data(edges)

    distances = np.array(rx.distance_matrix(graph, null_value=np.inf), dtype=float)

    # Place disconnected components slightly apart from each other.
    finite = distances[np.isfinite(distances)]
    far = (finite.max() if finite.size else 1.0) + 2.0
    distances[~np.isfinite(distances)] = far
    np.fill_diagonal(distances, 0.0)

    return distances


def _classical_mds(distances: np.ndarray) -> np.ndarray:
    n = len(distances)
    centering = np.eye(n) - np.ones((n, n)) / n
    gram = -0.5 * centering @ (distances**2) @ centering

    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    order = np.argsort(eigenvalues)[::-1][:2]

    return eigenvectors[:, order] * np.sqrt(np.maximum(eigenvalues[order], 1e-9))


def _stress_majorization(
    positions: np.ndarray,
    distances: np.ndarray,
    iterations: int,
) -> np.ndarray:
    n = len(distances)

    with np.errstate(divide="ignore"):
        weights = np.where(distances > 0, distances**-2.0, 0.0)

    laplacian = -weights
    np.fill_diagonal(laplacian, weights.sum(axis=1))
    laplacian_pinv = np.linalg.pinv(laplacian)

    for _ in range(iterations):
        difference = positions[:, None, :] - positions[None, :, :]
        current = np.linalg.norm(difference, axis=-1)

        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(current > 1e-12, weights * distances / current, 0.0)

        b_matrix = -ratio
        np.fill_diagonal(b_matrix, ratio.sum(axis=1))
        positions = laplacian_pinv @ (b_matrix @ positions)

    return positions - positions.mean(axis=0) if n else positions


def topology_layout(backend, iterations: int = 150) -> np.ndarray:
    """Return an ``(num_qubits, 2)`` array of qubit positions."""

    num_qubits = get_target(backend).num_qubits or 0

    if num_qubits == 0:
        return np.zeros((0, 2))

    if num_qubits == 1:
        return np.zeros((1, 2))

    distances = _graph_distances(num_qubits, coupling_edges(backend))
    positions = _classical_mds(distances)
    positions = _stress_majorization(positions, distances, iterations)

    # Landscape orientation: put the largest spread on the x axis.
    if np.ptp(positions[:, 1]) > np.ptp(positions[:, 0]):
        positions = positions[:, ::-1]

    # Linear chains come out with numerical noise on the y axis; flatten it.
    if np.ptp(positions[:, 1]) < 1e-3 * max(np.ptp(positions[:, 0]), 1.0):
        positions[:, 1] = 0.0

    return positions
