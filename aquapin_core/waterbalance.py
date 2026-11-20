"""FAO-56 daily soil water balance via pyfao56 (physics is not reimplemented)."""

from __future__ import annotations

import datetime as dt
import math

import numpy as np
import pandas as pd
from pyfao56 import Irrigation, Model, Parameters, Update, Weather

from .crops import CropParams
from .errors import WeatherApiError
from .types import WeatherDay

# Soil is NOT measured: a generic loam-like default. Flagged in every advice.
SOIL_ASSUMPTION: dict[str, float | str] = {
    "theta_fc": 0.25,
    "theta_wp": 0.10,
    "theta0": 0.25,  # simulation starts at field capacity
    "note": "default loam-like soil, not measured",
}
_MAX_FILLED_GAP_DAYS = 5


def _key(day: dt.date) -> str:
    return f"{day.year}-{day.timetuple().tm_yday:03d}"


def _daterange(start: dt.date, end: dt.date) -> list[dt.date]:
    return [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]


def _complete_weather(
    days: list[WeatherDay], start: dt.date, end: dt.date
) -> dict[dt.date, WeatherDay]:
    by_date = {d.date: d for d in days if start <= d.date <= end}
    missing = [d for d in _daterange(start, end) if d not in by_date]
    if len(missing) > _MAX_FILLED_GAP_DAYS:
        raise WeatherApiError(f"{len(missing)} weather days missing in {start}..{end}")
    last: WeatherDay | None = None
    for day in _daterange(start, end):
        if day in by_date:
            last = by_date[day]
        else:
            et0 = last.et0_mm if last else 2.0
            by_date[day] = WeatherDay(date=day, et0_mm=et0, rain_mm=0.0)
    return by_date


def _parameters(crop: CropParams) -> Parameters:
    par = Parameters()
    par.Kcmini, par.Kcmmid, par.Kcmend = crop.kcm_ini, crop.kcm_mid, crop.kcm_end
    par.Kcbini, par.Kcbmid, par.Kcbend = crop.kcb_ini, crop.kcb_mid, crop.kcb_end
    par.Lini = crop.stage_days["ini"]
    par.Ldev = crop.stage_days["dev"]
    par.Lmid = crop.stage_days["mid"]
    par.Lend = crop.stage_days["late"]
    par.hmax = crop.height_max_m
    par.Zrmax = crop.root_max_m
    par.pbase = crop.p_base
    par.thetaFC = float(SOIL_ASSUMPTION["theta_fc"])
    par.thetaWP = float(SOIL_ASSUMPTION["theta_wp"])
    par.theta0 = float(SOIL_ASSUMPTION["theta0"])
    return par


def run_balance(
    crop: CropParams,
    weather: list[WeatherDay],
    planting: dt.date,
    end: dt.date,
    kcb_by_date: dict[dt.date, float] | None = None,
    irrigations: dict[dt.date, float] | None = None,
    lat: float = 40.0,
) -> pd.DataFrame:
    """Run the model planting..end. Returns daily rows indexed by date."""
    if end < planting:
        raise ValueError("end must not precede planting date")
    days = _complete_weather(weather, planting, end)
    wth = Weather()
    wth.z, wth.lat, wth.wndht = 100.0, float(lat), 2.0
    for day in _daterange(planting, end):
        w = days[day]
        wth.wdata.loc[_key(day)] = [np.nan] * 8 + [w.rain_mm, w.et0_mm, "M"]

    upd = Update()
    for day, kcb in (kcb_by_date or {}).items():
        if planting <= day <= end:
            upd.udata.loc[_key(day)] = [kcb, np.nan, np.nan]

    irr = Irrigation()
    for day, depth in (irrigations or {}).items():
        if planting <= day <= end and depth > 0:
            irr.idata.loc[_key(day)] = [depth, 1.0, 100.0]

    model = Model(_key(planting), _key(end), _parameters(crop), wth, irr=irr, upd=upd)
    model.run()
    odata = model.odata
    out = pd.DataFrame(
        {
            "et0": odata["ETref"].astype(float),
            "kcb": odata["Kcb"].astype(float),
            "etc": odata["ETc"].astype(float),
            "eta": odata["ETa"].astype(float),
            "taw": odata["TAW"].astype(float),
            "raw": odata["RAW"].astype(float),
            "dr": odata["Dr"].astype(float),
            "rain": odata["Rain"].astype(float),
            "irrig": odata["Irrig"].astype(float),
        }
    )
    out.index = [dt.date(int(k[:4]), 1, 1) + dt.timedelta(days=int(k[5:]) - 1) for k in odata.index]
    return out


def simulate_with_advice(
    crop: CropParams,
    weather: list[WeatherDay],
    planting: dt.date,
    end: dt.date,
    kcb_by_date: dict[dt.date, float] | None = None,
    lat: float = 40.0,
    max_events: int = 40,
) -> tuple[pd.DataFrame, dict[dt.date, float]]:
    """Season simulation where every advice (Dr >= RAW) is followed.

    Returns the final daily frame and the irrigation events that were applied.
    """
    events: dict[dt.date, float] = {}
    frame = run_balance(crop, weather, planting, end, kcb_by_date, events, lat)
    for _ in range(max_events):
        trigger = frame[(frame["dr"] >= frame["raw"]) & (frame["irrig"] <= 0.0)]
        if events:
            trigger = trigger[trigger.index > max(events)]
        if trigger.empty:
            break
        day = trigger.index[0]
        events[day] = float(math.ceil(float(frame.loc[day, "dr"])))
        frame = run_balance(crop, weather, planting, end, kcb_by_date, events, lat)
    return frame, events
