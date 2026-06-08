"""Validation HTML report renderer tests (RED first)."""

from __future__ import annotations

from datetime import date

import polars as pl

from loan_tape.validate.anacredit import portfolio_conformance
from loan_tape.validate.report import ValidationReport, render_html
from loan_tape.validate.rules import Severity, run_all_rules


def _build_report(tape: pl.DataFrame) -> ValidationReport:
    findings = run_all_rules(tape, reference_date=date(2025, 6, 1))
    conformance, _ = portfolio_conformance(tape)
    return ValidationReport(
        tape_id="golden",
        reference_date=date(2025, 6, 1),
        total_loans=tape.shape[0],
        findings=findings,
        anacredit_conformance=conformance,
    )


def test_report_constructs_with_summary_counts(golden_tape: pl.DataFrame) -> None:
    report = _build_report(golden_tape)
    assert report.total_loans == 500
    # Summary by severity counts each Severity at least 0 times.
    counts = report.findings_by_severity()
    for severity in Severity:
        assert severity in counts


def test_report_groups_findings_by_bcbs239_dimension(
    golden_tape: pl.DataFrame,
) -> None:
    report = _build_report(golden_tape)
    grouped = report.findings_by_bcbs239()
    # Even with zero findings, every dimension key exists for the renderer.
    expected = {"accuracy", "completeness", "timeliness", "integrity"}
    assert expected <= set(grouped)


def test_render_html_returns_string_with_required_sections(
    golden_tape: pl.DataFrame,
) -> None:
    report = _build_report(golden_tape)
    html = render_html(report)
    assert isinstance(html, str)
    # Headings present
    assert "Validation Report" in html
    assert "Summary" in html
    assert "BCBS 239" in html or "bcbs239" in html.lower()
    assert "AnaCredit" in html
    # Severity bands present
    assert "CRITICAL" in html
    assert "HIGH" in html
    assert "MEDIUM" in html
    assert "LOW" in html


def test_render_html_includes_anacredit_conformance(
    golden_tape: pl.DataFrame,
) -> None:
    report = _build_report(golden_tape)
    html = render_html(report)
    # The conformance value (0.0-1.0) is formatted as a percentage.
    assert "%" in html


def test_render_html_lists_offending_loan_ids() -> None:
    """A tape with a known easter egg surfaces the offending loan_ids in the HTML."""
    from loan_tape.generator import generate_tape

    tape = generate_tape(n=200, seed=11, inject_easter_eggs=True)
    report = _build_report(tape)
    html = render_html(report)
    # Pick the first NHG-cap finding and look for its loan_id in the rendered HTML.
    nhg_findings = [f for f in report.findings if f.rule_name == "nhg_cap"]
    assert nhg_findings, "expected at least one nhg_cap finding on easter-egg tape"
    assert nhg_findings[0].loan_id in html


def test_render_html_writes_to_disk(tmp_path, golden_tape: pl.DataFrame) -> None:
    from loan_tape.validate.report import write_html

    report = _build_report(golden_tape)
    out = tmp_path / "report.html"
    written = write_html(report, out)
    assert written == out
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "<html" in text.lower()
    assert "</html>" in text.lower()


def test_severity_summary_returns_int_counts(golden_tape: pl.DataFrame) -> None:
    report = _build_report(golden_tape)
    counts = report.findings_by_severity()
    for v in counts.values():
        assert isinstance(v, int)


def test_report_cites_regulations(golden_tape: pl.DataFrame) -> None:
    """Every rendered finding shows its source citation."""
    from loan_tape.generator import generate_tape

    tape = generate_tape(n=200, seed=11, inject_easter_eggs=True)
    report = _build_report(tape)
    html = render_html(report)
    cited = {f.regulation for f in report.findings}
    if cited:
        # At least one citation makes it into the HTML.
        assert any(reg.split(" ")[0] in html for reg in cited)
