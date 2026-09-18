"""
Build Aer noise models from channels or from backend calibration data.
"""

from __future__ import annotations

from collections.abc import Sequence

from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel

from .channels import NoiseChannel, ReadoutNoise


class NoiseModelBuilder:
    """Fluent builder for Aer noise models.

    Example::

        model = (
            NoiseModelBuilder()
            .add(DepolarizingNoise(0.001), gates=["sx", "x"])
            .add(DepolarizingNoise(0.01, num_qubits=2), gates=["cx"])
            .add_readout(ReadoutNoise(0.02, 0.03))
            .build()
        )
    """

    def __init__(self, basis_gates: Sequence[str] | None = None):
        self._basis_gates = list(basis_gates) if basis_gates else None
        self._channels: list[tuple[NoiseChannel, list[str] | None, list[int] | None]] = []
        self._readout: list[tuple[ReadoutNoise, list[int] | None]] = []

    def add(
        self,
        channel: NoiseChannel,
        gates: Sequence[str] | None = None,
        qubits: Sequence[int] | None = None,
    ) -> NoiseModelBuilder:
        self._channels.append(
            (
                channel,
                list(gates) if gates else None,
                list(qubits) if qubits is not None else None,
            )
        )
        return self

    def add_readout(
        self,
        readout: ReadoutNoise,
        qubits: Sequence[int] | None = None,
    ) -> NoiseModelBuilder:
        self._readout.append((readout, list(qubits) if qubits is not None else None))
        return self

    def build(self) -> NoiseModel:
        noise_model = NoiseModel(basis_gates=self._basis_gates)

        for channel, gates, qubits in self._channels:
            channel.add_to(noise_model, gates, qubits)

        for readout, qubits in self._readout:
            readout.add_to(noise_model, qubits)

        return noise_model


def noise_model_from_backend(
    backend,
    gate_error: bool = True,
    readout_error: bool = True,
    thermal_relaxation: bool = True,
) -> NoiseModel:
    """Build a realistic noise model from a backend's calibration data."""

    return NoiseModel.from_backend(
        backend,
        gate_error=gate_error,
        readout_error=readout_error,
        thermal_relaxation=thermal_relaxation,
    )


def noisy_simulator(source=None, **options) -> AerSimulator:
    """Return an Aer simulator with noise.

    ``source`` may be a ``NoiseModel``, a ``NoiseChannel``, or a backend. A
    backend produces a simulator that mimics the device (noise, coupling map
    and basis gates). With ``source=None`` an ideal simulator is returned.
    """

    if source is None:
        return AerSimulator(**options)

    if isinstance(source, NoiseModel):
        return AerSimulator(noise_model=source, **options)

    if isinstance(source, (NoiseChannel, ReadoutNoise)):
        return AerSimulator(noise_model=source.to_noise_model(), **options)

    return AerSimulator.from_backend(source, **options)


def noise_model_summary(noise_model: NoiseModel) -> dict:
    """Return a JSON-friendly description of an Aer noise model."""

    return {
        "basis_gates": sorted(noise_model.basis_gates),
        "noisy_instructions": sorted(noise_model.noise_instructions),
        "noisy_qubits": sorted(noise_model.noise_qubits),
        "is_ideal": noise_model.is_ideal(),
        "num_local_quantum_errors": sum(
            len(errors) for errors in noise_model._local_quantum_errors.values()
        ),
        "all_qubit_quantum_errors": sorted(noise_model._default_quantum_errors),
        "has_readout_error": (
            noise_model._default_readout_error is not None
            or bool(noise_model._local_readout_errors)
        ),
    }
