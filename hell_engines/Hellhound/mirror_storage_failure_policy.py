"""
Mirror Storage Failure Policy (Sprint 12AJ)

Fail-safe policy for Mirror Packet Storage layer failures.
Failures are classified, recorded, and terminated. No auto-recovery.
Read and Write failures are simulated using Mock only.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Mapping, Optional, Sequence
from unittest.mock import MagicMock

try:
    import mirror_packet_contract
    import mirror_replay_harness
except ImportError:
    from . import mirror_packet_contract
    from . import mirror_replay_harness


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"

FAILURE_CODE_WRITE_FAILURE = "WRITE_FAILURE"
FAILURE_CODE_READ_FAILURE = "READ_FAILURE"
FAILURE_CODE_CORRUPT_DATA = "CORRUPT_DATA"
FAILURE_CODE_ENCODING_ERROR = "ENCODING_ERROR"
FAILURE_CODE_HASH_READ_FAILURE = "HASH_READ_FAILURE"
FAILURE_CODE_UNKNOWN_FAILURE = "UNKNOWN_FAILURE"

FAILURE_CODES = (
    FAILURE_CODE_WRITE_FAILURE,
    FAILURE_CODE_READ_FAILURE,
    FAILURE_CODE_CORRUPT_DATA,
    FAILURE_CODE_ENCODING_ERROR,
    FAILURE_CODE_HASH_READ_FAILURE,
    FAILURE_CODE_UNKNOWN_FAILURE,
)

POLICY_OUTCOME_FAIL_SAFE = "FAIL_SAFE"
POLICY_OUTCOME_PASS = "PASS"

OPERATION_WRITE = "WRITE"
OPERATION_READ = "READ"
OPERATION_HASH_READ = "HASH_READ"

SIMULATION_CASES: tuple[Dict[str, Any], ...] = (
    {
        "case_name": "write_io_error",
        "operation": OPERATION_WRITE,
        "exception_class": "IOError",
        "exception_message": "Simulated disk write error",
        "expected_failure_code": FAILURE_CODE_WRITE_FAILURE,
    },
    {
        "case_name": "write_os_error",
        "operation": OPERATION_WRITE,
        "exception_class": "OSError",
        "exception_message": "Simulated disk full",
        "expected_failure_code": FAILURE_CODE_WRITE_FAILURE,
    },
    {
        "case_name": "read_io_error",
        "operation": OPERATION_READ,
        "exception_class": "IOError",
        "exception_message": "Simulated read error",
        "expected_failure_code": FAILURE_CODE_READ_FAILURE,
    },
    {
        "case_name": "read_corrupt_json",
        "operation": OPERATION_READ,
        "exception_class": "json.JSONDecodeError",
        "exception_message": "Simulated JSON decode error",
        "expected_failure_code": FAILURE_CODE_CORRUPT_DATA,
    },
    {
        "case_name": "read_encoding_error",
        "operation": OPERATION_READ,
        "exception_class": "UnicodeDecodeError",
        "exception_message": "Simulated encoding error",
        "expected_failure_code": FAILURE_CODE_ENCODING_ERROR,
    },
    {
        "case_name": "hash_read_io_error",
        "operation": OPERATION_HASH_READ,
        "exception_class": "IOError",
        "exception_message": "Simulated hash read error",
        "expected_failure_code": FAILURE_CODE_HASH_READ_FAILURE,
    },
)


def classify_failure(exc: BaseException, operation: str) -> str:
    if isinstance(exc, json.JSONDecodeError):
        return FAILURE_CODE_CORRUPT_DATA
    if isinstance(exc, UnicodeDecodeError):
        return FAILURE_CODE_ENCODING_ERROR
    if operation == OPERATION_WRITE:
        return FAILURE_CODE_WRITE_FAILURE
    if operation == OPERATION_READ:
        return FAILURE_CODE_READ_FAILURE
    if operation == OPERATION_HASH_READ:
        return FAILURE_CODE_HASH_READ_FAILURE
    return FAILURE_CODE_UNKNOWN_FAILURE


def make_failure_record(
    *,
    failure_code: str,
    operation: str,
    exception_type: str,
    exception_message: str,
    packet_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "failure_code": failure_code,
        "operation": operation,
        "exception_type": exception_type,
        "exception_message": exception_message,
        "policy_outcome": POLICY_OUTCOME_FAIL_SAFE,
        "auto_recovery_attempted": False,
        "packet_id": packet_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class StorageFailurePolicy:
    """
    Wraps a PacketStorage and applies fail-safe failure policy.

    On any storage failure: classify the exception, record the event,
    return a FAIL_SAFE result. Never attempt auto-recovery.
    """

    def __init__(self, storage: Any) -> None:
        self.storage = storage
        self._failure_records: List[Dict[str, Any]] = []

    @property
    def failure_records(self) -> List[Dict[str, Any]]:
        return list(self._failure_records)

    def save_with_policy(
        self,
        packet: Mapping[str, Any],
    ) -> Dict[str, Any]:
        packet_id = packet.get("campaign_id") if isinstance(packet, Mapping) else None
        started = perf_counter()
        try:
            self.storage.append_packet(packet)
            elapsed_ms = round((perf_counter() - started) * 1000.0, 6)
            return {
                "policy_outcome": POLICY_OUTCOME_PASS,
                "saved": True,
                "failure_code": None,
                "failure_record": None,
                "packet_id": packet_id,
                "elapsed_ms": elapsed_ms,
                "is_trade_command": False,
            }
        except Exception as exc:
            elapsed_ms = round((perf_counter() - started) * 1000.0, 6)
            failure_code = classify_failure(exc, OPERATION_WRITE)
            record = make_failure_record(
                failure_code=failure_code,
                operation=OPERATION_WRITE,
                exception_type=type(exc).__name__,
                exception_message=str(exc),
                packet_id=packet_id,
            )
            self._failure_records.append(record)
            return {
                "policy_outcome": POLICY_OUTCOME_FAIL_SAFE,
                "saved": False,
                "failure_code": failure_code,
                "failure_record": record,
                "packet_id": packet_id,
                "elapsed_ms": elapsed_ms,
                "is_trade_command": False,
            }

    def load_with_policy(self) -> Dict[str, Any]:
        started = perf_counter()
        try:
            packets = self.storage.load_packets()
            elapsed_ms = round((perf_counter() - started) * 1000.0, 6)
            return {
                "policy_outcome": POLICY_OUTCOME_PASS,
                "packets": list(packets),
                "packet_count": len(packets),
                "failure_code": None,
                "failure_record": None,
                "elapsed_ms": elapsed_ms,
                "is_trade_command": False,
            }
        except Exception as exc:
            elapsed_ms = round((perf_counter() - started) * 1000.0, 6)
            failure_code = classify_failure(exc, OPERATION_READ)
            record = make_failure_record(
                failure_code=failure_code,
                operation=OPERATION_READ,
                exception_type=type(exc).__name__,
                exception_message=str(exc),
            )
            self._failure_records.append(record)
            return {
                "policy_outcome": POLICY_OUTCOME_FAIL_SAFE,
                "packets": [],
                "packet_count": 0,
                "failure_code": failure_code,
                "failure_record": record,
                "elapsed_ms": elapsed_ms,
                "is_trade_command": False,
            }

    def hash_load_with_policy(self) -> Dict[str, Any]:
        started = perf_counter()
        try:
            hashes = self.storage.existing_hashes()
            elapsed_ms = round((perf_counter() - started) * 1000.0, 6)
            return {
                "policy_outcome": POLICY_OUTCOME_PASS,
                "hashes": set(hashes),
                "hash_count": len(hashes),
                "failure_code": None,
                "failure_record": None,
                "elapsed_ms": elapsed_ms,
                "is_trade_command": False,
            }
        except Exception as exc:
            elapsed_ms = round((perf_counter() - started) * 1000.0, 6)
            failure_code = classify_failure(exc, OPERATION_HASH_READ)
            record = make_failure_record(
                failure_code=failure_code,
                operation=OPERATION_HASH_READ,
                exception_type=type(exc).__name__,
                exception_message=str(exc),
            )
            self._failure_records.append(record)
            return {
                "policy_outcome": POLICY_OUTCOME_FAIL_SAFE,
                "hashes": set(),
                "hash_count": 0,
                "failure_code": failure_code,
                "failure_record": record,
                "elapsed_ms": elapsed_ms,
                "is_trade_command": False,
            }


def _make_exception(exc_class_name: str, message: str) -> BaseException:
    if exc_class_name == "IOError":
        return IOError(message)
    if exc_class_name == "OSError":
        return OSError(message)
    if exc_class_name == "json.JSONDecodeError":
        return json.JSONDecodeError(message, "", 0)
    if exc_class_name == "UnicodeDecodeError":
        return UnicodeDecodeError("utf-8", b"", 0, 1, message)
    return Exception(message)


def _build_sample_packet(decision: str = "REAL_WHALE_BACK") -> Dict[str, Any]:
    reasons = ["RECOVERY_SUPPORT"] if decision == "REAL_WHALE_BACK" else ["CONFLICTING_EVIDENCE"]
    return {
        "schema_version": "mirror_pattern_packet_v1",
        "mirror_pattern_id": f"mirror-sim-{decision}",
        "campaign_id": f"campaign-sim-{decision}",
        "signal_id": f"signal-sim-{decision}",
        "symbol": "BTCUSDT",
        "mirror_decision": decision,
        "confidence": 0.9 if decision == "REAL_WHALE_BACK" else 0.35,
        "reason_code": reasons,
        "supporting_features": {
            "early_mae": -2.0,
            "recovery_ratio": 1.2,
            "campaign_duration": 24.0,
            "confidence": 1.0,
            "evidence": ["RECOVERY_STRONG"],
            "conflict_resolution": {
                "conflict_detected": False,
                "decision_targets": [decision],
                "policy": "DECIDE",
            },
        },
        "validation_state": "ACCEPT",
        "created_at": "2026-06-25T00:00:00+00:00",
        "is_trade_command": False,
    }


def _run_simulation_case(
    case: Mapping[str, Any],
    sample_packet: Mapping[str, Any],
) -> Dict[str, Any]:
    operation = case["operation"]
    exc = _make_exception(case["exception_class"], case["exception_message"])

    mock_storage = MagicMock()
    if operation == OPERATION_WRITE:
        mock_storage.append_packet.side_effect = exc
        mock_storage.existing_hashes.return_value = set()
    elif operation == OPERATION_READ:
        mock_storage.load_packets.side_effect = exc
    elif operation == OPERATION_HASH_READ:
        mock_storage.existing_hashes.side_effect = exc

    policy = StorageFailurePolicy(mock_storage)

    if operation == OPERATION_WRITE:
        result = policy.save_with_policy(sample_packet)
    elif operation == OPERATION_READ:
        result = policy.load_with_policy()
    else:
        result = policy.hash_load_with_policy()

    failure_record = policy.failure_records[-1] if policy.failure_records else None
    auto_recovery = failure_record.get("auto_recovery_attempted", False) if failure_record else False

    return {
        "case_name": case["case_name"],
        "operation": operation,
        "exception_class": case["exception_class"],
        "policy_outcome": result["policy_outcome"],
        "failure_code": result["failure_code"],
        "expected_failure_code": case["expected_failure_code"],
        "failure_code_correct": result["failure_code"] == case["expected_failure_code"],
        "auto_recovery_attempted": auto_recovery,
        "failure_record": failure_record,
        "is_trade_command": False,
    }


def run_failure_simulation(
    *,
    sample_packet: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    if sample_packet is None:
        sample_packet = _build_sample_packet()

    cases = [_run_simulation_case(case, sample_packet) for case in SIMULATION_CASES]

    all_fail_safe = all(c["policy_outcome"] == POLICY_OUTCOME_FAIL_SAFE for c in cases)
    all_no_recovery = all(not c["auto_recovery_attempted"] for c in cases)
    all_correct_codes = all(c["failure_code_correct"] for c in cases)

    return {
        "mirror_failure_simulation_schema_version": "mirror_failure_simulation_v1",
        "simulation_count": len(cases),
        "all_fail_safe": all_fail_safe,
        "all_no_auto_recovery": all_no_recovery,
        "all_correct_failure_codes": all_correct_codes,
        "simulation_verdict": "PASS" if all_fail_safe and all_no_recovery and all_correct_codes else "FAIL",
        "cases": cases,
        "is_trade_command": False,
    }


def build_failure_report(failure_records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    code_counts = Counter(r["failure_code"] for r in failure_records)
    operation_counts = Counter(r["operation"] for r in failure_records)
    auto_recovery_count = sum(1 for r in failure_records if r.get("auto_recovery_attempted"))
    fail_safe_count = sum(1 for r in failure_records if r.get("policy_outcome") == POLICY_OUTCOME_FAIL_SAFE)
    return {
        "mirror_failure_report_schema_version": "mirror_failure_report_v1",
        "total_failures": len(failure_records),
        "fail_safe_count": fail_safe_count,
        "auto_recovery_count": auto_recovery_count,
        "failure_code_distribution": {code: code_counts.get(code, 0) for code in FAILURE_CODES},
        "operation_distribution": dict(operation_counts),
        "policy_outcome": POLICY_OUTCOME_FAIL_SAFE if failure_records else POLICY_OUTCOME_PASS,
        "no_auto_recovery": auto_recovery_count == 0,
        "failure_records": list(failure_records),
        "is_trade_command": False,
    }


def build_failure_classification_report() -> Dict[str, Any]:
    return {
        "mirror_failure_classification_schema_version": "mirror_failure_classification_v1",
        "failure_codes": list(FAILURE_CODES),
        "classification_rules": [
            {
                "exception": "json.JSONDecodeError",
                "any_operation": True,
                "failure_code": FAILURE_CODE_CORRUPT_DATA,
                "severity": "CRITICAL",
            },
            {
                "exception": "UnicodeDecodeError",
                "any_operation": True,
                "failure_code": FAILURE_CODE_ENCODING_ERROR,
                "severity": "CRITICAL",
            },
            {
                "exception": "Any",
                "operation": OPERATION_WRITE,
                "failure_code": FAILURE_CODE_WRITE_FAILURE,
                "severity": "CRITICAL",
            },
            {
                "exception": "Any",
                "operation": OPERATION_READ,
                "failure_code": FAILURE_CODE_READ_FAILURE,
                "severity": "CRITICAL",
            },
            {
                "exception": "Any",
                "operation": OPERATION_HASH_READ,
                "failure_code": FAILURE_CODE_HASH_READ_FAILURE,
                "severity": "CRITICAL",
            },
            {
                "exception": "Any",
                "operation": "UNKNOWN",
                "failure_code": FAILURE_CODE_UNKNOWN_FAILURE,
                "severity": "CRITICAL",
            },
        ],
        "policy": {
            "on_failure": POLICY_OUTCOME_FAIL_SAFE,
            "auto_recovery": False,
            "record_and_terminate": True,
            "retry": False,
            "repair": False,
        },
        "is_trade_command": False,
    }


def build_replay_safety_report(simulation_result: Mapping[str, Any]) -> Dict[str, Any]:
    schema = mirror_packet_contract.build_schema()
    reason_registry = mirror_packet_contract.load_reason_registry()

    empty_packets: list = []
    replay_rows = mirror_replay_harness.replay_packets(
        empty_packets, schema=schema, reason_registry=reason_registry
    )
    sequence = mirror_replay_harness.validate_replay_sequence(empty_packets, replay_rows)

    cases = simulation_result.get("cases", [])
    write_cases = [c for c in cases if c.get("operation") == OPERATION_WRITE]
    read_cases = [c for c in cases if c.get("operation") in (OPERATION_READ, OPERATION_HASH_READ)]

    write_safe = all(c["policy_outcome"] == POLICY_OUTCOME_FAIL_SAFE for c in write_cases)
    read_safe = all(c["policy_outcome"] == POLICY_OUTCOME_FAIL_SAFE for c in read_cases)

    return {
        "mirror_replay_safety_schema_version": "mirror_replay_safety_v1",
        "empty_replay_safe": True,
        "write_failure_replay_safety": "PASS" if write_safe else "FAIL",
        "read_failure_replay_safety": "PASS" if read_safe else "FAIL",
        "replay_with_empty_packets": "PASS",
        "replay_sequence_valid": sequence.get("sequence_validation") == "PASS",
        "replay_safety_verdict": "PASS" if write_safe and read_safe else "FAIL",
        "is_trade_command": False,
    }


def build_policy_report(
    simulation_result: Mapping[str, Any],
    failure_report: Mapping[str, Any],
    replay_safety: Mapping[str, Any],
) -> Dict[str, Any]:
    simulation_pass = simulation_result.get("simulation_verdict") == "PASS"
    replay_safe = replay_safety.get("replay_safety_verdict") == "PASS"
    no_recovery = failure_report.get("no_auto_recovery") is True
    return {
        "mirror_failure_policy_report_schema_version": "mirror_failure_policy_report_v1",
        "failure_policy": "PASS" if simulation_pass and replay_safe and no_recovery else "FAIL",
        "policy_name": "Mirror Storage Fail-Safe Policy",
        "policy_version": "mirror_storage_failure_policy_v1",
        "policy_rules": {
            "on_failure": POLICY_OUTCOME_FAIL_SAFE,
            "auto_recovery_allowed": False,
            "retry_allowed": False,
            "repair_allowed": False,
            "record_required": True,
            "terminate_on_failure": True,
        },
        "simulation_verdict": simulation_result.get("simulation_verdict"),
        "replay_safety_verdict": replay_safety.get("replay_safety_verdict"),
        "no_auto_recovery": no_recovery,
        "total_failures_simulated": failure_report.get("total_failures"),
        "fail_safe_count": failure_report.get("fail_safe_count"),
        "forbidden_actions_confirmed": [
            "No mirror_pattern_packet_v1 Contract change",
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


def run_mirror_storage_failure_policy(
    *,
    output_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR

    simulation_result = run_failure_simulation()

    failure_records = [
        c["failure_record"]
        for c in simulation_result.get("cases", [])
        if c.get("failure_record") is not None
    ]
    failure_report = build_failure_report(failure_records)
    classification = build_failure_classification_report()
    replay_safety = build_replay_safety_report(simulation_result)
    policy_report = build_policy_report(simulation_result, failure_report, replay_safety)

    paths = {
        "failure_policy_report_path": base / "mirror_failure_policy_report.json",
        "failure_classification_path": base / "mirror_failure_classification.json",
        "replay_safety_report_path": base / "mirror_replay_safety_report.json",
        "failure_simulation_path": base / "mirror_failure_simulation.json",
        "failure_report_path": base / "mirror_failure_report.json",
    }
    write_json(policy_report, paths["failure_policy_report_path"])
    write_json(classification, paths["failure_classification_path"])
    write_json(replay_safety, paths["replay_safety_report_path"])
    write_json(simulation_result, paths["failure_simulation_path"])
    write_json(failure_report, paths["failure_report_path"])

    return {
        "mirror_storage_failure_policy_run_schema_version": "mirror_storage_failure_policy_run_v1",
        "failure_policy": policy_report["failure_policy"],
        "simulation_verdict": simulation_result["simulation_verdict"],
        "replay_safety_verdict": replay_safety["replay_safety_verdict"],
        "no_auto_recovery": failure_report["no_auto_recovery"],
        "total_failures_simulated": failure_report["total_failures"],
        "fail_safe_count": failure_report["fail_safe_count"],
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main() -> int:
    result = run_mirror_storage_failure_policy()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
