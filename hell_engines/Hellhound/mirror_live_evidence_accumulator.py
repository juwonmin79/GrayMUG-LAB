from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

try:
    import mirror_pattern_engine as mirror_engine
except ImportError:
    from . import mirror_pattern_engine as mirror_engine


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_SHADOW_LOG_PATH = DEFAULT_OUTPUT_DIR / "mirror_shadow_log.jsonl"

DECISIONS = {"REAL_WHALE_BACK", "FAKE_WHALE_BACK", "INCONCLUSIVE"}
REQUIRED_SHADOW_FIELDS = {
    "timestamp",
    "campaign_id",
    "signal_id",
    "symbol",
    "mirror_pattern_id",
    "mirror_decision",
    "confidence",
    "reason_code",
    "validation_state",
    "processing_time_ms",
    "mirror_packet",
    "audit",
    "shadow_mode",
    "replay_storage_compatible",
    "is_trade_command",
}
ALLOWED_SHADOW_FIELDS = REQUIRED_SHADOW_FIELDS | {
    "mirror_shadow_schema_version",
    "decision",
    "telegram",
    "telegram_enabled",
    "forbidden_actions_confirmed",
    "mirror_packet_validation",
    "validation_issues",
}
REQUIRED_MIRROR_PACKET_FIELDS = {
    "schema_version",
    "mirror_pattern_id",
    "campaign_id",
    "signal_id",
    "symbol",
    "mirror_decision",
    "confidence",
    "reason_code",
    "supporting_features",
    "validation_state",
    "created_at",
    "is_trade_command",
}


def run_mirror_live_evidence_accumulation(
    *,
    output_dir: Optional[Path | str] = None,
    shadow_log_path: Path | str = DEFAULT_SHADOW_LOG_PATH,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    rows = load_jsonl(shadow_log_path)
    reason_registry = load_reason_registry()

    decision_distribution = build_decision_distribution(rows)
    reason_distribution = build_reason_distribution(rows)
    processing_stats = build_processing_stats(rows)
    schema_stability = build_schema_stability(rows, reason_registry)
    replay_compatibility = build_replay_compatibility(rows)
    evidence_report = build_evidence_report(
        rows,
        decision_distribution,
        reason_distribution,
        processing_stats,
        schema_stability,
        replay_compatibility,
    )

    paths = {
        "live_evidence_report_path": base / "mirror_live_evidence_report.json",
        "live_decision_distribution_path": base / "mirror_live_decision_distribution.json",
        "live_reason_distribution_path": base / "mirror_live_reason_distribution.json",
        "live_schema_stability_path": base / "mirror_live_schema_stability.json",
        "live_replay_compatibility_path": base / "mirror_live_replay_compatibility.json",
        "live_processing_stats_path": base / "mirror_live_processing_stats.json",
    }
    write_json(evidence_report, paths["live_evidence_report_path"])
    write_json(decision_distribution, paths["live_decision_distribution_path"])
    write_json(reason_distribution, paths["live_reason_distribution_path"])
    write_json(schema_stability, paths["live_schema_stability_path"])
    write_json(replay_compatibility, paths["live_replay_compatibility_path"])
    write_json(processing_stats, paths["live_processing_stats_path"])

    return {
        "mirror_live_evidence_accumulator_run_schema_version": "mirror_live_evidence_accumulator_run_v1",
        "packet_count": len(rows),
        "decision_distribution": decision_distribution["counts"],
        "reason_distribution": reason_distribution["reason_counts"],
        "inconclusive_rate": decision_distribution["rates"].get("INCONCLUSIVE", 0.0),
        "schema_stability": schema_stability["schema_stability"],
        "replay_compatibility": replay_compatibility["replay_compatibility"],
        "json_validation": "PASS",
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def build_decision_distribution(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    counts = Counter(str(row.get("mirror_decision") or "") for row in rows)
    total = len(rows)
    normalized_counts = {decision: counts.get(decision, 0) for decision in sorted(DECISIONS)}
    return {
        "mirror_live_decision_distribution_schema_version": "mirror_live_decision_distribution_v1",
        "packet_count": total,
        "counts": normalized_counts,
        "rates": {key: round(value / total, 6) if total else 0.0 for key, value in normalized_counts.items()},
        "inconclusive_drift_check": classify_inconclusive_rate(normalized_counts.get("INCONCLUSIVE", 0), total),
        "rule_change_performed": False,
        "is_trade_command": False,
    }


def build_reason_distribution(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    counts = Counter(reason for row in rows for reason in row.get("reason_code", []))
    return {
        "mirror_live_reason_distribution_schema_version": "mirror_live_reason_distribution_v1",
        "packet_count": len(rows),
        "reason_counts": dict(sorted(counts.items())),
        "is_trade_command": False,
    }


def build_processing_stats(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    values = sorted(float(row.get("processing_time_ms", 0.0)) for row in rows)
    total = len(values)
    return {
        "mirror_live_processing_stats_schema_version": "mirror_live_processing_stats_v1",
        "packet_count": total,
        "average_processing_time_ms": round(sum(values) / total, 6) if total else None,
        "p90_processing_time_ms": percentile(values, 90) if values else None,
        "max_processing_time_ms": values[-1] if values else None,
        "is_trade_command": False,
    }


def build_schema_stability(rows: Sequence[Mapping[str, Any]], reason_registry: set[str]) -> Dict[str, Any]:
    missing_field: Counter[str] = Counter()
    unknown_field: Counter[str] = Counter()
    invalid_enum: Counter[str] = Counter()
    invalid_confidence = 0
    invalid_reason_code: Counter[str] = Counter()
    invalid_mirror_packet = 0

    for row in rows:
        missing_field.update(REQUIRED_SHADOW_FIELDS - set(row))
        unknown_field.update(set(row) - ALLOWED_SHADOW_FIELDS)
        decision = row.get("mirror_decision")
        if decision not in DECISIONS:
            invalid_enum[str(decision)] += 1
        confidence = row.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or confidence < 0.0 or confidence > 1.0:
            invalid_confidence += 1
        reasons = row.get("reason_code")
        if not isinstance(reasons, list) or not reasons:
            invalid_reason_code["missing_or_invalid_reason_code"] += 1
        else:
            for reason in reasons:
                if reason not in reason_registry:
                    invalid_reason_code[str(reason)] += 1
        mirror_packet = row.get("mirror_packet")
        if not isinstance(mirror_packet, Mapping) or REQUIRED_MIRROR_PACKET_FIELDS - set(mirror_packet):
            invalid_mirror_packet += 1

    issue_count = (
        sum(missing_field.values())
        + sum(unknown_field.values())
        + sum(invalid_enum.values())
        + invalid_confidence
        + sum(invalid_reason_code.values())
        + invalid_mirror_packet
    )
    return {
        "mirror_live_schema_stability_schema_version": "mirror_live_schema_stability_v1",
        "packet_count": len(rows),
        "schema_stability": "PASS" if rows and issue_count == 0 else "FAIL",
        "missing_field": dict(sorted(missing_field.items())),
        "unknown_field": dict(sorted(unknown_field.items())),
        "invalid_enum": dict(sorted(invalid_enum.items())),
        "invalid_confidence": invalid_confidence,
        "invalid_reason_code": dict(sorted(invalid_reason_code.items())),
        "invalid_mirror_packet": invalid_mirror_packet,
        "is_trade_command": False,
    }


def build_replay_compatibility(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    incompatible = []
    for index, row in enumerate(rows, start=1):
        issues = []
        if row.get("is_trade_command") is not False:
            issues.append("trade_command_not_false")
        if row.get("replay_storage_compatible") is not True:
            issues.append("replay_storage_compatible_not_true")
        if not isinstance(row.get("mirror_packet"), Mapping):
            issues.append("missing_mirror_packet")
        if row.get("timestamp") is None:
            issues.append("missing_timestamp")
        if issues:
            incompatible.append({"line": index, "campaign_id": row.get("campaign_id"), "issues": issues})
    return {
        "mirror_live_replay_compatibility_schema_version": "mirror_live_replay_compatibility_v1",
        "packet_count": len(rows),
        "replay_compatibility": "PASS" if rows and not incompatible else "FAIL",
        "incompatible_count": len(incompatible),
        "incompatible_rows": incompatible[:20],
        "format": "jsonl_append_only",
        "db_created": False,
        "supabase_connected": False,
        "is_trade_command": False,
    }


def build_evidence_report(
    rows: Sequence[Mapping[str, Any]],
    decision_distribution: Mapping[str, Any],
    reason_distribution: Mapping[str, Any],
    processing_stats: Mapping[str, Any],
    schema_stability: Mapping[str, Any],
    replay_compatibility: Mapping[str, Any],
) -> Dict[str, Any]:
    confidence_values = [float(row.get("confidence", 0.0)) for row in rows if isinstance(row.get("confidence"), (int, float))]
    symbol_counts = Counter(str(row.get("symbol") or "") for row in rows)
    return {
        "mirror_live_evidence_report_schema_version": "mirror_live_evidence_report_v1",
        "packet_count": len(rows),
        "decision_distribution": decision_distribution["counts"],
        "average_confidence": round(sum(confidence_values) / len(confidence_values), 6) if confidence_values else None,
        "reason_code_distribution": reason_distribution["reason_counts"],
        "symbol_distribution": dict(sorted(symbol_counts.items())),
        "processing_time": {
            "average_ms": processing_stats["average_processing_time_ms"],
            "p90_ms": processing_stats["p90_processing_time_ms"],
            "max_ms": processing_stats["max_processing_time_ms"],
        },
        "inconclusive_rate": decision_distribution["rates"].get("INCONCLUSIVE", 0.0),
        "inconclusive_drift_check": decision_distribution["inconclusive_drift_check"],
        "schema_stability": schema_stability["schema_stability"],
        "replay_compatibility": replay_compatibility["replay_compatibility"],
        "db_created": False,
        "supabase_connected": False,
        "rule_change_performed": False,
        "is_trade_command": False,
    }


def classify_inconclusive_rate(inconclusive_count: int, total: int) -> Dict[str, Any]:
    rate = round(inconclusive_count / total, 6) if total else 0.0
    if not total:
        level = "NO_DATA"
    elif rate >= 0.8:
        level = "HIGH_DRIFT"
    elif rate >= 0.5:
        level = "WATCH"
    else:
        level = "NORMAL"
    return {"rate": rate, "level": level, "rule_change_performed": False}


def percentile(values: Sequence[float], point: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return round(float(values[0]), 6)
    rank = (len(values) - 1) * (point / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(values) - 1)
    weight = rank - lower
    return round(values[lower] * (1.0 - weight) + values[upper] * weight, 6)


def load_reason_registry() -> set[str]:
    registry = mirror_engine.load_json(mirror_engine.MIRROR_REASON_REGISTRY_PATH)
    reasons = registry.get("reasons", [])
    return {str(row.get("reason_code")) for row in reasons if isinstance(row, Mapping) and row.get("reason_code")}


def load_jsonl(path: Path | str) -> list[Dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(rows: Iterable[Mapping[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(dict(row), sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    result = run_mirror_live_evidence_accumulation()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
