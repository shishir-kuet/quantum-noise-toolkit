# Hardware Validation on ibm_fez

Can calibration data alone predict how a circuit will perform on real hardware? This page
tests the toolkit's estimator against **IBM's 156-qubit Heron processor `ibm_fez`**.

![Estimate vs hardware](images/hardware_validation.png)

## Setup

| | |
|---|---|
| Device | `ibm_fez` (IBM Heron r2, 156 qubits, native CZ gate) |
| Job | `dams55o2fm4c73f3f2k0`, one job, 3 circuits, 4000 shots each, ~6 s of QPU time |
| Circuits | Bell state, 3-qubit GHZ, 5-qubit GHZ (chain of CNOTs, transpiled with `optimization_level=3`) |
| Calibration age | The device was calibrated ~4 minutes before the job ran |
| Metric | Probability of measuring an ideal outcome, `00…0` or `11…1` |
| Script | [`examples/hardware_validation.py`](../examples/hardware_validation.py); raw results in [`results/ibm_fez_validation.json`](results/ibm_fez_validation.json) |

Three predictions were compared with the hardware:

- **Estimate:** `analyse_circuit()`, the product of `(1 − error)` over every gate and
  measurement on the physical qubits the transpiler chose.
- **Estimate + idle:** the same, plus T1/T2 decoherence of qubits idling between gates
  (`include_idle=True`).
- **Noisy simulation:** Aer with `NoiseModel.from_backend` (depolarizing gate errors, thermal
  relaxation and readout errors).

## Results

| Circuit | Physical qubits | 2Q gates | Estimate | Estimate + idle | Noisy simulation | **Hardware** |
|---|---|---|---|---|---|---|
| Bell | 142, 143 | 1 | 0.987 | 0.987 | 0.988 | **0.983** |
| GHZ-3 | 142–144 | 2 | 0.978 | 0.978 | 0.979 | **0.976** |
| GHZ-5 | 140–144 | 4 | 0.958 | 0.955 | 0.959 | **0.929** |

For Bell and GHZ-3 the estimate matches the hardware to within **0.4 percentage points**,
within about two standard deviations of shot noise (±0.2 points at 4000 shots). The simulation's output
distribution also matches the hardware closely: Hellinger fidelity 0.999 (Bell), 0.997
(GHZ-3), 0.988 (GHZ-5).

## Explaining the GHZ-5 gap

The GHZ-5 hardware result is **3 points** below every prediction. Two causes were tested.

**Idle decoherence explains only 0.3 points.** Scheduling the circuit with the device's gate
durations shows 648 ns of idle time across the five qubits. Charging each idle window the
average error of T1/T2 relaxation lowers the estimate from 0.958 to 0.955. The effect is real
but small.

**Most of the gap comes from one qubit.** For each qubit, the diagnosis counts the shots where
only that qubit disagrees with the ideal outcome. It then compares that rate with the same rate
in the calibrated simulation:

| Qubit | Hardware | Calibration predicts |
|---|---|---|
| **Q140** | **3.30 %** | **1.09 %** |
| Q141 | 0.67 % | 0.68 % |
| Q142 | 0.40 % | 0.58 % |
| Q143 | 0.53 % | 0.55 % |
| Q144 | 0.57 % | 0.57 % |

Four of the five qubits behave exactly as their calibration predicts. **Qubit 140 fails three
times more often**, which accounts for about 2.2 of the 3 missing points. Its errors are
mostly 1 → 0 flips (2.35 % of shots versus 0.95 % for 0 → 1). That asymmetry is the signature
of energy relaxation, and it is consistent with Q140's T1 fluctuating between calibration and
execution, for example through a two-level-system (TLS) defect. Static calibration data cannot
capture this.

## Takeaways

- For small circuits the calibration-based estimate is accurate to within a few tenths of a
  percentage point, at a tiny fraction of the cost of simulation or hardware time.
- The remaining error is not spread evenly. It concentrates on individual qubits whose behavior
  drifts from their calibration. Comparing per-qubit flip rates with the calibrated prediction
  finds them directly.
- Practical consequence: re-rank qubits shortly before a run, or exclude qubits that recently
  misbehaved, when choosing a layout.

## Reproduce

```bash
python examples/hardware_validation.py --dry-run                   # no QPU time
python examples/hardware_validation.py ibm_fez                     # submit a new job
python examples/hardware_validation.py --job-id dams55o2fm4c73f3f2k0  # re-analyse this job
```

Re-analysing an old job uses the device's *current* calibration, so the estimates can differ
slightly from the values above.
