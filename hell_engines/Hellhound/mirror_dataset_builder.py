"""
Mirror Dataset Builder (Sprint 12AL)

Converts Mirror Pattern Packets into ML-ready Dataset Samples.
Maintains canonical JSON, packet hash, and contract version.
No ML implementation. No Feature Engineering. Dataset Contract only.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Mapping, Optional, Sequence

try:
    import mirror_dataset_contract as dataset_contract
    import mirror_packet_contract
    import mirror_replay_harness
except ImportError:
    from . import mirror_dataset_contract as dataset_contract
    from . import mirror_packet_contract
    from . import mirror_replay_harness


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_SOURCE_PATH = DEFAULT_OUTPUT_DIR / "mirror_shadow_log.jsonl"
DEFAULT_DATASET_PATH = DEFAULT_OUTPUT_DIR / "mirror_dataset.jsonl"


def _canonical_hash(packet: Mapping[str, Any]) -> str:
    payload = json.dumps(dict(packet), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _make_sample_id(packet: Mapping[str, Any]) -> str:
    return f"ds-{_canonical_hash(packet)[:16]}"


def _extract_feature(supporting: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "early_mae": supporting.get("early_mae"),
        "recovery_ratio": supporting.get("recovery_ratio"),
        "campaign_duration": supporting.get("campaign_duration"),
        "confidence": supporting.get("confidence"),
    }


def _build_replay_metadata(packet: Mapping[str, Any], schema: Mapping[str, Any], reason_registry: set) -> Dict[str, Any]:
    replay_rows = mirror_replay_harness.replay_packets([packet], schema=schema, reason_registry=reason_registry)
    row = replay_rows[0] if replay_rows else {}
    return {
        "replay_result": "PASS" if not row.get("packet_mutated") and row.get("contract_validation") == "PASS" else "FAIL",
        "contract_validation": row.get("contract_validation", "FAIL"),
        "packet_mutated": row.get("packet_mutated", False),
    }


def _build_readback_status(packet: Mapping[str, Any], packet_hash: str) -> Dict[str, Any]:
    # Verify canonical JSON round-trip preserves identity
    canonical = json.dumps(dict(packet), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    roundtrip = json.loads(canonical)
    roundtrip_hash = _canonical_hash(roundtrip)
    return {
        "hash_verified": roundtrip_hash == packet_hash,
        "encoding": "utf-8_without_bom",
    }


def build_dataset_sample(
    packet: Mapping[str, Any],
    *,
    schema: Optional[Mapping[str, Any]] = None,
    reason_registry: Optional[set] = None,
    sample_id: Optional[str] = None,
) -> Dict[str, Any]:
    if schema is None:
        schema = mirror_packet_contract.build_schema()
    if reason_registry is None:
        reason_registry = mirror_packet_contract.load_reason_registry()

    packet_hash = _canonical_hash(packet)
    supporting = packet.get("supporting_features") or {}

    replay_metadata = _build_replay_metadata(packet, schema, reason_registry)
    readback_status = _build_readback_status(packet, packet_hash)

    return {
        "sample_id": sample_id or _make_sample_id(packet),
        "contract_version": mirror_packet_contract.CONTRACT_VERSION,
        "dataset_contract_version": dataset_contract.DATASET_CONTRACT_VERSION,
        "packet_hash": packet_hash,
        "feature": _extract_feature(supporting),
        "evidence": list(supporting.get("evidence") or []),
        "reason": list(packet.get("reason_code") or []),
        "decision": packet.get("mirror_decision"),
        "replay_metadata": replay_metadata,
        "persistence_metadata": {
            "storage_type": "jsonl_file",
            "append_only": True,
            "dataset_version": dataset_contract.DATASET_CONTRACT_VERSION,
        },
        "readback_status": readback_status,
        "outcome_placeholder": None,
        "label_placeholder": None,
        "created_at": packet.get("created_at"),
        "is_trade_command": False,
    }


def build_dataset_samples(
    packets: Sequence[Mapping[str, Any]],
    *,
    schema: Optional[Mapping[str, Any]] = None,
    reason_registry: Optional[set] = None,
) -> List[Dict[str, Any]]:
    if schema is None:
        schema = mirror_packet_contract.build_schema()
    if reason_registry is None:
        reason_registry = mirror_packet_contract.load_reason_registry()
    return [
        build_dataset_sample(p, schema=schema, reason_registry=reason_registry)
        for p in packets
    ]


def write_dataset(samples: Sequence[Mapping[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        for sample in samples:
            file.write(json.dumps(dict(sample), sort_keys=True) + "\n")


def build_dataset_statistics(samples: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    decision_counts = Counter(s.get("decision") for s in samples)
    replay_pass = sum(1 for s in samples if s.get("replay_metadata", {}).get("replay_result") == "PASS")
    hash_verified = sum(1 for s in samples if s.get("readback_status", {}).get("hash_verified") is True)
    outcome_null = sum(1 for s in samples if s.get("outcome_placeholder") is None)
    label_null = sum(1 for s in samples if s.get("label_placeholder") is None)
    mutation_count = sum(1 for s in samples if s.get("replay_metadata", {}).get("packet_mutated") is True)
    validation = dataset_contract.validate_samples(samples)

    return {
        "mirror_dataset_statistics_schema_version": "mirror_dataset_statistics_v1",
        "dataset_contract_version": dataset_contract.DATASET_CONTRACT_VERSION,
        "sample_count": len(samples),
        "decision_distribution": {
            decision: decision_counts.get(decision, 0)
            for decision in mirror_packet_contract.DECISION_ENUM
        },
        "replay_pass_count": replay_pass,
        "hash_verified_count": hash_verified,
        "outcome_placeholder_null_count": outcome_null,
        "label_placeholder_null_count": label_null,
        "mutation_count": mutation_count,
        "validation_result": validation["validation_result"],
        "validation_pass_count": validation["pass_count"],
        "is_trade_command": False,
    }


def run_mirror_dataset_builder(
    *,
    output_dir: Optional[Path | str] = None,
    source_path: Path | str = DEFAULT_SOURCE_PATH,
    source_packets: Optional[Sequence[Mapping[str, Any]]] = None,
    dataset_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    storage_path = Path(dataset_path) if dataset_path is not None else base / "mirror_dataset.jsonl"

    if source_packets is not None:
        packets = list(source_packets)
    else:
        packets = mirror_replay_harness.load_replay_packets(source_path)

    schema = mirror_packet_contract.build_schema()
    reason_registry = mirror_packet_contract.load_reason_registry()

    started = perf_counter()
    samples = build_dataset_samples(packets, schema=schema, reason_registry=reason_registry)
    elapsed_ms = round((perf_counter() - started) * 1000.0, 6)

    # Remove existing dataset for clean run (append-only in production; clean for test runs)
    if storage_path.exists():
        storage_path.unlink()
    write_dataset(samples, storage_path)

    validation = dataset_contract.validate_samples(samples)
    statistics = build_dataset_statistics(samples)

    # Build a representative single sample for report
    sample_report = dict(samples[0]) if samples else {}

    schema_doc = dataset_contract.build_dataset_schema()

    paths = {
        "dataset_sample_path": base / "mirror_dataset_sample.json",
        "dataset_statistics_path": base / "mirror_dataset_statistics.json",
        "dataset_schema_path": base / "mirror_dataset_schema.json",
        "dataset_validation_path": base / "mirror_dataset_validation.json",
    }
    _write_json(sample_report, paths["dataset_sample_path"])
    _write_json(statistics, paths["dataset_statistics_path"])
    _write_json(schema_doc, paths["dataset_schema_path"])
    _write_json(validation, paths["dataset_validation_path"])

    return {
        "mirror_dataset_builder_run_schema_version": "mirror_dataset_builder_run_v1",
        "dataset_contract_version": dataset_contract.DATASET_CONTRACT_VERSION,
        "contract_version": mirror_packet_contract.CONTRACT_VERSION,
        "packet_count": len(packets),
        "sample_count": len(samples),
        "validation_result": validation["validation_result"],
        "mutation_count": statistics["mutation_count"],
        "hash_verified_count": statistics["hash_verified_count"],
        "outcome_placeholder_null_count": statistics["outcome_placeholder_null_count"],
        "label_placeholder_null_count": statistics["label_placeholder_null_count"],
        "elapsed_ms": elapsed_ms,
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main() -> int:
    result = run_mirror_dataset_builder()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
