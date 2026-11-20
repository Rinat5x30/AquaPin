"""Confidence level from the age of the last clear satellite observation.

Thresholds are initial assumptions (Sentinel-2 revisit is a few days); they are
to be calibrated by the backtest, not tuned by hand.
"""

from __future__ import annotations

from .types import Confidence

HIGH_MAX_DAYS = 7
MEDIUM_MAX_DAYS = 14


def confidence_from_age(days: int | None) -> Confidence:
    if days is None or days < 0:
        return "low"
    if days <= HIGH_MAX_DAYS:
        return "high"
    if days <= MEDIUM_MAX_DAYS:
        return "medium"
    return "low"
