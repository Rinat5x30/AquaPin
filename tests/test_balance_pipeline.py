"""Water balance wrapper and the end-to-end pipeline with faked adapters."""

from __future__ import annotations

import datetime as dt

import pytest

from aquapin_core.crops import get_crop
from aquapin_core.errors import AquaPinError, GeometryError, StaleWeatherError, WeatherApiError
from aquapin_core.kc import daily_kcb
from aquapin_core.pipeline import compute_advice
from aquapin_core.types import Observation, WeatherDay
from aquapin_core.versioning import params_hash, pipeline_version
from aquapin_core.waterbalance import run_balance, simulate_with_advice

CROP = get_crop("winter_wheat")
P = dt.date(2025, 11, 1)


def wx(start: dt.date, end: dt.date, et0: float = 3.0, rain: float = 0.0) -> list[WeatherDay]:
    return [
        WeatherDay(start + dt.timedelta(days=i), et0, rain) for i in range((end - start).days + 1)
    ]


def test_dry_weather_depletes_monotonically() -> None:
    f = run_balance(CROP, wx(P, P + dt.timedelta(days=60)), P, P + dt.timedelta(days=60))
    assert f["dr"].iloc[-1] > f["dr"].iloc[0]
    assert (f["dr"].diff().dropna() >= -1e-9).all()


def test_rain_reduces_deficit() -> None:
    end = P + dt.timedelta(days=30)
    dry = run_balance(CROP, wx(P, end), P, end)
    wet = run_balance(CROP, wx(P, end, rain=2.0), P, end)
    assert wet["dr"].iloc[-1] < dry["dr"].iloc[-1]


def test_irrigation_reduces_deficit_by_its_depth() -> None:
    end = P + dt.timedelta(days=40)
    day = P + dt.timedelta(days=30)
    base = run_balance(CROP, wx(P, end), P, end)
    irr = run_balance(CROP, wx(P, end), P, end, irrigations={day: 10.0})
    assert base.loc[day, "dr"] - irr.loc[day, "dr"] == pytest.approx(10.0, abs=0.6)


def test_satellite_kcb_changes_result() -> None:
    end = P + dt.timedelta(days=80)
    obs = [Observation(P + dt.timedelta(days=i), 0.8, 1.0, "x") for i in (10, 40, 70)]
    table = run_balance(CROP, wx(P, end), P, end)
    sat = run_balance(CROP, wx(P, end), P, end, kcb_by_date=daily_kcb(obs, CROP, end))
    assert sat["kcb"].iloc[60] > table["kcb"].iloc[60]


def test_small_weather_gap_is_filled_big_gap_raises() -> None:
    end = P + dt.timedelta(days=20)
    days = [d for d in wx(P, end) if d.date not in {P + dt.timedelta(days=5)}]
    assert len(run_balance(CROP, days, P, end)) == 21
    sparse = wx(P, P + dt.timedelta(days=3))
    with pytest.raises(WeatherApiError):
        run_balance(CROP, sparse, P, end)


def test_end_before_planting() -> None:
    with pytest.raises(ValueError):
        run_balance(CROP, wx(P, P), P, P - dt.timedelta(days=1))


def test_simulate_with_advice_irrigates_when_deficit_reaches_raw() -> None:
    end = P + dt.timedelta(days=150)
    frame, events = simulate_with_advice(CROP, wx(P, end, et0=4.0), P, end)
    assert events, "a long dry spell must trigger advice"
    for day in events:
        assert frame.loc[day, "irrig"] > 0


def run(fake_weather, fake_satellite, **over):  # type: ignore[no-untyped-def]
    today = over.pop("today", dt.date(2026, 3, 1))
    kw = dict(
        lat=40.0,
        lon=49.0,
        radius_m=150.0,
        crop_id="winter_wheat",
        planting_date=P,
        today=today,
        weather=fake_weather(et0=3.0, today=today),
        satellite=fake_satellite(),
    )
    kw.update(over)
    return compute_advice(**kw)  # type: ignore[arg-type]


def test_pipeline_without_satellite_is_low_confidence_table_kcb(fake_weather, fake_satellite) -> None:  # type: ignore[no-untyped-def]
    res = run(fake_weather, fake_satellite)
    a = res.advice
    assert a.kcb_source == "table" and a.confidence == "low" and a.last_clear_days is None
    assert any("table curve" in s for s in a.assumptions)  # the fallback is never silent
    assert a.pipeline_version and a.params_hash == params_hash("winter_wheat")


def test_pipeline_with_recent_satellite_is_high_confidence(fake_weather, fake_satellite) -> None:  # type: ignore[no-untyped-def]
    today = dt.date(2026, 3, 1)
    obs = [Observation(today - dt.timedelta(days=d), 0.6, 1.0, f"i{d}") for d in (40, 20, 3)]
    res = run(fake_weather, lambda: fake_satellite(obs), today=today)
    a = res.advice
    assert a.kcb_source == "satellite" and a.confidence == "high" and a.last_clear_days == 3
    assert a.observation_dates == tuple(
        o.date.isoformat() for o in sorted(obs, key=lambda o: o.date)
    )
    assert a.m3_per_ha == a.irrigate_mm * 10


def test_pipeline_forecast_rain_cancels_irrigation(fake_weather, fake_satellite) -> None:  # type: ignore[no-untyped-def]
    today = next(
        d
        for d in (dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range(90))
        if run(
            fake_weather, fake_satellite, today=d, weather=fake_weather(et0=4.0, today=d)
        ).advice.decision
        == "irrigate"
    )
    dry = run(fake_weather, fake_satellite, today=today, weather=fake_weather(et0=4.0, today=today))
    assert dry.advice.decision == "irrigate"
    rainy = fake_weather(et0=4.0, today=today)
    original = rainy.fetch

    def fetch(lat, lon, start, end):  # type: ignore[no-untyped-def]
        return [
            WeatherDay(d.date, d.et0_mm, 100.0 if d.is_forecast else d.rain_mm, d.is_forecast)
            for d in original(lat, lon, start, end)
        ]

    rainy.fetch = fetch  # type: ignore[method-assign]
    wet = run(fake_weather, fake_satellite, today=today, weather=rainy)
    assert wet.advice.decision == "wait" and wet.advice.rain_next_3d_mm >= 300


def test_pipeline_refuses_stale_weather(fake_weather, fake_satellite) -> None:  # type: ignore[no-untyped-def]
    today = dt.date(2026, 3, 1)
    stale = fake_weather(today=today, last_observed=today - dt.timedelta(days=6))
    with pytest.raises(StaleWeatherError):
        run(fake_weather, fake_satellite, today=today, weather=stale)


def test_pipeline_rejects_bad_input(fake_weather, fake_satellite) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(GeometryError):
        run(fake_weather, fake_satellite, radius_m=99999.0)
    with pytest.raises(AquaPinError):
        run(fake_weather, fake_satellite, planting_date=dt.date(2026, 6, 1))


def test_params_hash_is_stable_and_version_present() -> None:
    assert params_hash("winter_wheat") == params_hash("winter_wheat")
    assert pipeline_version().startswith("0.1.0")
