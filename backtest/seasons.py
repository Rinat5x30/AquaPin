"""Wheat seasons per site from the BIF metadata (species + sowing date) and daily flux frames."""

from __future__ import annotations

import datetime as dt
import zipfile
from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent / "data"
S2_ERA_START = dt.date(2017, 3, 1)  # Sentinel-2 L2A coverage used for NDVI


def _open(site: str, kind: str) -> pd.DataFrame:
    z = zipfile.ZipFile(DATA / f"{site}.zip")
    name = next(n for n in z.namelist() if f"_FLUXNET_{kind}_" in n and n.endswith(".csv"))
    return pd.read_csv(z.open(name))


def site_meta(site: str) -> dict[str, float]:
    bif = _open(site, "BIF")
    loc = bif[bif.VARIABLE_GROUP == "GRP_LOCATION"].set_index("VARIABLE")["DATAVALUE"]
    return {"lat": float(loc["LOCATION_LAT"]), "lon": float(loc["LOCATION_LONG"])}


def sowings(site: str) -> list[tuple[dt.date, str]]:
    bif = _open(site, "BIF")
    spp = bif[bif.VARIABLE_GROUP == "GRP_SPP"]
    if spp.empty:
        return []
    w = spp.pivot_table(index="GROUP_ID", columns="VARIABLE", values="DATAVALUE", aggfunc="first")
    out = []
    for _, r in w.iterrows():
        if "SPP_DATE" in w.columns and "SPP_O" in w.columns and isinstance(r["SPP_DATE"], str):
            out.append((dt.datetime.strptime(r["SPP_DATE"][:8], "%Y%m%d").date(), str(r["SPP_O"])))
    return sorted(out)


def daily(site: str) -> pd.DataFrame:
    dd = _open(site, "FLUXMET_DD")
    dd = dd.replace(-9999, float("nan"))
    dd["date"] = pd.to_datetime(dd["TIMESTAMP"].astype(str), format="%Y%m%d").dt.date
    return dd.set_index("date")


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    for site in [
        "DE-Geb",
        "FR-Aur",
        "FR-Gri",
        "BE-Lon",
        "CH-Oe2",
        "CN-Lch",
        "CN-Yuc",
        "DE-Kli",
        "DE-RuS",
    ]:
        m = site_meta(site)
        s = sowings(site)
        wheat = [(d, n) for d, n in s if "Triticum" in n and d >= S2_ERA_START]
        dd = daily(site)
        print(
            f"{site} lat={m['lat']:.3f} lon={m['lon']:.3f} daily {dd.index.min()}..{dd.index.max()} | sowings={len(s)} wheat>=2017: "
            + ", ".join(f"{d} {n[:12]}" for d, n in wheat)
        )
