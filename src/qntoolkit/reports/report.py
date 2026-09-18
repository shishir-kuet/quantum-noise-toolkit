"""
Structured reports rendered to Markdown, HTML, JSON or CSV.

A :class:`Report` is a title plus a list of sections; each section holds
key/value facts and/or a table (a pandas DataFrame). The same report can
be rendered to any supported format.
"""

from __future__ import annotations

import html
import json
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

FORMATS = ("markdown", "html", "json", "csv")

EXTENSIONS = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".html": "html",
    ".htm": "html",
    ".json": "json",
    ".csv": "csv",
}


def _plain(value):
    """Convert numpy/pandas scalars and containers to JSON-friendly values."""

    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]

    if isinstance(value, np.generic):
        value = value.item()

    if isinstance(value, float) and math.isnan(value):
        return None

    return value


def _format_value(value) -> str:
    value = _plain(value)

    if value is None:
        return "n/a"

    if isinstance(value, float):
        if value == 0 or 1e-3 <= abs(value) < 1e5:
            return f"{value:.4g}"
        return f"{value:.3e}"

    if isinstance(value, dict):
        return ", ".join(f"{key}: {_format_value(item)}" for key, item in value.items())

    if isinstance(value, list):
        return ", ".join(_format_value(item) for item in value)

    return str(value)


@dataclass
class ReportSection:
    title: str
    facts: dict = field(default_factory=dict)
    table: pd.DataFrame | None = None
    text: str | None = None
    # The primary section's table is what the CSV export contains.
    primary: bool = False


@dataclass
class Report:
    title: str
    sections: list[ReportSection] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    )

    def add_section(self, title: str, **kwargs) -> ReportSection:
        section = ReportSection(title, **kwargs)
        self.sections.append(section)
        return section

    # ------------------------------------------------------------------
    # Renderers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "generated_at": self.generated_at,
            "sections": [
                {
                    "title": section.title,
                    **({"text": section.text} if section.text else {}),
                    **({"facts": _plain(section.facts)} if section.facts else {}),
                    **(
                        {"table": _plain(_frame(section.table).to_dict(orient="records"))}
                        if section.table is not None
                        else {}
                    ),
                }
                for section in self.sections
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", "", f"_Generated {self.generated_at}_", ""]

        for section in self.sections:
            lines += [f"## {section.title}", ""]

            if section.text:
                lines += [section.text, ""]

            if section.facts:
                lines += ["| Property | Value |", "|---|---|"]
                lines += [
                    f"| {key} | {_format_value(value)} |" for key, value in section.facts.items()
                ]
                lines.append("")

            if section.table is not None:
                lines += [_markdown_table(section.table), ""]

        return "\n".join(lines)

    def to_html(self) -> str:
        body = [
            f"<h1>{html.escape(self.title)}</h1>",
            f'<p class="meta">Generated {html.escape(self.generated_at)}</p>',
        ]

        for section in self.sections:
            body.append(f"<section><h2>{html.escape(section.title)}</h2>")

            if section.text:
                body.append(f"<p>{html.escape(section.text)}</p>")

            if section.facts:
                rows = "".join(
                    f"<tr><th>{html.escape(str(key))}</th>"
                    f"<td>{html.escape(_format_value(value))}</td></tr>"
                    for key, value in section.facts.items()
                )
                body.append(f'<table class="facts"><tbody>{rows}</tbody></table>')

            if section.table is not None:
                body.append(_html_table(section.table))

            body.append("</section>")

        return _HTML_TEMPLATE.format(
            title=html.escape(self.title),
            body="\n".join(body),
        )

    def to_csv(self) -> str:
        """CSV export.

        Contains the primary section's table if there is one, else the only
        table of the report, else all key/value facts in long format.
        """

        tables = [section for section in self.sections if section.table is not None]
        primary = [section for section in tables if section.primary]

        if primary or len(tables) == 1:
            return _frame((primary or tables)[0].table).to_csv(index=False)

        facts = [
            {"section": section.title, "property": key, "value": _format_value(value)}
            for section in self.sections
            for key, value in section.facts.items()
        ]

        return pd.DataFrame(facts, columns=["section", "property", "value"]).to_csv(index=False)

    def render(self, fmt: str = "markdown") -> str:
        fmt = fmt.lower()

        renderers = {
            "markdown": self.to_markdown,
            "md": self.to_markdown,
            "html": self.to_html,
            "json": self.to_json,
            "csv": self.to_csv,
        }

        if fmt not in renderers:
            raise ValueError(f"Unknown report format '{fmt}'. Choose from {FORMATS}.")

        return renderers[fmt]()

    def save(self, output: str | Path, fmt: str | None = None) -> str:
        """Render and write the report. The format is inferred from the
        file extension unless ``fmt`` is given. Returns the rendered text."""

        path = Path(output)
        fmt = fmt or EXTENSIONS.get(path.suffix.lower())

        if fmt is None:
            raise ValueError(
                f"Cannot infer report format from '{path.name}'. "
                f"Use one of {sorted(EXTENSIONS)} or pass fmt."
            )

        content = self.render(fmt)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        return content

    def __str__(self) -> str:
        return self.to_markdown()


def _frame(table: pd.DataFrame) -> pd.DataFrame:
    """Turn a named index into a column; drop anonymous range indexes."""

    return table.reset_index() if table.index.name else table.reset_index(drop=True)


def _cell(value) -> str:
    return _format_value(value).replace("|", "\\|")


def _markdown_table(table: pd.DataFrame) -> str:
    frame = _frame(table)
    header = "| " + " | ".join(str(column) for column in frame.columns) + " |"
    divider = "|" + "---|" * len(frame.columns)
    rows = [
        "| " + " | ".join(_cell(value) for value in row) + " |"
        for row in frame.itertuples(index=False)
    ]

    return "\n".join([header, divider, *rows])


def _html_table(table: pd.DataFrame) -> str:
    frame = _frame(table)
    head = "".join(f"<th>{html.escape(str(column))}</th>" for column in frame.columns)
    rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(_format_value(value))}</td>" for value in row) + "</tr>"
        for row in frame.itertuples(index=False)
    )

    return (
        f'<div class="scroll"><table class="data"><thead><tr>{head}</tr></thead>'
        f"<tbody>{rows}</tbody></table></div>"
    )


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --surface: #fcfcfb; --ink: #0b0b0b; --muted: #52514e;
    --rule: #e4e3df; --accent: #2a78d6;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --surface: #1a1a19; --ink: #ffffff; --muted: #c3c2b7;
             --rule: #383835; --accent: #3987e5; }}
  }}
  body {{ margin: 0; padding: 32px 16px; background: var(--surface); color: var(--ink);
         font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
  main {{ max-width: 1040px; margin: 0 auto; }}
  h1 {{ font-size: 1.7rem; margin: 0 0 4px; }}
  h2 {{ font-size: 1.15rem; margin: 32px 0 12px; padding-bottom: 6px;
        border-bottom: 2px solid var(--accent); }}
  .meta {{ color: var(--muted); margin: 0; }}
  .scroll {{ overflow-x: auto; }}
  table {{ border-collapse: collapse; font-variant-numeric: tabular-nums; }}
  th, td {{ padding: 5px 12px; border-bottom: 1px solid var(--rule); text-align: left; }}
  table.data th {{ color: var(--muted); font-weight: 600; white-space: nowrap; }}
  table.data td {{ white-space: nowrap; }}
  table.facts th {{ color: var(--muted); font-weight: 500; }}
</style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""
