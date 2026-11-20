"""Shared fixtures. No test may touch the network: external APIs are faked at the adapter boundary."""

from __future__ import annotations

import datetime as dt

import pytest

from aquapin_core.types import Observation, WeatherDay


class FakeWeather:
    """Constant weather for every requested day; days after `today` are forecasts."""

    def __init__(
        self,
        et0: float = 3.0,
        rain: float = 0.0,
        today: dt.date | None = None,
        last_observed: dt.date | None = None,
    ) -> None:
        self.et0, self.rain, self.today, self.last_observed = et0, rain, today, last_observed

    def fetch(self, lat: float, lon: float, start: dt.date, end: dt.date) -> list[WeatherDay]:
        today = self.today or end
        days = []
        d = start
        while d <= end:
            if self.last_observed is None or d <= self.last_observed or d > today:
                days.append(WeatherDay(d, self.et0, self.rain, is_forecast=d > today))
            d += dt.timedelta(days=1)
        return days


class FakeSatellite:
    def __init__(self, observations: list[Observation] | None = None) -> None:
        self._obs = observations or []

    def observations(
        self, lat: float, lon: float, radius_m: float, start: dt.date, end: dt.date
    ) -> list[Observation]:
        return [o for o in self._obs if start <= o.date <= end]


@pytest.fixture
def fake_weather() -> type[FakeWeather]:
    return FakeWeather


@pytest.fixture
def fake_satellite() -> type[FakeSatellite]:
    return FakeSatellite
