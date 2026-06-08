"""Eval runner — discovers rubrics under ``evals/rubrics/`` and runs paired pytest cases.

Usage::

    uv run python evals/runner.py
    uv run python evals/runner.py --rubric stress_scenario

Output: dated report under ``evals/results/<YYYY-MM-DD-HHMMSS>.md``.

TODO Day 1 PM #3 / Day 2 AM #3 / Day 2 MID #3: implement full runner once rubrics land.
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUBRICS_DIR = ROOT / "evals" / "rubrics"
RESULTS_DIR = ROOT / "evals" / "results"


def discover_rubrics() -> list[Path]:
    """Discover all rubric markdown files."""
    return sorted(p for p in RUBRICS_DIR.glob("*.md") if not p.name.startswith("_"))


def run_rubric(rubric: Path) -> tuple[bool, str]:
    """Run the pytest case paired to a rubric.

    Convention: rubric ``evals/rubrics/<name>.md`` is paired with
    ``tests/eval/test_<name>.py`` (or ``tests/integration/test_<name>.py``).
    Returns (passed, output).
    """
    name = rubric.stem
    candidates = [
        ROOT / "tests" / "eval" / f"test_{name}.py",
        ROOT / "tests" / "integration" / f"test_{name}.py",
    ]
    target = next((c for c in candidates if c.exists()), None)
    if target is None:
        return False, f"No paired pytest case found for rubric '{name}'."

    result = subprocess.run(  # noqa: S603
        ["uv", "run", "pytest", str(target), "-q", "--tb=short"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    return result.returncode == 0, result.stdout + result.stderr


def write_report(rubrics: list[Path], results: list[tuple[bool, str]]) -> Path:
    """Write the dated eval report."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d-%H%M%S")
    report = RESULTS_DIR / f"{timestamp}.md"

    passed = sum(1 for ok, _ in results if ok)
    total = len(results)

    lines = [
        f"# Eval results — {timestamp} UTC",
        "",
        f"**Summary:** {passed} / {total} rubrics passed.",
        "",
    ]
    for rubric, (ok, output) in zip(rubrics, results, strict=True):
        status = "✅ PASS" if ok else "❌ FAIL"
        lines.extend(
            [
                f"## {rubric.stem} — {status}",
                "",
                "```",
                output.strip() or "(no output)",
                "```",
                "",
            ]
        )

    report.write_text("\n".join(lines), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run eval rubrics for the loan-tape analyzer.")
    parser.add_argument(
        "--rubric", type=str, default=None, help="Run only the named rubric (without .md)."
    )
    args = parser.parse_args(argv)

    rubrics = discover_rubrics()
    if args.rubric is not None:
        rubrics = [r for r in rubrics if r.stem == args.rubric]
        if not rubrics:
            print(f"No rubric named '{args.rubric}'.", file=sys.stderr)
            return 2

    if not rubrics:
        print("No rubrics discovered. Add files under evals/rubrics/*.md", file=sys.stderr)
        return 0  # not an error on day 0

    results = [run_rubric(r) for r in rubrics]
    report = write_report(rubrics, results)

    failed = [r.stem for r, (ok, _) in zip(rubrics, results, strict=True) if not ok]
    print(f"Report: {report}")
    if failed:
        print(f"Failed rubrics: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
