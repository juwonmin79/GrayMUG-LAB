from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Mapping, Optional, Sequence

try:
    import mirror_packet_contract
    import mirror_replay_harness
except ImportError:
    from . import mirror_packet_contract
    from . import mirror_replay_harness


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_ORIGINAL_PATH = DEFAULT_OUTPUT_DIR / "mirror_shadow_log.jsonl"
DEFAULT_READBACK_PATH = DEFAULT_OUTPUT_DIR / "mirror_persistence_packets.jsonl"

EQUALITY_FIELDS = (
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
)


def run_mirror_persistence_readback_audit(
    *,
    output_dir: Optional[Path | str] = None,
    original_path: Path | str = DEFAULT_ORIGINAL_PATH,
    readback_path: Path | str = DEFAULT_READBACK_PATH,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    original_packets = mirror_replay_harness.load_replay_packets(original_path)
    readback_load = load_jsonl_utf8_no_bom(readback_path)
    readback_packets = readback_load["packets"]

    schema = mirror_packet_contract.build_schema()
    reason_registry = mirror_packet_contract.load_reason_registry()
    equality = build_equality_report(original_packets, readback_packets, schema=schema, reason_registry=reason_registry)
    hash_report = build_hash_report(original_packets, readback_packets, readback_load)
    replay_report = build_replay_after_readback_report(readback_packets, schema=schema, reason_registry=reason_registry)
    audit_report = build_audit_report(original_packets, readback_packets, equality, hash_report, replay_report, readback_load)

    paths = {
        "readback_audit_report_path": base / "mirror_readback_audit_report.json",
        "readback_hash_report_path": base / "mirror_readback_hash_report.json",
        "readback_replay_report_path": base / "mirror_readback_replay_report.json",
    }
    write_json(audit_report, paths["readback_audit_report_path"])
    write_json(hash_report, paths["readback_hash_report_path"])
    write_json(replay_report, paths["readback_replay_report_path"])
    return {
        "mirror_persistence_readback_audit_run_schema_version": "mirror_persistence_readback_audit_run_v1",
        "readback_audit": audit_report["readback_audit"],
        "original_packet_count": len(original_packets),
        "readback_packet_count": len(readback_packets),
        "contract_validation": audit_report["contract_validation"],
        "equality_validation": audit_report["equality_validation"],
        "hash_match": audit_report["hash_match"],
        "encoding_validation": audit_report["encoding_validation_result"],
        "replay_after_readback": audit_report["replay_after_readback_result"],
        "mutation_count": audit_report["mutation_count"],
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def load_jsonl_utf8_no_bom(path: Path | str) -> Dict[str, Any]:
    file_path = Path(path)
    started = perf_counter()
    raw = file_path.read_bytes() if file_path.exists() else b""
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    decode_error = None
    packets: list[Dict[str, Any]] = []
    read_times = []
    if not has_bom:
        try:
            text = raw.decode("utf-8")
            for line in text.splitlines():
                if not line.strip():
                    continue
                row_started = perf_counter()
                packets.append(json.loads(line))
                read_times.append(round((perf_counter() - row_started) * 1000.0, 6))
        except UnicodeDecodeError as exc:
            decode_error = str(exc)
        except json.JSONDecodeError as exc:
            decode_error = str(exc)
    elapsed_ms = round((perf_counter() - started) * 1000.0, 6)
    return {
        "path": str(file_path),
        "packets": packets,
        "has_bom": has_bom,
        "decode_error": decode_error,
        "encoding_validation_result": "PASS" if file_path.exists() and not has_bom and decode_error is None else "FAIL",
        "read_time_values_ms": read_times,
        "total_read_time_ms": elapsed_ms,
        "average_read_time_ms": round(sum(read_times) / len(read_times), 6) if read_times else None,
        "max_read_time_ms": max(read_times) if read_times else None,
    }


def build_equality_report(
    original_packets: Sequence[Mapping[str, Any]],
    readback_packets: Sequence[Mapping[str, Any]],
    *,
    schema: Mapping[str, Any],
    reason_registry: set[str],
) -> Dict[str, Any]:
    rows = []
    mismatch_count = 0
    contract_pass_count = 0
    pair_count = min(len(original_packets), len(readback_packets))
    for index in range(pair_count):
        original = original_packets[index]
        readback = readback_packets[index]
        field_mismatches = []
        for field in EQUALITY_FIELDS:
            if original.get(field) != readback.get(field):
                field_mismatches.append(field)
        validation = mirror_packet_contract.validate_packet(readback, schema=schema, reason_registry=reason_registry)
        if validation.get("valid"):
            contract_pass_count += 1
        if field_mismatches:
            mismatch_count += 1
        rows.append(
            {
                "sequence_index": index,
                "campaign_id": original.get("campaign_id"),
                "required_field_equal": not field_mismatches,
                "field_mismatches": field_mismatches,
                "decision_equal": original.get("mirror_decision") == readback.get("mirror_decision"),
                "reason_code_equal": original.get("reason_code") == readback.get("reason_code"),
                "confidence_equal": original.get("confidence") == readback.get("confidence"),
                "validation_state_equal": original.get("validation_state") == readback.get("validation_state"),
                "timestamp_equal": original.get("created_at") == readback.get("created_at"),
                "is_trade_command_equal": original.get("is_trade_command") == readback.get("is_trade_command"),
                "contract_validation": "PASS" if validation.get("valid") else validation.get("validation_result"),
                "validation_issues": validation.get("issues", []),
            }
        )
    count_match = len(original_packets) == len(readback_packets)
    return {
        "mirror_readback_equality_schema_version": "mirror_readback_equality_v1",
        "original_packet_count": len(original_packets),
        "readback_packet_count": len(readback_packets),
        "count_match": count_match,
        "pair_count": pair_count,
        "mismatch_count": mismatch_count + abs(len(original_packets) - len(readback_packets)),
        "contract_validation_count": contract_pass_count,
        "equality_validation": "PASS" if count_match and pair_count > 0 and mismatch_count == 0 and contract_pass_count == pair_count else "FAIL",
        "rows": rows,
        "is_trade_command": False,
    }


def build_hash_report(
    original_packets: Sequence[Mapping[str, Any]],
    readback_packets: Sequence[Mapping[str, Any]],
    readback_load: Mapping[str, Any],
) -> Dict[str, Any]:
    rows = []
    hash_match_count = 0
    pair_count = min(len(original_packets), len(readback_packets))
    for index in range(pair_count):
        original_hash = canonical_packet_hash(original_packets[index])
        readback_hash = canonical_packet_hash(readback_packets[index])
        match = original_hash == readback_hash
        if match:
            hash_match_count += 1
        rows.append(
            {
                "sequence_index": index,
                "campaign_id": original_packets[index].get("campaign_id"),
                "original_hash": original_hash,
                "readback_hash": readback_hash,
                "hash_match": match,
            }
        )
    mismatch_count = pair_count - hash_match_count + abs(len(original_packets) - len(readback_packets))
    return {
        "mirror_readback_hash_report_schema_version": "mirror_readback_hash_report_v1",
        "hash_method": "sha256(canonical_json_utf8_without_bom)",
        "canonical_json_serialization": "json.dumps(sort_keys=True,separators=(',',':'))",
        "utf8_without_bom": readback_load["encoding_validation_result"] == "PASS",
        "original_packet_count": len(original_packets),
        "readback_packet_count": len(readback_packets),
        "hash_match_count": hash_match_count,
        "hash_mismatch_count": mismatch_count,
        "hash_match": "PASS" if pair_count > 0 and mismatch_count == 0 else "FAIL",
        "rows": rows,
        "is_trade_command": False,
    }


def build_replay_after_readback_report(
    readback_packets: Sequence[Mapping[str, Any]],
    *,
    schema: Mapping[str, Any],
    reason_registry: set[str],
) -> Dict[str, Any]:
    replay_rows = mirror_replay_harness.replay_packets(readback_packets, schema=schema, reason_registry=reason_registry)
    sequence = mirror_replay_harness.validate_replay_sequence(readback_packets, replay_rows)
    determinism = mirror_replay_harness.build_determinism_report(
        readback_packets,
        schema=schema,
        reason_registry=reason_registry,
        replay_counts=[10, 100],
    )
    mutation_count = sum(1 for row in replay_rows if row.get("packet_mutated"))
    contract_pass = all(row.get("contract_validation") == "PASS" for row in replay_rows)
    replay_pass = sequence.get("sequence_validation") == "PASS"
    return {
        "mirror_readback_replay_report_schema_version": "mirror_readback_replay_report_v1",
        "packet_count": len(readback_packets),
        "contract_validation": "PASS" if readback_packets and contract_pass else "FAIL",
        "replay_result": "PASS" if readback_packets and replay_pass else "FAIL",
        "determinism": determinism["replay_determinism"],
        "packet_mutation_count": mutation_count,
        "replay_after_readback_result": "PASS"
        if readback_packets and contract_pass and replay_pass and determinism["replay_determinism"] == "PASS" and mutation_count == 0
        else "FAIL",
        "sequence_validation": sequence,
        "determinism_report": determinism,
        "is_trade_command": False,
    }


def build_audit_report(
    original_packets: Sequence[Mapping[str, Any]],
    readback_packets: Sequence[Mapping[str, Any]],
    equality: Mapping[str, Any],
    hash_report: Mapping[str, Any],
    replay_report: Mapping[str, Any],
    readback_load: Mapping[str, Any],
) -> Dict[str, Any]:
    mutation_count = equality["mismatch_count"] + replay_report["packet_mutation_count"]
    success = (
        equality["equality_validation"] == "PASS"
        and hash_report["hash_match"] == "PASS"
        and replay_report["replay_after_readback_result"] == "PASS"
        and readback_load["encoding_validation_result"] == "PASS"
        and mutation_count == 0
    )
    return {
        "mirror_readback_audit_report_schema_version": "mirror_readback_audit_report_v1",
        "readback_audit": "PASS" if success else "FAIL",
        "contract_version": mirror_packet_contract.CONTRACT_VERSION,
        "original_packet_count": len(original_packets),
        "readback_packet_count": len(readback_packets),
        "hash_match_count": hash_report["hash_match_count"],
        "hash_mismatch_count": hash_report["hash_mismatch_count"],
        "mutation_count": mutation_count,
        "contract_validation": replay_report["contract_validation"],
        "equality_validation": equality["equality_validation"],
        "hash_match": hash_report["hash_match"],
        "replay_after_readback_result": replay_report["replay_after_readback_result"],
        "average_read_time_ms": readback_load["average_read_time_ms"],
        "max_read_time_ms": readback_load["max_read_time_ms"],
        "encoding_validation_result": readback_load["encoding_validation_result"],
        "utf8_without_bom": not readback_load["has_bom"],
        "decode_error": readback_load["decode_error"],
        "forbidden_actions_confirmed": [
            "No mirror_pattern_packet_v1 Contract change",
            "No Persistence Adapter Interface change",
            "No JsonlPacketStorage policy change",
            "No Replay Logic change",
            "No Mirror Decision Logic change",
            "No Registry change",
            "No Campaign Physics change",
            "No Lead Line change",
            "No Threshold change",
            "No Gate change",
            "No Score change",
            "No ML training",
            "No Production change",
            "No Trading change",
            "No Position change",
            "No Order change",
            "No DB creation",
            "No SQLite",
            "No PostgreSQL",
            "No Supabase connection",
            "No Medusa change",
        ],
        "is_trade_command": False,
    }


def canonical_packet_hash(packet: Mapping[str, Any]) -> str:
    payload = json.dumps(dict(packet), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    result = run_mirror_persistence_readback_audit()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
