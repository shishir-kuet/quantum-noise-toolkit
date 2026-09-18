# Theory: Quantum Noise on NISQ Devices

This note summarizes the physics behind the quantities the toolkit extracts and models.

## Decoherence: T1 and T2

**T1 (energy relaxation).** An excited qubit \|1⟩ decays to \|0⟩ by exchanging energy with its
environment. The excited-state population decays as

    P₁(t) = P₁(0) · e^(−t / T1)

**T2 (dephasing).** The relative phase of a superposition is randomized; the off-diagonal
element of the density matrix decays as e^(−t / T2). Relaxation also destroys coherence, so

    1/T2 = 1/(2 T1) + 1/T_φ      ⇒      T2 ≤ 2 T1

where T_φ is the pure-dephasing time. `ThermalRelaxation` enforces T2 ≤ 2 T1.

## Noise as quantum channels

Noise is described by a completely positive, trace-preserving map with Kraus operators Kᵢ:

    ρ → Σᵢ Kᵢ ρ Kᵢ†,      Σᵢ Kᵢ† Kᵢ = I

| Channel | Kraus operators / action |
|---|---|
| Bit flip (p) | √(1−p) I, √p X |
| Phase flip (p) | √(1−p) I, √p Z |
| Depolarizing (p) | ρ → (1 − p) ρ + p I/d |
| Amplitude damping (γ) | K₀ = [[1, 0], [0, √(1−γ)]], K₁ = [[0, √γ], [0, 0]] |
| Phase damping (γ) | K₀ = [[1, 0], [0, √(1−γ)]], K₁ = [[0, 0], [0, √γ]] |
| Thermal relaxation | Amplitude + phase damping with γ₁ = 1 − e^(−t/T1), dephasing from T2 |

## Readout error

Measurement is described by a confusion matrix M[measured, prepared]:

    M = [[1 − p(1|0),  p(0|1)    ],
         [p(1|0),      1 − p(0|1)]]

IBM reports the average assignment error (p(1|0) + p(0|1)) / 2 as the `measure` error.

## Gate errors

Calibration reports an error per gate and qubit(s), usually 1 − average gate fidelity estimated
by randomized benchmarking. Two-qubit gates (CX, ECR, CZ) are typically 10× noisier than
single-qubit gates, so the two-qubit gate count usually dominates a circuit's error.

## Fidelity measures

| Measure | Definition |
|---|---|
| State fidelity | F(ρ, σ) = (Tr √(√ρ σ √ρ))² |
| Trace distance | D(ρ, σ) = ½ ‖ρ − σ‖₁ |
| Purity | Tr ρ² (1 for pure states, 1/d for maximally mixed) |
| Process fidelity | F_pro = ⟨Φ⁺\| (E ⊗ I)(\|Φ⁺⟩⟨Φ⁺\|) \|Φ⁺⟩ |
| Average gate fidelity | F_avg = (d F_pro + 1) / (d + 1) |
| Hellinger fidelity | (Σₓ √(pₓ qₓ))² between measurement distributions |
| Total variation distance | ½ Σₓ \|pₓ − qₓ\| |

For a single-qubit depolarizing channel with probability p: F_pro = 1 − 3p/4 and F_avg = 1 − p/2.

## Estimated success probability

Assuming independent errors, a circuit runs error-free with probability

    ESP = Π_gates (1 − ε_g) · Π_measurements (1 − ε_m)

computed on the physical qubits chosen by the transpiler. This is the model used by
`analyse_circuit`. It ignores crosstalk and error cancellation, so it is a fast, slightly
optimistic first-order estimate. It is widely used for layout selection and for comparing
backends.

### Idle decoherence

Gate errors already include decoherence *during* gates, but not while a qubit waits for
others. With `include_idle=True` the circuit is scheduled as late as possible (ALAP) with the
device's gate durations. Each idle window of length t, after the qubit's first operation, is
charged the average gate error of the T1/T2 relaxation channel:

    ε_idle(t) = 1 − (3 + e^(−t/T1) + 2 e^(−t/T2)) / 6

Qubits waiting in \|0⟩ before their first gate are not charged, because the ground state does
not decay. See [hardware_validation.md](hardware_validation.md) for how much this matters on
real hardware.

## Why the toolkit excludes faulty hardware from averages

IBM marks a disabled qubit or coupler with error 1.0. Including these in a mean would turn, for
example, a median two-qubit error of 0.004 into a mean of 0.045 on a 156-qubit device. The
toolkit reports them as faulty counts and hotspots, and computes averages over working hardware.

## Further reading

- M. A. Nielsen and I. L. Chuang, *Quantum Computation and Quantum Information*, ch. 8
- J. Preskill, "Quantum Computing in the NISQ era and beyond", *Quantum* 2, 79 (2018)
- E. Magesan, J. M. Gambetta, J. Emerson, "Scalable and robust randomized benchmarking of
  quantum processes", *PRL* 106, 180504 (2011)
- B. Iglewicz and D. Hoaglin, *How to Detect and Handle Outliers* (1993), for the modified
  z-score used in hotspot detection
