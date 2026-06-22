from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence


PROMOTION_SCHEMA_VERSION = "hellhound_shadow_promotion_v1"
OUTCOME_BANDS = (
    (0.0, 0.2),
    (0.2, 0.4),
    (0.4, 0.6),
    (0.6, 0.8),
    (0.8, 1.0000001),
)


def evaluate_promotion_candidate(
    *,
    hellhound_score: float,
    accumulation_score: float,
    repeat_activity_score: float,
    structure_type: str,
    distribution_risk: float,
) -> Dict[str, Any]:
    """Rule-based shadow promotion gate. It never emits a trade command."""
    reasons = []
    structure = str(structure_type or "UNKNOWN").upper()
    score = _clamp(hellhound_score)
    accumulation = _clamp(accumulation_score)
    repeat = _clamp(repeat_activity_score)
    risk = _clamp(distribution_risk)

    if risk >= 0.65:
        status = "REJECT"
        reasons.append("distribution_risk is too high for shadow promotion.")
    elif structure in {"DISTRIBUTION", "CAPITULATION"}:
        status = "REJECT"
        reasons.append(f"structure_type={structure} is not a promotion structure.")
    elif score >= 0.60 and risk <= 0.40:
        status = "PROMOTE"
        reasons.append("hellhound_score >= 0.60 and distribution_risk <= 0.40.")
    elif structure == "ACCUMULATION_BASE" and accumulation >= 0.55 and repeat >= 0.25 and risk <= 0.40:
        status = "PROMOTE"
        reasons.append("ACCUMULATION_BASE has sufficient accumulation and repeat activity with low risk.")
    elif score >= 0.40 and risk <= 0.55:
        status = "WATCH"
        reasons.append("middle score/risk profile remains watchable.")
    else:
        status = "REJECT"
        reasons.append("score is too weak for shadow promotion.")

    return {
        "promotion_schema_version": PROMOTION_SCHEMA_VERSION,
        "promotion_status": status,
        "hellhound_score": score,
        "accumulation_score": accumulation,
        "repeat_activity_score": repeat,
        "structure_type": structure,
        "distribution_risk": risk,
        "reasons": reasons,
    }


def build_shadow_decision(
    *,
    symbol: str,
    setup_type: str,
    structure_type: str,
    hellhound_score: float,
    accumulation_score: float,
    repeat_activity_score: float,
    distribution_risk: float,
) -> Dict[str, Any]:
    promotion = evaluate_promotion_candidate(
        hellhound_score=hellhound_score,
        accumulation_score=accumulation_score,
        repeat_activity_score=repeat_activity_score,
        structure_type=structure_type,
        distribution_risk=distribution_risk,
    )
    return {
        "promotion_schema_version": PROMOTION_SCHEMA_VERSION,
        "symbol": str(symbol).upper(),
        "setup_type": str(setup_type or "UNKNOWN").upper(),
        "structure_type": promotion["structure_type"],
        "hellhound_score": promotion["hellhound_score"],
        "promotion_status": promotion["promotion_status"],
        "reasons": promotion["reasons"],
        "is_trade_command": False,
    }


def replay_shadow_cases(cases: Sequence[Mapping[str, Any]]) -> list[Dict[str, Any]]:
    return [
        build_shadow_decision(
            symbol=str(case.get("symbol") or case.get("setup_type") or "UNKNOWN"),
            setup_type=str(case.get("setup_type") or "UNKNOWN"),
            structure_type=str(case.get("structure_type") or "UNKNOWN"),
            hellhound_score=float(case.get("hellhound_score") or 0.0),
            accumulation_score=float(case.get("accumulation_score") or 0.0),
            repeat_activity_score=float(case.get("repeat_activity_score") or 0.0),
            distribution_risk=float(case.get("distribution_risk") or 0.0),
        )
        for case in cases
    ]


def compute_outcome_correlation(outcomes: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Summarize supplied shadow outcomes by hellhound_score band and window."""
    bands = {
        _band_label(low, high): {
            "score_band": _band_label(low, high),
            "total": 0,
            "success": 0,
            "fail": 0,
            "win_rate": None,
            "windows": {},
        }
        for low, high in OUTCOME_BANDS
    }
    for outcome in outcomes:
        score = _optional_float(outcome.get("hellhound_score"))
        if score is None:
            continue
        band = bands[_band_for_score(score)]
        result = str(outcome.get("result") or "").upper()
        window = str(outcome.get("evaluation_window") or "unknown")
        band["total"] += 1
        window_stats = band["windows"].setdefault(
            window,
            {"total": 0, "success": 0, "fail": 0, "win_rate": None},
        )
        window_stats["total"] += 1
        if result == "SUCCESS":
            band["success"] += 1
            window_stats["success"] += 1
        elif result == "FAIL":
            band["fail"] += 1
            window_stats["fail"] += 1

    for band in bands.values():
        band["win_rate"] = _win_rate(band["success"], band["fail"])
        for stats in band["windows"].values():
            stats["win_rate"] = _win_rate(stats["success"], stats["fail"])
    return {
        "promotion_schema_version": PROMOTION_SCHEMA_VERSION,
        "score_bands": list(bands.values()),
    }


def _band_for_score(score: float) -> str:
    clamped = _clamp(score)
    for low, high in OUTCOME_BANDS:
        if low <= clamped < high:
            return _band_label(low, high)
    return "0.8~1.0"


def _band_label(low: float, high: float) -> str:
    if high > 1:
        high = 1.0
    return f"{low:.1f}~{high:.1f}"


def _win_rate(success: int, fail: int) -> float | None:
    denominator = success + fail
    if denominator == 0:
        return None
    return round(success / denominator, 4)


def _clamp(value: Any) -> float:
    numeric = _optional_float(value)
    if numeric is None:
        return 0.0
    return round(min(max(numeric, 0.0), 1.0), 4)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
