"""End-to-end advice: weather + satellite -> Kcb -> water balance -> AdviceResult."""

from __future__ import annotations

import dataclasses
import datetime as dt
from typing import Any, Protocol

from .confidence import confidence_from_age
from .crops import get_crop
from .errors import AquaPinError
from .geometry import validate_point
from .kc import daily_kcb
from .types import AdviceResult, KcbSource, Observation, WeatherDay
from .versioning import params_hash, pipeline_version
from .waterbalance import SOIL_ASSUMPTION, simulate_with_advice
from .weather import WeatherClient, ensure_fresh

RAIN_SKIP_FRACTION = 0.5  # skip irrigation if forecast 3-day rain covers this share of the deficit
FORECAST_DAYS = 3


class ObservationSource(Protocol):
    def observations(
        self, lat: float, lon: float, radius_m: float, start: dt.date, end: dt.date
    ) -> list[Observation]: ...


@dataclasses.dataclass
class PipelineResult:
    advice: AdviceResult
    observations: list[Observation]
    weather: list[WeatherDay]
    timeline: list[dict[str, Any]]
    irrigation_events: dict[str, float]


def _assumptions(planting: dt.date, kcb_source: str) -> tuple[str, ...]:
    items = [
        f"Soil: {SOIL_ASSUMPTION['note']} (theta_FC {SOIL_ASSUMPTION['theta_fc']}, "
        f"theta_WP {SOIL_ASSUMPTION['theta_wp']})",
        f"Planting date: {planting.isoformat()} (as provided)",
        "Water balance assumes only rain plus the irrigations advised earlier; "
        "your actual irrigation history is unknown",
        "NDVI to Kcb is an unfitted scaling heuristic; measured error is in the accuracy check",
    ]
    if kcb_source == "table":
        items.append("No clear satellite image: Kcb comes from the FAO-56 table curve")
    return tuple(items)


def compute_advice(
    *,
    lat: float,
    lon: float,
    radius_m: float,
    crop_id: str,
    planting_date: dt.date,
    today: dt.date,
    weather: WeatherClient,
    satellite: ObservationSource,
) -> PipelineResult:
    validate_point(lat, lon, radius_m)
    crop = get_crop(crop_id)
    if planting_date > today:
        raise AquaPinError("planting date is in the future")

    days = weather.fetch(lat, lon, planting_date, today + dt.timedelta(days=FORECAST_DAYS))
    ensure_fresh(days, today)
    obs = satellite.observations(lat, lon, radius_m, planting_date, today)
    kcb_map = daily_kcb(obs, crop, today)
    frame, events = simulate_with_advice(crop, days, planting_date, today, kcb_map, lat)

    row = frame.loc[today] if today in frame.index else frame.iloc[-1]
    raw, taw = float(row["raw"]), float(row["taw"])
    irrigated_today = float(events.get(today, 0.0))
    dr = float(row["dr"]) + irrigated_today  # depletion before today's irrigation
    rain_3d = sum(
        d.rain_mm for d in days if today < d.date <= today + dt.timedelta(days=FORECAST_DAYS)
    )
    needs = irrigated_today > 0.0
    irrigate_mm = irrigated_today
    if needs and rain_3d >= RAIN_SKIP_FRACTION * max(dr, 1.0):
        needs, irrigate_mm = False, 0.0

    last_obs = max((o.date for o in obs), default=None)
    age = (today - last_obs).days if last_obs else None
    source: KcbSource = "satellite" if obs else "table"
    advice = AdviceResult(
        computed_on=today,
        decision="irrigate" if needs else "wait",
        irrigate_mm=irrigate_mm,
        m3_per_ha=irrigate_mm * 10.0,
        depletion_mm=round(dr, 1),
        raw_mm=round(raw, 1),
        taw_mm=round(taw, 1),
        kcb=round(float(row["kcb"]), 3),
        kcb_source=source,
        last_clear_days=age,
        confidence=confidence_from_age(age),
        rain_next_3d_mm=round(rain_3d, 1),
        crop_id=crop_id,
        pipeline_version=pipeline_version(),
        params_hash=params_hash(crop_id),
        observation_dates=tuple(o.date.isoformat() for o in obs),
        assumptions=_assumptions(planting_date, source),
    )
    timeline = [
        {
            "date": d.isoformat(),
            "dr": round(float(r["dr"]), 1),
            "raw": round(float(r["raw"]), 1),
            "taw": round(float(r["taw"]), 1),
            "kcb": round(float(r["kcb"]), 3),
            "rain": round(float(r["rain"]), 1),
            "et0": round(float(r["et0"]), 1),
            "irrig": round(float(r["irrig"]), 1),
        }
        for d, r in frame.iterrows()
    ]
    return PipelineResult(
        advice=advice,
        observations=obs,
        weather=days,
        timeline=timeline,
        irrigation_events={d.isoformat(): v for d, v in events.items()},
    )
