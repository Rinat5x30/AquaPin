"""NDVI -> Kcb (no fitting).

Method (documented heuristic, NOT a published crop equation): scale field NDVI
between bare-soil and full-cover NDVI, then map linearly between the FAO-56
Table 17 Kcb_ini and Kcb_mid of the crop. NDVI_soil / NDVI_full are assumptions
(see crops.json); the backtest must test them.
"""

from __future__ import annotations

import datetime as dt

import numpy as np

from .crops import CropParams
from .types import Observation


def ndvi_to_kcb(ndvi: float, crop: CropParams) -> float:
    if not np.isfinite(ndvi):
        raise ValueError("ndvi must be finite")
    span = crop.ndvi_full - crop.ndvi_soil
    frac = float(np.clip((ndvi - crop.ndvi_soil) / span, 0.0, 1.0))
    return crop.kcb_ini + (crop.kcb_mid - crop.kcb_ini) * frac


def daily_kcb(
    observations: list[Observation], crop: CropParams, end: dt.date
) -> dict[dt.date, float]:
    """Linear interpolation between clear observations, held after the last one.

    Dates before the first observation are not returned (the model uses its table curve).
    """
    if not observations:
        return {}
    obs = sorted(observations, key=lambda o: o.date)
    first = obs[0].date
    xs = np.array([(o.date - first).days for o in obs], dtype=float)
    ys = np.array([ndvi_to_kcb(o.ndvi, crop) for o in obs], dtype=float)
    out: dict[dt.date, float] = {}
    day = first
    while day <= end:
        out[day] = float(np.interp((day - first).days, xs, ys))
        day += dt.timedelta(days=1)
    return out
