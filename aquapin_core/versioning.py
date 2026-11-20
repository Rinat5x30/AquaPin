"""pipeline_version and a hash of every parameter that changes the result."""

from __future__ import annotations

import hashlib
import json
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import __version__, confidence, geometry
from .crops import crops_version, get_crop
from .waterbalance import SOIL_ASSUMPTION


@lru_cache(maxsize=1)
def pipeline_version() -> str:
    root = Path(__file__).resolve().parent.parent
    try:
        # fixed argv, no user input: only reads the commit hash of this checkout
        out = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return __version__
    sha = out.stdout.strip()
    return f"{__version__}+{sha}" if out.returncode == 0 and sha else __version__


def params_hash(crop_id: str) -> str:
    crop = get_crop(crop_id)
    payload: dict[str, Any] = {
        "crops_version": crops_version(),
        "crop": crop.raw,
        "soil": SOIL_ASSUMPTION,
        "confidence": [confidence.HIGH_MAX_DAYS, confidence.MEDIUM_MAX_DAYS],
        "geometry": [geometry.MIN_RADIUS_M, geometry.MAX_RADIUS_M, geometry.WINDOW_PAD],
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]
