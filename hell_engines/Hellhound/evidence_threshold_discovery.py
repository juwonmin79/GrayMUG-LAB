from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Dict, Mapping, Optional, Sequence


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
VALIDATION_PATH = DEFAULT_OUTPUT_DIR / "mirror_candidate_validation.json"
STATISTICS_PATH = DEFAULT_OUTPUT_DIR / "mirror_candidate_statistics.json"
RANKING_PATH = DEFAULT_OUTPUT_DIR / "mirror_discriminator_ranking.json"
EXPANSION_REPORT_PATH = DEFAULT_OUTPUT_DIR / "replay_expansion_report.json"
CONTRAST_DATASET_PATH = DEFAULT_OUTPUT_DIR / "mirror_contrast_dataset.json"

CANDIDATES = {
    "hellhound_score_slope": "score_slope",
    "rsi_persistence": "rsi_persistence",
    "volume_delay": "volume_delay",
}
PERCENTILES = (10, 25, 50, 75, 90)


def run_evidence_threshold_discovery(
    *,
    output_dir: Optional[Path | str] = None,
    validation_path: Path | str = VALIDATION_PATH,
    statistics_path: Path | str = STATISTICS_PATH,
    ranking_path: Path | str = RANKING_PATH,
    expansion_report_path: Path | str = EXPANSION_REPORT_PATH,
    contrast_dataset_path: Path | str = CONTRAST_DATASET_PATH,
) -> Dict[str, Any]:
    inputs = {
        "replay_expansion_report": load_json(expansion_report_path),
        "mirror_candidate_validation": load_json(validation_path),
        "mirror_candidate_statistics": load_json(statistics_path),
        "mirror_discriminator_ranking": load_json(ranking_path),
        "mirror_contrast_dataset": load_json(contrast_dataset_path),
    }
    samples = list(inputs["mirror_candidate_validation"].get("samples") or [])
    distributions = build_distribution_report(samples)
    scans = build_threshold_scan(samples)
    best = build_best_thresholds(scans)
    confidence = build_threshold_confidence(best, distributions, inputs)
    candidates = build_threshold_candidates(best, distributions, confidence)

    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    paths = {
        "threshold_candidates_path": base / "evidence_threshold_candidates.json",
        "distribution_report_path": base / "candidate_distribution_report.json",
        "threshold_scan_path": base / "candidate_threshold_scan.json",
        "best_threshold_path": base / "candidate_best_threshold.json",
        "threshold_confidence_path": base / "candidate_threshold_confidence.json",
    }
    write_json(candidates, paths["threshold_candidates_path"])
    write_json(distributions, paths["distribution_report_path"])
    write_json(scans, paths["threshold_scan_path"])
    write_json(best, paths["best_threshold_path"])
    write_json(confidence, paths["threshold_confidence_path"])
    return {
        "evidence_threshold_discovery_schema_version": "evidence_threshold_discovery_run_v1",
        "candidate_count": len(CANDIDATES),
        "sample_count": len(samples),
        "success_count": sum(1 for sample in samples if sample.get("case_type") == "success"),
        "failure_count": sum(1 for sample in samples if sample.get("case_type") == "failure"),
        "verdicts": {row["candidate"]: row["verdict"] for row in candidates["candidates"]},
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def build_distribution_report(samples: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = []
    for public_name, metric_name in CANDIDATES.items():
        success = candidate_values(samples, metric_name, "success")
        failure = candidate_values(samples, metric_name, "failure")
        rows.append(
            {
                "candidate": public_name,
                "source_metric": metric_name,
                "distribution": {
                    "success": describe_distribution(success),
                    "failure": describe_distribution(failure),
                },
                "is_trade_command": False,
            }
        )
    return {
        "candidate_distribution_report_schema_version": "candidate_distribution_report_v1",
        "candidates": rows,
        "is_trade_command": False,
    }


def build_threshold_scan(samples: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    candidates = []
    for public_name, metric_name in CANDIDATES.items():
        values = labeled_values(samples, metric_name)
        thresholds = threshold_grid([value for value, _ in values])
        scan_rows = []
        for direction in ("success_higher", "success_lower"):
            for threshold in thresholds:
                metrics = classification_metrics(values, threshold, direction)
                scan_rows.append(
                    {
                        "threshold": _round(threshold),
                        "direction": direction,
                        **metrics,
                        "is_trade_command": False,
                    }
                )
        scan_rows.sort(
            key=lambda row: (
                -float(row["balanced_accuracy"]),
                -float(row["f1"]),
                -float(row["precision"]),
                row["direction"],
                float(row["threshold"]),
            )
        )
        candidates.append(
            {
                "candidate": public_name,
                "source_metric": metric_name,
                "scan_count": len(scan_rows),
                "threshold_scan": scan_rows,
                "is_trade_command": False,
            }
        )
    return {
        "candidate_threshold_scan_schema_version": "candidate_threshold_scan_v1",
        "selection_sort": "best balanced accuracy, then F1, then precision, then deterministic threshold order",
        "candidates": candidates,
        "is_trade_command": False,
    }


def build_best_thresholds(scan_report: Mapping[str, Any]) -> Dict[str, Any]:
    rows = []
    for item in scan_report.get("candidates", []):
        best = dict((item.get("threshold_scan") or [{}])[0])
        rows.append(
            {
                "candidate": item["candidate"],
                "source_metric": item["source_metric"],
                "evidence_threshold": best.get("threshold"),
                "direction": best.get("direction"),
                "precision": best.get("precision"),
                "recall": best.get("recall"),
                "f1": best.get("f1"),
                "balanced_accuracy": best.get("balanced_accuracy"),
                "confusion": best.get("confusion"),
                "threshold_source": "Replay Dataset ROC-style exhaustive scan",
                "is_trade_command": False,
            }
        )
    return {
        "candidate_best_threshold_schema_version": "candidate_best_threshold_v1",
        "candidates": rows,
        "is_trade_command": False,
    }


def build_threshold_confidence(
    best_report: Mapping[str, Any],
    distribution_report: Mapping[str, Any],
    inputs: Mapping[str, Any],
) -> Dict[str, Any]:
    distribution_by_candidate = {row["candidate"]: row for row in distribution_report.get("candidates", [])}
    ranking_by_candidate = {
        normalize_candidate_name(row.get("candidate")): row
        for row in inputs["mirror_discriminator_ranking"].get("ranking", [])
    }
    rows = []
    for row in best_report.get("candidates", []):
        distribution = distribution_by_candidate[row["candidate"]]["distribution"]
        temporary = temporary_threshold_proxy(distribution, row["direction"])
        temporary_metrics = temporary["metrics"]
        evidence_metrics = {
            "precision": row["precision"],
            "recall": row["recall"],
            "f1": row["f1"],
            "balanced_accuracy": row["balanced_accuracy"],
        }
        verdict = verdict_for(row, distribution)
        rank_row = ranking_by_candidate.get(row["candidate"], {})
        rows.append(
            {
                "candidate": row["candidate"],
                "temporary_threshold": temporary["threshold"],
                "temporary_threshold_source": temporary["source"],
                "evidence_threshold": row["evidence_threshold"],
                "direction": row["direction"],
                "threshold_difference": diff(row["evidence_threshold"], temporary["threshold"]),
                "precision_change": diff(evidence_metrics["precision"], temporary_metrics["precision"]),
                "recall_change": diff(evidence_metrics["recall"], temporary_metrics["recall"]),
                "f1_change": diff(evidence_metrics["f1"], temporary_metrics["f1"]),
                "balanced_accuracy_change": diff(evidence_metrics["balanced_accuracy"], temporary_metrics["balanced_accuracy"]),
                "temporary_metrics": temporary_metrics,
                "evidence_metrics": evidence_metrics,
                "previous_stability_score": rank_row.get("mirror_candidate_stability_score"),
                "verdict": verdict,
                "confidence_note": confidence_note(verdict, distribution),
                "is_trade_command": False,
            }
        )
    return {
        "candidate_threshold_confidence_schema_version": "candidate_threshold_confidence_v1",
        "threshold_comparison_note": "Temporary threshold is the Sprint 12P median-pivot proxy used in repeatability calculation, not a hardcoded production threshold.",
        "allowed_verdicts": ["SUPPORTED_BY_DATA", "NOT_ENOUGH_EVIDENCE", "REJECT"],
        "candidates": rows,
        "is_trade_command": False,
    }


def build_threshold_candidates(
    best_report: Mapping[str, Any],
    distribution_report: Mapping[str, Any],
    confidence_report: Mapping[str, Any],
) -> Dict[str, Any]:
    distribution_by_candidate = {row["candidate"]: row for row in distribution_report.get("candidates", [])}
    confidence_by_candidate = {row["candidate"]: row for row in confidence_report.get("candidates", [])}
    rows = []
    for row in best_report.get("candidates", []):
        confidence = confidence_by_candidate[row["candidate"]]
        rows.append(
            {
                "candidate": row["candidate"],
                "evidence_threshold": row["evidence_threshold"],
                "direction": row["direction"],
                "precision": row["precision"],
                "recall": row["recall"],
                "f1": row["f1"],
                "balanced_accuracy": row["balanced_accuracy"],
                "verdict": confidence["verdict"],
                "distribution": distribution_by_candidate[row["candidate"]]["distribution"],
                "comparison_to_temporary": {
                    "temporary_threshold": confidence["temporary_threshold"],
                    "threshold_difference": confidence["threshold_difference"],
                    "precision_change": confidence["precision_change"],
                    "recall_change": confidence["recall_change"],
                    "f1_change": confidence["f1_change"],
                    "balanced_accuracy_change": confidence["balanced_accuracy_change"],
                },
                "candidate_state": "Evidence Threshold Candidate",
                "is_trade_command": False,
            }
        )
    return {
        "evidence_threshold_candidates_schema_version": "evidence_threshold_candidates_v1",
        "candidate_scope": list(CANDIDATES.keys()),
        "new_candidate_added": False,
        "verdict_vocabulary": ["SUPPORTED_BY_DATA", "NOT_ENOUGH_EVIDENCE", "REJECT"],
        "candidates": rows,
        "is_trade_command": False,
    }


def candidate_values(samples: Sequence[Mapping[str, Any]], metric_name: str, case_type: str) -> list[float]:
    values = []
    for sample in samples:
        if sample.get("case_type") != case_type:
            continue
        value = sample.get("candidate_metrics", {}).get(metric_name, {}).get("primary_value")
        parsed = _number(value)
        if parsed is not None:
            values.append(parsed)
    return values


def labeled_values(samples: Sequence[Mapping[str, Any]], metric_name: str) -> list[tuple[float, str]]:
    values = []
    for sample in samples:
        case_type = str(sample.get("case_type") or "")
        value = sample.get("candidate_metrics", {}).get(metric_name, {}).get("primary_value")
        parsed = _number(value)
        if parsed is not None and case_type in {"success", "failure"}:
            values.append((parsed, case_type))
    return values


def describe_distribution(values: Sequence[float]) -> Dict[str, Any]:
    return {
        "count": len(values),
        "values": [_round(value) for value in values],
        "mean": _round(mean(values)) if values else None,
        "median": _round(median(values)) if values else None,
        "std": _round(stdev(values)) if len(values) > 1 else 0.0 if values else None,
        "percentiles": {f"p{point}": _round(percentile(values, point)) for point in PERCENTILES} if values else {},
    }


def threshold_grid(values: Sequence[float]) -> list[float]:
    unique = sorted(set(float(value) for value in values))
    if not unique:
        return []
    if len(unique) == 1:
        return unique
    thresholds = [unique[0] - abs(unique[1] - unique[0]) / 2.0]
    thresholds.extend((left + right) / 2.0 for left, right in zip(unique, unique[1:]))
    thresholds.append(unique[-1] + abs(unique[-1] - unique[-2]) / 2.0)
    return thresholds


def classification_metrics(values: Sequence[tuple[float, str]], threshold: float, direction: str) -> Dict[str, Any]:
    tp = fp = tn = fn = 0
    for value, label in values:
        if direction == "success_higher":
            predicted_success = value >= threshold
        else:
            predicted_success = value <= threshold
        if predicted_success and label == "success":
            tp += 1
        elif predicted_success and label == "failure":
            fp += 1
        elif not predicted_success and label == "failure":
            tn += 1
        else:
            fn += 1
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    specificity = safe_div(tn, tn + fp)
    f1 = safe_div(2.0 * precision * recall, precision + recall)
    balanced_accuracy = (recall + specificity) / 2.0
    return {
        "precision": _round(precision),
        "recall": _round(recall),
        "f1": _round(f1),
        "balanced_accuracy": _round(balanced_accuracy),
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
    }


def temporary_threshold_proxy(distribution: Mapping[str, Any], direction: str) -> Dict[str, Any]:
    success_values = [float(value) for value in distribution["success"]["values"]]
    failure_values = [float(value) for value in distribution["failure"]["values"]]
    values = [(value, "success") for value in success_values] + [(value, "failure") for value in failure_values]
    threshold = median(success_values + failure_values)
    return {
        "threshold": _round(threshold),
        "source": "Sprint 12P median-pivot repeatability proxy; not a hardcoded threshold",
        "metrics": classification_metrics(values, threshold, direction),
    }


def verdict_for(best: Mapping[str, Any], distribution: Mapping[str, Any]) -> str:
    success_count = int(distribution["success"]["count"])
    failure_count = int(distribution["failure"]["count"])
    balanced_accuracy = float(best.get("balanced_accuracy") or 0.0)
    f1 = float(best.get("f1") or 0.0)
    if success_count < 20 or failure_count < 20:
        if balanced_accuracy <= 0.55 and f1 <= 0.55:
            return "REJECT"
        return "NOT_ENOUGH_EVIDENCE"
    if balanced_accuracy >= 0.7 and f1 >= 0.7:
        return "SUPPORTED_BY_DATA"
    if balanced_accuracy <= 0.55 and f1 <= 0.55:
        return "REJECT"
    return "NOT_ENOUGH_EVIDENCE"


def confidence_note(verdict: str, distribution: Mapping[str, Any]) -> str:
    if verdict == "SUPPORTED_BY_DATA":
        return "Replay distributions and threshold scan support this candidate under the predeclared metric rule."
    if verdict == "REJECT":
        return "Threshold scan does not separate success and failure strongly enough on current replay data."
    return (
        "Current sample count is limited "
        f"(success={distribution['success']['count']}, failure={distribution['failure']['count']}); "
        "threshold is data-derived but requires more replay evidence before support."
    )


def percentile(values: Sequence[float], point: int) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (point / 100.0)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def normalize_candidate_name(value: Any) -> str:
    if value == "score_slope":
        return "hellhound_score_slope"
    return str(value)


def safe_div(left: float, right: float) -> float:
    return left / right if right else 0.0


def diff(left: Any, right: Any) -> Optional[float]:
    left_num = _number(left)
    right_num = _number(right)
    if left_num is None or right_num is None:
        return None
    return _round(left_num - right_num)


def load_json(path: Path | str) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return dict(data) if isinstance(data, Mapping) else {}


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
    result = run_evidence_threshold_discovery()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
