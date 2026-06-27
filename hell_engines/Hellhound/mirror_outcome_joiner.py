"""
Mirror Outcome Joiner (Sprint 12AN)

Joins Mirror Dataset Samples with Replay Outcomes.
Fills outcome_placeholder with replay_outcome.
live_outcome is always JSON null — Live Sprint only.
Never fills label_placeholder. Never modifies original dataset.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

try:
    import mirror_dataset_contract as dataset_contract
    import mirror_packet_contract
    import mirror_replay_harness
except ImportError:
    from . import mirror_dataset_contract as dataset_contract
    from . import mirror_packet_contract
    from . import mirror_replay_harness


JOINER_VERSION = "mirror_outcome_joiner_v1"
OUTCOME_CONTRACT_VERSION = "mirror_outcome_contract_v1"

REPLAY_OUTCOME_STATUS = ("VALID", "MUTATED", "INVALID", "NO_MATCH")

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_DATASET_PATH = DEFAULT_OUTPUT_DIR / "mirror_dataset.jsonl"
DEFAULT_SOURCE_PATH = DEFAULT_OUTPUT_DIR / "mirror_shadow_log.jsonl"


def _canonical_hash(obj: Mapping[str, Any]) -> str:
    payload = json.dumps(dict(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _replay_outcome_status(replay_row: Optional[Mapping[str, Any]]) -> str:
    if not replay_row:
        return "NO_MATCH"
    if replay_row.get("packet_mutated"):
        return "MUTATED"
    if replay_row.get("contract_validation") != "PASS":
        return "INVALID"
    return "VALID"


def build_outcome_placeholder(replay_row: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Build outcome_placeholder structure. live_outcome is always null."""
    status = _replay_outcome_status(replay_row)
    metadata: Dict[str, Any] = {}
    if replay_row:
        metadata = {
            "contract_validation": replay_row.get("contract_validation"),
            "packet_mutated": replay_row.get("packet_mutated", False),
            "decision": replay_row.get("decision"),
            "confidence": replay_row.get("confidence"),
            "validation_state": replay_row.get("validation_state"),
            "processing_time_ms": replay_row.get("processing_time_ms"),
        }
    return {
        "replay_outcome": {
            "status": status,
            "metadata": metadata,
        },
        "live_outcome": None,  # JSON null — Live Sprint only
    }


def join_sample_with_outcome(
    sample: Mapping[str, Any],
    replay_row: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Return a new sample dict with outcome_placeholder filled. Never mutates input."""
    joined = copy.deepcopy(dict(sample))
    joined["outcome_placeholder"] = build_outcome_placeholder(replay_row)
    # label_placeholder intentionally stays None
    return joined


def join_dataset_with_replay(
    samples: Sequence[Mapping[str, Any]],
    packets: Sequence[Mapping[str, Any]],
    *,
    schema: Optional[Mapping[str, Any]] = None,
    reason_registry: Optional[set] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Match samples to packets by packet_hash, run replay, join outcomes.
    Returns (joined_samples, join_mapping).
    Read-only: never modifies input samples or packets.
    """
    if schema is None:
        schema = mirror_packet_contract.build_schema()
    if reason_registry is None:
        reason_registry = mirror_packet_contract.load_reason_registry()

    # Build packet_hash → packet lookup
    packet_by_hash: Dict[str, Any] = {}
    for packet in packets:
        packet_by_hash[_canonical_hash(packet)] = packet

    # Collect only matched packets in sample order for replay
    matched: List[Tuple[str, Any]] = []  # (packet_hash, packet)
    for sample in samples:
        ph = sample.get("packet_hash")
        if ph and ph in packet_by_hash:
            matched.append((ph, packet_by_hash[ph]))

    # Run replay in batch
    replay_by_hash: Dict[str, Any] = {}
    if matched:
        hashes, matched_packets = zip(*matched)
        replay_rows = mirror_replay_harness.replay_packets(
            list(matched_packets), schema=schema, reason_registry=reason_registry
        )
        for h, row in zip(hashes, replay_rows):
            replay_by_hash[h] = row

    # Join and build mapping
    joined_samples: List[Dict[str, Any]] = []
    join_mapping: List[Dict[str, Any]] = []

    for sample in samples:
        ph = sample.get("packet_hash")
        replay_row = replay_by_hash.get(ph) if ph else None
        joined = join_sample_with_outcome(sample, replay_row)
        joined_samples.append(joined)
        join_mapping.append({
            "sample_id": sample.get("sample_id"),
            "packet_hash": ph,
            "matched": ph in replay_by_hash,
            "outcome_status": joined["outcome_placeholder"]["replay_outcome"]["status"],
            "live_outcome_null": joined["outcome_placeholder"]["live_outcome"] is None,
            "label_placeholder_null": joined.get("label_placeholder") is None,
        })

    return joined_samples, join_mapping


def validate_join(
    joined_samples: Sequence[Mapping[str, Any]],
    original_samples: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Validate join correctness. Checks mutation, contract, and placeholder rules."""
    issues: List[Dict[str, Any]] = []

    for i, (joined, original) in enumerate(zip(joined_samples, original_samples)):
        sample_id = joined.get("sample_id")

        # Packet hash unchanged
        if joined.get("packet_hash") != original.get("packet_hash"):
            issues.append({"index": i, "sample_id": sample_id, "issue": "packet_hash_mutated"})

        # Core data fields unchanged
        for field in ("feature", "evidence", "reason", "decision", "contract_version", "dataset_contract_version"):
            if joined.get(field) != original.get(field):
                issues.append({"index": i, "sample_id": sample_id, "issue": f"{field}_mutated"})

        # label_placeholder still null
        if joined.get("label_placeholder") is not None:
            issues.append({"index": i, "sample_id": sample_id, "issue": "label_placeholder_filled"})

        # outcome_placeholder is now filled (not None) and has correct structure
        op = joined.get("outcome_placeholder")
        if op is None:
            issues.append({"index": i, "sample_id": sample_id, "issue": "outcome_placeholder_missing"})
        elif not isinstance(op, dict):
            issues.append({"index": i, "sample_id": sample_id, "issue": "outcome_placeholder_wrong_type"})
        else:
            if "replay_outcome" not in op:
                issues.append({"index": i, "sample_id": sample_id, "issue": "replay_outcome_missing"})
            if "live_outcome" not in op:
                issues.append({"index": i, "sample_id": sample_id, "issue": "live_outcome_missing"})
            elif op.get("live_outcome") is not None:
                issues.append({"index": i, "sample_id": sample_id, "issue": "live_outcome_not_null"})

    mutation_count = sum(1 for iss in issues if "mutated" in iss.get("issue", ""))
    valid = not issues
    return {
        "join_validation_result": "PASS" if valid else "FAIL",
        "issue_count": len(issues),
        "mutation_count": mutation_count,
        "issues": issues,
    }


def build_join_statistics(
    joined_samples: Sequence[Mapping[str, Any]],
    join_mapping: Sequence[Mapping[str, Any]],
    validation: Mapping[str, Any],
) -> Dict[str, Any]:
    status_counts = Counter(m.get("outcome_status") for m in join_mapping)
    matched = sum(1 for m in join_mapping if m.get("matched"))
    live_null = sum(1 for s in joined_samples if s.get("outcome_placeholder", {}).get("live_outcome") is None)
    label_null = sum(1 for s in joined_samples if s.get("label_placeholder") is None)

    return {
        "outcome_statistics_schema_version": "mirror_outcome_statistics_v1",
        "outcome_contract_version": OUTCOME_CONTRACT_VERSION,
        "sample_count": len(joined_samples),
        "matched_count": matched,
        "unmatched_count": len(joined_samples) - matched,
        "join_result": "PASS" if matched == len(joined_samples) else "PARTIAL",
        "outcome_status_distribution": {s: status_counts.get(s, 0) for s in REPLAY_OUTCOME_STATUS},
        "live_outcome_null_count": live_null,
        "label_placeholder_null_count": label_null,
        "mutation_count": validation.get("mutation_count", 0),
        "join_validation_result": validation.get("join_validation_result"),
        "is_trade_command": False,
    }


def run_mirror_outcome_joiner(
    *,
    output_dir: Optional["Path | str"] = None,
    dataset_path: Optional["Path | str"] = None,
    source_path: Optional["Path | str"] = None,
    source_packets: Optional[Sequence[Mapping[str, Any]]] = None,
    source_samples: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    ds_path = Path(dataset_path) if dataset_path is not None else DEFAULT_DATASET_PATH
    src_path = Path(source_path) if source_path is not None else DEFAULT_SOURCE_PATH

    # Load samples
    if source_samples is not None:
        samples = list(source_samples)
    else:
        samples = dataset_contract.load_dataset(ds_path)

    # Load packets
    if source_packets is not None:
        packets = list(source_packets)
    else:
        packets = mirror_replay_harness.load_replay_packets(src_path)

    schema = mirror_packet_contract.build_schema()
    reason_registry = mirror_packet_contract.load_reason_registry()

    started = perf_counter()
    joined_samples, join_mapping = join_dataset_with_replay(
        samples, packets, schema=schema, reason_registry=reason_registry
    )
    elapsed_ms = round((perf_counter() - started) * 1000.0, 6)

    validation = validate_join(joined_samples, samples)
    statistics = build_join_statistics(joined_samples, join_mapping, validation)

    join_report = {
        "outcome_joiner_version": JOINER_VERSION,
        "outcome_contract_version": OUTCOME_CONTRACT_VERSION,
        "dataset_contract_version": dataset_contract.DATASET_CONTRACT_VERSION,
        "contract_version": mirror_packet_contract.CONTRACT_VERSION,
        "sample_count": len(samples),
        "matched_count": statistics["matched_count"],
        "unmatched_count": statistics["unmatched_count"],
        "join_result": statistics["join_result"],
        "join_validation_result": validation["join_validation_result"],
        "mutation_count": validation["mutation_count"],
        "live_outcome_null_count": statistics["live_outcome_null_count"],
        "label_placeholder_null_count": statistics["label_placeholder_null_count"],
        "elapsed_ms": elapsed_ms,
        "is_trade_command": False,
    }

    outcome_mapping = {
        "outcome_mapping_schema_version": "mirror_outcome_mapping_v1",
        "outcome_contract_version": OUTCOME_CONTRACT_VERSION,
        "sample_count": len(join_mapping),
        "rows": join_mapping,
        "is_trade_command": False,
    }

    _write_json(join_report, base / "mirror_outcome_join_report.json")
    _write_json(outcome_mapping, base / "mirror_outcome_mapping.json")
    _write_json(statistics, base / "mirror_outcome_statistics.json")

    return join_report


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main() -> int:
    result = run_mirror_outcome_joiner()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("join_validation_result") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
