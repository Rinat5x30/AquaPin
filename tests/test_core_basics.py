"""Geometry, crops (with FAO-56 regression against pyfao56), kc, confidence."""

from __future__ import annotations

import datetime as dt
import json
import math

import numpy as np
import pytest
from pyfao56.tools import FAO56Tables

from aquapin_core import crops as crops_mod
from aquapin_core.confidence import confidence_from_age
from aquapin_core.crops import get_crop, list_crops
from aquapin_core.errors import CropParamsError, GeometryError
from aquapin_core.geometry import circle_mask, validate_point, window_bbox
from aquapin_core.kc import daily_kcb, ndvi_to_kcb
from aquapin_core.types import Observation


@pytest.mark.parametrize("lat,lon,r", [(40, 49, 150), (-10, 120, 30), (60, 10, 500)])
def test_validate_point_accepts(lat: float, lon: float, r: float) -> None:
    validate_point(lat, lon, r)


@pytest.mark.parametrize(
    "lat,lon,r",
    [
        (91, 0, 100),
        (0, 181, 100),
        (80, 0, 100),
        (40, 49, 10),
        (40, 49, 5000),
        (math.nan, 0, 100),
        (0, math.inf, 100),
    ],
)
def test_validate_point_rejects(lat: float, lon: float, r: float) -> None:
    with pytest.raises(GeometryError):
        validate_point(lat, lon, r)


def test_window_bbox_is_centred_and_larger_than_field() -> None:
    w, s, e, n = window_bbox(40.0, 49.0, 200.0)
    assert w < 49.0 < e and s < 40.0 < n
    assert (n - s) * 111_320 == pytest.approx(2 * 200 * 3, rel=0.01)


def test_circle_mask_area() -> None:
    mask = circle_mask((101, 101), 250.0, 10.0)
    assert mask.sum() == pytest.approx(math.pi * 25**2, rel=0.05)
    assert mask[50, 50] and not mask[0, 0]


def test_every_crop_value_has_a_source() -> None:
    for crop_id in list_crops():
        entry = json.loads(crops_mod._PATH.read_text(encoding="utf-8"))["crops"][crop_id]
        for key, item in entry.items():
            if key != "name":
                assert item["source"], f"{crop_id}.{key} has no source"


def test_crop_without_source_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    broken = {"version": "x", "crops": {"c": {"name": "c"}}}
    monkeypatch.setattr(crops_mod, "_load", lambda: broken)
    with pytest.raises(CropParamsError):
        get_crop("c")


def test_unknown_crop() -> None:
    with pytest.raises(CropParamsError):
        get_crop("banana")


def test_wheat_matches_fao56_tables_via_pyfao56() -> None:
    """Regression: our copied FAO-56 values must equal the pyfao56 packaged tables."""
    t = FAO56Tables()
    crop = get_crop("winter_wheat")
    row17 = t.table17[t.table17["Crop"] == "winter wheat"].iloc[0]
    assert (crop.kcb_ini, crop.kcb_mid, crop.kcb_end) == (
        float(row17["Kcbini"]),
        float(row17["Kcbmid"]),
        float(row17["Kcbend"]),
    )
    row22 = t.table22[t.table22["Crop"] == "winter wheat"].iloc[0]
    assert crop.root_max_m == float(row22["Zrmax1"]) and crop.p_base == float(row22["pbase"])
    row12 = t.table12[t.table12["Crop"] == "winter wheat non-frozen soils"].iloc[0]
    assert (crop.kcm_ini, crop.kcm_mid, crop.kcm_end) == (
        float(row12["Kcmini"]),
        float(row12["Kcmmid"]),
        float(row12["Kcmend"]),
    )
    row11 = t.table11[
        (t.table11["Crop"] == "winter wheat") & (t.table11["Region"] == "mediterranean")
    ].iloc[0]
    assert crop.stage_days == {
        "ini": int(row11["Lini"]),
        "dev": int(row11["Ldev"]),
        "mid": int(row11["Lmid"]),
        "late": int(row11["Llate"]),
    }


def test_ndvi_to_kcb_endpoints_and_monotonic() -> None:
    crop = get_crop("winter_wheat")
    assert ndvi_to_kcb(0.0, crop) == pytest.approx(crop.kcb_ini)
    assert ndvi_to_kcb(0.99, crop) == pytest.approx(crop.kcb_mid)
    values = [ndvi_to_kcb(x, crop) for x in np.linspace(0, 1, 21)]
    assert values == sorted(values)


def test_ndvi_to_kcb_rejects_nan() -> None:
    with pytest.raises(ValueError):
        ndvi_to_kcb(float("nan"), get_crop("winter_wheat"))


def test_daily_kcb_interpolates_and_holds() -> None:
    crop = get_crop("winter_wheat")
    d0 = dt.date(2026, 1, 1)
    obs = [Observation(d0, 0.15, 1.0, "a"), Observation(d0 + dt.timedelta(days=10), 0.85, 1.0, "b")]
    out = daily_kcb(obs, crop, d0 + dt.timedelta(days=15))
    assert out[d0] == pytest.approx(crop.kcb_ini)
    assert out[d0 + dt.timedelta(days=5)] == pytest.approx((crop.kcb_ini + crop.kcb_mid) / 2)
    assert out[d0 + dt.timedelta(days=15)] == pytest.approx(crop.kcb_mid)  # held after last obs
    assert daily_kcb([], crop, d0) == {}


@pytest.mark.parametrize(
    "age,expected",
    [
        (None, "low"),
        (0, "high"),
        (7, "high"),
        (8, "medium"),
        (14, "medium"),
        (15, "low"),
        (-1, "low"),
    ],
)
def test_confidence(age: int | None, expected: str) -> None:
    assert confidence_from_age(age) == expected
