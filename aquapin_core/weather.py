"""Open-Meteo daily ET0 + precipitation client (archive + forecast)."""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Callable
from typing import Any, Protocol

import requests

from .errors import StaleWeatherError, WeatherApiError
from .types import WeatherDay

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
_DAILY = "et0_fao_evapotranspiration,precipitation_sum"
_ARCHIVE_LAG_DAYS = 6  # archive is complete up to about today-6; newer days come from forecast API
MAX_AGE_DAYS = 2  # weather older than this is refused (no guessing)


class WeatherClient(Protocol):
    def fetch(self, lat: float, lon: float, start: dt.date, end: dt.date) -> list[WeatherDay]: ...


def parse_daily(payload: dict[str, Any], today: dt.date) -> list[WeatherDay]:
    """Parse an Open-Meteo `daily` payload. Days with missing values are skipped."""
    try:
        daily = payload["daily"]
        times = daily["time"]
        et0 = daily["et0_fao_evapotranspiration"]
        rain = daily["precipitation_sum"]
    except (KeyError, TypeError) as exc:
        raise WeatherApiError("malformed weather payload: missing daily fields") from exc
    if not (len(times) == len(et0) == len(rain)):
        raise WeatherApiError("malformed weather payload: array length mismatch")
    out: list[WeatherDay] = []
    for t, e, r in zip(times, et0, rain, strict=True):
        if e is None or r is None:
            continue
        try:
            day = dt.date.fromisoformat(t)
        except ValueError as exc:
            raise WeatherApiError(f"malformed weather date: {t!r}") from exc
        out.append(
            WeatherDay(
                date=day,
                et0_mm=max(float(e), 0.0),
                rain_mm=max(float(r), 0.0),
                is_forecast=day > today,
            )
        )
    return out


def ensure_fresh(days: list[WeatherDay], today: dt.date) -> None:
    observed = [d.date for d in days if not d.is_forecast]
    if not observed:
        raise StaleWeatherError("no observed weather days available")
    age = (today - max(observed)).days
    if age > MAX_AGE_DAYS:
        raise StaleWeatherError(f"latest weather is {age} days old (limit {MAX_AGE_DAYS})")


class OpenMeteoClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: float = 25.0,
        retries: int = 2,
        sleep: Callable[[float], None] = time.sleep,
        today: Callable[[], dt.date] = dt.date.today,
    ) -> None:
        self._session = session or requests.Session()
        self._timeout = timeout
        self._retries = retries
        self._sleep = sleep
        self._today = today

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        last: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                resp = self._session.get(url, params=params, timeout=self._timeout)
                if resp.status_code == 429 or resp.status_code >= 500:
                    last = WeatherApiError(f"weather provider returned HTTP {resp.status_code}")
                else:
                    resp.raise_for_status()
                    payload: dict[str, Any] = resp.json()
                    return payload
            except requests.exceptions.RequestException as exc:
                last = exc
            except ValueError as exc:  # invalid JSON
                raise WeatherApiError("weather provider returned invalid JSON") from exc
            if attempt < self._retries:
                self._sleep(2.0**attempt)
        raise WeatherApiError(f"weather request failed after retries: {last}") from last

    def fetch(self, lat: float, lon: float, start: dt.date, end: dt.date) -> list[WeatherDay]:
        today = self._today()
        base = {
            "latitude": f"{lat:.4f}",
            "longitude": f"{lon:.4f}",
            "daily": _DAILY,
            "timezone": "UTC",
        }
        cutoff = today - dt.timedelta(days=_ARCHIVE_LAG_DAYS)
        days: dict[dt.date, WeatherDay] = {}
        if start <= cutoff:
            arch_end = min(end, cutoff)
            payload = self._get(
                ARCHIVE_URL,
                {**base, "start_date": start.isoformat(), "end_date": arch_end.isoformat()},
            )
            days.update({d.date: d for d in parse_daily(payload, today)})
        if end > cutoff:
            first = max(start, cutoff + dt.timedelta(days=1))
            past = min((today - first).days, 92)
            future = min(max((end - today).days + 1, 1), 16)
            payload = self._get(
                FORECAST_URL, {**base, "past_days": max(past, 0), "forecast_days": future}
            )
            days.update({d.date: d for d in parse_daily(payload, today) if start <= d.date <= end})
        return [days[k] for k in sorted(days)]
