"""Sentinel-2 L2A access: STAC search + windowed COG reads (Earth Search, no API key)."""

from __future__ import annotations

import dataclasses
import datetime as dt
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np
import rasterio
import requests
from PIL import Image
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds

from .errors import SatelliteReadError, StacSearchError
from .geometry import circle_mask, window_bbox
from .types import Observation

STAC_URL = "https://earth-search.aws.element84.com/v1/search"
COLLECTION = "sentinel-2-l2a"
MIN_VALID_FRACTION = 0.8
VALID_SCL = (4, 5)  # vegetation, not vegetated; clouds/shadow/snow/water excluded

# ColorBrewer RdYlGn anchors: classic red -> green scale (user decision).
_RAMP_X = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 0.9])
_RAMP_RGB = np.array(
    [
        [165, 0, 38],
        [244, 109, 67],
        [254, 224, 139],
        [166, 217, 106],
        [26, 152, 80],
        [0, 104, 55],
    ],
    dtype=float,
)


@dataclasses.dataclass(frozen=True)
class StacItem:
    id: str
    date: dt.date
    cloud_cover: float | None
    assets: dict[str, dict[str, Any]]
    boa_offset_applied: bool = False


@dataclasses.dataclass
class ChipResult:
    observation: Observation | None
    ndvi: np.ndarray
    valid: np.ndarray
    bounds_lonlat: tuple[float, float, float, float]  # west, south, east, north


FrameSink = Callable[[StacItem, ChipResult], None]


def parse_items(payload: dict[str, Any]) -> list[StacItem]:
    try:
        features = payload["features"]
    except (KeyError, TypeError) as exc:
        raise StacSearchError("malformed STAC response: no features") from exc
    items: list[StacItem] = []
    for feat in features:
        try:
            props = feat["properties"]
            day = dt.date.fromisoformat(props["datetime"][:10])
            assets = {
                k: feat["assets"][k] for k in ("red", "nir", "scl", "visual") if k in feat["assets"]
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise StacSearchError("malformed STAC feature") from exc
        if {"red", "nir", "scl"} <= assets.keys():
            items.append(
                StacItem(
                    id=str(feat["id"]),
                    date=day,
                    cloud_cover=props.get("eo:cloud_cover"),
                    assets=assets,
                    boa_offset_applied=bool(props.get("earthsearch:boa_offset_applied")),
                )
            )
    return items


def search_items(
    bbox: tuple[float, float, float, float],
    start: dt.date,
    end: dt.date,
    max_cloud: float = 80.0,
    session: requests.Session | None = None,
    timeout: float = 30.0,
) -> list[StacItem]:
    body = {
        "collections": [COLLECTION],
        "bbox": list(bbox),
        "datetime": f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z",
        "limit": 500,
        "query": {"eo:cloud_cover": {"lt": max_cloud}},
        "sortby": [{"field": "properties.datetime", "direction": "asc"}],
    }
    try:
        resp = (session or requests).post(STAC_URL, json=body, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
    except requests.exceptions.RequestException as exc:
        raise StacSearchError(f"STAC search failed: {exc}") from exc
    except ValueError as exc:
        raise StacSearchError("STAC returned invalid JSON") from exc
    return parse_items(payload)


def _scale_offset(asset: dict[str, Any], item: StacItem) -> tuple[float, float]:
    """(scale, offset) to turn stored DN into reflectance.

    Earth Search sets `earthsearch:boa_offset_applied` when the -1000 BOA offset is
    already baked into the data; then the raster:bands offset must NOT be applied again.
    """
    if item.boa_offset_applied:
        return 1e-4, 0.0
    bands = asset.get("raster:bands") or []
    if bands and "scale" in bands[0] and "offset" in bands[0]:
        return float(bands[0]["scale"]), float(bands[0]["offset"])
    offset = -0.1 if item.date >= dt.date(2022, 1, 25) else 0.0  # processing baseline 04.00
    return 1e-4, offset


def compute_ndvi(
    red_dn: np.ndarray,
    nir_dn: np.ndarray,
    scl: np.ndarray,
    scale: tuple[float, float],
    scale_nir: tuple[float, float],
) -> tuple[np.ndarray, np.ndarray]:
    """NDVI and validity mask (clear land pixels only)."""
    red = red_dn.astype("float64") * scale[0] + scale[1]
    nir = nir_dn.astype("float64") * scale_nir[0] + scale_nir[1]
    denom = nir + red
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = np.where(denom > 0, (nir - red) / denom, np.nan)
    valid = (
        np.isin(scl, VALID_SCL)
        & (red_dn > 0)
        & (nir_dn > 0)
        & np.isfinite(ndvi)
        & (denom > 0.02)
        & (ndvi >= -1.0)
        & (ndvi <= 1.0)
    )
    return ndvi, valid


def _window(ds: Any, bbox: tuple[float, float, float, float]) -> Window:
    bounds = transform_bounds("EPSG:4326", ds.crs, *bbox, densify_pts=5)
    win = from_bounds(*bounds, transform=ds.transform)
    win = win.round_offsets(op="floor").round_lengths(op="ceil")
    if (
        win.col_off < 0
        or win.row_off < 0
        or win.col_off + win.width > ds.width
        or win.row_off + win.height > ds.height
        or win.width < 3
        or win.height < 3
    ):
        raise SatelliteReadError("field window is outside this tile")
    return win


def _read(
    href: str,
    bbox: tuple[float, float, float, float],
    shape: tuple[int, int] | None,
    bands: int = 1,
) -> tuple[np.ndarray, Window, Any]:
    try:
        with (
            rasterio.Env(
                GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF",
                GDAL_HTTP_MAX_RETRY="3",
                GDAL_HTTP_RETRY_DELAY="1",
            ),
            rasterio.open(href) as ds,
        ):
            win = _window(ds, bbox)
            out_shape = shape or (int(win.height), int(win.width))
            idx: int | list[int] = 1 if bands == 1 else list(range(1, bands + 1))
            data = ds.read(
                idx,
                window=win,
                out_shape=(out_shape if bands == 1 else (bands, *out_shape)),
                resampling=Resampling.nearest,
            )
            return data, win, (ds.crs, ds.window_transform(win), ds.res[0])
    except rasterio.errors.RasterioError as exc:
        raise SatelliteReadError(f"raster read failed: {exc}") from exc


def read_chip(item: StacItem, lat: float, lon: float, radius_m: float) -> ChipResult:
    bbox = window_bbox(lat, lon, radius_m)
    red, _, meta = _read(item.assets["red"]["href"], bbox, None)
    nir, _, _ = _read(item.assets["nir"]["href"], bbox, red.shape)
    scl, _, _ = _read(item.assets["scl"]["href"], bbox, red.shape)
    crs, transform, pixel_m = meta
    ndvi, valid = compute_ndvi(
        red,
        nir,
        scl,
        _scale_offset(item.assets["red"], item),
        _scale_offset(item.assets["nir"], item),
    )
    mask = circle_mask(red.shape, radius_m, float(pixel_m))
    n_mask = int(mask.sum())
    obs: Observation | None = None
    if n_mask > 0:
        frac = float((valid & mask).sum()) / n_mask
        if frac >= MIN_VALID_FRACTION:
            obs = Observation(
                date=item.date,
                ndvi=float(np.nanmean(ndvi[valid & mask])),
                valid_fraction=frac,
                item_id=item.id,
                cloud_cover=item.cloud_cover,
            )
    h, w = red.shape
    west, south, east, north = rasterio.transform.array_bounds(h, w, transform)
    lonlat = transform_bounds(crs, "EPSG:4326", west, south, east, north)
    return ChipResult(observation=obs, ndvi=ndvi, valid=valid, bounds_lonlat=lonlat)


class StacObservationSource:
    """Cloud-screened NDVI observations for a circular field."""

    def __init__(
        self,
        session: requests.Session | None = None,
        max_workers: int = 6,
        frame_sink: FrameSink | None = None,
        max_cloud: float = 80.0,
    ) -> None:
        self._session = session
        self._workers = max_workers
        self._sink = frame_sink
        self._max_cloud = max_cloud

    def observations(
        self, lat: float, lon: float, radius_m: float, start: dt.date, end: dt.date
    ) -> list[Observation]:
        items = search_items(
            window_bbox(lat, lon, radius_m), start, end, self._max_cloud, self._session
        )

        def work(item: StacItem) -> tuple[StacItem, ChipResult] | None:
            try:
                return item, read_chip(item, lat, lon, radius_m)
            except SatelliteReadError:
                return None  # tile edge or transient read failure: skip this item

        with ThreadPoolExecutor(max_workers=self._workers) as pool:
            results = [r for r in pool.map(work, items) if r is not None]
        best: dict[dt.date, tuple[StacItem, ChipResult]] = {}
        for item, chip in results:
            if chip.observation is None:
                continue
            cur = best.get(item.date)
            if cur is None or (
                chip.observation.valid_fraction
                > (cur[1].observation.valid_fraction if cur[1].observation else 0)
            ):
                best[item.date] = (item, chip)
        if self._sink:
            for item, chip in best.values():
                self._sink(item, chip)
        return [
            chip.observation
            for _, chip in sorted(best.values(), key=lambda x: x[0].date)
            if chip.observation is not None
        ]


def ndvi_to_rgba(ndvi: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """RGBA uint8 image: classic red->green ramp; invalid pixels transparent."""
    x = np.clip(np.nan_to_num(ndvi, nan=0.0), 0.0, 0.9)
    rgba = np.zeros((*ndvi.shape, 4), dtype=np.uint8)
    for c in range(3):
        rgba[..., c] = np.interp(x, _RAMP_X, _RAMP_RGB[:, c]).astype(np.uint8)
    rgba[..., 3] = np.where(valid, 255, 0).astype(np.uint8)
    return rgba


def save_png(rgba: np.ndarray, path: str) -> None:
    Image.fromarray(rgba, mode="RGBA").save(path, optimize=True)


def true_color_chip(
    item: StacItem, lat: float, lon: float, radius_m: float, path: str
) -> tuple[float, float, float, float]:
    """Save a Sentinel-2 true-colour (TCI) chip as JPEG basemap; returns lon/lat bounds."""
    if "visual" not in item.assets:
        raise SatelliteReadError("item has no visual asset")
    bbox = window_bbox(lat, lon, radius_m)
    data, _, (crs, transform, _) = _read(item.assets["visual"]["href"], bbox, None, bands=3)
    _, h, w = data.shape
    img = Image.fromarray(np.moveaxis(data, 0, -1).astype(np.uint8), mode="RGB")
    img.save(path, quality=85, optimize=True)
    west, south, east, north = rasterio.transform.array_bounds(h, w, transform)
    w, s, e, n = transform_bounds(crs, "EPSG:4326", west, south, east, north)
    return (float(w), float(s), float(e), float(n))
