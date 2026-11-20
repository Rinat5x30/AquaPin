"""Plain-text rendering of an advice dict (Telegram and API consumers)."""

from __future__ import annotations

from typing import Any

from aquapin_core.validation import load_validation

from .i18n import tr


def validation_params() -> dict[str, Any] | None:
    v = load_validation()
    if v is None:
        return None
    return {
        "seasons": v["seasons"],
        "sites": v["sites"],
        "rmse": v["rmse_satellite"],
        "rmse_tab": v["rmse_table_best"],
        "china": v["china_irrigated"]["rmse_satellite"],
        "china_tab": v["china_irrigated"]["rmse_table_best"],
        "eu": v["europe_rainfed"]["rmse_satellite"],
        "eu_tab": v["europe_rainfed"]["rmse_table_best"],
        "b_lo": v["rel_bias_pct_closure_corrected"],
        "b_hi": v["rel_bias_pct_uncorrected"],
    }


def validation_text(lang: str, short: bool = False) -> str:
    """Honest accuracy statement from the backtest; falls back to 'not yet validated'."""
    p = validation_params()
    if p is None:
        return tr(lang, "why_validation")
    return tr(lang, "validation_short" if short else "validation_line", **p)


def advice_text(advice: dict[str, Any], lang: str) -> str:
    lines: list[str] = []
    if advice["decision"] == "irrigate":
        mm = f"{advice['irrigate_mm']:.0f}"
        m3 = f"{advice['m3_per_ha']:.0f}"
        lines.append(f"{tr(lang, 'irrigate')}: {tr(lang, 'mm_line', mm=mm, m3=m3)}")
    else:
        lines.append(tr(lang, "wait"))
    conf = tr(lang, f"conf_{advice['confidence']}")
    age = advice.get("last_clear_days")
    reason = tr(lang, "conf_reason", age=age) if age is not None else tr(lang, "conf_reason_none")
    lines.append(f"{tr(lang, 'confidence')}: {conf}. {reason}")
    lines.append(f"{tr(lang, 'why_dr')}: {advice['depletion_mm']} / {advice['raw_mm']} mm")
    lines.append(f"{tr(lang, 'why_rain')}: {advice['rain_next_3d_mm']} mm")
    src = tr(lang, "why_src_sat" if advice["kcb_source"] == "satellite" else "why_src_table")
    lines.append(f"{tr(lang, 'why_kcb')}: {advice['kcb']} ({src})")
    lines.append(validation_text(lang, short=True))
    return "\n".join(lines)
