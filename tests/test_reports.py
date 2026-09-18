import csv
import io
import json

import pytest

from qntoolkit.noise_models import (
    AmplitudeDamping,
    DepolarizingNoise,
    ReadoutNoise,
    noise_model_from_backend,
)
from qntoolkit.reports import (
    Report,
    generate_backend_report,
    generate_circuit_report,
    generate_noise_summary,
)


@pytest.mark.parametrize("extension", ["md", "html", "json", "csv"])
def test_backend_report_formats(manila, tmp_path, extension):
    output = tmp_path / f"report.{extension}"
    report = generate_backend_report(manila, output=output)

    assert isinstance(report, Report)
    content = output.read_text(encoding="utf-8")
    assert content

    if extension == "json":
        data = json.loads(content)
        assert data["title"] == "Backend report: fake_manila"
        titles = [section["title"] for section in data["sections"]]
        assert "Summary" in titles and "Qubit calibration" in titles
    elif extension == "csv":
        rows = list(csv.DictReader(io.StringIO(content)))
        assert len(rows) == 5
        assert "t1_us" in rows[0]
    elif extension == "html":
        assert content.startswith("<!DOCTYPE html>")
        assert "fake_manila" in content
    else:
        assert content.startswith("# Backend report: fake_manila")


def test_backend_report_lists_hotspots(fez):
    markdown = generate_backend_report(fez).to_markdown()

    assert "## Error hotspots" in markdown
    assert "cz_error" in markdown


def test_circuit_report(ghz, manila):
    report = generate_circuit_report(ghz, manila, seed_transpiler=1)
    markdown = report.to_markdown()

    assert "success probability" in markdown
    assert "Error budget" in markdown

    rows = list(csv.DictReader(io.StringIO(report.to_csv())))
    assert {"section", "property", "value"} <= set(rows[0])


def test_noise_summary_for_channels():
    report = generate_noise_summary(
        [DepolarizingNoise(0.01), AmplitudeDamping(0.05), ReadoutNoise(0.02)]
    )
    rows = report.to_dict()["sections"][0]["table"]

    assert len(rows) == 3
    assert rows[0]["average_gate_fidelity"] == pytest.approx(0.995)


def test_noise_summary_for_noise_model(manila):
    report = generate_noise_summary(noise_model_from_backend(manila))
    facts = report.to_dict()["sections"][0]["facts"]

    assert "cx" in facts["noisy_instructions"]


def test_unknown_extension(manila, tmp_path):
    with pytest.raises(ValueError):
        generate_backend_report(manila, output=tmp_path / "report.pdf")
