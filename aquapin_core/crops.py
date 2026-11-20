"""Crop parameters loaded from a versioned JSON file; every value has a source."""

from __future__ import annotations

import dataclasses
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .errors import CropParamsError

_PATH = Path(__file__).with_name("crops.json")
_REQUIRED = (
    "kcb_ini",
    "kcb_mid",
    "kcb_end",
    "kcm_ini",
    "kcm_mid",
    "kcm_end",
    "stage_days",
    "root_max_m",
    "p_base",
    "height_max_m",
    "ndvi_soil",
    "ndvi_full",
)


@dataclasses.dataclass(frozen=True)
class CropParams:
    crop_id: str
    name: str
    kcb_ini: float
    kcb_mid: float
    kcb_end: float
    kcm_ini: float
    kcm_mid: float
    kcm_end: float
    stage_days: dict[str, int]
    root_max_m: float
    p_base: float
    height_max_m: float
    ndvi_soil: float
    ndvi_full: float
    raw: dict[str, Any]


@lru_cache(maxsize=1)
def _load() -> dict[str, Any]:
    with _PATH.open(encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return data


def crops_version() -> str:
    return str(_load()["version"])


def list_crops() -> list[str]:
    return sorted(_load()["crops"])


def get_crop(crop_id: str) -> CropParams:
    crops = _load()["crops"]
    if crop_id not in crops:
        raise CropParamsError(f"unknown crop: {crop_id!r}")
    entry = crops[crop_id]
    for key in _REQUIRED:
        item = entry.get(key)
        if not isinstance(item, dict) or not item.get("source"):
            raise CropParamsError(f"{crop_id}.{key} has no source")
    v = {k: entry[k]["value"] for k in _REQUIRED}
    return CropParams(
        crop_id=crop_id,
        name=entry["name"],
        kcb_ini=float(v["kcb_ini"]),
        kcb_mid=float(v["kcb_mid"]),
        kcb_end=float(v["kcb_end"]),
        kcm_ini=float(v["kcm_ini"]),
        kcm_mid=float(v["kcm_mid"]),
        kcm_end=float(v["kcm_end"]),
        stage_days={k: int(x) for k, x in v["stage_days"].items()},
        root_max_m=float(v["root_max_m"]),
        p_base=float(v["p_base"]),
        height_max_m=float(v["height_max_m"]),
        ndvi_soil=float(v["ndvi_soil"]),
        ndvi_full=float(v["ndvi_full"]),
        raw=entry,
    )
