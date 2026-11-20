"""Plain data types shared by core, web and bot."""

from __future__ import annotations

import dataclasses
import datetime as dt
from typing import Any, Literal

Confidence = Literal["high", "medium", "low"]
Decision = Literal["irrigate", "wait"]
KcbSource = Literal["satellite", "table"]


@dataclasses.dataclass(frozen=True)
class Observation:
    """One cloud-screened field-mean NDVI value."""

    date: dt.date
    ndvi: float
    valid_fraction: float
    item_id: str
    cloud_cover: float | None = None


@dataclasses.dataclass(frozen=True)
class WeatherDay:
    date: dt.date
    et0_mm: float
    rain_mm: float
    is_forecast: bool = False


@dataclasses.dataclass(frozen=True)
class AdviceResult:
    """The single advice object rendered by web, bot and API."""

    computed_on: dt.date
    decision: Decision
    irrigate_mm: float
    m3_per_ha: float
    depletion_mm: float
    raw_mm: float
    taw_mm: float
    kcb: float
    kcb_source: KcbSource
    last_clear_days: int | None
    confidence: Confidence
    rain_next_3d_mm: float
    crop_id: str
    pipeline_version: str
    params_hash: str
    observation_dates: tuple[str, ...]
    assumptions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = dataclasses.asdict(self)
        data["computed_on"] = self.computed_on.isoformat()
        data["observation_dates"] = list(self.observation_dates)
        data["assumptions"] = list(self.assumptions)
        return data
