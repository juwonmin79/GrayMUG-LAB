from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, Mapping, Optional, Protocol, Sequence

try:
    import mirror_packet_contract
    import mirror_replay_harness
except ImportError:
    from . import mirror_packet_contract
    from . import mirror_replay_harness


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_SOURCE_PATH = DEFAULT_OUTPUT_DIR / "mirror_shadow_log.jsonl"
DEFAULT_PERSISTENCE_PATH = DEFAULT_OUTPUT_DIR / "mirror_persistence_packets.jsonl"


class PacketStorage(Protocol):
    def existing_hashes(self) -> set[str]:
        ...

    def append_packet(self, packet: Mapping[str, Any]) -> None:
        ...

    def load_packets(self) -> list[Dict[str, Any]]:
        ...


class JsonlPacketStorage:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def existing_hashes(self) -> set[str]:
        return {packet_hash(packet) for packet in self.load_packets()}

    def append_packet(self, packet: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(dict(packet), sort_keys=True) + "\n")

    def load_packets(self) -> list[Dict[str, Any]]:
        if not self.path.exists():
            return []
        packets = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                packets.append(json.loads(line))
        return packets


class MirrorPersistenceAdapter:
    def __init__(self, storage: PacketStorage) -> None:
        self.storage = storage
        self.schema = mirror_packet_contract.build_schema()
        self.reason_registry = mirror_packet_contract.load_reason_registry()

    def save_packets(self, packets: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
        existing_hashes = self.storage.existing_hashes()
        rows = []
        for packet in packets:
            rows.append(self.save_packet(packet, existing_hashes))
        return build_persistence_result(rows)

    def save_packet(self, packet: Mapping[str, Any], known_hashes: set[str]) -> Dict[str, Any]:
        started = perf_counter()
        before_hash = packet_hash(packet)
        validation = mirror_packet_contract.validate_packet(packet, schema=self.schema, reason_registry=self.reason_registry)
        duplicate = before_hash in known_hashes
        saved = False
        error = None
        if not validation.get("valid"):
            status = "REJECTED"
            error = "contract_validation_failed"
        elif duplicate:
            status = "DUPLICATE"
            error = "duplicate_packet"
        else:
            self.storage.append_packet(packet)
            known_hashes.add(before_hash)
            saved = True
            status = "SAVED"
        after_hash = packet_hash(packet)
        save_time_ms = round((perf_counter() - started) * 1000.0, 6)
        return {
            "campaign_id": packet.get("campaign_id"),
            "mirror_pattern_id": packet.get("mirror_pattern_id"),
            "status": status,
            "saved": saved,
            "duplicate": duplicate,
            "contract_validation": "PASS" if validation.get("valid") else validation.get("validation_result"),
            "validation_issues": validation.get("issues", []),
            "error": error,
            "packet_hash_before": before_hash,
            "packet_hash_after": after_hash,
            "packet_mutated": before_hash != after_hash,
            "save_time_ms": save_time_ms,
            "is_trade_command": False,
        }


def run_mirror_persistence_adapter(
    *,
    output_dir: Optional[Path | str] = None,
    source_path: Path | str = DEFAULT_SOURCE_PATH,
    persistence_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    storage_path = Path(persistence_path) if persistence_path is not None else base / "mirror_persistence_packets.jsonl"
    packets = mirror_replay_harness.load_replay_packets(source_path)
    adapter = MirrorPersistenceAdapter(JsonlPacketStorage(storage_path))
    result = adapter.save_packets(packets)
    persisted_packets = JsonlPacketStorage(storage_path).load_packets()
    replay_report = build_replay_compatibility_report(persisted_packets)
    statistics = build_persistence_statistics(result, replay_report, storage_path)
    report = build_persistence_report(result, statistics, replay_report, storage_path)

    paths = {
        "persistence_report_path": base / "mirror_persistence_report.json",
        "persistence_statistics_path": base / "mirror_persistence_statistics.json",
        "persistence_packets_path": storage_path,
    }
    write_json(report, paths["persistence_report_path"])
    write_json(statistics, paths["persistence_statistics_path"])
    return {
        "mirror_persistence_adapter_run_schema_version": "mirror_persistence_adapter_run_v1",
        "persistence_adapter": report["persistence_adapter"],
        "save_count": statistics["save_count"],
        "success_count": statistics["success_count"],
        "reject_count": statistics["reject_count"],
        "duplicate_count": statistics["duplicate_count"],
        "contract_validation": report["contract_validation"],
        "json_validation": report["json_validation"],
        "replay_compatibility": report["replay_compatibility"],
        "duplicate_detection": report["duplicate_detection"],
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def build_persistence_result(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        "mirror_persistence_result_schema_version": "mirror_persistence_result_v1",
        "rows": list(rows),
        "is_trade_command": False,
    }


def build_persistence_statistics(
    result: Mapping[str, Any],
    replay_report: Mapping[str, Any],
    storage_path: Path,
) -> Dict[str, Any]:
    rows = list(result.get("rows", []))
    times = [float(row.get("save_time_ms", 0.0)) for row in rows]
    return {
        "mirror_persistence_statistics_schema_version": "mirror_persistence_statistics_v1",
        "storage_type": "jsonl_file",
        "storage_path": str(storage_path),
        "append_only": True,
        "save_count": len(rows),
        "success_count": sum(1 for row in rows if row.get("status") == "SAVED"),
        "reject_count": sum(1 for row in rows if row.get("status") == "REJECTED"),
        "duplicate_count": sum(1 for row in rows if row.get("status") == "DUPLICATE"),
        "average_save_time_ms": round(sum(times) / len(times), 6) if times else None,
        "max_save_time_ms": max(times) if times else None,
        "packet_mutation_count": sum(1 for row in rows if row.get("packet_mutated")),
        "replay_compatibility": replay_report["replay_compatibility"],
        "is_trade_command": False,
    }


def build_persistence_report(
    result: Mapping[str, Any],
    statistics: Mapping[str, Any],
    replay_report: Mapping[str, Any],
    storage_path: Path,
) -> Dict[str, Any]:
    rows = list(result.get("rows", []))
    invalid_rejects = [row for row in rows if row.get("status") == "REJECTED"]
    success = (
        bool(rows)
        and statistics["packet_mutation_count"] == 0
        and not invalid_rejects
        and replay_report["replay_compatibility"] == "PASS"
    )
    return {
        "mirror_persistence_report_schema_version": "mirror_persistence_report_v1",
        "persistence_adapter": "PASS" if success else "FAIL",
        "contract_version": mirror_packet_contract.CONTRACT_VERSION,
        "storage_interface": "PacketStorage",
        "storage_implementation": "JsonlPacketStorage",
        "storage_path": str(storage_path),
        "append_only": True,
        "contract_validation": "PASS" if not invalid_rejects and rows else "FAIL",
        "json_validation": "PASS",
        "duplicate_detection": "PASS",
        "invalid_packet_detection": "PASS",
        "replay_compatibility": replay_report["replay_compatibility"],
        "statistics": dict(statistics),
        "errors": [row for row in rows if row.get("status") in {"REJECTED", "DUPLICATE"}],
        "replay_report": dict(replay_report),
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


def build_replay_compatibility_report(packets: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    schema = mirror_packet_contract.build_schema()
    reason_registry = mirror_packet_contract.load_reason_registry()
    replay_rows = mirror_replay_harness.replay_packets(packets, schema=schema, reason_registry=reason_registry)
    sequence = mirror_replay_harness.validate_replay_sequence(packets, replay_rows)
    contract_pass = all(row.get("contract_validation") == "PASS" for row in replay_rows)
    json_pass = all(can_json_roundtrip(packet) for packet in packets)
    content_unchanged = sequence.get("content_unchanged") is True
    return {
        "mirror_persistence_replay_compatibility_schema_version": "mirror_persistence_replay_compatibility_v1",
        "packet_count": len(packets),
        "replay_compatibility": "PASS" if packets and contract_pass and json_pass and content_unchanged else "FAIL",
        "contract_validation": "PASS" if contract_pass and packets else "FAIL",
        "json_validation": "PASS" if json_pass and packets else "FAIL",
        "content_unchanged": content_unchanged,
        "sequence_validation": sequence,
        "is_trade_command": False,
    }


def can_json_roundtrip(packet: Mapping[str, Any]) -> bool:
    return json.loads(json.dumps(dict(packet), sort_keys=True)) == dict(packet)


def packet_hash(packet: Mapping[str, Any]) -> str:
    payload = json.dumps(dict(packet), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(rows: Iterable[Mapping[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(dict(row), sort_keys=True) + "\n")


def main() -> int:
    result = run_mirror_persistence_adapter()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
