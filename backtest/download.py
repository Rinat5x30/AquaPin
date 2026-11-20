"""Download open (CC-BY) ICOS FLUXNET archives for the backtest sites. No login, no personal data."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

SITES = ["DE-Geb", "FR-Aur", "FR-Gri", "BE-Lon", "CH-Oe2", "CN-Lch", "CN-Yuc", "DE-Kli", "DE-RuS"]
DATA = Path(__file__).parent / "data"
prods = json.loads((DATA / "icos_products.json").read_text(encoding="utf-8"))


def fetch(site: str) -> str:
    target = DATA / f"{site}.zip"
    if target.exists() and target.stat().st_size > 1_000_000:
        return f"{site}: cached"
    p = next(o for o in prods if f"_{site}_" in o["fileName"])
    did = p["dobj"].rsplit("/", 1)[-1]
    url = f"https://data.icos-cp.eu/licence_accept?ids=%5B%22{did}%22%5D"
    with requests.get(
        url, stream=True, timeout=120, headers={"Referer": "https://github.com/fluxnet/shuttle"}
    ) as r:
        r.raise_for_status()
        with target.open("wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return f"{site}: {target.stat().st_size / 1e6:.0f} MB ({p['fileName']})"


with ThreadPoolExecutor(4) as ex:
    for line in ex.map(fetch, SITES):
        print(line, flush=True)
