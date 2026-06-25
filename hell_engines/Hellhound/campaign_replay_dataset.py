from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Dict, Mapping, Optional, Sequence


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
VALIDATION_PATH = DEFAULT_OUTPUT_DIR / "mirror_candidate_validation.json"
CONTRAST_DATASET_PATH = DEFAULT_OUTPUT_DIR / "mirror_contrast_dataset.json"
BTC_REPLAY_DATASET_PATH = DEFAULT_OUTPUT_DIR / "btc_replay_dataset.jsonl"

FEATURES = ("hellhound_score", "rsi_15m", "volume_ratio_ma20")
CAMPAIGN_METRICS = (
    "score_slope",
    "rsi_persistence",
    "volume_delay",
    "early_mae",
    "peak_mfe",
    "campaign_duration",
    "ignition_delay",
)
MIN_SUCCESS_CAMPAIGNS = 10
MIN_FAILURE_CAMPAIGNS = 10


def run_campaign_replay_dataset(
    *,
    output_dir: Optional[Path | str] = None,
    validation_path: Path | str = VALIDATION_PATH,
    contrast_dataset_path: Path | str = CONTRAST_DATASET_PATH,
    btc_replay_dataset_path: Path | str = BTC_REPLAY_DATASET_PATH,
) -> Dict[str, Any]:
    validation = load_json(validation_path)
    source_rows = load_source_rows(contrast_dataset_path, btc_replay_dataset_path)
    campaigns = build_campaigns(list(validation.get("samples") or []), source_rows)
    dataset = build_campaign_dataset(campaigns)
    timeline = build_feature_timeline(campaigns)
    statistics = build_campaign_statistics(campaigns)
    duration = build_duration_distribution(campaigns)
    matrix = build_candidate_matrix(campaigns)
    summary = build_summary_report(campaigns, dataset, statistics, matrix)

    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    paths = {
        "dataset_path": base / "campaign_replay_dataset.json",
        "summary_path": base / "campaign_summary_report.json",
        "statistics_path": base / "campaign_statistics.json",
        "timeline_path": base / "campaign_feature_timeline.json",
        "duration_distribution_path": base / "campaign_duration_distribution.json",
        "candidate_matrix_path": base / "campaign_candidate_matrix.json",
    }
    write_json(dataset, paths["dataset_path"])
    write_json(summary, paths["summary_path"])
    write_json(statistics, paths["statistics_path"])
    write_json(timeline, paths["timeline_path"])
    write_json(duration, paths["duration_distribution_path"])
    write_json(matrix, paths["candidate_matrix_path"])
    return {
        "campaign_replay_dataset_run_schema_version": "campaign_replay_dataset_run_v1",
        "campaign_count": len(campaigns),
        "success_campaign_count": sum(1 for campaign in campaigns if campaign["outcome"] == "SUCCESS"),
        "failure_campaign_count": sum(1 for campaign in campaigns if campaign["outcome"] == "FAILURE"),
        "inconclusive_campaign_count": sum(1 for campaign in campaigns if campaign["outcome"] == "INCONCLUSIVE"),
        "sprint_status": dataset["sprint_status"],
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


def build_campaigns(samples: Sequence[Mapping[str, Any]], source_rows: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[Dict[str, Any]]:
    campaigns = []
    for index, sample in enumerate(samples, start=1):
        source_case_id = str(sample.get("source_case_id") or "")
        rows = [dict(row) for row in source_rows.get(source_case_id, [])]
        window_rows = filter_rows(rows, str(sample.get("coverage_start")), str(sample.get("coverage_end")))
        if not window_rows:
            continue
        target = dict(sample.get("target") or {})
        campaign = build_campaign(index, sample, window_rows, target)
        campaigns.append(campaign)
    campaigns.sort(key=lambda row: (row["outcome"], row["campaign_id"]))
    return campaigns


def build_campaign(index: int, sample: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], target: Mapping[str, Any]) -> Dict[str, Any]:
    case_type = str(sample.get("case_type") or "")
    outcome = "SUCCESS" if case_type == "success" else "FAILURE" if case_type == "failure" else "INCONCLUSIVE"
    symbol = str(sample.get("symbol") or target.get("symbol") or "")
    start_time = str(sample.get("coverage_start") or rows[0].get("timestamp"))
    end_time = str(sample.get("coverage_end") or rows[-1].get("timestamp"))
    ignition_time = str(target.get("ignition_time") or sample.get("anchor_timestamp") or "")
    peak_time = str(target.get("local_peak_time") or ignition_time)
    expansion_start = first_timestamp_after(rows, ignition_time) or ignition_time
    campaign_id = f"campaign-{index:03d}-{symbol}-{outcome.lower()}"
    feature_timeline = build_timeline_rows(rows, ignition_time, peak_time, outcome)
    metrics = campaign_metrics(rows, feature_timeline, sample, start_time, ignition_time, end_time)
    return {
        "campaign_id": campaign_id,
        "source_sample_id": sample.get("sample_id"),
        "source_case_id": sample.get("source_case_id"),
        "sample_source": sample.get("sample_source"),
        "symbol": symbol,
        "campaign_type": f"{outcome}_CAMPAIGN",
        "start_time": start_time,
        "end_time": end_time,
        "duration": metrics["campaign_duration"],
        "replay": {
            "accumulation_start": target.get("accumulation_start") or start_time,
            "ignition_time": ignition_time,
            "expansion_start": expansion_start,
            "peak_time": peak_time,
            "distribution_time": peak_time if outcome == "SUCCESS" else None,
            "failure_time": end_time if outcome == "FAILURE" else None,
        },
        "outcome": outcome,
        "failure_archetype": sample.get("failure_archetype"),
        "metrics": metrics,
        "feature_timeline": feature_timeline,
        "is_trade_command": False,
    }


def build_timeline_rows(
    rows: Sequence[Mapping[str, Any]],
    ignition_time: str,
    peak_time: str,
    outcome: str,
) -> list[Dict[str, Any]]:
    timeline = []
    for row in rows:
        timestamp = str(row.get("timestamp") or "")
        timeline.append(
            {
                "timestamp": timestamp,
                "phase": phase_for(timestamp, rows[0].get("timestamp"), ignition_time, peak_time, outcome),
                "hellhound_score": _number(row.get("hellhound_score")),
                "rsi_15m": _number(row.get("rsi_15m")),
                "volume_ratio_ma20": _number(row.get("volume_ratio_ma20")),
                "is_trade_command": False,
            }
        )
    return timeline


def campaign_metrics(
    rows: Sequence[Mapping[str, Any]],
    timeline: Sequence[Mapping[str, Any]],
    sample: Mapping[str, Any],
    start_time: str,
    ignition_time: str,
    end_time: str,
) -> Dict[str, Any]:
    candidate_metrics = sample.get("candidate_metrics", {})
    early_rows = [row for row in rows if str(row.get("timestamp") or "") <= ignition_time]
    mae_values = [_number(row.get("mae_pct")) for row in early_rows]
    mfe_values = [_number(row.get("mfe_pct")) for row in rows]
    return {
        "score_slope": candidate_metrics.get("score_slope", {}).get("primary_value"),
        "rsi_persistence": candidate_metrics.get("rsi_persistence", {}).get("primary_value"),
        "volume_delay": candidate_metrics.get("volume_delay", {}).get("primary_value"),
        "early_mae": _round(min(value for value in mae_values if value is not None)) if any(value is not None for value in mae_values) else None,
        "peak_mfe": _round(max(value for value in mfe_values if value is not None)) if any(value is not None for value in mfe_values) else None,
        "campaign_duration": duration_hours(start_time, end_time),
        "campaign_duration_candles": len(rows),
        "ignition_delay": duration_hours(start_time, ignition_time),
        "candidate_stage_summary": candidate_stage_summary(timeline),
        "is_trade_command": False,
    }


def candidate_stage_summary(timeline: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    summary = {}
    for feature in FEATURES:
        values = [(row["phase"], _number(row.get(feature))) for row in timeline]
        present_phases = sorted({phase for phase, value in values if value is not None})
        max_phase = max_present_phase(values)
        collapse = collapse_phase(values)
        summary[feature] = {
            "appears_in_phases": present_phases,
            "max_average_phase": max_phase,
            "collapse_phase": collapse,
            "persistence_candles": persistence_candles([value for _, value in values]),
        }
    return summary


def build_campaign_dataset(campaigns: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    success_count = sum(1 for campaign in campaigns if campaign["outcome"] == "SUCCESS")
    failure_count = sum(1 for campaign in campaigns if campaign["outcome"] == "FAILURE")
    status = "COMPLETE" if success_count >= MIN_SUCCESS_CAMPAIGNS and failure_count >= MIN_FAILURE_CAMPAIGNS else "PARTIAL"
    return {
        "campaign_replay_dataset_schema_version": "campaign_replay_dataset_v1",
        "sprint_status": status,
        "sample_requirement": {
            "success_campaign_min": MIN_SUCCESS_CAMPAIGNS,
            "failure_campaign_min": MIN_FAILURE_CAMPAIGNS,
            "inconclusive_excluded_from_minimum": True,
        },
        "campaign_count": len(campaigns),
        "success_campaign_count": success_count,
        "failure_campaign_count": failure_count,
        "inconclusive_campaign_count": sum(1 for campaign in campaigns if campaign["outcome"] == "INCONCLUSIVE"),
        "campaigns": [
            {key: value for key, value in campaign.items() if key != "feature_timeline"}
            for campaign in campaigns
        ],
        "is_trade_command": False,
    }


def build_feature_timeline(campaigns: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        "campaign_feature_timeline_schema_version": "campaign_feature_timeline_v1",
        "features": list(FEATURES),
        "campaigns": [
            {
                "campaign_id": campaign["campaign_id"],
                "symbol": campaign["symbol"],
                "outcome": campaign["outcome"],
                "timeline": campaign["feature_timeline"],
                "is_trade_command": False,
            }
            for campaign in campaigns
        ],
        "is_trade_command": False,
    }


def build_campaign_statistics(campaigns: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    groups = {
        "SUCCESS": [campaign for campaign in campaigns if campaign["outcome"] == "SUCCESS"],
        "FAILURE": [campaign for campaign in campaigns if campaign["outcome"] == "FAILURE"],
        "INCONCLUSIVE": [campaign for campaign in campaigns if campaign["outcome"] == "INCONCLUSIVE"],
    }
    return {
        "campaign_statistics_schema_version": "campaign_statistics_v1",
        "groups": {
            name: {
                "count": len(rows),
                "metrics": {metric: describe(metric_values(rows, metric)) for metric in CAMPAIGN_METRICS},
            }
            for name, rows in groups.items()
        },
        "success_failure_comparison": compare_groups(groups["SUCCESS"], groups["FAILURE"]),
        "is_trade_command": False,
    }


def build_duration_distribution(campaigns: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        "campaign_duration_distribution_schema_version": "campaign_duration_distribution_v1",
        "duration_hours": {
            "SUCCESS": describe(metric_values([campaign for campaign in campaigns if campaign["outcome"] == "SUCCESS"], "campaign_duration")),
            "FAILURE": describe(metric_values([campaign for campaign in campaigns if campaign["outcome"] == "FAILURE"], "campaign_duration")),
            "INCONCLUSIVE": describe(metric_values([campaign for campaign in campaigns if campaign["outcome"] == "INCONCLUSIVE"], "campaign_duration")),
        },
        "duration_candles": {
            "SUCCESS": describe([_number(campaign["metrics"].get("campaign_duration_candles")) for campaign in campaigns if campaign["outcome"] == "SUCCESS"]),
            "FAILURE": describe([_number(campaign["metrics"].get("campaign_duration_candles")) for campaign in campaigns if campaign["outcome"] == "FAILURE"]),
            "INCONCLUSIVE": describe([_number(campaign["metrics"].get("campaign_duration_candles")) for campaign in campaigns if campaign["outcome"] == "INCONCLUSIVE"]),
        },
        "is_trade_command": False,
    }


def build_candidate_matrix(campaigns: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = []
    for campaign in campaigns:
        stage = campaign["metrics"]["candidate_stage_summary"]
        rows.append(
            {
                "campaign_id": campaign["campaign_id"],
                "symbol": campaign["symbol"],
                "outcome": campaign["outcome"],
                "score_slope": campaign["metrics"]["score_slope"],
                "rsi_persistence": campaign["metrics"]["rsi_persistence"],
                "volume_delay": campaign["metrics"]["volume_delay"],
                "feature_phase_summary": stage,
                "is_trade_command": False,
            }
        )
    return {
        "campaign_candidate_matrix_schema_version": "campaign_candidate_matrix_v1",
        "candidate_metrics": ["score_slope", "rsi_persistence", "volume_delay"],
        "features": list(FEATURES),
        "rows": rows,
        "phase_comparison": phase_comparison(rows),
        "is_trade_command": False,
    }


def build_summary_report(
    campaigns: Sequence[Mapping[str, Any]],
    dataset: Mapping[str, Any],
    statistics: Mapping[str, Any],
    matrix: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "campaign_summary_report_schema_version": "campaign_summary_report_v1",
        "sprint_status": dataset["sprint_status"],
        "campaign_count": len(campaigns),
        "success_campaign_count": dataset["success_campaign_count"],
        "failure_campaign_count": dataset["failure_campaign_count"],
        "inconclusive_campaign_count": dataset["inconclusive_campaign_count"],
        "sample_requirement_met": dataset["sprint_status"] == "COMPLETE",
        "source_priority_used": [
            "outputs/ existing Replay Dataset expansion",
            "hound_positions real trade history if needed",
            "Binance Historical Pull only if required",
        ],
        "binance_pull_executed": False,
        "forbidden_actions_confirmed": [
            "No Mirror Pattern Layer implementation",
            "No ML training",
            "No threshold change",
            "No Hellhound Score calculation change",
            "No gate change",
            "No Replay data mutation",
            "No new candidate feature",
        ],
        "outcome_metric_summary": statistics.get("success_failure_comparison"),
        "phase_comparison": matrix.get("phase_comparison"),
        "is_trade_command": False,
    }


def phase_for(timestamp: str, start_time: Any, ignition_time: str, peak_time: str, outcome: str) -> str:
    start = str(start_time or "")
    if timestamp < ignition_time:
        midpoint = midpoint_time(start, ignition_time)
        return "Pre-Accumulation" if midpoint and timestamp < midpoint else "Accumulation"
    if timestamp == ignition_time:
        return "Ignition"
    if timestamp <= peak_time:
        return "Expansion"
    return "Distribution" if outcome == "SUCCESS" else "Failure"


def phase_comparison(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for outcome in ("SUCCESS", "FAILURE"):
        outcome_rows = [row for row in rows if row["outcome"] == outcome]
        result[outcome] = {}
        for feature in FEATURES:
            phase_counts: Dict[str, int] = {}
            collapse_counts: Dict[str, int] = {}
            for row in outcome_rows:
                summary = row["feature_phase_summary"][feature]
                for phase in summary["appears_in_phases"]:
                    phase_counts[phase] = phase_counts.get(phase, 0) + 1
                collapse = summary["collapse_phase"]
                if collapse:
                    collapse_counts[collapse] = collapse_counts.get(collapse, 0) + 1
            result[outcome][feature] = {
                "appearance_phase_counts": phase_counts,
                "collapse_phase_counts": collapse_counts,
            }
    return result


def compare_groups(success: Sequence[Mapping[str, Any]], failure: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    comparison = {}
    for metric in CAMPAIGN_METRICS:
        success_mean = describe(metric_values(success, metric))["mean"]
        failure_mean = describe(metric_values(failure, metric))["mean"]
        comparison[metric] = {
            "success_mean": success_mean,
            "failure_mean": failure_mean,
            "delta_success_minus_failure": diff(success_mean, failure_mean),
        }
    return comparison


def metric_values(campaigns: Sequence[Mapping[str, Any]], metric: str) -> list[Optional[float]]:
    return [_number(campaign.get("metrics", {}).get(metric)) for campaign in campaigns]


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


def max_present_phase(values: Sequence[tuple[str, Optional[float]]]) -> Optional[str]:
    phase_values: Dict[str, list[float]] = {}
    for phase, value in values:
        if value is not None:
            phase_values.setdefault(phase, []).append(value)
    if not phase_values:
        return None
    return max(phase_values, key=lambda phase: mean(phase_values[phase]))


def collapse_phase(values: Sequence[tuple[str, Optional[float]]]) -> Optional[str]:
    parsed = [(phase, float(value)) for phase, value in values if value is not None]
    if len(parsed) < 2:
        return None
    largest_drop = 0.0
    collapse = None
    for (previous_phase, previous), (current_phase, current) in zip(parsed, parsed[1:]):
        del previous_phase
        drop = previous - current
        if drop > largest_drop:
            largest_drop = drop
            collapse = current_phase
    return collapse


def persistence_candles(values: Sequence[Optional[float]]) -> int:
    series = [value for value in values if value is not None]
    best = current = 0
    for previous, current_value in zip(series, series[1:]):
        if current_value >= previous:
            current += 1
        else:
            current = 0
        best = max(best, current)
    return best


def filter_rows(rows: Sequence[Mapping[str, Any]], start_time: str, end_time: str) -> list[Dict[str, Any]]:
    return [dict(row) for row in rows if start_time <= str(row.get("timestamp") or "") <= end_time]


def first_timestamp_after(rows: Sequence[Mapping[str, Any]], timestamp: str) -> Optional[str]:
    for row in rows:
        current = str(row.get("timestamp") or "")
        if current > timestamp:
            return current
    return None


def duration_hours(start: str, end: str) -> Optional[float]:
    try:
        left = datetime.fromisoformat(start)
        right = datetime.fromisoformat(end)
    except ValueError:
        return None
    return _round((right - left).total_seconds() / 3600.0)


def midpoint_time(start: str, end: str) -> Optional[str]:
    try:
        left = datetime.fromisoformat(start)
        right = datetime.fromisoformat(end)
    except ValueError:
        return None
    return (left + (right - left) / 2).isoformat()


def diff(left: Any, right: Any) -> Optional[float]:
    left_value = _number(left)
    right_value = _number(right)
    if left_value is None or right_value is None:
        return None
    return _round(left_value - right_value)


def load_json(path: Path | str) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
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
    result = run_campaign_replay_dataset()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
