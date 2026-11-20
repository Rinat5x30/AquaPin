"""Run the backtest exactly as written in PROTOCOL.md.

Usage: python backtest/run_backtest.py            (uses the on-disk cache in backtest/cache)
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import seasons as S  # noqa: E402

from aquapin_core.crops import get_crop  # noqa: E402
from aquapin_core.kc import daily_kcb  # noqa: E402
from aquapin_core.satellite import StacObservationSource  # noqa: E402
from aquapin_core.types import Observation, WeatherDay  # noqa: E402
from aquapin_core.waterbalance import run_balance, simulate_with_advice  # noqa: E402
from aquapin_core.weather import OpenMeteoClient  # noqa: E402

CACHE = HERE / "cache"
RESULTS = HERE / "results"
CACHE.mkdir(exist_ok=True)
RESULTS.mkdir(exist_ok=True)
RADIUS_M = 100.0
QC_MIN = 0.7
EU_SITES = ["DE-Geb", "FR-Gri", "BE-Lon", "DE-RuS"]
CN_SITES = ["CN-Lch", "CN-Yuc"]
IDAHO_STAGES = {
    "ini": 160,
    "dev": 75,
    "mid": 75,
    "late": 25,
}  # FAO-56 Table 11, winter wheat, Idaho


def build_seasons() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for site in EU_SITES:
        meta, sow, dd = S.site_meta(site), S.sowings(site), S.daily(site)
        for i, (d, name) in enumerate(sow):
            if "Triticum" not in name or d < S.S2_ERA_START:
                continue
            cap = dt.date(d.year + 1, 7, 31) if d.month >= 8 else dt.date(d.year, 8, 15)
            nxt = next((x for x, _ in sow[i + 1 :]), None)
            end = min(cap, (nxt - dt.timedelta(days=1)) if nxt else cap, dd.index.max())
            if (end - d).days >= 120:
                out.append(
                    {
                        **meta,
                        "site": site,
                        "start": d,
                        "end": end,
                        "irrigated": False,
                        "source": "BIF sowing record",
                    }
                )
    for site in CN_SITES:
        meta = S.site_meta(site)
        for year in (2017, 2018, 2019):
            out.append(
                {
                    **meta,
                    "site": site,
                    "start": dt.date(year, 10, 5),
                    "end": dt.date(year + 1, 6, 10),
                    "irrigated": True,
                    "source": "ASSUMED from literature (not in archive)",
                }
            )
    return out


def _key(s: dict[str, Any]) -> str:
    return f"{s['site']}_{s['start'].isoformat()}"


def get_weather(s: dict[str, Any]) -> list[WeatherDay]:
    path = CACHE / f"wx_{_key(s)}.json"
    if path.exists():
        return [
            WeatherDay(dt.date.fromisoformat(d), e, r) for d, e, r in json.loads(path.read_text())
        ]
    days = OpenMeteoClient().fetch(s["lat"], s["lon"], s["start"], s["end"])
    path.write_text(json.dumps([[d.date.isoformat(), d.et0_mm, d.rain_mm] for d in days]))
    return days


def get_obs(s: dict[str, Any]) -> list[Observation]:
    path = CACHE / f"obs_{_key(s)}.json"
    if path.exists():
        return [
            Observation(dt.date.fromisoformat(d), n, f, i)
            for d, n, f, i in json.loads(path.read_text())
        ]
    obs = StacObservationSource(max_workers=6).observations(
        s["lat"], s["lon"], RADIUS_M, s["start"], s["end"]
    )
    path.write_text(
        json.dumps([[o.date.isoformat(), o.ndvi, o.valid_fraction, o.item_id] for o in obs])
    )
    return obs


def observed_et(dd: pd.DataFrame, start: dt.date, end: dt.date) -> dict[str, pd.Series]:
    sub = dd.loc[start:end]
    lam = (2.501 - 0.002361 * sub["TA_F"]) * 1e6  # J/kg
    good = sub["LE_F_MDS_QC"] >= QC_MIN
    out = {}
    for name, col in (("le_mds", "LE_F_MDS"), ("le_corr", "LE_CORR")):
        et = (sub[col] * 86400.0 / lam).clip(lower=0.0)
        out[name] = et.where(good & et.notna())
    return out


def metrics(model: pd.Series, obs: pd.Series) -> dict[str, float] | None:
    m = pd.concat([model, obs], axis=1, keys=["m", "o"]).dropna()
    if len(m) < 20:
        return None
    err = m["m"] - m["o"]
    first = m.index[0].toordinal()
    week = np.array([(d.toordinal() - first) // 7 for d in m.index])
    w = m.groupby(week).agg(["mean", "count"])
    w = w[w[("m", "count")] >= 4]
    werr = w[("m", "mean")] - w[("o", "mean")]
    return {
        "n": float(len(m)),
        "obs_mean": float(m["o"].mean()),
        "bias": float(err.mean()),
        "rmse": float(math.sqrt((err**2).mean())),
        "mae": float(err.abs().mean()),
        "r": float(np.corrcoef(m["m"], m["o"])[0, 1]),
        "rmse7": float(math.sqrt((werr**2).mean())) if len(werr) >= 3 else float("nan"),
        "total_bias_pct": float(100.0 * (m["m"].sum() - m["o"].sum()) / m["o"].sum()),
    }


def evaluate(s: dict[str, Any]) -> dict[str, Any]:
    crop = get_crop("winter_wheat")
    crop_idaho = dataclasses.replace(crop, stage_days=IDAHO_STAGES)
    weather, obs = get_weather(s), get_obs(s)
    kcb = daily_kcb(obs, crop, s["end"])
    variants = {
        "satellite": (crop, kcb),
        "table_med": (crop, None),
        "table_idaho": (crop_idaho, None),
    }
    frames: dict[str, pd.Series] = {}
    for name, (c, k) in variants.items():
        if s["irrigated"]:
            frame, _ = simulate_with_advice(c, weather, s["start"], s["end"], k, s["lat"])
        else:
            frame = run_balance(c, weather, s["start"], s["end"], k, None, s["lat"])
        frames[name] = frame["eta"]
    dd = S.daily(s["site"])
    targets = observed_et(dd, s["start"], s["end"])
    peak = max(obs, key=lambda o: o.ndvi) if obs else None
    res: dict[str, Any] = {
        "site": s["site"],
        "start": s["start"].isoformat(),
        "end": s["end"].isoformat(),
        "irrigated": s["irrigated"],
        "source": s["source"],
        "n_obs": len(obs),
        "ndvi_peak": round(peak.ndvi, 2) if peak else None,
        "ndvi_peak_date": peak.date.isoformat() if peak else None,
        "targets": {},
    }
    pairs: dict[str, dict[str, list[list[float]]]] = {}
    for tname, series in targets.items():
        res["targets"][tname] = {v: metrics(f, series) for v, f in frames.items()}
        pairs[tname] = {}
        for v, f in frames.items():
            mm = pd.concat([f, series], axis=1, keys=["m", "o"]).dropna()
            pairs[tname][v] = [[float(a), float(b)] for a, b in zip(mm["m"], mm["o"], strict=True)]
    res["_pairs"] = pairs
    return res


def sign_test_p(wins: int, n: int) -> float:
    if n == 0:
        return float("nan")
    k = min(wins, n - wins)
    return min(1.0, 2.0 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n)


def summarise(results: list[dict[str, Any]], target: str) -> dict[str, Any]:
    def pooled(variant: str, subset: list[dict[str, Any]]) -> dict[str, float] | None:
        pr = [p for r in subset for p in r["_pairs"][target][variant]]
        if len(pr) < 30:
            return None
        a = np.array(pr)
        err = a[:, 0] - a[:, 1]
        return {
            "n": float(len(a)),
            "bias": float(err.mean()),
            "rmse": float(np.sqrt((err**2).mean())),
            "mae": float(np.abs(err).mean()),
            "r": float(np.corrcoef(a[:, 0], a[:, 1])[0, 1]),
        }

    out: dict[str, Any] = {}
    groups = {
        "all": results,
        "europe_rainfed": [r for r in results if not r["irrigated"]],
        "china_irrigated": [r for r in results if r["irrigated"]],
    }
    for gname, subset in groups.items():
        usable = [
            r
            for r in subset
            if all(r["targets"][target][v] for v in ("satellite", "table_med", "table_idaho"))
        ]
        wins = 0
        for r in usable:
            t = r["targets"][target]
            best_base = min(t["table_med"]["rmse"], t["table_idaho"]["rmse"])
            wins += t["satellite"]["rmse"] < best_base
        out[gname] = {
            "seasons": len(usable),
            "satellite_better_than_best_baseline": wins,
            "sign_test_p": sign_test_p(wins, len(usable)),
            "pooled": {v: pooled(v, usable) for v in ("satellite", "table_med", "table_idaho")},
        }
    return out


def main() -> None:
    seasons = build_seasons()
    print(f"{len(seasons)} site-seasons", flush=True)

    def work(s: dict[str, Any]) -> dict[str, Any]:
        try:
            r = evaluate(s)
            print(f"done {s['site']} {s['start']} obs={r['n_obs']}", flush=True)
            return r
        except Exception as exc:  # noqa: BLE001 - script: record the failure, keep going
            print(f"FAILED {s['site']} {s['start']}: {type(exc).__name__}: {exc}", flush=True)
            return {
                "site": s["site"],
                "start": s["start"].isoformat(),
                "error": f"{type(exc).__name__}: {exc}",
            }

    with ThreadPoolExecutor(4) as ex:
        results = list(ex.map(work, seasons))
    ok = [r for r in results if "error" not in r]
    summary = {t: summarise(ok, t) for t in ("le_mds", "le_corr")}
    out = {
        "protocol": "backtest/PROTOCOL.md",
        "run_on": dt.date.today().isoformat(),
        "seasons_planned": len(seasons),
        "seasons_ok": len(ok),
        "failed": [r for r in results if "error" in r],
        "summary": summary,
        "seasons": [{k: v for k, v in r.items() if k != "_pairs"} for r in ok],
    }
    (RESULTS / "results.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary["le_mds"], indent=1))


if __name__ == "__main__":
    main()
