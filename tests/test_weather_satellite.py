"""Adapters: Open-Meteo and STAC/NDVI logic with recorded-style fixtures (no network)."""

from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np
import pytest
import requests

from aquapin_core import satellite, weather
from aquapin_core.errors import StacSearchError, StaleWeatherError, WeatherApiError
from aquapin_core.types import WeatherDay

TODAY = dt.date(2026, 5, 20)


def payload(days: int = 3, start: dt.date = dt.date(2026, 5, 18)) -> dict[str, Any]:
    dates = [(start + dt.timedelta(days=i)).isoformat() for i in range(days)]
    return {
        "daily": {
            "time": dates,
            "et0_fao_evapotranspiration": [3.1] * days,
            "precipitation_sum": [0.0, 2.5, None][:days],
        }
    }


def test_parse_daily_skips_missing_values_and_marks_forecast() -> None:
    days = weather.parse_daily(payload(3), TODAY)
    assert [d.date.isoformat() for d in days] == ["2026-05-18", "2026-05-19"]
    assert days[1].rain_mm == 2.5 and not days[1].is_forecast
    forecast = weather.parse_daily(payload(3, dt.date(2026, 5, 21)), TODAY)
    assert all(d.is_forecast for d in forecast)


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"daily": {}},
        {"daily": {"time": [1], "et0_fao_evapotranspiration": [], "precipitation_sum": []}},
    ],
)
def test_parse_daily_malformed(bad: dict[str, Any]) -> None:
    with pytest.raises(WeatherApiError):
        weather.parse_daily(bad, TODAY)


def test_ensure_fresh() -> None:
    fresh = [WeatherDay(TODAY - dt.timedelta(days=1), 3, 0)]
    weather.ensure_fresh(fresh, TODAY)
    with pytest.raises(StaleWeatherError):
        weather.ensure_fresh([WeatherDay(TODAY - dt.timedelta(days=5), 3, 0)], TODAY)
    with pytest.raises(StaleWeatherError):
        weather.ensure_fresh([], TODAY)
    with pytest.raises(StaleWeatherError):  # forecast days do not count as observations
        weather.ensure_fresh([WeatherDay(TODAY + dt.timedelta(days=1), 3, 0, True)], TODAY)


class FakeResponse:
    def __init__(self, status: int = 200, body: Any = None, bad_json: bool = False) -> None:
        self.status_code, self._body, self._bad = status, body, bad_json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(str(self.status_code))

    def json(self) -> Any:
        if self._bad:
            raise ValueError("bad json")
        return self._body


class FakeSession:
    def __init__(self, responses: list[Any]) -> None:
        self.responses, self.calls = responses, []

    def get(self, url: str, params: dict[str, Any], timeout: float) -> FakeResponse:
        self.calls.append((url, params))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r  # type: ignore[no-any-return]

    def post(self, url: str, json: Any, timeout: float) -> FakeResponse:
        self.calls.append((url, json))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r  # type: ignore[no-any-return]


def client(session: FakeSession) -> weather.OpenMeteoClient:
    return weather.OpenMeteoClient(session=session, sleep=lambda s: None, today=lambda: TODAY)  # type: ignore[arg-type]


def test_client_retries_429_then_succeeds() -> None:
    s = FakeSession([FakeResponse(429), FakeResponse(200, payload(2))])
    days = client(s).fetch(40, 49, dt.date(2026, 5, 18), dt.date(2026, 5, 19))
    assert len(days) == 2 and len(s.calls) == 2


def test_client_gives_up_after_retries() -> None:
    s = FakeSession([FakeResponse(503)] * 3)
    with pytest.raises(WeatherApiError):
        client(s).fetch(40, 49, dt.date(2026, 5, 18), dt.date(2026, 5, 19))


def test_client_timeout_and_invalid_json() -> None:
    s = FakeSession([requests.exceptions.Timeout()] * 3)
    with pytest.raises(WeatherApiError):
        client(s).fetch(40, 49, dt.date(2026, 5, 1), dt.date(2026, 5, 2))
    with pytest.raises(WeatherApiError):
        client(FakeSession([FakeResponse(200, bad_json=True)])).fetch(
            40, 49, dt.date(2026, 5, 1), dt.date(2026, 5, 2)
        )


def test_client_routes_old_dates_to_archive_and_recent_to_forecast() -> None:
    old = FakeSession([FakeResponse(200, payload(2, dt.date(2026, 3, 1)))])
    client(old).fetch(40, 49, dt.date(2026, 3, 1), dt.date(2026, 3, 2))
    assert old.calls[0][0] == weather.ARCHIVE_URL
    recent = FakeSession([FakeResponse(200, payload(3, dt.date(2026, 5, 18)))])
    client(recent).fetch(40, 49, dt.date(2026, 5, 18), dt.date(2026, 5, 20))
    assert recent.calls[0][0] == weather.FORECAST_URL


# ---- satellite ----


def feature(**over: Any) -> dict[str, Any]:
    assets = {k: {"href": f"https://x/{k}.tif"} for k in ("red", "nir", "scl", "visual")}
    base = {
        "id": "S2_T",
        "properties": {
            "datetime": "2026-04-17T07:38:37Z",
            "eo:cloud_cover": 5.0,
            "earthsearch:boa_offset_applied": True,
        },
        "assets": assets,
    }
    base.update(over)
    return base


def test_parse_items() -> None:
    items = satellite.parse_items({"features": [feature(), feature(assets={"red": {"href": "x"}})]})
    assert len(items) == 1 and items[0].date == dt.date(2026, 4, 17) and items[0].boa_offset_applied
    with pytest.raises(StacSearchError):
        satellite.parse_items({})
    with pytest.raises(StacSearchError):
        satellite.parse_items({"features": [{"id": "x"}]})


def test_scale_offset_respects_boa_flag() -> None:
    item = satellite.parse_items({"features": [feature()]})[0]
    asset = {"raster:bands": [{"scale": 0.0001, "offset": -0.1}]}
    assert satellite._scale_offset(asset, item) == (
        1e-4,
        0.0,
    )  # offset already applied: never subtract again
    unflagged = satellite.parse_items(
        {"features": [feature(properties={"datetime": "2026-04-17T00:00:00Z"})]}
    )[0]
    assert satellite._scale_offset(asset, unflagged) == (0.0001, -0.1)


def test_compute_ndvi_masks_clouds_and_nodata() -> None:
    red = np.array([[400, 400, 400, 0]], dtype="uint16")
    nir = np.array([[3600, 3600, 3600, 3600]], dtype="uint16")
    scl = np.array([[4, 9, 5, 4]], dtype="uint8")
    ndvi, valid = satellite.compute_ndvi(red, nir, scl, (1e-4, 0.0), (1e-4, 0.0))
    assert ndvi[0, 0] == pytest.approx(0.8)
    assert valid.tolist() == [[True, False, True, False]]  # cloud (9) and nodata (0) excluded


def test_compute_ndvi_never_outputs_out_of_range_valid_pixels() -> None:
    red = np.array([[1, 5000]], dtype="uint16")
    nir = np.array([[1, 10]], dtype="uint16")
    ndvi, valid = satellite.compute_ndvi(
        red, nir, np.array([[4, 4]], dtype="uint8"), (1e-4, 0.0), (1e-4, 0.0)
    )
    assert not valid.any() or np.all(np.abs(ndvi[valid]) <= 1.0)


def test_ndvi_to_rgba_ramp_and_transparency() -> None:
    ndvi = np.array([[0.0, 0.9, 0.5]])
    rgba = satellite.ndvi_to_rgba(ndvi, np.array([[True, True, False]]))
    assert tuple(rgba[0, 0, :3]) == (165, 0, 38) and tuple(rgba[0, 1, :3]) == (0, 104, 55)
    assert rgba[0, 2, 3] == 0 and rgba[0, 0, 3] == 255


def test_search_items_error_paths() -> None:
    with pytest.raises(StacSearchError):
        satellite.search_items(
            (0, 0, 1, 1),
            dt.date(2026, 1, 1),
            dt.date(2026, 1, 2),
            session=FakeSession([requests.exceptions.ConnectionError()]),
        )  # type: ignore[arg-type]
    with pytest.raises(StacSearchError):
        satellite.search_items(
            (0, 0, 1, 1),
            dt.date(2026, 1, 1),
            dt.date(2026, 1, 2),
            session=FakeSession([FakeResponse(429)]),
        )  # type: ignore[arg-type]
    items = satellite.search_items(
        (0, 0, 1, 1),
        dt.date(2026, 1, 1),
        dt.date(2026, 1, 2),
        session=FakeSession([FakeResponse(200, {"features": [feature()]})]),
    )  # type: ignore[arg-type]
    assert len(items) == 1
