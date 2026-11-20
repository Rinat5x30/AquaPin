"""Point validation and window geometry for a circular field."""

from __future__ import annotations

import math

import numpy as np

from .errors import GeometryError

# Initial limits; real values are to be set from measurements (task T2).
MAX_RADIUS_M = 500.0
MIN_RADIUS_M = 30.0
WINDOW_PAD = 3.0  # window half-size = radius * WINDOW_PAD (context around the field)
_M_PER_DEG_LAT = 111_320.0


def validate_point(lat: float, lon: float, radius_m: float) -> None:
    if not (math.isfinite(lat) and math.isfinite(lon) and math.isfinite(radius_m)):
        raise GeometryError("lat, lon and radius must be finite numbers")
    if not -60.0 <= lat <= 75.0:
        raise GeometryError("latitude must be within -60..75 (agricultural range)")
    if not -180.0 <= lon <= 180.0:
        raise GeometryError("longitude must be within -180..180")
    if not MIN_RADIUS_M <= radius_m <= MAX_RADIUS_M:
        raise GeometryError(f"radius must be {MIN_RADIUS_M:.0f}..{MAX_RADIUS_M:.0f} m")


def window_bbox(lat: float, lon: float, radius_m: float) -> tuple[float, float, float, float]:
    """(west, south, east, north) of the context window around the field."""
    half = radius_m * WINDOW_PAD
    dlat = half / _M_PER_DEG_LAT
    dlon = half / (_M_PER_DEG_LAT * max(math.cos(math.radians(lat)), 0.05))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


def circle_mask(shape: tuple[int, int], radius_m: float, pixel_m: float) -> np.ndarray:
    """Boolean mask of the field circle centred in a window of given shape."""
    rows, cols = shape
    yy, xx = np.ogrid[:rows, :cols]
    cy, cx = (rows - 1) / 2.0, (cols - 1) / 2.0
    dist_m = np.hypot(yy - cy, xx - cx) * pixel_m
    mask: np.ndarray = dist_m <= radius_m
    return mask
