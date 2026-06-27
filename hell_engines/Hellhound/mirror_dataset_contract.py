"""
Mirror Dataset Contract (Sprint 12AL)

Defines the Dataset Sample schema and validation rules
for Mirror Foundation ML dataset preparation.
Dataset Contract is separate from mirror_pattern_packet_v1 Contract.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

try:
    import mirror_packet_contract
except ImportError:
    from . import mirror_packet_contract


DATASET_CONTRACT_VERSION = "mirror_dataset_v1"
PACKET_CONTRACT_VERSION = mirror_packet_contract.CONTRACT_VERSION

REQUIRED_FIELDS = (
    "sample_id",
    "contract_version",
    "dataset_contract_version",
    "packet_hash",
    "feature",
    "evidence",
    "reason",
    "decision",
    "replay_metadata",
    "persistence_metadata",
    "readback_status",
    "outcome_placeholder",
    "label_placeholder",
    "created_at",
    "is_trade_command",
)

FEATURE_FIELDS = ("early_mae", "recovery_ratio", "campaign_duration", "confidence")

REPLAY_METADATA_FIELDS = ("replay_result", "contract_validation", "packet_mutated")
PERSISTENCE_METADATA_FIELDS = ("storage_type", "append_only", "dataset_version")
READBACK_STATUS_FIELDS = ("hash_verified", "encoding")

PACKET_HASH_HEX_LENGTH = 64


def build_dataset_schema() -> Dict[str, Any]:
    return {
        "dataset_schema_version": "mirror_dataset_schema_v1",
        "dataset_contract_version": DATASET_CONTRACT_VERSION,
        "packet_contract_version": PACKET_CONTRACT_VERSION,
        "required_fields": list(REQUIRED_FIELDS),
        "placeholder_policy": {
            "outcome_placeholder": "null — JSON null only. Never 0, '', 'unknown', or false.",
            "label_placeholder": "null — JSON null only. Never 0, '', 'unknown', or false.",
            "fill_condition": "Actual Outcome Validator and Label Builder stages only.",
        },
        "feature_fields": list(FEATURE_FIELDS),
        "replay_metadata_fields": list(REPLAY_METADATA_FIELDS),
        "persistence_metadata_fields": list(PERSISTENCE_METADATA_FIELDS),
        "readback_status_fields": list(READBACK_STATUS_FIELDS),
        "is_trade_command": False,
    }


def validate_sample(sample: Mapping[str, Any]) -> Dict[str, Any]:
    issues: list[Dict[str, str]] = []

    missing = [f for f in REQUIRED_FIELDS if f not in sample]
    issues.extend({"code": "missing_field", "field": f, "severity": "REJECT"} for f in missing)

    if "contract_version" in sample and sample["contract_version"] != PACKET_CONTRACT_VERSION:
        issues.append({"code": "wrong_contract_version", "field": "contract_version", "severity": "REJECT"})

    if "dataset_contract_version" in sample and sample["dataset_contract_version"] != DATASET_CONTRACT_VERSION:
        issues.append({"code": "wrong_dataset_contract_version", "field": "dataset_contract_version", "severity": "REJECT"})

    if "outcome_placeholder" in sample and sample["outcome_placeholder"] is not None:
        issues.append({"code": "placeholder_not_null", "field": "outcome_placeholder", "severity": "REJECT"})

    if "label_placeholder" in sample and sample["label_placeholder"] is not None:
        issues.append({"code": "placeholder_not_null", "field": "label_placeholder", "severity": "REJECT"})

    if "decision" in sample and sample["decision"] not in mirror_packet_contract.DECISION_ENUM:
        issues.append({"code": "invalid_decision", "field": "decision", "severity": "REJECT"})

    if "is_trade_command" in sample and sample["is_trade_command"] is not False:
        issues.append({"code": "is_trade_command_true", "field": "is_trade_command", "severity": "REJECT"})

    if "packet_hash" in sample:
        h = sample["packet_hash"]
        if not isinstance(h, str) or len(h) != PACKET_HASH_HEX_LENGTH or not all(c in "0123456789abcdef" for c in h):
            issues.append({"code": "invalid_packet_hash", "field": "packet_hash", "severity": "REJECT"})

    if "feature" in sample and not isinstance(sample["feature"], Mapping):
        issues.append({"code": "invalid_feature_type", "field": "feature", "severity": "REJECT"})

    if "evidence" in sample and not isinstance(sample["evidence"], list):
        issues.append({"code": "invalid_evidence_type", "field": "evidence", "severity": "REJECT"})

    if "reason" in sample and not isinstance(sample["reason"], list):
        issues.append({"code": "invalid_reason_type", "field": "reason", "severity": "REJECT"})

    valid = not any(row["severity"] == "REJECT" for row in issues)
    return {
        "valid": valid,
        "validation_result": "PASS" if valid else "REJECT",
        "issues": issues,
        "sample_id": sample.get("sample_id"),
    }


def validate_samples(samples: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    results = [validate_sample(s) for s in samples]
    pass_count = sum(1 for r in results if r["valid"])
    return {
        "mirror_dataset_validation_schema_version": "mirror_dataset_validation_v1",
        "dataset_contract_version": DATASET_CONTRACT_VERSION,
        "sample_count": len(samples),
        "pass_count": pass_count,
        "fail_count": len(samples) - pass_count,
        "validation_result": "PASS" if samples and pass_count == len(samples) else "FAIL",
        "results": results,
        "is_trade_command": False,
    }


def load_dataset(path: Path | str) -> List[Dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    samples = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            samples.append(json.loads(line))
    return samples


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    schema = build_dataset_schema()
    print(json.dumps(schema, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
