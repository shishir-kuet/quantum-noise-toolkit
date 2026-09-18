import numpy as np
import pytest
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel

from qntoolkit.noise_models import (
    AmplitudeDamping,
    BitFlip,
    ComposedNoise,
    CustomNoise,
    DepolarizingNoise,
    NoiseModelBuilder,
    PhaseDamping,
    PhaseFlip,
    ReadoutNoise,
    ResetNoise,
    ThermalRelaxation,
    noise_model_from_backend,
    noise_model_summary,
    noisy_simulator,
)

ZERO = np.array([1, 0])
ONE = np.array([0, 1])
PLUS = np.array([1, 1]) / np.sqrt(2)


def test_bit_flip_probabilities():
    assert BitFlip(0.25).apply(ZERO).probabilities() == pytest.approx([0.75, 0.25])


def test_phase_flip_keeps_populations_and_kills_coherence():
    state = PhaseFlip(0.5).apply(PLUS)

    assert state.probabilities() == pytest.approx([0.5, 0.5])
    assert abs(state.data[0, 1]) == pytest.approx(0.0, abs=1e-12)


def test_amplitude_damping_relaxes_to_ground():
    assert AmplitudeDamping(1.0).apply(ONE).probabilities() == pytest.approx([1.0, 0.0])
    assert AmplitudeDamping(0.3).apply(ONE).probabilities() == pytest.approx([0.3, 0.7])


def test_phase_damping_coherence():
    gamma = 0.36
    state = PhaseDamping(gamma).apply(PLUS)

    assert state.data[0, 1].real == pytest.approx(0.5 * np.sqrt(1 - gamma))


def test_full_depolarizing_gives_maximally_mixed_state():
    state = DepolarizingNoise(1.0).apply(ZERO)

    assert np.allclose(state.data, np.eye(2) / 2)


def test_two_qubit_depolarizing():
    channel = DepolarizingNoise(0.1, num_qubits=2)

    assert channel.num_qubits == 2
    assert channel.to_quantum_error().num_qubits == 2


def test_thermal_relaxation():
    channel = ThermalRelaxation(t1=100, t2=80, gate_time=100)
    state = channel.apply(ONE)

    assert state.probabilities()[0] == pytest.approx(1 - np.exp(-1), rel=1e-6)

    with pytest.raises(ValueError):
        ThermalRelaxation(t1=10, t2=30, gate_time=1)


def test_reset_noise():
    assert ResetNoise(1.0).apply(ONE).probabilities() == pytest.approx([1.0, 0.0])

    with pytest.raises(ValueError):
        ResetNoise(0.7, 0.7)


def test_kraus_operators_are_trace_preserving():
    for channel in (
        BitFlip(0.1),
        AmplitudeDamping(0.2),
        PhaseDamping(0.3),
        ThermalRelaxation(50, 40, 1),
        AmplitudeDamping(0.2).compose(PhaseDamping(0.1)),
    ):
        total = sum(op.conj().T @ op for op in channel.kraus_operators())
        assert np.allclose(total, np.eye(2)), channel


def test_custom_noise():
    p = 0.2
    kraus = [np.sqrt(1 - p) * np.eye(2), np.sqrt(p) * np.array([[0, 1], [1, 0]])]
    custom = CustomNoise(kraus, name="my_bit_flip")

    assert custom.num_qubits == 1
    assert custom.apply(ZERO).probabilities() == pytest.approx([0.8, 0.2])


def test_composition():
    composed = BitFlip(0.1).compose(BitFlip(0.1))

    assert isinstance(composed, ComposedNoise)
    # Two independent flips: P(flip) = 2 p (1 - p).
    assert composed.apply(ZERO).probabilities()[1] == pytest.approx(0.18)

    with pytest.raises(ValueError):
        BitFlip(0.1).compose(DepolarizingNoise(0.1, num_qubits=2))


def test_invalid_probabilities():
    with pytest.raises(ValueError):
        BitFlip(1.5)

    with pytest.raises(ValueError):
        DepolarizingNoise(-0.1)


def test_channel_equality():
    assert BitFlip(0.1) == BitFlip(0.1)
    assert BitFlip(0.1) != PhaseFlip(0.1)
    assert len({BitFlip(0.1), BitFlip(0.1)}) == 1


def test_readout_noise():
    readout = ReadoutNoise(0.02, 0.04)

    assert readout.error == pytest.approx(0.03)
    assert np.allclose(readout.confusion_matrix().sum(axis=0), 1.0)


def test_builder_and_simulation():
    model = (
        NoiseModelBuilder()
        .add(BitFlip(0.2), gates=["x"])
        .add_readout(ReadoutNoise(0.0, 0.0))
        .build()
    )

    assert isinstance(model, NoiseModel)

    circuit = QuantumCircuit(1)
    circuit.x(0)
    circuit.measure_all()

    simulator = noisy_simulator(model)
    job = simulator.run(transpile(circuit, simulator), shots=4000, seed_simulator=7)
    counts = job.result().get_counts()

    # The X gate is followed by a 20% bit flip, so ~20% of shots read 0.
    assert counts.get("0", 0) / 4000 == pytest.approx(0.2, abs=0.03)


def test_noise_model_from_backend(manila):
    model = noise_model_from_backend(manila)
    summary = noise_model_summary(model)

    assert not summary["is_ideal"]
    assert "cx" in summary["noisy_instructions"]
    assert summary["has_readout_error"]
    assert summary["noisy_qubits"] == [0, 1, 2, 3, 4]


def test_noisy_simulator_sources(manila):
    assert isinstance(noisy_simulator(), AerSimulator)
    assert isinstance(noisy_simulator(BitFlip(0.1)), AerSimulator)
    assert isinstance(noisy_simulator(manila), AerSimulator)
