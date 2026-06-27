"""
Mirror Outcome Distribution Analyzer (Sprint 12AP)

Aggregates Market Outcome results per Decision group for Label Policy design.
No Label generation. No Threshold. No Rule. No Score. Distribution only.
window_duration = campaign_duration (from Outcome Window Evaluator — no recalculation).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean, median, stdev
from time import perf_counter
from typing import Any, Dict, List, Mapping, Optional, Sequence

try:
    import mirror_dataset_contract as dataset_contract
    import mirror_outcome_window_evaluator as window_evaluator
    import mirror_packet_contract
    import mirror_replay_harness
except ImportError:
    from . import mirror_dataset_contract as dataset_contract
    from . import mirror_outcome_window_evaluator as window_evaluator
    from . import mirror_packet_contract
    from . import mirror_replay_harness


ANALYZER_VERSION = "mirror_outcome_distribution_analyzer_v1"

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_DATASET_PATH = DEFAULT_OUTPUT_DIR / "mirror_dataset.jsonl"
DEFAULT_SOURCE_PATH = DEFAULT_OUTPUT_DIR / "mirror_shadow_log.jsonl"

_ANALYSIS_FIELDS = ("mfe", "mae", "return_pct", "window_duration")


def _percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    idx = (p / 100) * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return round(sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo]), 6)


def _field_stats(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {
            "mean": None,
            "median": None,
            "minimum": None,
            "maximum": None,
            "standard_deviation": None,
            "percentile_25": None,
            "percentile_75": None,
            "percentile_90": None,
        }
    return {
        "mean": round(mean(values), 6),
        "median": round(median(values), 6),
        "minimum": round(min(values), 6),
        "maximum": round(max(values), 6),
        "standard_deviation": round(stdev(values), 6) if len(values) >= 2 else None,
        "percentile_25": _percentile(values, 25),
        "percentile_75": _percentile(values, 75),
        "percentile_90": _percentile(values, 90),
    }


def _group_stats(group_evals: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    completed = [e for e in group_evals if e.get("market_outcome", {}).get("completed")]
    incomplete = [e for e in group_evals if not e.get("market_outcome", {}).get("completed")]

    def _vals(field: str) -> List[float]:
        return [e["market_outcome"][field] for e in completed if e["market_outcome"].get(field) is not None]

    ret_vals = _vals("return_pct")

    return {
        "sample_count": len(group_evals),
        "completed_count": len(completed),
        "incomplete_count": len(incomplete),
        "positive_return_count": sum(1 for v in ret_vals if v > 0),
        "negative_return_count": sum(1 for v in ret_vals if v < 0),
        "mfe": _field_stats(_vals("mfe")),
        "mae": _field_stats(_vals("mae")),
        "return_pct": _field_stats(ret_vals),
        "window_duration": _field_stats(_vals("window_duration")),
    }


def build_distribution_by_decision(
    evaluations: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for decision in mirror_packet_contract.DECISION_ENUM:
        group = [e for e in evaluations if e.get("decision") == decision]
        result[decision] = _group_stats(group)
    result["overall"] = _group_stats(evaluations)
    return result


def build_extreme_cases(
    evaluations: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    completed = [e for e in evaluations if e.get("market_outcome", {}).get("completed")]

    def _extreme(field: str, maximize: bool) -> Optional[Dict[str, Any]]:
        candidates = [
            (e["market_outcome"].get(field), e)
            for e in completed
            if e["market_outcome"].get(field) is not None
        ]
        if not candidates:
            return None
        _, ev = (max if maximize else min)(candidates, key=lambda x: x[0])
        return {
            "sample_id": ev.get("sample_id"),
            "decision": ev.get("decision"),
            "packet_hash": ev.get("packet_hash"),
            "market_outcome": ev.get("market_outcome"),
            "created_at": ev.get("window_start"),
        }

    return {
        "max_mfe": _extreme("mfe", maximize=True),
        "max_mae": _extreme("mae", maximize=True),
        "max_return": _extreme("return_pct", maximize=True),
        "min_return": _extreme("return_pct", maximize=False),
        "max_window_duration": _extreme("window_duration", maximize=True),
        "min_window_duration": _extreme("window_duration", maximize=False),
    }


def build_observations(evaluations: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    total = len(evaluations)
    completed = sum(1 for e in evaluations if e.get("market_outcome", {}).get("completed"))
    incomplete = total - completed
    incomplete_ratio = round(incomplete / total, 4) if total > 0 else 0.0

    obs: Dict[str, Any] = {
        "total_sample_count": total,
        "completed_count": completed,
        "incomplete_count": incomplete,
        "incomplete_ratio": incomplete_ratio,
        "time_to_peak_available": False,
        "time_to_trough_available": False,
        "window_duration_basis": "campaign_duration (Replay summary — not candle-level end timestamp)",
    }

    if incomplete > 0:
        obs["incomplete_warning"] = (
            f"incomplete_count={incomplete} ({incomplete_ratio * 100:.1f}%). "
            "Statistics are computed from completed samples only. "
            "Interpret distribution results with caution."
        )

    return obs


def validate_distribution(
    distribution_by_decision: Mapping[str, Any],
) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    for group_name, stats in distribution_by_decision.items():
        if group_name == "overall":
            continue

        # Counts must be consistent
        if stats["completed_count"] + stats["incomplete_count"] != stats["sample_count"]:
            issues.append({"group": group_name, "issue": "count_mismatch"})

        # Mean within [min, max] for each field
        for field in _ANALYSIS_FIELDS:
            fstats = stats.get(field) or {}
            if fstats.get("mean") is not None:
                if not (fstats["minimum"] <= fstats["mean"] <= fstats["maximum"]):
                    issues.append({"group": group_name, "field": field, "issue": "mean_out_of_range"})

        # mfe and mae must be non-negative
        for nonneg_field in ("mfe", "mae"):
            fstats = stats.get(nonneg_field) or {}
            if fstats.get("minimum") is not None and fstats["minimum"] < 0:
                issues.append({"group": group_name, "field": nonneg_field, "issue": "minimum_negative"})

    valid = not issues
    return {
        "distribution_validation_result": "PASS" if valid else "FAIL",
        "issue_count": len(issues),
        "issues": issues,
    }


def run_mirror_outcome_distribution_analyzer(
    *,
    output_dir: Optional["Path | str"] = None,
    source_evaluations: Optional[Sequence[Mapping[str, Any]]] = None,
    source_samples: Optional[Sequence[Mapping[str, Any]]] = None,
    source_packets: Optional[Sequence[Mapping[str, Any]]] = None,
    dataset_path: Optional["Path | str"] = None,
    source_path: Optional["Path | str"] = None,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR

    if source_evaluations is not None:
        evaluations = list(source_evaluations)
    else:
        if source_samples is not None:
            samples = list(source_samples)
        else:
            ds_path = Path(dataset_path) if dataset_path is not None else DEFAULT_DATASET_PATH
            samples = dataset_contract.load_dataset(ds_path)

        if source_packets is not None:
            packets = list(source_packets)
        else:
            src_path = Path(source_path) if source_path is not None else DEFAULT_SOURCE_PATH
            packets = mirror_replay_harness.load_replay_packets(src_path)

        evaluations = window_evaluator.evaluate_dataset_windows(samples, packets)

    started = perf_counter()
    distribution = build_distribution_by_decision(evaluations)
    extreme_cases = build_extreme_cases(evaluations)
    validation = validate_distribution(distribution)
    observations = build_observations(evaluations)
    elapsed_ms = round((perf_counter() - started) * 1000.0, 6)

    report = {
        "analyzer_version": ANALYZER_VERSION,
        "sample_count": len(evaluations),
        "completed_count": observations["completed_count"],
        "incomplete_count": observations["incomplete_count"],
        "incomplete_ratio": observations["incomplete_ratio"],
        "distribution_validation_result": validation["distribution_validation_result"],
        "decision_groups": list(mirror_packet_contract.DECISION_ENUM),
        "observations": observations,
        "elapsed_ms": elapsed_ms,
        "is_trade_command": False,
    }

    stats_output = {
        "statistics_schema_version": "mirror_outcome_distribution_statistics_v1",
        "analyzer_version": ANALYZER_VERSION,
        **distribution,
        "is_trade_command": False,
    }
    extremes_output = {
        "extreme_cases_schema_version": "mirror_outcome_extreme_cases_v1",
        "analyzer_version": ANALYZER_VERSION,
        **extreme_cases,
        "is_trade_command": False,
    }

    _write_json(report, base / "mirror_outcome_distribution_report.json")
    _write_json(distribution, base / "mirror_outcome_distribution_by_decision.json")
    _write_json(extremes_output, base / "mirror_outcome_extreme_cases.json")
    _write_json(stats_output, base / "mirror_outcome_distribution_statistics.json")

    return report


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main() -> int:
    result = run_mirror_outcome_distribution_analyzer()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("distribution_validation_result") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
