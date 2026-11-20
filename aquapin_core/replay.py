"""Viewer payload (frames, basemap, per-day timeline) shared by demo build and live jobs."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from .confidence import confidence_from_age
from .errors import AquaPinError
from .geometry import window_bbox
from .pipeline import PipelineResult, compute_advice
from .satellite import (
    ChipResult,
    StacItem,
    StacObservationSource,
    ndvi_to_rgba,
    save_png,
    search_items,
    true_color_chip,
)
from .weather import OpenMeteoClient, WeatherClient


class FrameWriter:
    """Frame sink: writes NDVI PNG frames into `folder/frames` and remembers their bounds."""

    def __init__(self, folder: Path) -> None:
        self._folder = folder
        (folder / "frames").mkdir(parents=True, exist_ok=True)
        self._frames: dict[str, dict[str, Any]] = {}

    def __call__(self, item: StacItem, chip: ChipResult) -> None:
        name = f"{item.date.isoformat()}.png"
        save_png(ndvi_to_rgba(chip.ndvi, chip.valid), str(self._folder / "frames" / name))
        w, s, e, n = chip.bounds_lonlat
        self._frames[item.date.isoformat()] = {
            "date": item.date.isoformat(),
            "file": f"frames/{name}",
            "bounds": [[s, w], [n, e]],
            "ndvi": round(chip.observation.ndvi, 3) if chip.observation else None,
        }

    def frames(self) -> list[dict[str, Any]]:
        return [self._frames[k] for k in sorted(self._frames)]


def write_basemap(
    folder: Path, lat: float, lon: float, radius_m: float, start: dt.date, end: dt.date
) -> list[list[float]] | None:
    """Sentinel-2 true-colour chip (open data, no tile provider) from the clearest nearby item."""
    mid = start + (end - start) / 2
    items = search_items(
        window_bbox(lat, lon, radius_m),
        mid - dt.timedelta(days=25),
        min(mid + dt.timedelta(days=25), end),
        max_cloud=15.0,
    )
    for item in sorted(items, key=lambda i: i.cloud_cover if i.cloud_cover is not None else 100.0):
        if "visual" not in item.assets:
            continue
        try:
            w, s, e, n = true_color_chip(item, lat, lon, radius_m, str(folder / "base.jpg"))
        except AquaPinError:
            continue
        return [[s, w], [n, e]]
    return None


def day_rows(res: PipelineResult) -> list[dict[str, Any]]:
    obs_dates = [o.date for o in res.observations]
    rows: list[dict[str, Any]] = []
    for row in res.timeline:
        d = dt.date.fromisoformat(row["date"])
        prior = [x for x in obs_dates if x <= d]
        last = max(prior) if prior else None
        age = (d - last).days if last else None
        rows.append(
            {
                **row,
                "frame": last.isoformat() if last else None,
                "age": age,
                "confidence": confidence_from_age(age),
                "decision": "irrigate" if row["irrig"] > 0 else "wait",
            }
        )
    return rows


def build_viewer(
    *,
    folder: Path,
    lat: float,
    lon: float,
    radius_m: float,
    crop_id: str,
    planting: dt.date,
    today: dt.date,
    weather: WeatherClient | None = None,
    max_cloud: float = 80.0,
) -> tuple[dict[str, Any], PipelineResult]:
    """Run the pipeline and write frames + basemap into `folder`. Returns (viewer data, result)."""
    folder.mkdir(parents=True, exist_ok=True)
    writer = FrameWriter(folder)
    res = compute_advice(
        lat=lat,
        lon=lon,
        radius_m=radius_m,
        crop_id=crop_id,
        planting_date=planting,
        today=today,
        weather=weather or OpenMeteoClient(),
        satellite=StacObservationSource(frame_sink=writer, max_cloud=max_cloud),
    )
    base_bounds = write_basemap(folder, lat, lon, radius_m, planting, today)
    data: dict[str, Any] = {
        "lat": lat,
        "lon": lon,
        "radius_m": radius_m,
        "crop_id": crop_id,
        "planting": planting.isoformat(),
        "end": today.isoformat(),
        "base": "base.jpg" if base_bounds else None,
        "base_bounds": base_bounds,
        "frames": writer.frames(),
        "days": day_rows(res),
        "irrigation_events": res.irrigation_events,
        "advice_final": res.advice.to_dict(),
        "built_on": dt.date.today().isoformat(),
    }
    return data, res
