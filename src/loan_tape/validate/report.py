"""Validation report renderer — HTML output grouped by severity + BCBS 239.

The renderer takes a ``ValidationReport`` aggregate (findings + AnaCredit
conformance + summary metadata) and emits a standalone HTML document suitable
for the Streamlit page (Day 1/2 PM #3) or for archiving under
``docs/sample-reports/<tape>-<date>.html``.

Design:

- Pure-Python, no external templating engine dependency at runtime
  (jinja2 is already in deps but we keep this module standalone so the
  Streamlit page can re-use it without surprises).
- One inline ``<style>`` block; no external CSS.
- Findings grouped by Severity, then by BCBS 239 dimension within each.
- Every finding shows: rule_name, regulation citation, loan_id, message.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from loan_tape.validate.rules import RuleResult, Severity

# ---------------------------------------------------------------------------
# Report aggregate
# ---------------------------------------------------------------------------


_SEVERITY_ORDER: tuple[Severity, ...] = (
    Severity.CRITICAL,
    Severity.HIGH,
    Severity.MEDIUM,
    Severity.LOW,
)

_BCBS239_ORDER: tuple[str, ...] = ("accuracy", "completeness", "timeliness", "integrity")

_SEVERITY_COLOR: dict[Severity, str] = {
    Severity.CRITICAL: "#b91c1c",  # red-700
    Severity.HIGH: "#c2410c",  # orange-700
    Severity.MEDIUM: "#a16207",  # yellow-700
    Severity.LOW: "#15803d",  # green-700
}


@dataclass(frozen=True)
class ValidationReport:
    """Aggregate of every validation output for a single tape run."""

    tape_id: str
    reference_date: date
    total_loans: int
    findings: list[RuleResult] = field(default_factory=list)
    anacredit_conformance: float = 0.0

    # ---- summaries -----------------------------------------------------

    def findings_by_severity(self) -> dict[Severity, int]:
        out = {s: 0 for s in Severity}
        for f in self.findings:
            out[f.severity] += 1
        return out

    def findings_by_bcbs239(self) -> dict[str, list[RuleResult]]:
        out: dict[str, list[RuleResult]] = {d: [] for d in _BCBS239_ORDER}
        for f in self.findings:
            out.setdefault(f.bcbs239_dimension, []).append(f)
        return out

    def findings_at(self, severity: Severity) -> list[RuleResult]:
        return [f for f in self.findings if f.severity == severity]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _summary_card(label: str, value: str, color: str = "#1e293b") -> str:
    return (
        f'<div class="card" style="border-left:4px solid {color};">'
        f'<div class="card-label">{_esc(label)}</div>'
        f'<div class="card-value">{_esc(value)}</div>'
        "</div>"
    )


def _findings_table(findings: list[RuleResult], limit: int = 50) -> str:
    if not findings:
        return '<p class="empty">No findings in this group.</p>'
    rows = []
    for f in findings[:limit]:
        rows.append(
            "<tr>"
            f"<td>{_esc(f.rule_name)}</td>"
            f"<td>{_esc(f.loan_id)}</td>"
            f"<td>{_esc(f.regulation)}</td>"
            f"<td>{_esc(f.message)}</td>"
            "</tr>"
        )
    truncated = (
        f'<p class="truncated">Showing first {limit} of {len(findings)} findings.</p>'
        if len(findings) > limit
        else ""
    )
    return (
        '<table class="findings">'
        "<thead><tr>"
        "<th>Rule</th><th>Loan</th><th>Regulation</th><th>Detail</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>" + truncated
    )


def render_html(report: ValidationReport) -> str:
    """Render the report as a complete HTML5 document."""
    severity_counts = report.findings_by_severity()
    bcbs239_groups = report.findings_by_bcbs239()
    conformance_pct = f"{report.anacredit_conformance * 100:.2f}%"

    summary_cards = "".join(
        [
            _summary_card("Tape", report.tape_id),
            _summary_card("Reference date", str(report.reference_date)),
            _summary_card("Loans validated", f"{report.total_loans:,}"),
            _summary_card("AnaCredit conformance", conformance_pct),
        ]
    )

    severity_cards = "".join(
        _summary_card(
            sev.value,
            f"{severity_counts.get(sev, 0):,}",
            color=_SEVERITY_COLOR[sev],
        )
        for sev in _SEVERITY_ORDER
    )

    severity_sections = []
    for sev in _SEVERITY_ORDER:
        items = report.findings_at(sev)
        if not items:
            continue
        severity_sections.append(
            f'<section class="severity-section" data-severity="{sev.value}">'
            f'<h3 style="color:{_SEVERITY_COLOR[sev]};">{sev.value} '
            f"<span class=\"count\">({len(items)})</span></h3>"
            f"{_findings_table(items)}"
            "</section>"
        )
    severity_html = (
        "".join(severity_sections)
        or '<p class="empty">No findings of any severity.</p>'
    )

    bcbs239_sections = []
    for dim in _BCBS239_ORDER:
        items = bcbs239_groups.get(dim, [])
        bcbs239_sections.append(
            f'<section class="bcbs239-section" data-dimension="{dim}">'
            f"<h3>{_esc(dim.title())} <span class=\"count\">({len(items)})</span></h3>"
            f"{_findings_table(items, limit=25)}"
            "</section>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Validation Report — {_esc(report.tape_id)}</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #0f172a; background: #f8fafc; margin: 0; padding: 24px;
  }}
  h1 {{ margin-top: 0; }}
  .cards {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 16px 0 24px; }}
  .card {{
    background: white; padding: 12px 16px; min-width: 160px;
    border-radius: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
  }}
  .card-label {{ font-size: 12px; color: #64748b; text-transform: uppercase; }}
  .card-value {{ font-size: 22px; font-weight: 600; margin-top: 4px; }}
  section {{ background: white; padding: 16px; border-radius: 6px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05); margin-bottom: 16px; }}
  h3 .count {{ color: #64748b; font-weight: 400; font-size: 14px; }}
  table.findings {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  table.findings th, table.findings td {{
    text-align: left; padding: 6px 8px; border-bottom: 1px solid #e2e8f0;
  }}
  table.findings th {{ color: #475569; font-weight: 600; }}
  .empty {{ color: #64748b; font-style: italic; }}
  .truncated {{ color: #64748b; font-size: 12px; margin-top: 8px; }}
  .group-heading {{ margin-top: 32px; }}
</style>
</head>
<body>
  <h1>Validation Report</h1>
  <p>BCBS 239 + AnaCredit + Dutch mortgage rules. See
    <code>docs/regulation-map.md</code> for citations.</p>

  <h2 class="group-heading">Summary</h2>
  <div class="cards">{summary_cards}</div>
  <div class="cards">{severity_cards}</div>

  <h2 class="group-heading">Findings by Severity</h2>
  {severity_html}

  <h2 class="group-heading">Findings by BCBS 239 Dimension</h2>
  {''.join(bcbs239_sections)}

  <h2 class="group-heading">AnaCredit Conformance</h2>
  <p>Conformance share across the tape: <strong>{conformance_pct}</strong>.
     Required attributes and enumerations per ECB Regulation 2016/867 Annex II;
     full crosswalk in <code>docs/appendix/anacredit-mapping.md</code>.</p>

  <hr>
  <p style="font-size:12px;color:#64748b;">
    Generated by the loan-tape validation engine.
    Synthetic data only — no PII (GDPR-clear).
    Tool out of EU AI Act Annex III §5(b) scope (analytics, not creditworthiness scoring).
  </p>
</body>
</html>
"""


def write_html(report: ValidationReport, out_path: Path) -> Path:
    """Render and write the report to disk. Returns the path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_html(report), encoding="utf-8")
    return out_path


__all__ = ["ValidationReport", "render_html", "write_html"]
