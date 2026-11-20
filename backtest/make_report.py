"""Turn results.json into results/REPORT.md (honest tables, including negative results)."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
res = json.loads((HERE / "results" / "results.json").read_text(encoding="utf-8"))
V = ("satellite", "table_med", "table_idaho")


def f(x: float | None, d: int = 2) -> str:
    return "-" if x is None else f"{x:.{d}f}"


lines = [
    "# AquaPin backtest report",
    "",
    f"Run on {res['run_on']}. Protocol: `backtest/PROTOCOL.md` (written before the run; model unchanged, nothing tuned).",
    f"Seasons planned {res['seasons_planned']}, evaluated {res['seasons_ok']}, failed {len(res['failed'])}.",
    "",
    "Compared quantity: daily model ETa vs tower ET (mm/day). RMSE in mm/day. Verdict baseline = the better of the two "
    "FAO-56 table curves per season (strongest honest baseline).",
    "",
]
for target, label in (
    ("le_mds", "Tower ET from LE_F_MDS (no energy-balance closure correction)"),
    ("le_corr", "Tower ET from LE_CORR (closure-corrected)"),
):
    lines += [
        f"## {label}",
        "",
        "| Group | Seasons | Satellite better | Sign test p | Satellite RMSE | Table-Med RMSE | Table-Idaho RMSE | Sat bias | Best-table bias |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for g, d in res["summary"][target].items():
        p = d["pooled"]
        if not p["satellite"]:
            continue
        best = min(("table_med", "table_idaho"), key=lambda v: p[v]["rmse"])
        lines.append(
            f"| {g} | {d['seasons']} | {d['satellite_better_than_best_baseline']}/{d['seasons']} | {f(d['sign_test_p'])} | "
            f"{f(p['satellite']['rmse'])} | {f(p['table_med']['rmse'])} | {f(p['table_idaho']['rmse'])} | "
            f"{f(p['satellite']['bias'])} | {f(p[best]['bias'])} ({best}) |"
        )
    lines.append("")


def extras(target: str, exclude: set[tuple[str, str]] | None = None) -> dict[str, dict[str, float]]:
    """Pooled relative bias and mean weekly RMSE per variant (all usable seasons)."""
    rows = [
        s["targets"][target]
        for s in res["seasons"]
        if all(s["targets"][target][v] for v in V)
        and (s["site"], s["start"]) not in (exclude or set())
    ]
    out: dict[str, dict[str, float]] = {}
    for v in V:
        n = sum(x[v]["n"] for x in rows)
        out[v] = {
            "rel_bias_pct": 100.0
            * sum(x[v]["n"] * x[v]["bias"] for x in rows)
            / sum(x[v]["n"] * x[v]["obs_mean"] for x in rows),
            "rmse7_mean": sum(x[v]["rmse7"] for x in rows) / len(rows),
            "rmse_pooled": (sum(x[v]["n"] * x[v]["rmse"] ** 2 for x in rows) / n) ** 0.5,
            "seasons": len(rows),
        }
    return out


OUTLIER = {("FR-Gri", "2017-09-25")}
lines += [
    "## Relative bias and weekly error",
    "",
    "| Target | Set | Variant | Pooled RMSE (mm/d) | Mean weekly RMSE (mm/d) | Relative bias |",
    "|---|---|---|---|---|---|",
]
for target in ("le_mds", "le_corr"):
    for label, excl in (
        ("all 20 seasons (protocol)", None),
        ("without FR-Gri 2017 (post-hoc sensitivity)", OUTLIER),
    ):
        for v, d in extras(target, excl).items():
            lines.append(
                f"| {target} | {label} | {v} | {f(d['rmse_pooled'])} | {f(d['rmse7_mean'])} | {d['rel_bias_pct']:+.0f}% |"
            )
lines += [
    "",
    "FR-Gri 2017-09-25 shows mean tower ET of 0.10 mm/day over 136 valid days, which is implausible for a wheat season "
    "(likely a data or crop-record problem). The protocol did not allow exclusions, so the main result keeps it.",
    "",
]

lines += [
    "## Per season (tower ET from LE_F_MDS; RMSE mm/day; r in brackets)",
    "",
    "| Site | Season start | Irrig. | S2 obs | NDVI peak (date) | Days | Obs ET | Satellite | Table-Med | Table-Idaho | Sat < best table |",
    "|---|---|---|---|---|---|---|---|---|---|---|",
]
for s in res["seasons"]:
    t = s["targets"]["le_mds"]
    if not all(t[v] for v in V):
        lines.append(
            f"| {s['site']} | {s['start']} | - | {s['n_obs']} | too few valid tower days | | | | | | |"
        )
        continue
    better = t["satellite"]["rmse"] < min(t["table_med"]["rmse"], t["table_idaho"]["rmse"])
    lines.append(
        f"| {s['site']} | {s['start']} | {'yes' if s['irrigated'] else 'no'} | {s['n_obs']} | "
        f"{s['ndvi_peak']} ({s['ndvi_peak_date']}) | {int(t['satellite']['n'])} | {f(t['satellite']['obs_mean'])} | "
        + " | ".join(f"{f(t[v]['rmse'])} ({f(t[v]['r'])})" for v in V)
        + f" | {'yes' if better else 'no'} |"
    )
lines += [
    "",
    "## Notes",
    "",
    "- Chinese seasons (CN-Lch, CN-Yuc) were ASSUMED to be winter wheat from the literature (not recorded in the archive); "
    "the NDVI peak date column is a sanity check (winter wheat should peak in March to May).",
    "- Data: ICOS Carbon Portal FLUXNET-archive products (CC-BY 4.0): DE-Geb, FR-Gri, BE-Lon, DE-RuS (ICOS), CN-Lch, CN-Yuc (ChinaFLUX). Cite the site PIs when reusing.",
    "- No site in the pilot region (Azerbaijan). Tower footprint and a 100 m circle differ. ET, not irrigation amounts, is validated.",
]
(HERE / "results" / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))


def write_validation() -> None:
    """Small summary shipped with the product (shown in the UI and the bot)."""
    mds, cor = extras("le_mds"), extras("le_corr")
    g = res["summary"]["le_mds"]

    def grp(name: str) -> dict[str, float]:
        p = g[name]["pooled"]
        return {
            "rmse_satellite": round(p["satellite"]["rmse"], 2),
            "rmse_table_best": round(min(p["table_med"]["rmse"], p["table_idaho"]["rmse"]), 2),
            "seasons": g[name]["seasons"],
        }

    val = {
        "run_on": res["run_on"],
        "protocol": "backtest/PROTOCOL.md",
        "seasons": res["seasons_ok"],
        "sites": 6,
        "regions": "Europe and China",
        "target": "tower ET (LE_F_MDS), mm/day",
        "rmse_satellite": round(mds["satellite"]["rmse_pooled"], 2),
        "rmse_table_med": round(mds["table_med"]["rmse_pooled"], 2),
        "rmse_table_idaho": round(mds["table_idaho"]["rmse_pooled"], 2),
        "rmse_table_best": round(
            min(mds["table_med"]["rmse_pooled"], mds["table_idaho"]["rmse_pooled"]), 2
        ),
        "rmse7_satellite": round(mds["satellite"]["rmse7_mean"], 2),
        "rmse7_table_best": round(
            min(mds["table_med"]["rmse7_mean"], mds["table_idaho"]["rmse7_mean"]), 2
        ),
        "rel_bias_pct_uncorrected": round(mds["satellite"]["rel_bias_pct"]),
        "rel_bias_pct_closure_corrected": round(cor["satellite"]["rel_bias_pct"]),
        "seasons_satellite_better_than_best_table": g["all"]["satellite_better_than_best_baseline"],
        "sign_test_p": round(g["all"]["sign_test_p"], 2),
        "europe_rainfed": grp("europe_rainfed"),
        "china_irrigated": grp("china_irrigated"),
    }
    out = HERE.parent / "aquapin_core" / "validation.json"
    out.write_text(json.dumps(val, indent=1), encoding="utf-8")
    print("wrote", out)


write_validation()
