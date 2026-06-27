"""
Mirror Dataset Integrity Checker (Sprint 12AM)

Read-only validation of mirror_dataset.jsonl.
Never modifies dataset. Never auto-recovers. Records issues and returns fail-safe result.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

try:
    import mirror_dataset_contract as dataset_contract
    import mirror_packet_contract
except ImportError:
    from . import mirror_dataset_contract as dataset_contract
    from . import mirror_packet_contract


INTEGRITY_CHECKER_VERSION = "mirror_dataset_integrity_checker_v1"

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_DATASET_PATH = DEFAULT_OUTPUT_DIR / "mirror_dataset.jsonl"

_PARSED_ROWS = List[Tuple[int, Dict[str, Any]]]
_PARSE_ERRORS = List[Dict[str, Any]]


def _canonical_hash(obj: Mapping[str, Any]) -> str:
    payload = json.dumps(dict(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _check_utf8_bom(path: Path) -> Dict[str, Any]:
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    return {"utf8_bom_detected": bom, "encoding_result": "FAIL" if bom else "PASS"}


def _parse_jsonl(path: Path) -> Tuple[_PARSED_ROWS, _PARSE_ERRORS]:
    text = path.read_text(encoding="utf-8")
    rows: _PARSED_ROWS = []
    errors: _PARSE_ERRORS = []
    for idx, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            rows.append((idx, row))
        except json.JSONDecodeError as exc:
            errors.append({"line_index": idx, "raw_line": line[:200], "error": str(exc)})
    return rows, errors


def _check_contract_consistency(rows: _PARSED_ROWS) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    for i, row in rows:
        cv = row.get("contract_version")
        dcv = row.get("dataset_contract_version")
        if cv != mirror_packet_contract.CONTRACT_VERSION:
            issues.append({"line_index": i, "sample_id": row.get("sample_id"), "field": "contract_version", "value": cv})
        if dcv != dataset_contract.DATASET_CONTRACT_VERSION:
            issues.append({"line_index": i, "sample_id": row.get("sample_id"), "field": "dataset_contract_version", "value": dcv})
    return {
        "contract_consistency_result": "PASS" if not issues else "FAIL",
        "issue_count": len(issues),
        "issues": issues,
    }


def _check_hash_format(rows: _PARSED_ROWS) -> Dict[str, Any]:
    invalid: List[Dict[str, Any]] = []
    for i, row in rows:
        h = row.get("packet_hash", "")
        valid = isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h)
        if not valid:
            invalid.append({"line_index": i, "sample_id": row.get("sample_id"), "packet_hash": h})
    return {
        "hash_format_result": "PASS" if not invalid else "FAIL",
        "invalid_hash_count": len(invalid),
        "invalid_hashes": invalid,
    }


def _check_duplicates(rows: _PARSED_ROWS) -> Dict[str, Any]:
    ph_list = [row.get("packet_hash") for _, row in rows]
    si_list = [row.get("sample_id") for _, row in rows]

    ph_counts = Counter(h for h in ph_list if h is not None)
    si_counts = Counter(sid for sid in si_list if sid is not None)

    dup_ph = [h for h, count in ph_counts.items() if count > 1]
    dup_si = [sid for sid, count in si_counts.items() if count > 1]

    return {
        "duplicate_result": "PASS" if not dup_ph and not dup_si else "FAIL",
        "duplicate_packet_hash_count": len(dup_ph),
        "duplicate_sample_id_count": len(dup_si),
        "duplicate_packet_hashes": dup_ph,
        "duplicate_sample_ids": dup_si,
    }


def _check_canonical_roundtrip(rows: _PARSED_ROWS) -> Dict[str, Any]:
    failures: List[Dict[str, Any]] = []
    for i, row in rows:
        try:
            canonical = json.dumps(dict(row), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
            roundtrip = json.loads(canonical)
            if roundtrip != dict(row):
                failures.append({"line_index": i, "sample_id": row.get("sample_id"), "issue": "roundtrip_mismatch"})
        except (TypeError, ValueError, OverflowError) as exc:
            failures.append({"line_index": i, "sample_id": row.get("sample_id"), "issue": f"serialization_error: {exc}"})
    return {
        "canonical_roundtrip_result": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
    }


def _check_append_order(rows: _PARSED_ROWS) -> Dict[str, Any]:
    reversals: List[Dict[str, Any]] = []
    prev_ts: Optional[str] = None
    prev_idx: Optional[int] = None
    for i, row in rows:
        ts = row.get("created_at")
        if not isinstance(ts, str):
            continue
        if prev_ts is not None and ts < prev_ts:
            reversals.append({
                "line_index": i,
                "sample_id": row.get("sample_id"),
                "created_at": ts,
                "previous_line_index": prev_idx,
                "previous_created_at": prev_ts,
            })
        prev_ts = ts
        prev_idx = i
    return {
        "append_order_result": "PASS" if not reversals else "FAIL",
        "time_reversal_count": len(reversals),
        "reversals": reversals,
    }


def _check_placeholders(rows: _PARSED_ROWS) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    for i, row in rows:
        if row.get("outcome_placeholder") is not None:
            issues.append({"line_index": i, "sample_id": row.get("sample_id"), "field": "outcome_placeholder", "value": str(row["outcome_placeholder"])})
        if row.get("label_placeholder") is not None:
            issues.append({"line_index": i, "sample_id": row.get("sample_id"), "field": "label_placeholder", "value": str(row["label_placeholder"])})
    return {
        "placeholder_integrity_result": "PASS" if not issues else "FAIL",
        "issue_count": len(issues),
        "issues": issues,
    }


def _build_hash_audit(rows: _PARSED_ROWS) -> Dict[str, Any]:
    audit_rows: List[Dict[str, Any]] = []
    for i, row in rows:
        h = row.get("packet_hash", "")
        valid_fmt = isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h)
        audit_rows.append({
            "line_index": i,
            "sample_id": row.get("sample_id"),
            "packet_hash": h,
            "sample_canonical_hash": _canonical_hash(row),
            "hash_format_valid": valid_fmt,
        })
    return {
        "hash_audit_schema_version": "mirror_dataset_hash_audit_v1",
        "hash_audit_result": "PASS" if all(r["hash_format_valid"] for r in audit_rows) else "FAIL",
        "sample_count": len(audit_rows),
        "rows": audit_rows,
        "is_trade_command": False,
    }


def check_dataset_integrity(
    path: "Path | str",
    *,
    output_dir: "Optional[Path | str]" = None,
    write_reports: bool = False,
) -> Dict[str, Any]:
    """Read-only integrity check. Never modifies the dataset."""
    dataset_path = Path(path)

    if not dataset_path.exists():
        result: Dict[str, Any] = {
            "integrity_checker_version": INTEGRITY_CHECKER_VERSION,
            "integrity_result": "FAIL",
            "error": "dataset_not_found",
            "dataset_path": str(dataset_path),
            "is_trade_command": False,
        }
        if write_reports and output_dir is not None:
            base = Path(output_dir)
            _write_json(result, base / "mirror_dataset_integrity_report.json")
        return result

    bom_check = _check_utf8_bom(dataset_path)
    rows, parse_errors = _parse_jsonl(dataset_path)

    contract_check = _check_contract_consistency(rows)
    hash_check = _check_hash_format(rows)
    dup_check = _check_duplicates(rows)
    roundtrip_check = _check_canonical_roundtrip(rows)
    order_check = _check_append_order(rows)
    placeholder_check = _check_placeholders(rows)
    hash_audit = _build_hash_audit(rows)

    overall_pass = all([
        bom_check["encoding_result"] == "PASS",
        len(parse_errors) == 0,
        contract_check["contract_consistency_result"] == "PASS",
        hash_check["hash_format_result"] == "PASS",
        dup_check["duplicate_result"] == "PASS",
        roundtrip_check["canonical_roundtrip_result"] == "PASS",
        order_check["append_order_result"] == "PASS",
        placeholder_check["placeholder_integrity_result"] == "PASS",
    ])

    report: Dict[str, Any] = {
        "integrity_checker_version": INTEGRITY_CHECKER_VERSION,
        "dataset_path": str(dataset_path),
        "integrity_result": "PASS" if overall_pass else "FAIL",
        "sample_count": len(rows),
        "parse_error_count": len(parse_errors),
        "parse_errors": parse_errors,
        "utf8_bom_detected": bom_check["utf8_bom_detected"],
        "encoding_result": bom_check["encoding_result"],
        "contract_consistency_result": contract_check["contract_consistency_result"],
        "contract_issue_count": contract_check["issue_count"],
        "hash_format_result": hash_check["hash_format_result"],
        "invalid_hash_count": hash_check["invalid_hash_count"],
        "duplicate_result": dup_check["duplicate_result"],
        "duplicate_packet_hash_count": dup_check["duplicate_packet_hash_count"],
        "duplicate_sample_id_count": dup_check["duplicate_sample_id_count"],
        "canonical_roundtrip_result": roundtrip_check["canonical_roundtrip_result"],
        "roundtrip_failure_count": roundtrip_check["failure_count"],
        "append_order_result": order_check["append_order_result"],
        "time_reversal_count": order_check["time_reversal_count"],
        "placeholder_integrity_result": placeholder_check["placeholder_integrity_result"],
        "placeholder_issue_count": placeholder_check["issue_count"],
        "is_trade_command": False,
    }

    if write_reports and output_dir is not None:
        base = Path(output_dir)
        dup_report = {
            "duplicate_checker_schema_version": "mirror_dataset_duplicate_checker_v1",
            **dup_check,
            "is_trade_command": False,
        }
        _write_json(report, base / "mirror_dataset_integrity_report.json")
        _write_json(hash_audit, base / "mirror_dataset_hash_audit.json")
        _write_json(dup_report, base / "mirror_dataset_duplicate_report.json")

    return report


def run_mirror_dataset_integrity_checker(
    *,
    dataset_path: "Optional[Path | str]" = None,
    output_dir: "Optional[Path | str]" = None,
) -> Dict[str, Any]:
    path = Path(dataset_path) if dataset_path is not None else DEFAULT_DATASET_PATH
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    return check_dataset_integrity(path, output_dir=base, write_reports=True)


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main() -> int:
    result = run_mirror_dataset_integrity_checker()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("integrity_result") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
