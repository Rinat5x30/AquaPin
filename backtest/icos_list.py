"""List ICOS FLUXNET-archive products (open, CC-BY) with station metadata. No login, no personal data."""

import json
import sys

import requests

SPARQL = "https://meta.icos-cp.eu/sparql"
QUERY = """
prefix cpmeta: <http://meta.icos-cp.eu/ontologies/cpmeta/>
prefix prov: <http://www.w3.org/ns/prov#>
select ?dobj ?fileName ?size ?station ?stationName ?lat ?lon ?eco where {
  VALUES ?spec {<http://meta.icos-cp.eu/resources/cpmeta/miscFluxnetArchiveProduct>}
  ?dobj cpmeta:hasObjectSpec ?spec .
  ?dobj cpmeta:hasSizeInBytes ?size .
  ?dobj cpmeta:hasName ?fileName .
  FILTER NOT EXISTS {[] cpmeta:isNextVersionOf ?dobj}
  ?dobj cpmeta:wasAcquiredBy/prov:wasAssociatedWith ?station .
  OPTIONAL {?station cpmeta:hasName ?stationName}
  OPTIONAL {?station cpmeta:hasEcosystemType ?eco}
  OPTIONAL {?station cpmeta:hasLatitude ?lat}
  OPTIONAL {?station cpmeta:hasLongitude ?lon}
}
order by desc(?fileName)
"""
resp = requests.post(
    SPARQL,
    data={"query": QUERY},
    headers={"Accept": "application/json", "Referer": "https://github.com/fluxnet/shuttle"},
    timeout=60,
)
print(resp.status_code)
rows = resp.json()["results"]["bindings"]
sys.stdout.reconfigure(encoding="utf-8")
out = []
for r in rows:
    g = lambda k: r.get(k, {}).get("value", "")
    out.append(
        {
            k: g(k)
            for k in ("dobj", "fileName", "size", "station", "stationName", "lat", "lon", "eco")
        }
    )
json.dump(
    out,
    open("backtest/data/icos_products.json", "w", encoding="utf-8"),
    ensure_ascii=False,
    indent=1,
)
print(len(out), "products")
for o in out[:6]:
    print(o["fileName"], o["eco"].split("/")[-1], o["stationName"], o["lat"], o["lon"], o["size"])
from collections import Counter

print(Counter(o["eco"].split("/")[-1] for o in out))
