"""
Common quantum information metrics for states, channels and measurement counts.

Channel arguments accept anything Qiskit's ``quantum_info`` understands
(``Operator``, ``Kraus``, ``SuperOp``, circuits, ...) as well as toolkit
:class:`~qntoolkit.noise_models.NoiseChannel` objects.
"""

from __future__ import annotations

import numpy as np
from qiskit.quantum_info import DensityMatrix
from qiskit.quantum_info import average_gate_fidelity as _average_gate_fidelity
from qiskit.quantum_info import hellinger_fidelity as _hellinger_fidelity
from qiskit.quantum_info import process_fidelity as _process_fidelity
from qiskit.quantum_info import purity as _purity
from qiskit.quantum_info import state_fidelity as _state_fidelity
from qiskit_aer.noise import QuantumError

from qntoolkit.noise_models import NoiseChannel


def _as_channel(channel):
    if isinstance(channel, NoiseChannel):
        channel = channel.to_quantum_error()

    if isinstance(channel, QuantumError):
        return channel.to_quantumchannel()

    return channel


def state_fidelity(state_a, state_b, validate: bool = True) -> float:
    """Fidelity F(rho, sigma) = (Tr sqrt(sqrt(rho) sigma sqrt(rho)))^2."""

    return float(_state_fidelity(state_a, state_b, validate=validate))


def process_fidelity(channel, target=None) -> float:
    """Process (entanglement) fidelity of ``channel`` with ``target``.

    If ``target`` is omitted the identity channel is used, which measures how
    close a noise channel is to doing nothing.
    """

    return float(_process_fidelity(_as_channel(channel), target=_as_channel(target)))


def gate_fidelity(channel, target=None) -> float:
    """Average gate fidelity of ``channel`` with ``target`` (identity by default)."""

    return float(_average_gate_fidelity(_as_channel(channel), target=_as_channel(target)))


def gate_error(channel, target=None) -> float:
    """Average gate error, ``1 - gate_fidelity``."""

    return 1.0 - gate_fidelity(channel, target)


def purity(state) -> float:
    """Purity Tr(rho^2); 1 for pure states, 1/d for the maximally mixed state."""

    return float(np.real(_purity(state)))


def trace_distance(state_a, state_b) -> float:
    """Trace distance 0.5 * ||rho - sigma||_1."""

    difference = DensityMatrix(state_a).data - DensityMatrix(state_b).data
    eigenvalues = np.linalg.eigvalsh(difference)

    return float(0.5 * np.sum(np.abs(eigenvalues)))


def _normalize(counts: dict) -> dict:
    total = sum(counts.values())

    if total <= 0:
        raise ValueError("Counts must contain at least one shot.")

    return {key: value / total for key, value in counts.items()}


def hellinger_fidelity(counts_a: dict, counts_b: dict) -> float:
    """Hellinger fidelity between two measurement count distributions."""

    return float(_hellinger_fidelity(counts_a, counts_b))


def total_variation_distance(counts_a: dict, counts_b: dict) -> float:
    """Total variation distance between two count distributions."""

    p = _normalize(counts_a)
    q = _normalize(counts_b)

    return float(0.5 * sum(abs(p.get(key, 0.0) - q.get(key, 0.0)) for key in p.keys() | q.keys()))
