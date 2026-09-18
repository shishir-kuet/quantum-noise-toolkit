"""
Standard quantum noise channels built on top of Qiskit Aer.

Every channel can be converted to an Aer ``QuantumError``, inspected as a
set of Kraus operators, applied to a quantum state, composed with other
channels and turned into a ready-to-use Aer ``NoiseModel``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence

import numpy as np
from qiskit.quantum_info import DensityMatrix, Kraus
from qiskit_aer.noise import (
    NoiseModel,
    QuantumError,
    amplitude_damping_error,
    depolarizing_error,
    kraus_error,
    pauli_error,
    phase_damping_error,
    reset_error,
    thermal_relaxation_error,
)
from qiskit_aer.noise import ReadoutError as AerReadoutError

DEFAULT_SINGLE_QUBIT_GATES = ("id", "x", "sx", "h", "u")
DEFAULT_TWO_QUBIT_GATES = ("cx", "cz", "ecr")


def _check_probability(value: float, name: str) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value}.")

    return float(value)


class NoiseChannel(ABC):
    """Base class for all noise channels."""

    num_qubits: int = 1

    @abstractmethod
    def to_quantum_error(self) -> QuantumError:
        """Return the equivalent Aer ``QuantumError``."""

    def kraus_operators(self) -> list[np.ndarray]:
        """Return the Kraus operators of the channel."""

        return list(Kraus(self.to_quantum_error().to_quantumchannel()).data)

    def apply(self, state) -> DensityMatrix:
        """Apply the channel to a state and return the resulting density matrix."""

        return DensityMatrix(state).evolve(Kraus(self.kraus_operators()))

    def compose(self, other: NoiseChannel) -> ComposedNoise:
        """Return the channel that applies ``self`` and then ``other``."""

        return ComposedNoise([self, other])

    def default_gates(self) -> tuple[str, ...]:
        if self.num_qubits == 1:
            return DEFAULT_SINGLE_QUBIT_GATES

        if self.num_qubits == 2:
            return DEFAULT_TWO_QUBIT_GATES

        raise ValueError(
            f"No default gates for a {self.num_qubits}-qubit channel; pass gates explicitly."
        )

    def add_to(
        self,
        noise_model: NoiseModel,
        gates: Sequence[str] | None = None,
        qubits: Sequence[int] | None = None,
    ) -> NoiseModel:
        """Attach this channel to ``gates`` in an existing noise model.

        If ``qubits`` is given, the error is only applied on those qubits
        (as the gate's qargs); otherwise it applies to all qubits.
        """

        gates = list(gates or self.default_gates())
        error = self.to_quantum_error()

        if qubits is None:
            noise_model.add_all_qubit_quantum_error(error, gates)
        else:
            noise_model.add_quantum_error(error, gates, list(qubits))

        return noise_model

    def to_noise_model(
        self,
        gates: Sequence[str] | None = None,
        qubits: Sequence[int] | None = None,
    ) -> NoiseModel:
        """Return a new Aer ``NoiseModel`` containing only this channel."""

        return self.add_to(NoiseModel(), gates, qubits)

    def _parameters(self) -> dict:
        return {}

    def __repr__(self) -> str:
        arguments = ", ".join(f"{key}={value!r}" for key, value in self._parameters().items())
        return f"{type(self).__name__}({arguments})"

    def __eq__(self, other) -> bool:
        return type(self) is type(other) and self._parameters() == other._parameters()

    def __hash__(self) -> int:
        return hash((type(self).__name__, tuple(self._parameters().items())))


class DepolarizingNoise(NoiseChannel):
    """Depolarizing channel: with probability ``p`` the state is replaced by
    the maximally mixed state."""

    def __init__(self, probability: float, num_qubits: int = 1):
        if num_qubits < 1:
            raise ValueError("num_qubits must be at least 1.")

        # Aer allows p up to 4^n / (4^n - 1) (a full Pauli twirl); we keep the
        # physically intuitive range [0, 1].
        self.probability = _check_probability(probability, "probability")
        self.num_qubits = num_qubits

    def to_quantum_error(self) -> QuantumError:
        return depolarizing_error(self.probability, self.num_qubits)

    def _parameters(self) -> dict:
        return {"probability": self.probability, "num_qubits": self.num_qubits}


class BitFlip(NoiseChannel):
    """Applies an X error with probability ``p``."""

    def __init__(self, probability: float):
        self.probability = _check_probability(probability, "probability")

    def to_quantum_error(self) -> QuantumError:
        return pauli_error([("X", self.probability), ("I", 1 - self.probability)])

    def _parameters(self) -> dict:
        return {"probability": self.probability}


class PhaseFlip(NoiseChannel):
    """Applies a Z error with probability ``p``."""

    def __init__(self, probability: float):
        self.probability = _check_probability(probability, "probability")

    def to_quantum_error(self) -> QuantumError:
        return pauli_error([("Z", self.probability), ("I", 1 - self.probability)])

    def _parameters(self) -> dict:
        return {"probability": self.probability}


class AmplitudeDamping(NoiseChannel):
    """Energy relaxation |1> -> |0> with probability ``gamma``."""

    def __init__(self, gamma: float, excited_state_population: float = 0.0):
        self.gamma = _check_probability(gamma, "gamma")
        self.excited_state_population = _check_probability(
            excited_state_population, "excited_state_population"
        )

    def to_quantum_error(self) -> QuantumError:
        return amplitude_damping_error(
            self.gamma,
            excited_state_population=self.excited_state_population,
        )

    def _parameters(self) -> dict:
        return {
            "gamma": self.gamma,
            "excited_state_population": self.excited_state_population,
        }


class PhaseDamping(NoiseChannel):
    """Pure dephasing: loss of phase coherence without energy loss."""

    def __init__(self, gamma: float):
        self.gamma = _check_probability(gamma, "gamma")

    def to_quantum_error(self) -> QuantumError:
        return phase_damping_error(self.gamma)

    def _parameters(self) -> dict:
        return {"gamma": self.gamma}


class ThermalRelaxation(NoiseChannel):
    """Combined T1/T2 relaxation during a gate of duration ``gate_time``.

    ``t1``, ``t2`` and ``gate_time`` must use the same time unit.
    """

    def __init__(
        self,
        t1: float,
        t2: float,
        gate_time: float,
        excited_state_population: float = 0.0,
    ):
        if t1 <= 0 or t2 <= 0:
            raise ValueError("t1 and t2 must be positive.")

        if t2 > 2 * t1:
            raise ValueError(f"t2 ({t2}) cannot exceed 2 * t1 ({2 * t1}).")

        if gate_time < 0:
            raise ValueError("gate_time must be non-negative.")

        self.t1 = float(t1)
        self.t2 = float(t2)
        self.gate_time = float(gate_time)
        self.excited_state_population = _check_probability(
            excited_state_population, "excited_state_population"
        )

    def to_quantum_error(self) -> QuantumError:
        return thermal_relaxation_error(
            self.t1,
            self.t2,
            self.gate_time,
            excited_state_population=self.excited_state_population,
        )

    def _parameters(self) -> dict:
        return {
            "t1": self.t1,
            "t2": self.t2,
            "gate_time": self.gate_time,
            "excited_state_population": self.excited_state_population,
        }


class ResetNoise(NoiseChannel):
    """Resets the qubit to |0> with ``prob_0`` or to |1> with ``prob_1``."""

    def __init__(self, prob_0: float, prob_1: float = 0.0):
        self.prob_0 = _check_probability(prob_0, "prob_0")
        self.prob_1 = _check_probability(prob_1, "prob_1")

        if self.prob_0 + self.prob_1 > 1:
            raise ValueError("prob_0 + prob_1 must not exceed 1.")

    def to_quantum_error(self) -> QuantumError:
        return reset_error(self.prob_0, self.prob_1)

    def _parameters(self) -> dict:
        return {"prob_0": self.prob_0, "prob_1": self.prob_1}


class CustomNoise(NoiseChannel):
    """A user-defined channel from Kraus operators or an Aer ``QuantumError``."""

    def __init__(self, operators: Iterable[np.ndarray] | QuantumError, name: str = "custom"):
        if isinstance(operators, QuantumError):
            self._error = operators
        else:
            self._error = kraus_error([np.asarray(op, dtype=complex) for op in operators])

        self.name = name
        self.num_qubits = self._error.num_qubits

    def to_quantum_error(self) -> QuantumError:
        return self._error

    def _parameters(self) -> dict:
        return {"name": self.name, "num_qubits": self.num_qubits}

    def __eq__(self, other) -> bool:
        return self is other

    __hash__ = object.__hash__


class ComposedNoise(NoiseChannel):
    """Sequential composition of channels acting on the same qubits."""

    def __init__(self, channels: Sequence[NoiseChannel]):
        flat: list[NoiseChannel] = []

        for channel in channels:
            if isinstance(channel, ComposedNoise):
                flat.extend(channel.channels)
            else:
                flat.append(channel)

        if not flat:
            raise ValueError("ComposedNoise needs at least one channel.")

        sizes = {channel.num_qubits for channel in flat}

        if len(sizes) != 1:
            raise ValueError("All composed channels must act on the same number of qubits.")

        self.channels = flat
        self.num_qubits = sizes.pop()

    def to_quantum_error(self) -> QuantumError:
        error = self.channels[0].to_quantum_error()

        for channel in self.channels[1:]:
            error = error.compose(channel.to_quantum_error())

        return error

    def _parameters(self) -> dict:
        return {"channels": tuple(self.channels)}

    def __repr__(self) -> str:
        return " -> ".join(repr(channel) for channel in self.channels)


class ReadoutNoise:
    """Classical measurement error.

    ``p1_given0`` is the probability of reading 1 when the qubit is in |0>,
    ``p0_given1`` the probability of reading 0 when the qubit is in |1>.
    """

    def __init__(self, p1_given0: float, p0_given1: float | None = None):
        self.p1_given0 = _check_probability(p1_given0, "p1_given0")
        self.p0_given1 = _check_probability(
            p1_given0 if p0_given1 is None else p0_given1, "p0_given1"
        )

    @property
    def error(self) -> float:
        """Average assignment error."""

        return (self.p1_given0 + self.p0_given1) / 2

    def confusion_matrix(self) -> np.ndarray:
        """Return ``M[measured, prepared]``."""

        return np.array(
            [
                [1 - self.p1_given0, self.p0_given1],
                [self.p1_given0, 1 - self.p0_given1],
            ]
        )

    def to_readout_error(self) -> AerReadoutError:
        return AerReadoutError(
            [
                [1 - self.p1_given0, self.p1_given0],
                [self.p0_given1, 1 - self.p0_given1],
            ]
        )

    def add_to(
        self,
        noise_model: NoiseModel,
        qubits: Sequence[int] | None = None,
    ) -> NoiseModel:
        error = self.to_readout_error()

        if qubits is None:
            noise_model.add_all_qubit_readout_error(error)
        else:
            for qubit in qubits:
                noise_model.add_readout_error(error, [qubit])

        return noise_model

    def to_noise_model(self, qubits: Sequence[int] | None = None) -> NoiseModel:
        return self.add_to(NoiseModel(), qubits)

    def __repr__(self) -> str:
        return f"ReadoutNoise(p1_given0={self.p1_given0!r}, p0_given1={self.p0_given1!r})"

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, ReadoutNoise)
            and self.p1_given0 == other.p1_given0
            and self.p0_given1 == other.p0_given1
        )

    def __hash__(self) -> int:
        return hash(("ReadoutNoise", self.p1_given0, self.p0_given1))
