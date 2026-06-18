from __future__ import annotations


MAX_INFLUENCE = {
    "CORE": 0.20,
    "WARD": 0.15,
    "HOUND": 0.30,
}

POLICY_REASON = {
    "CORE": "Core is the BTC mainline engine, so LAB influence stays conservative.",
    "WARD": "Ward is the survival engine, so LAB influence stays most conservative.",
    "HOUND": "Hound consumes target priority boosts, so LAB influence can be larger.",
}


def get_max_influence(engine: str) -> float:
    normalized = str(engine).upper()
    if normalized not in MAX_INFLUENCE:
        raise ValueError(f"unsupported engine for calibration policy: {engine}")
    return MAX_INFLUENCE[normalized]


def get_policy_reason(engine: str) -> str:
    normalized = str(engine).upper()
    if normalized not in POLICY_REASON:
        raise ValueError(f"unsupported engine for calibration policy: {engine}")
    return POLICY_REASON[normalized]
