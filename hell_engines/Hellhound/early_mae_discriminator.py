from __future__ import annotations

import json
import math
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Dict, Mapping, Optional, Sequence


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
CAMPAIGN_DATASET_PATH = DEFAULT_OUTPUT_DIR / "campaign_replay_dataset.json"
REPLAY_EXPANSION_PATH = DEFAULT_OUTPUT_DIR / "replay_expansion_report.json"
VALIDATION_PATH = DEFAULT_OUTPUT_DIR / "mirror_candidate_validation.json"
CONTRAST_DATASET_PATH = DEFAULT_OUTPUT_DIR / "mirror_contrast_dataset.json"
BTC_REPLAY_DATASET_PATH = DEFAULT_OUTPUT_DIR / "btc_replay_dataset.jsonl"

PHYSICS_CANDIDATES = (
    "early_mae",
    "recovery_ratio",
    "initial_drawdown_velocity",
    "campaign_duration",
)
MIN_SUCCESS = 10
MIN_FAILURE = 10


def run_early_mae_discriminator(
    *,
    output_dir: Optional[Path | str] = None,
    campaign_dataset_path: Path | str = CAMPAIGN_DATASET_PATH,
    replay_expansion_path: Path | str = REPLAY_EXPANSION_PATH,
    validation_path: Path | str = VALIDATION_PATH,
    contrast_dataset_path: Path | str = CONTRAST_DATASET_PATH,
    btc_replay_dataset_path: Path | str = BTC_REPLAY_DATASET_PATH,
) -> Dict[str, Any]:
    campaign_dataset = load_json(campaign_dataset_path)
    replay_expansion = load_json(replay_expansion_path)
    validation = load_json(validation_path)
    source_rows = load_source_rows(contrast_dataset_path, btc_replay_dataset_path)
    campaign_rows = build_campaign_physics_rows(campaign_dataset.get("campaigns") or [], source_rows)
    statistics = build_statistics(campaign_rows)
    candidate_report = build_candidate_report(campaign_rows, statistics)
    confidence = build_confidence(candidate_report, campaign_dataset, replay_expansion, validation)
    discriminator = build_discriminator_output(campaign_rows, candidate_report, confidence)
    physics_summary = build_physics_summary(campaign_rows, statistics, candidate_report, confidence)

    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    paths = {
        "discriminator_path": base / "early_mae_discriminator.json",
        "statistics_path": base / "early_mae_statistics.json",
        "candidate_report_path": base / "early_mae_candidate_report.json",
        "confidence_path": base / "early_mae_confidence.json",
        "physics_summary_path": base / "campaign_physics_summary.json",
    }
    write_json(discriminator, paths["discriminator_path"])
    write_json(statistics, paths["statistics_path"])
    write_json(candidate_report, paths["candidate_report_path"])
    write_json(confidence, paths["confidence_path"])
    write_json(physics_summary, paths["physics_summary_path"])
    return {
        "early_mae_discriminator_run_schema_version": "early_mae_discriminator_run_v1",
        "campaign_count": len(campaign_rows),
        "success_count": sum(1 for row in campaign_rows if row["outcome"] == "SUCCESS"),
        "failure_count": sum(1 for row in campaign_rows if row["outcome"] == "FAILURE"),
        "inconclusive_excluded": True,
        "evidence_level": confidence["overall_evidence_level"],
        "top_candidate": candidate_report["candidate_ranking"][0]["candidate"] if candidate_report["candidate_ranking"] else None,
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def load_source_rows(contrast_dataset_path: Path | str, btc_replay_dataset_path: Path | str) -> Dict[str, list[Dict[str, Any]]]:
    rows_by_source: Dict[str, list[Dict[str, Any]]] = {}
    contrast_path = Path(contrast_dataset_path)
    if contrast_path.exists():
        contrast = load_json(contrast_path)
        for case in contrast.get("cases", []):
            if isinstance(case, Mapping):
                rows_by_source[str(case.get("case_id"))] = [dict(row) for row in case.get("rows") or []]
    btc_rows = load_jsonl(btc_replay_dataset_path)
    if btc_rows:
        rows_by_source["btc-replay-success-BTCUSDT"] = btc_rows
    return rows_by_source


def build_campaign_physics_rows(
    campaigns: Sequence[Mapping[str, Any]],
    source_rows: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[Dict[str, Any]]:
    rows = []
    for campaign in campaigns:
        if campaign.get("outcome") == "INCONCLUSIVE":
            continue
        source = source_rows.get(str(campaign.get("source_case_id") or ""), [])
        replay_rows = filter_rows(source, str(campaign.get("start_time") or ""), str(campaign.get("end_time") or ""))
        physics = compute_campaign_physics(campaign, replay_rows)
        rows.append(
            {
                "campaign_id": campaign.get("campaign_id"),
                "symbol": campaign.get("symbol"),
                "outcome": campaign.get("outcome"),
                "campaign_type": campaign.get("campaign_type"),
                "source_case_id": campaign.get("source_case_id"),
                "source_sample_id": campaign.get("source_sample_id"),
                "start_time": campaign.get("start_time"),
                "end_time": campaign.get("end_time"),
                "early_mae": physics["early_mae"],
                "peak_mfe": physics["peak_mfe"],
                "time_to_early_mae": physics["time_to_early_mae"],
                "time_to_peak_mfe": physics["time_to_peak_mfe"],
                "recovery_time": physics["recovery_time"],
                "recovery_ratio": physics["recovery_ratio"],
                "initial_drawdown_velocity": physics["initial_drawdown_velocity"],
                "campaign_duration": campaign.get("metrics", {}).get("campaign_duration"),
                "row_source_available": bool(replay_rows),
                "is_trade_command": False,
            }
        )
    return rows


def compute_campaign_physics(campaign: Mapping[str, Any], replay_rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    metrics = dict(campaign.get("metrics") or {})
    start_time = str(campaign.get("start_time") or "")
    ignition_time = str(campaign.get("replay", {}).get("ignition_time") or "")
    early_rows = [row for row in replay_rows if str(row.get("timestamp") or "") <= ignition_time]
    if not early_rows:
        early_rows = list(replay_rows)
    early_row = min(
        (row for row in early_rows if _number(row.get("mae_pct")) is not None),
        key=lambda row: _number(row.get("mae_pct")),
        default=None,
    )
    peak_row = max(
        (row for row in replay_rows if _number(row.get("mfe_pct")) is not None),
        key=lambda row: _number(row.get("mfe_pct")),
        default=None,
    )
    early_mae = _number(early_row.get("mae_pct")) if early_row else _number(metrics.get("early_mae"))
    peak_mfe = _number(peak_row.get("mfe_pct")) if peak_row else _number(metrics.get("peak_mfe"))
    early_time = str(early_row.get("timestamp")) if early_row else None
    peak_time = str(peak_row.get("timestamp")) if peak_row else None
    time_to_early = duration_hours(start_time, early_time) if early_time else None
    time_to_peak = duration_hours(start_time, peak_time) if peak_time else None
    recovery_time = diff(time_to_peak, time_to_early)
    recovery_ratio = recovery_ratio_value(early_mae, peak_mfe)
    velocity = drawdown_velocity(early_mae, time_to_early)
    return {
        "early_mae": _round(early_mae),
        "peak_mfe": _round(peak_mfe),
        "time_to_early_mae": _round(time_to_early),
        "time_to_peak_mfe": _round(time_to_peak),
        "recovery_time": _round(recovery_time),
        "recovery_ratio": _round(recovery_ratio),
        "initial_drawdown_velocity": _round(velocity),
    }


def build_statistics(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    groups = {
        "SUCCESS": [row for row in rows if row["outcome"] == "SUCCESS"],
        "FAILURE": [row for row in rows if row["outcome"] == "FAILURE"],
    }
    metrics = (
        "early_mae",
        "peak_mfe",
        "time_to_early_mae",
        "time_to_peak_mfe",
        "recovery_time",
        "recovery_ratio",
        "initial_drawdown_velocity",
        "campaign_duration",
    )
    return {
        "early_mae_statistics_schema_version": "early_mae_statistics_v1",
        "sample_counts": {name: len(group) for name, group in groups.items()},
        "groups": {
            name: {
                metric: describe([_number(row.get(metric)) for row in group])
                for metric in metrics
            }
            for name, group in groups.items()
        },
        "success_failure_delta": {
            metric: diff(
                describe([_number(row.get(metric)) for row in groups["SUCCESS"]])["mean"],
                describe([_number(row.get(metric)) for row in groups["FAILURE"]])["mean"],
            )
            for metric in metrics
        },
        "is_trade_command": False,
    }


def build_candidate_report(rows: Sequence[Mapping[str, Any]], statistics: Mapping[str, Any]) -> Dict[str, Any]:
    ranking = []
    for candidate in PHYSICS_CANDIDATES:
        success = values_for(rows, candidate, "SUCCESS")
        failure = values_for(rows, candidate, "FAILURE")
        direction = "success_higher" if safe_mean(success) >= safe_mean(failure) else "success_lower"
        separation = separation_score(success, failure)
        repeatability = repeatability_score(success, failure, direction)
        discriminator_score = _round((min(separation / 2.0, 1.0) * 0.5) + (repeatability * 0.5))
        ranking.append(
            {
                "candidate": candidate,
                "direction": direction,
                "success_mean": describe(success)["mean"],
                "failure_mean": describe(failure)["mean"],
                "separation_score": _round(separation),
                "repeatability": _round(repeatability),
                "candidate_score": discriminator_score,
                "verdict": candidate_verdict(discriminator_score, repeatability, separation, len(success), len(failure)),
                "is_trade_command": False,
            }
        )
    ranking.sort(key=lambda row: row["candidate_score"], reverse=True)
    for index, row in enumerate(ranking, start=1):
        row["rank"] = index
    checks = {
        "early_mae_discriminator": verdict_for_candidate(ranking, "early_mae"),
        "recovery_ratio_discriminator": verdict_for_candidate(ranking, "recovery_ratio"),
        "initial_drawdown_velocity_discriminator": verdict_for_candidate(ranking, "initial_drawdown_velocity"),
        "campaign_duration_discriminator": verdict_for_candidate(ranking, "campaign_duration"),
    }
    return {
        "early_mae_candidate_report_schema_version": "early_mae_candidate_report_v1",
        "candidate_ranking": ranking,
        "verification_checks": checks,
        "statistics_source": statistics.get("early_mae_statistics_schema_version"),
        "allowed_results": ["VERIFIED", "PARTIAL", "NOT_ENOUGH_EVIDENCE"],
        "is_trade_command": False,
    }


def build_confidence(
    candidate_report: Mapping[str, Any],
    campaign_dataset: Mapping[str, Any],
    replay_expansion: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> Dict[str, Any]:
    success_count = int(campaign_dataset.get("success_campaign_count") or 0)
    failure_count = int(campaign_dataset.get("failure_campaign_count") or 0)
    sample_requirement_met = success_count >= MIN_SUCCESS and failure_count >= MIN_FAILURE
    ranking = list(candidate_report.get("candidate_ranking") or [])
    top = ranking[0] if ranking else {}
    verified = [row for row in ranking if row.get("verdict") == "VERIFIED"]
    partial = [row for row in ranking if row.get("verdict") == "PARTIAL"]
    if verified:
        level = "VERIFIED"
    elif partial:
        level = "PARTIAL"
    else:
        level = "NOT_ENOUGH_EVIDENCE"
    return {
        "early_mae_confidence_schema_version": "early_mae_confidence_v1",
        "overall_evidence_level": level,
        "sample_requirement_met": sample_requirement_met,
        "success_campaign_count": success_count,
        "failure_campaign_count": failure_count,
        "inconclusive_excluded": True,
        "top_candidate": top.get("candidate"),
        "verified_candidates": [row["candidate"] for row in verified],
        "partial_candidates": [row["candidate"] for row in partial],
        "not_enough_evidence_candidates": [
            row["candidate"] for row in ranking if row.get("verdict") == "NOT_ENOUGH_EVIDENCE"
        ],
        "input_sources": {
            "campaign_replay_dataset": campaign_dataset.get("campaign_replay_dataset_schema_version"),
            "replay_expansion_report": replay_expansion.get("replay_expansion_report_schema_version"),
            "mirror_candidate_validation": validation.get("mirror_candidate_validation_schema_version"),
            "binance_historical_pull": "forbidden_not_executed",
        },
        "confidence_note": "Evidence is generated from Campaign Replay rows only; no threshold, gate, score, ML, or production logic was changed.",
        "is_trade_command": False,
    }


def build_discriminator_output(
    rows: Sequence[Mapping[str, Any]],
    candidate_report: Mapping[str, Any],
    confidence: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "early_mae_discriminator_schema_version": "early_mae_discriminator_v1",
        "objective": "Test whether Early MAE and derived campaign physics metrics distinguish Success and Failure Campaigns.",
        "campaign_physics_rows": list(rows),
        "candidate_ranking": candidate_report.get("candidate_ranking"),
        "evidence_level": confidence.get("overall_evidence_level"),
        "forbidden_actions_confirmed": [
            "No Mirror Pattern implementation",
            "No ML training",
            "No threshold change",
            "No gate change",
            "No score calculation change",
            "No Replay mutation",
            "No Production code change",
        ],
        "is_trade_command": False,
    }


def build_physics_summary(
    rows: Sequence[Mapping[str, Any]],
    statistics: Mapping[str, Any],
    candidate_report: Mapping[str, Any],
    confidence: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "campaign_physics_summary_schema_version": "campaign_physics_summary_v1",
        "campaign_count": len(rows),
        "success_count": sum(1 for row in rows if row["outcome"] == "SUCCESS"),
        "failure_count": sum(1 for row in rows if row["outcome"] == "FAILURE"),
        "evidence_level": confidence.get("overall_evidence_level"),
        "verified": confidence.get("verified_candidates"),
        "not_verified": confidence.get("not_enough_evidence_candidates"),
        "partial": confidence.get("partial_candidates"),
        "candidate_ranking": candidate_report.get("candidate_ranking"),
        "key_deltas": statistics.get("success_failure_delta"),
        "next_sprint_recommendation": next_sprint_recommendation(confidence),
        "is_trade_command": False,
    }


def values_for(rows: Sequence[Mapping[str, Any]], metric: str, outcome: str) -> list[float]:
    return [
        float(value)
        for value in (_number(row.get(metric)) for row in rows if row.get("outcome") == outcome)
        if value is not None
    ]


def repeatability_score(success: Sequence[float], failure: Sequence[float], direction: str) -> float:
    if not success or not failure:
        return 0.0
    pivot = median(list(success) + list(failure))
    if direction == "success_higher":
        success_hits = sum(1 for value in success if value > pivot)
        failure_hits = sum(1 for value in failure if value <= pivot)
    else:
        success_hits = sum(1 for value in success if value < pivot)
        failure_hits = sum(1 for value in failure if value >= pivot)
    return ((success_hits / len(success)) + (failure_hits / len(failure))) / 2.0


def separation_score(success: Sequence[float], failure: Sequence[float]) -> float:
    if not success or not failure:
        return 0.0
    success_sd = stdev(success) if len(success) > 1 else 0.0
    failure_sd = stdev(failure) if len(failure) > 1 else 0.0
    pooled = math.sqrt((success_sd**2 + failure_sd**2) / 2.0)
    if pooled == 0:
        return 0.0 if mean(success) == mean(failure) else 9.999999
    return abs(mean(success) - mean(failure)) / pooled


def candidate_verdict(score: Optional[float], repeatability: float, separation: float, success_count: int, failure_count: int) -> str:
    if success_count < MIN_SUCCESS or failure_count < MIN_FAILURE:
        return "NOT_ENOUGH_EVIDENCE"
    score_value = float(score or 0.0)
    if score_value >= 0.75 and repeatability >= 0.7 and separation >= 1.0:
        return "VERIFIED"
    if score_value >= 0.55 and repeatability >= 0.6:
        return "PARTIAL"
    return "NOT_ENOUGH_EVIDENCE"


def verdict_for_candidate(ranking: Sequence[Mapping[str, Any]], candidate: str) -> str:
    match = next((row for row in ranking if row.get("candidate") == candidate), None)
    return str(match.get("verdict")) if match else "NOT_ENOUGH_EVIDENCE"


def next_sprint_recommendation(confidence: Mapping[str, Any]) -> str:
    if confidence.get("overall_evidence_level") == "VERIFIED":
        return "Review verified Campaign Physics evidence before considering any Mirror or Campaign Intelligence design."
    if confidence.get("overall_evidence_level") == "PARTIAL":
        return "Expand Campaign Replay evidence before implementation; Early MAE physics is promising but not final."
    return "Do not implement Mirror or Campaign logic; collect more Campaign Replay evidence."


def recovery_ratio_value(early_mae: Optional[float], peak_mfe: Optional[float]) -> Optional[float]:
    if early_mae is None or peak_mfe is None:
        return None
    denominator = abs(float(early_mae))
    if denominator == 0:
        return None
    return float(peak_mfe) / denominator


def drawdown_velocity(early_mae: Optional[float], time_to_early: Optional[float]) -> Optional[float]:
    if early_mae is None or time_to_early is None:
        return None
    denominator = max(float(time_to_early), 0.25)
    return float(early_mae) / denominator


def filter_rows(rows: Sequence[Mapping[str, Any]], start_time: str, end_time: str) -> list[Dict[str, Any]]:
    return [dict(row) for row in rows if start_time <= str(row.get("timestamp") or "") <= end_time]


def duration_hours(start: str, end: Optional[str]) -> Optional[float]:
    if not end:
        return None
    try:
        left = datetime.fromisoformat(start)
        right = datetime.fromisoformat(end)
    except ValueError:
        return None
    return (right - left).total_seconds() / 3600.0


def describe(values: Sequence[Optional[float]]) -> Dict[str, Any]:
    parsed = [float(value) for value in values if value is not None]
    return {
        "count": len(parsed),
        "mean": _round(mean(parsed)) if parsed else None,
        "median": _round(median(parsed)) if parsed else None,
        "std": _round(stdev(parsed)) if len(parsed) > 1 else 0.0 if parsed else None,
        "min": _round(min(parsed)) if parsed else None,
        "max": _round(max(parsed)) if parsed else None,
    }


def safe_mean(values: Sequence[float]) -> float:
    return mean(values) if values else 0.0


def diff(left: Any, right: Any) -> Optional[float]:
    left_value = _number(left)
    right_value = _number(right)
    if left_value is None or right_value is None:
        return None
    return _round(left_value - right_value)


def load_json(path: Path | str) -> Dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    data = json.loads(file_path.read_text(encoding="utf-8"))
    return dict(data) if isinstance(data, Mapping) else {}


def load_jsonl(path: Path | str) -> list[Dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if isinstance(row, Mapping) and row.get("is_trade_command") is False:
                rows.append(dict(row))
    return rows


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: Optional[float]) -> Optional[float]:
    return round(float(value), 6) if value is not None else None


def main() -> int:
    result = run_early_mae_discriminator()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
