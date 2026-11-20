"""Build offline demo fields from REAL Sentinel-2 + Open-Meteo data.

Usage: python scripts/build_demo.py [slug ...]
Writes fields/static/fields/demo/<slug>/{data.json, base.jpg, frames/<date>.png}.
Uses the same build_viewer() as the live job queue (no duplicated logic).
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aquapin_core.replay import build_viewer  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "fields" / "static" / "fields" / "demo"
CROP = "winter_wheat"
RADIUS_M = 250.0
NOTE = (
    "Replay uses all observations of the season (retrospective); live advice uses only past data."
)

DEMO: list[dict[str, Any]] = [
    {
        "slug": "kura-lowland",
        "name": "Kura lowland, Azerbaijan",
        "name_ru": "Куринская низменность, Азербайджан",
        "lat": 40.0,
        "lon": 48.6,
        "planting": "2025-11-01",
        "end": "2026-05-31",
    },
    {
        "slug": "punjab",
        "name": "Punjab plains, India",
        "name_ru": "Равнина Пенджаба, Индия",
        "lat": 31.0,
        "lon": 75.4,
        "planting": "2025-11-15",
        "end": "2026-04-30",
    },
    {
        "slug": "saiss",
        "name": "Saiss plain, Morocco",
        "name_ru": "Равнина Сайс, Марокко",
        "lat": 33.9,
        "lon": -5.35,
        "planting": "2025-11-20",
        "end": "2026-06-10",
    },
]


def build(cfg: dict[str, Any]) -> None:
    slug = str(cfg["slug"])
    folder = OUT / slug
    shutil.rmtree(folder / "frames", ignore_errors=True)
    print(f"[{slug}] computing...", flush=True)
    data, res = build_viewer(
        folder=folder,
        lat=float(cfg["lat"]),
        lon=float(cfg["lon"]),
        radius_m=RADIUS_M,
        crop_id=CROP,
        planting=dt.date.fromisoformat(cfg["planting"]),
        today=dt.date.fromisoformat(cfg["end"]),
    )
    data.update({"slug": slug, "name": cfg["name"], "name_ru": cfg["name_ru"], "note": NOTE})
    (folder / "data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(
        f"[{slug}] frames={len(data['frames'])} events={len(res.irrigation_events)} "
        f"base={'yes' if data['base'] else 'NO'}",
        flush=True,
    )


if __name__ == "__main__":
    wanted = set(sys.argv[1:])
    for cfg in DEMO:
        if not wanted or cfg["slug"] in wanted:
            build(cfg)
