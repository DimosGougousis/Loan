"""Day-0 smoke test. Keeps CI green from the first commit.

Replaced/superseded by real unit tests as Day 1+ tasks land.
"""

from __future__ import annotations

import loan_tape
from loan_tape.schema import IFRS9Stage, LoanPlaceholder


def test_package_imports() -> None:
    """The library imports and reports a version."""
    assert isinstance(loan_tape.__version__, str)
    assert loan_tape.__version__.count(".") == 2


def test_ifrs9_stage_enum() -> None:
    """IFRS 9 stage enum has the three expected stages."""
    assert IFRS9Stage.ONE.value == "1"
    assert IFRS9Stage.TWO.value == "2"
    assert IFRS9Stage.THREE.value == "3"


def test_loan_placeholder_constructs() -> None:
    """The placeholder schema accepts a minimal loan."""
    loan = LoanPlaceholder(loan_id="LN-0001")
    assert loan.loan_id == "LN-0001"
    assert loan.ifrs9_stage == IFRS9Stage.ONE
