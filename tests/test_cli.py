import pytest

from qntoolkit.cli import main

GHZ_QASM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0], q[1];
cx q[1], q[2];
measure q -> c;
"""


def test_backends_fake(capsys):
    assert main(["backends", "--fake"]) == 0
    assert "fake_fez" in capsys.readouterr().out


def test_summary(capsys):
    assert main(["summary", "fake_manila", "--top", "2"]) == 0
    output = capsys.readouterr().out

    assert "fake_manila" in output
    assert "Backend Score" in output


def test_hotspots(capsys):
    assert main(["hotspots", "fake_fez", "--limit", "3"]) == 0
    assert "cz_error" in capsys.readouterr().out


def test_analyze_qasm(tmp_path, capsys):
    path = tmp_path / "ghz.qasm"
    path.write_text(GHZ_QASM, encoding="utf-8")

    assert main(["analyze", str(path), "fake_fez", "--seed", "1", "--idle"]) == 0
    assert "Success Probability" in capsys.readouterr().out


def test_report_and_dashboard(tmp_path):
    report = tmp_path / "report.html"
    image = tmp_path / "dashboard.png"

    assert main(["report", "fake_manila", "-o", str(report)]) == 0
    assert main(["dashboard", "fake_manila", "-o", str(image)]) == 0

    assert report.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")
    assert image.stat().st_size > 10_000


def test_errors_are_reported(capsys):
    assert main(["summary", "fake_does_not_exist"]) == 1
    assert "error:" in capsys.readouterr().err

    with pytest.raises(SystemExit):
        main(["not-a-command"])
