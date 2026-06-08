"""Dutch mortgage loan-tape schema — Pydantic v2.

This module is the contract between all analytics, validation, and ECL paths.
Every field has a regulatory rationale documented in ``docs/domain-primer.md``.

TODO Day 1 AM #1: replace this placeholder with the full schema covering
§2.1–§2.4 of the plan (borrower, contract, collateral, credit-risk, affordability).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class IFRS9Stage(str, Enum):
    """IFRS 9 staging.

    Stage 1: performing (12-month ECL).
    Stage 2: SICR — significant increase in credit risk (lifetime ECL).
    Stage 3: credit-impaired (lifetime ECL).
    """

    ONE = "1"
    TWO = "2"
    THREE = "3"


class LoanPlaceholder(BaseModel):
    """PLACEHOLDER schema — replaced in Day 1 AM #1.

    Exists so ``import loan_tape`` and a smoke test succeed from day 0.
    """

    loan_id: str = Field(..., description="Primary key")
    ifrs9_stage: IFRS9Stage = Field(default=IFRS9Stage.ONE)
