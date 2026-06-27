"""
Mirror Foundation End-to-End Validator (Sprint 12AK)

Connects all Foundation layers and validates the complete pipeline
without changing any logic, contract, or policy.

Pipeline:
  Feature → Evidence → Reason → Decision → Mirror Packet
  → Replay → Persistence → Readback Audit → Storage Failure Policy
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Mapping, Optional, Sequence
from unittest.mock import MagicMock

try:
    import mirror_packet_contract
    import mirror_persistence_adapter as persistence
    import mirror_replay_harness
    import mirror_storage_failure_policy as failure_policy
except ImportError:
    from . import mirror_packet_contract
    from . import mirror_persistence_adapter as persistence
    from . import mirror_replay_harness
    from . import mirror_storage_failure_policy as failure_policy


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_SOURCE_PATH = DEFAULT_OUTPUT_DIR / "mirror_shadow_log.jsonl"

E2E_PIPELINE_STAGES = ("replay", "persistence", "readback_audit", "failure_policy")


def _canonical_hash(packet: Mapping[str, Any]) -> str:
    payload = json.dumps(dict(packet), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _run_replay_stage(
    packets: Sequence[Mapping[str, Any]],
    schema: Mapping[str, Any],
    reason_registry: set,
) -> Dict[str, Any]:
    started = perf_counter()
    replay_rows = mirror_replay_harness.replay_packets(packets, schema=schema, reason_registry=reason_registry)
    sequence = mirror_replay_harness.validate_replay_sequence(packets, replay_rows)
    elapsed_ms = round((perf_counter() - started) * 1000.0, 6)

    mutation_count = sum(1 for row in replay_rows if row.get("packet_mutated"))
    contract_pass = all(row.get("contract_validation") == "PASS" for row in replay_rows)
    content_unchanged = sequence.get("content_unchanged") is True

    return {
        "stage": "replay",
        "packet_count": len(packets),
        "stage_result": "PASS" if packets and contract_pass and content_unchanged and mutation_count == 0 else "FAIL",
        "mutation_count": mutation_count,
        "contract_pass": contract_pass,
        "content_unchanged": content_unchanged,
        "sequence_validation": sequence.get("sequence_validation"),
        "elapsed_ms": elapsed_ms,
        "is_trade_command": False,
    }


def _run_persistence_stage(
    packets: Sequence[Mapping[str, Any]],
    storage_path: Path,
) -> Dict[str, Any]:
    started = perf_counter()
    storage = persistence.JsonlPacketStorage(storage_path)
    adapter = persistence.MirrorPersistenceAdapter(storage)
    result = adapter.save_packets(packets)
    elapsed_ms = round((perf_counter() - started) * 1000.0, 6)

    rows = result.get("rows", [])
    mutation_count = sum(1 for row in rows if row.get("packet_mutated"))
    save_count = sum(1 for row in rows if row.get("status") == "SAVED")
    reject_count = sum(1 for row in rows if row.get("status") == "REJECTED")

    return {
        "stage": "persistence",
        "packet_count": len(packets),
        "stage_result": "PASS" if packets and save_count == len(packets) and mutation_count == 0 else "FAIL",
        "mutation_count": mutation_count,
        "save_count": save_count,
        "reject_count": reject_count,
        "duplicate_count": sum(1 for row in rows if row.get("status") == "DUPLICATE"),
        "elapsed_ms": elapsed_ms,
        "is_trade_command": False,
    }


def _run_readback_stage(
    original_packets: Sequence[Mapping[str, Any]],
    storage_path: Path,
    schema: Mapping[str, Any],
    reason_registry: set,
) -> Dict[str, Any]:
    started = perf_counter()
    storage = persistence.JsonlPacketStorage(storage_path)
    readback_packets = storage.load_packets()

    original_hashes = [_canonical_hash(p) for p in original_packets]
    readback_hashes = [_canonical_hash(p) for p in readback_packets]

    pair_count = min(len(original_hashes), len(readback_hashes))
    hash_match_count = sum(1 for a, b in zip(original_hashes, readback_hashes) if a == b)
    hash_mismatch_count = pair_count - hash_match_count + abs(len(original_hashes) - len(readback_hashes))
    mutation_count = pair_count - hash_match_count

    # Verify replay is still possible after readback
    replay_rows = mirror_replay_harness.replay_packets(readback_packets, schema=schema, reason_registry=reason_registry)
    replay_pass = all(row.get("contract_validation") == "PASS" for row in replay_rows) if readback_packets else True
    elapsed_ms = round((perf_counter() - started) * 1000.0, 6)

    count_match = len(original_packets) == len(readback_packets)
    pass_cond = (
        bool(original_packets)
        and count_match
        and hash_mismatch_count == 0
        and mutation_count == 0
        and replay_pass
    )

    return {
        "stage": "readback_audit",
        "original_packet_count": len(original_packets),
        "readback_packet_count": len(readback_packets),
        "stage_result": "PASS" if pass_cond else "FAIL",
        "hash_match_count": hash_match_count,
        "hash_mismatch_count": hash_mismatch_count,
        "mutation_count": mutation_count,
        "count_match": count_match,
        "replay_after_readback": "PASS" if replay_pass else "FAIL",
        "elapsed_ms": elapsed_ms,
        "is_trade_command": False,
    }


def _run_failure_policy_stage() -> Dict[str, Any]:
    started = perf_counter()
    sim = failure_policy.run_failure_simulation()
    elapsed_ms = round((perf_counter() - started) * 1000.0, 6)

    return {
        "stage": "failure_policy",
        "stage_result": sim["simulation_verdict"],
        "all_fail_safe": sim["all_fail_safe"],
        "all_no_auto_recovery": sim["all_no_auto_recovery"],
        "all_correct_failure_codes": sim["all_correct_failure_codes"],
        "simulation_count": sim["simulation_count"],
        "elapsed_ms": elapsed_ms,
        "is_trade_command": False,
    }


def run_e2e_pipeline(
    packets: Sequence[Mapping[str, Any]],
    *,
    storage_path: Path,
) -> Dict[str, Any]:
    schema = mirror_packet_contract.build_schema()
    reason_registry = mirror_packet_contract.load_reason_registry()

    pipeline_started = perf_counter()
    stage_results: List[Dict[str, Any]] = []

    replay_stage = _run_replay_stage(packets, schema, reason_registry)
    stage_results.append(replay_stage)

    persistence_stage = _run_persistence_stage(packets, storage_path)
    stage_results.append(persistence_stage)

    readback_stage = _run_readback_stage(packets, storage_path, schema, reason_registry)
    stage_results.append(readback_stage)

    failure_stage = _run_failure_policy_stage()
    stage_results.append(failure_stage)

    total_elapsed_ms = round((perf_counter() - pipeline_started) * 1000.0, 6)
    total_mutation_count = sum(s.get("mutation_count", 0) for s in stage_results)
    all_pass = all(s["stage_result"] == "PASS" for s in stage_results)

    return {
        "mirror_e2e_pipeline_schema_version": "mirror_e2e_pipeline_v1",
        "contract_version": mirror_packet_contract.CONTRACT_VERSION,
        "packet_count": len(packets),
        "pipeline_result": "PASS" if all_pass and total_mutation_count == 0 else "FAIL",
        "total_mutation_count": total_mutation_count,
        "total_elapsed_ms": total_elapsed_ms,
        "stage_results": stage_results,
        "is_trade_command": False,
    }


def run_e2e_failure_injection(
    packets: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """
    Inject Write and Read failures at Persistence stage using MagicMock.
    Verify: FAIL_SAFE result, no bad packets downstream, pipeline does not crash.
    No real file system change.
    """
    injection_cases = []

    # Case 1: Write failure — nothing reaches storage
    mock_write_fail = MagicMock()
    mock_write_fail.append_packet.side_effect = IOError("Simulated disk write failure")
    mock_write_fail.existing_hashes.return_value = set()
    mock_write_fail.load_packets.return_value = []

    write_policy = failure_policy.StorageFailurePolicy(mock_write_fail)
    write_results = [write_policy.save_with_policy(p) for p in packets]
    downstream_load = write_policy.load_with_policy()

    write_all_fail_safe = all(r["policy_outcome"] == failure_policy.POLICY_OUTCOME_FAIL_SAFE for r in write_results)
    write_none_saved = all(not r["saved"] for r in write_results)
    write_downstream_empty = downstream_load["packet_count"] == 0

    injection_cases.append({
        "case": "write_failure",
        "exception_class": "IOError",
        "all_fail_safe": write_all_fail_safe,
        "none_saved": write_none_saved,
        "downstream_packet_count": downstream_load["packet_count"],
        "no_bad_packets_downstream": write_downstream_empty,
        "failure_record_count": len(write_policy.failure_records),
        "injection_result": "PASS" if write_all_fail_safe and write_none_saved and write_downstream_empty else "FAIL",
        "is_trade_command": False,
    })

    # Case 2: Read failure — downstream gets fail-safe empty list
    mock_read_fail = MagicMock()
    mock_read_fail.load_packets.side_effect = IOError("Simulated disk read failure")
    mock_read_fail.existing_hashes.return_value = set()

    read_policy = failure_policy.StorageFailurePolicy(mock_read_fail)
    read_result = read_policy.load_with_policy()

    read_fail_safe = read_result["policy_outcome"] == failure_policy.POLICY_OUTCOME_FAIL_SAFE
    read_empty = read_result["packet_count"] == 0

    injection_cases.append({
        "case": "read_failure",
        "exception_class": "IOError",
        "all_fail_safe": read_fail_safe,
        "downstream_packet_count": read_result["packet_count"],
        "no_bad_packets_downstream": read_empty,
        "failure_record_count": len(read_policy.failure_records),
        "injection_result": "PASS" if read_fail_safe and read_empty else "FAIL",
        "is_trade_command": False,
    })

    # Case 3: Corrupt data read — classified correctly, downstream gets empty
    mock_corrupt = MagicMock()
    mock_corrupt.load_packets.side_effect = json.JSONDecodeError("Simulated corrupt JSON", "", 0)

    corrupt_policy = failure_policy.StorageFailurePolicy(mock_corrupt)
    corrupt_result = corrupt_policy.load_with_policy()

    corrupt_classified = corrupt_result["failure_code"] == failure_policy.FAILURE_CODE_CORRUPT_DATA
    corrupt_fail_safe = corrupt_result["policy_outcome"] == failure_policy.POLICY_OUTCOME_FAIL_SAFE

    injection_cases.append({
        "case": "corrupt_data_read",
        "exception_class": "json.JSONDecodeError",
        "failure_code": corrupt_result["failure_code"],
        "correct_classification": corrupt_classified,
        "all_fail_safe": corrupt_fail_safe,
        "downstream_packet_count": corrupt_result["packet_count"],
        "no_bad_packets_downstream": corrupt_result["packet_count"] == 0,
        "injection_result": "PASS" if corrupt_classified and corrupt_fail_safe else "FAIL",
        "is_trade_command": False,
    })

    all_pass = all(c["injection_result"] == "PASS" for c in injection_cases)

    return {
        "mirror_e2e_failure_injection_schema_version": "mirror_e2e_failure_injection_v1",
        "injection_count": len(injection_cases),
        "all_fail_safe": all(c["all_fail_safe"] for c in injection_cases),
        "all_no_bad_packets_downstream": all(c["no_bad_packets_downstream"] for c in injection_cases),
        "failure_injection_result": "PASS" if all_pass else "FAIL",
        "cases": injection_cases,
        "is_trade_command": False,
    }


def build_e2e_report(
    pipeline_result: Mapping[str, Any],
    failure_injection: Mapping[str, Any],
) -> Dict[str, Any]:
    pipeline_pass = pipeline_result.get("pipeline_result") == "PASS"
    injection_pass = failure_injection.get("failure_injection_result") == "PASS"
    mutation_zero = pipeline_result.get("total_mutation_count", 1) == 0

    readback_stage = next(
        (s for s in pipeline_result.get("stage_results", []) if s.get("stage") == "readback_audit"),
        {},
    )

    return {
        "mirror_e2e_report_schema_version": "mirror_e2e_report_v1",
        "e2e_result": "PASS" if pipeline_pass and injection_pass and mutation_zero else "FAIL",
        "contract_version": pipeline_result.get("contract_version"),
        "packet_count": pipeline_result.get("packet_count"),
        "total_mutation_count": pipeline_result.get("total_mutation_count"),
        "pipeline_result": pipeline_result.get("pipeline_result"),
        "failure_injection_result": failure_injection.get("failure_injection_result"),
        "hash_match_count": readback_stage.get("hash_match_count"),
        "hash_mismatch_count": readback_stage.get("hash_mismatch_count"),
        "replay_after_readback": readback_stage.get("replay_after_readback"),
        "total_elapsed_ms": pipeline_result.get("total_elapsed_ms"),
        "stage_results": pipeline_result.get("stage_results"),
        "forbidden_actions_confirmed": [
            "No mirror_pattern_packet_v1 Contract change",
            "No Mirror Decision Logic change",
            "No Replay Logic change",
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


def build_e2e_failure_report(failure_injection: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "mirror_e2e_failure_report_schema_version": "mirror_e2e_failure_report_v1",
        "failure_injection_result": failure_injection.get("failure_injection_result"),
        "injection_count": failure_injection.get("injection_count"),
        "all_fail_safe": failure_injection.get("all_fail_safe"),
        "all_no_bad_packets_downstream": failure_injection.get("all_no_bad_packets_downstream"),
        "cases": failure_injection.get("cases"),
        "is_trade_command": False,
    }


def build_e2e_timing_report(pipeline_result: Mapping[str, Any]) -> Dict[str, Any]:
    stage_timings = {
        s["stage"]: s.get("elapsed_ms")
        for s in pipeline_result.get("stage_results", [])
    }
    return {
        "mirror_e2e_timing_schema_version": "mirror_e2e_timing_v1",
        "total_elapsed_ms": pipeline_result.get("total_elapsed_ms"),
        "stage_timings_ms": stage_timings,
        "stage_order": list(E2E_PIPELINE_STAGES),
        "is_trade_command": False,
    }


def run_mirror_foundation_e2e_validator(
    *,
    output_dir: Optional[Path | str] = None,
    source_path: Path | str = DEFAULT_SOURCE_PATH,
    source_packets: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR

    if source_packets is not None:
        packets = list(source_packets)
    else:
        packets = mirror_replay_harness.load_replay_packets(source_path)

    # Use a dedicated E2E storage path (separate from main persistence)
    e2e_storage_path = base / "mirror_e2e_storage.jsonl"
    # Remove if exists to ensure clean run
    if e2e_storage_path.exists():
        e2e_storage_path.unlink()

    pipeline_result = run_e2e_pipeline(packets, storage_path=e2e_storage_path)
    failure_injection = run_e2e_failure_injection(packets)

    e2e_report = build_e2e_report(pipeline_result, failure_injection)
    failure_report = build_e2e_failure_report(failure_injection)
    timing_report = build_e2e_timing_report(pipeline_result)

    paths = {
        "e2e_report_path": base / "mirror_foundation_e2e_report.json",
        "e2e_failure_report_path": base / "mirror_foundation_e2e_failure_report.json",
        "e2e_timing_path": base / "mirror_foundation_e2e_timing.json",
    }
    _write_json(e2e_report, paths["e2e_report_path"])
    _write_json(failure_report, paths["e2e_failure_report_path"])
    _write_json(timing_report, paths["e2e_timing_path"])

    return {
        "mirror_foundation_e2e_validator_run_schema_version": "mirror_foundation_e2e_validator_run_v1",
        "e2e_result": e2e_report["e2e_result"],
        "pipeline_result": pipeline_result["pipeline_result"],
        "failure_injection_result": failure_injection["failure_injection_result"],
        "contract_version": mirror_packet_contract.CONTRACT_VERSION,
        "packet_count": len(packets),
        "total_mutation_count": pipeline_result["total_mutation_count"],
        "total_elapsed_ms": pipeline_result["total_elapsed_ms"],
        "all_fail_safe_on_injection": failure_injection["all_fail_safe"],
        "all_no_bad_packets_downstream": failure_injection["all_no_bad_packets_downstream"],
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main() -> int:
    result = run_mirror_foundation_e2e_validator()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
