from __future__ import annotations

import copy
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

try:
    import mirror_packet_contract
except ImportError:
    from . import mirror_packet_contract


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_GOLDEN_SAMPLE_PATH = DEFAULT_OUTPUT_DIR / "mirror_packet_golden_samples.json"
DEFAULT_PACKET_PATH = DEFAULT_OUTPUT_DIR / "mirror_shadow_log.jsonl"

REPLAY_COUNTS = (10, 100)
STABLE_FIELDS = ("mirror_decision", "reason_code", "confidence", "validation_state")


def run_mirror_replay_harness(
    *,
    output_dir: Optional[Path | str] = None,
    golden_sample_path: Path | str = DEFAULT_GOLDEN_SAMPLE_PATH,
    packet_path: Path | str = DEFAULT_PACKET_PATH,
    replay_counts: Sequence[int] = REPLAY_COUNTS,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    schema = mirror_packet_contract.build_schema()
    reason_registry = mirror_packet_contract.load_reason_registry()
    packets = load_replay_packets(packet_path)
    replay_rows = replay_packets(packets, schema=schema, reason_registry=reason_registry)
    sequence_validation = validate_replay_sequence(packets, replay_rows)
    golden_report = replay_golden_samples(golden_sample_path, schema=schema, reason_registry=reason_registry)
    determinism = build_determinism_report(packets, schema=schema, reason_registry=reason_registry, replay_counts=replay_counts)
    statistics = build_replay_statistics(replay_rows, sequence_validation, golden_report, determinism)
    report = build_replay_report(packets, replay_rows, sequence_validation, golden_report, determinism, statistics)

    paths = {
        "replay_report_path": base / "mirror_replay_report.json",
        "replay_statistics_path": base / "mirror_replay_statistics.json",
        "replay_determinism_path": base / "mirror_replay_determinism.json",
    }
    write_json(report, paths["replay_report_path"])
    write_json(statistics, paths["replay_statistics_path"])
    write_json(determinism, paths["replay_determinism_path"])
    return {
        "mirror_replay_harness_run_schema_version": "mirror_replay_harness_run_v1",
        "replay_harness": report["replay_harness"],
        "packet_count": len(packets),
        "replay_count": len(replay_rows),
        "contract_validation": report["contract_validation"],
        "replay_compatibility": report["replay_compatibility"],
        "golden_sample_replay": report["golden_sample_replay"],
        "replay_determinism": report["replay_determinism"],
        "fake_golden_sample": golden_report["decision_results"]["FAKE_WHALE_BACK"]["status"],
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def load_replay_packets(path: Path | str) -> list[Dict[str, Any]]:
    rows = load_jsonl(path)
    packets = []
    for row in rows:
        if isinstance(row.get("mirror_packet"), Mapping):
            packets.append(dict(row["mirror_packet"]))
        else:
            packets.append(dict(row))
    return packets


def replay_packets(
    packets: Sequence[Mapping[str, Any]],
    *,
    schema: Mapping[str, Any],
    reason_registry: set[str],
) -> list[Dict[str, Any]]:
    rows = []
    previous_timestamp: Optional[str] = None
    for index, packet in enumerate(packets):
        before_hash = stable_hash(packet)
        replay_packet = copy.deepcopy(packet)
        started = perf_counter()
        validation = mirror_packet_contract.validate_packet(replay_packet, schema=schema, reason_registry=reason_registry)
        processing_time_ms = round((perf_counter() - started) * 1000.0, 6)
        after_hash = stable_hash(packet)
        timestamp = str(packet.get("created_at") or "")
        rows.append(
            {
                "sequence_index": index,
                "campaign_id": packet.get("campaign_id"),
                "timestamp": timestamp,
                "timestamp_order_valid": timestamp_order_valid(previous_timestamp, timestamp),
                "decision": packet.get("mirror_decision"),
                "reason_code": copy.deepcopy(packet.get("reason_code")),
                "confidence": packet.get("confidence"),
                "validation_state": packet.get("validation_state"),
                "contract_validation": "PASS" if validation.get("valid") else validation.get("validation_result"),
                "validation_issues": validation.get("issues", []),
                "packet_hash_before": before_hash,
                "packet_hash_after": after_hash,
                "packet_mutated": before_hash != after_hash,
                "processing_time_ms": processing_time_ms,
                "is_trade_command": False,
            }
        )
        previous_timestamp = timestamp
    return rows


def validate_replay_sequence(packets: Sequence[Mapping[str, Any]], replay_rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    sequence_errors = []
    for index, (packet, replay) in enumerate(zip(packets, replay_rows)):
        if replay.get("sequence_index") != index:
            sequence_errors.append({"index": index, "error": "sequence_index_changed"})
        if replay.get("decision") != packet.get("mirror_decision"):
            sequence_errors.append({"index": index, "error": "decision_changed"})
        if replay.get("reason_code") != packet.get("reason_code"):
            sequence_errors.append({"index": index, "error": "reason_code_changed"})
        if replay.get("confidence") != packet.get("confidence"):
            sequence_errors.append({"index": index, "error": "confidence_changed"})
        if replay.get("validation_state") != packet.get("validation_state"):
            sequence_errors.append({"index": index, "error": "validation_state_changed"})
        if replay.get("packet_mutated"):
            sequence_errors.append({"index": index, "error": "packet_mutated"})
        if not replay.get("timestamp_order_valid"):
            sequence_errors.append({"index": index, "error": "timestamp_order_invalid"})
    return {
        "mirror_replay_sequence_validation_schema_version": "mirror_replay_sequence_validation_v1",
        "packet_count": len(packets),
        "sequence_validation": "PASS" if packets and not sequence_errors else "FAIL",
        "sequence_errors": sequence_errors,
        "packet_order_preserved": not any(row.get("error") == "sequence_index_changed" for row in sequence_errors),
        "timestamp_order_preserved": not any(row.get("error") == "timestamp_order_invalid" for row in sequence_errors),
        "content_unchanged": not any(row.get("error") in {"decision_changed", "reason_code_changed", "confidence_changed", "validation_state_changed", "packet_mutated"} for row in sequence_errors),
        "is_trade_command": False,
    }


def replay_golden_samples(
    golden_sample_path: Path | str,
    *,
    schema: Mapping[str, Any],
    reason_registry: set[str],
) -> Dict[str, Any]:
    golden = load_json(golden_sample_path)
    samples = golden.get("samples", {}) if isinstance(golden.get("samples"), Mapping) else {}
    results: Dict[str, Dict[str, Any]] = {}
    for decision in mirror_packet_contract.DECISION_ENUM:
        sample = samples.get(decision)
        if isinstance(sample, Mapping) and sample.get("status") == "absent_in_source":
            results[decision] = {
                "status": "SKIPPED",
                "reason": "absent in source",
                "synthetic_sample_created": False,
            }
            continue
        if not isinstance(sample, Mapping):
            results[decision] = {
                "status": "SKIPPED",
                "reason": "absent in source",
                "synthetic_sample_created": False,
            }
            continue
        replay = replay_packets([sample], schema=schema, reason_registry=reason_registry)[0]
        stable = all(replay.get(field_alias(field)) == sample.get(field) for field in STABLE_FIELDS)
        results[decision] = {
            "status": "PASS" if replay["contract_validation"] == "PASS" and stable and not replay["packet_mutated"] else "FAIL",
            "reason": None,
            "synthetic_sample_created": False,
            "contract_validation": replay["contract_validation"],
            "decision": replay["decision"],
            "reason_code": replay["reason_code"],
            "confidence": replay["confidence"],
            "validation_state": replay["validation_state"],
        }
    replay_pass = all(row["status"] in {"PASS", "SKIPPED"} for row in results.values()) and any(row["status"] == "PASS" for row in results.values())
    return {
        "mirror_golden_sample_replay_schema_version": "mirror_golden_sample_replay_v1",
        "source": str(golden_sample_path),
        "golden_sample_replay": "PASS" if replay_pass else "FAIL",
        "decision_results": results,
        "fake_golden_sample": "SKIPPED (absent in source)" if results["FAKE_WHALE_BACK"]["status"] == "SKIPPED" else results["FAKE_WHALE_BACK"]["status"],
        "synthetic_samples_created": False,
        "is_trade_command": False,
    }


def build_determinism_report(
    packets: Sequence[Mapping[str, Any]],
    *,
    schema: Mapping[str, Any],
    reason_registry: set[str],
    replay_counts: Sequence[int],
) -> Dict[str, Any]:
    runs = []
    for replay_count in replay_counts:
        baseline = replay_packets(packets, schema=schema, reason_registry=reason_registry)
        mismatches = []
        started = perf_counter()
        for iteration in range(replay_count):
            current = replay_packets(packets, schema=schema, reason_registry=reason_registry)
            for index, (left, right) in enumerate(zip(baseline, current)):
                for field in ("decision", "reason_code", "confidence", "validation_state", "contract_validation"):
                    if left.get(field) != right.get(field):
                        mismatches.append({"iteration": iteration, "index": index, "field": field})
        elapsed_ms = round((perf_counter() - started) * 1000.0, 6)
        runs.append(
            {
                "replay_count": replay_count,
                "packet_count": len(packets),
                "total_replayed_packets": replay_count * len(packets),
                "determinism": "PASS" if not mismatches else "FAIL",
                "mismatch_count": len(mismatches),
                "mismatches": mismatches[:20],
                "elapsed_ms": elapsed_ms,
            }
        )
    return {
        "mirror_replay_determinism_schema_version": "mirror_replay_determinism_v1",
        "runs": runs,
        "replay_determinism": "PASS" if runs and all(row["determinism"] == "PASS" for row in runs) else "FAIL",
        "stable_fields": list(STABLE_FIELDS),
        "is_trade_command": False,
    }


def build_replay_statistics(
    replay_rows: Sequence[Mapping[str, Any]],
    sequence_validation: Mapping[str, Any],
    golden_report: Mapping[str, Any],
    determinism: Mapping[str, Any],
) -> Dict[str, Any]:
    times = [float(row.get("processing_time_ms", 0.0)) for row in replay_rows]
    success_count = sum(1 for row in replay_rows if row.get("contract_validation") == "PASS" and not row.get("packet_mutated"))
    failure_count = len(replay_rows) - success_count
    return {
        "mirror_replay_statistics_schema_version": "mirror_replay_statistics_v1",
        "replay_count": len(replay_rows),
        "success_count": success_count,
        "failure_count": failure_count,
        "contract_validation_count": sum(1 for row in replay_rows if row.get("contract_validation") == "PASS"),
        "average_processing_time_ms": round(sum(times) / len(times), 6) if times else None,
        "max_processing_time_ms": max(times) if times else None,
        "replay_determinism": determinism["replay_determinism"],
        "sequence_validation": sequence_validation["sequence_validation"],
        "golden_sample_replay": golden_report["golden_sample_replay"],
        "fake_golden_sample": golden_report["fake_golden_sample"],
        "is_trade_command": False,
    }


def build_replay_report(
    packets: Sequence[Mapping[str, Any]],
    replay_rows: Sequence[Mapping[str, Any]],
    sequence_validation: Mapping[str, Any],
    golden_report: Mapping[str, Any],
    determinism: Mapping[str, Any],
    statistics: Mapping[str, Any],
) -> Dict[str, Any]:
    success = (
        bool(packets)
        and statistics["failure_count"] == 0
        and sequence_validation["sequence_validation"] == "PASS"
        and golden_report["golden_sample_replay"] == "PASS"
        and determinism["replay_determinism"] == "PASS"
    )
    return {
        "mirror_replay_report_schema_version": "mirror_replay_report_v1",
        "replay_harness": "PASS" if success else "FAIL",
        "contract_version": mirror_packet_contract.CONTRACT_VERSION,
        "packet_count": len(packets),
        "replay_count": len(replay_rows),
        "success_count": statistics["success_count"],
        "failure_count": statistics["failure_count"],
        "contract_validation": "PASS" if statistics["contract_validation_count"] == len(replay_rows) and replay_rows else "FAIL",
        "replay_compatibility": "PASS" if sequence_validation["sequence_validation"] == "PASS" else "FAIL",
        "golden_sample_replay": golden_report["golden_sample_replay"],
        "fake_golden_sample": golden_report["fake_golden_sample"],
        "replay_determinism": determinism["replay_determinism"],
        "average_processing_time_ms": statistics["average_processing_time_ms"],
        "max_processing_time_ms": statistics["max_processing_time_ms"],
        "sequence_validation": sequence_validation,
        "golden_sample_report": golden_report,
        "determinism_summary": determinism,
        "forbidden_actions_confirmed": [
            "No Mirror Packet Contract change",
            "No Production change",
            "No Trading change",
            "No Position change",
            "No Order change",
            "No Replay Decision Logic change",
            "No Campaign Physics change",
            "No Lead Line change",
            "No Mirror Registry Logic change",
            "No Mirror Decision Logic change",
            "No Threshold change",
            "No Gate change",
            "No Score change",
            "No ML training",
            "No DB creation",
            "No Supabase connection",
            "No Medusa change",
        ],
        "is_trade_command": False,
    }


def field_alias(field: str) -> str:
    return "decision" if field == "mirror_decision" else field


def timestamp_order_valid(previous: Optional[str], current: str) -> bool:
    if not previous:
        return True
    previous_dt = parse_timestamp(previous)
    current_dt = parse_timestamp(current)
    if previous_dt is None or current_dt is None:
        return False
    return current_dt >= previous_dt


def parse_timestamp(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def stable_hash(packet: Mapping[str, Any]) -> str:
    payload = json.dumps(dict(packet), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    return [json.loads(line) for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    result = run_mirror_replay_harness()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
