"""
Command-line interface: ``qntoolkit <command> ...`` (or ``python -m qntoolkit``).

Examples::

    qntoolkit backends --fake
    qntoolkit summary fake_fez
    qntoolkit hotspots ibm_fez
    qntoolkit analyze circuit.qasm ibm_fez --idle
    qntoolkit report ibm_fez -o fez_report.html
    qntoolkit dashboard ibm_fez -o dashboard.png
"""

from __future__ import annotations

import argparse
import sys
import warnings
from collections.abc import Sequence
from pathlib import Path

from qntoolkit import __version__


def _load(name: str):
    from qntoolkit.utils import load_backend

    # Some fake backends warn that their data is synthetic; keep CLI output clean.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        return load_backend(name)


def _load_circuit(path: str):
    from qiskit import qasm2, qasm3

    source = Path(path).read_text(encoding="utf-8")

    if "OPENQASM 3" in source:
        return qasm3.loads(source)

    return qasm2.loads(source, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)


def _backends(args: argparse.Namespace) -> None:
    if args.fake:
        from qntoolkit.utils import list_fake_backends

        names = list_fake_backends()
    else:
        from qiskit_ibm_runtime import QiskitRuntimeService

        from qntoolkit.utils import list_backends

        names = list_backends(QiskitRuntimeService())

    print("\n".join(names))


def _summary(args: argparse.Namespace) -> None:
    from qntoolkit.analysis import backend_score, best_qubits, worst_qubits
    from qntoolkit.characterization import backend_summary

    backend = _load(args.backend)

    print(backend_summary(backend))
    print(f"Backend Score         : {backend_score(backend):.1f}/100")
    print(f"Best qubits           : {best_qubits(backend, args.top)}")
    print(f"Worst qubits          : {worst_qubits(backend, args.top)}")


def _hotspots(args: argparse.Namespace) -> None:
    from qntoolkit.analysis import error_hotspots

    hotspots = error_hotspots(_load(args.backend), threshold=args.threshold)

    if hotspots.empty:
        print("No calibration outliers detected.")
        return

    print(hotspots.head(args.limit).to_string(index=False))


def _analyze(args: argparse.Namespace) -> None:
    from qntoolkit.analysis import analyse_circuit

    analysis = analyse_circuit(
        _load_circuit(args.circuit),
        _load(args.backend),
        optimization_level=args.optimization_level,
        seed_transpiler=args.seed,
        include_idle=args.idle,
    )
    print(analysis)


def _report(args: argparse.Namespace) -> None:
    from qntoolkit.reports import generate_backend_report

    generate_backend_report(_load(args.backend), output=args.output)
    print(f"Report written to {args.output}")


def _dashboard(args: argparse.Namespace) -> None:
    import matplotlib

    matplotlib.use("Agg")

    from qntoolkit.visualization import plot_calibration_dashboard

    plot_calibration_dashboard(_load(args.backend), filename=args.output)
    print(f"Dashboard written to {args.output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qntoolkit",
        description="Characterize, analyse and visualize noise on quantum hardware.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    backend_help = "backend name: ibm_*, fake_* or aer_simulator"

    command = commands.add_parser("backends", help="list available backends")
    command.add_argument("--fake", action="store_true", help="list offline fake backends")
    command.set_defaults(handler=_backends)

    command = commands.add_parser("summary", help="calibration summary and qubit ranking")
    command.add_argument("backend", help=backend_help)
    command.add_argument("--top", type=int, default=5, help="number of best/worst qubits")
    command.set_defaults(handler=_summary)

    command = commands.add_parser("hotspots", help="anomalous qubits and couplers")
    command.add_argument("backend", help=backend_help)
    command.add_argument("--threshold", type=float, default=3.5, help="robust z-score cut-off")
    command.add_argument("--limit", type=int, default=20, help="maximum rows to show")
    command.set_defaults(handler=_hotspots)

    command = commands.add_parser("analyze", help="estimate a circuit's success probability")
    command.add_argument("circuit", help="OpenQASM 2 or 3 file")
    command.add_argument("backend", help=backend_help)
    command.add_argument("--idle", action="store_true", help="include idle-qubit decoherence")
    command.add_argument("--optimization-level", type=int, default=1, choices=range(4))
    command.add_argument("--seed", type=int, default=None, help="transpiler seed")
    command.set_defaults(handler=_analyze)

    command = commands.add_parser("report", help="write a backend report")
    command.add_argument("backend", help=backend_help)
    command.add_argument(
        "-o", "--output", default="backend_report.md", help=".md, .html, .json or .csv file"
    )
    command.set_defaults(handler=_report)

    command = commands.add_parser("dashboard", help="write a calibration dashboard image")
    command.add_argument("backend", help=backend_help)
    command.add_argument("-o", "--output", default="dashboard.png", help="image file")
    command.set_defaults(handler=_dashboard)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    from qntoolkit.utils.exceptions import QNToolkitError

    try:
        args.handler(args)
    except (QNToolkitError, FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
