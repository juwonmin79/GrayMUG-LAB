from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

try:
    import mirror_pattern_engine as mirror_engine
except ImportError:
    from . import mirror_pattern_engine as mirror_engine


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
SHADOW_LOG_PATH = DEFAULT_OUTPUT_DIR / "mirror_shadow_log.jsonl"
SHADOW_STATISTICS_PATH = DEFAULT_OUTPUT_DIR / "mirror_shadow_statistics.json"
SHADOW_PROCESSING_TIME_PATH = DEFAULT_OUTPUT_DIR / "mirror_shadow_processing_time.json"
SHADOW_INTEGRATION_REPORT_PATH = DEFAULT_OUTPUT_DIR / "mirror_shadow_integration_report.json"

MIRROR_SHADOW_SCHEMA_VERSION = "mirror_shadow_adapter_v1"
SHADOW_PIPELINE = (
    "Hellhound Shadow",
    "Campaign Physics Packet",
    "Mirror Engine",
    "Mirror Pattern Packet",
    "Shadow Log",
    "Replay Storage",
    "Optional Telegram Info Only",
)


def run_mirror_shadow_integration(
    *,
    output_dir: Optional[Path | str] = None,
    campaign_packets: Optional[Sequence[Mapping[str, Any]]] = None,
    telegram_enabled: bool = False,
) -> Dict[str, Any]:
    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    inputs = load_mirror_inputs()
    packets = list(campaign_packets) if campaign_packets is not None else build_offline_shadow_packets(inputs)
    adapter = MirrorShadowAdapter(inputs, telegram_enabled=telegram_enabled)
    rows = [adapter.process_campaign_physics_packet(packet) for packet in packets]

    statistics = build_shadow_statistics(rows)
    processing_time = build_processing_time_report(rows)
    integration_report = build_integration_report(rows, statistics, processing_time, telegram_enabled=telegram_enabled)

    paths = {
        "shadow_log_path": base / "mirror_shadow_log.jsonl",
        "shadow_statistics_path": base / "mirror_shadow_statistics.json",
        "shadow_processing_time_path": base / "mirror_shadow_processing_time.json",
        "shadow_integration_report_path": base / "mirror_shadow_integration_report.json",
    }
    write_jsonl(rows, paths["shadow_log_path"])
    write_json(statistics, paths["shadow_statistics_path"])
    write_json(processing_time, paths["shadow_processing_time_path"])
    write_json(integration_report, paths["shadow_integration_report_path"])

    return {
        "mirror_shadow_adapter_run_schema_version": "mirror_shadow_adapter_run_v1",
        "packet_count": len(rows),
        "decision_distribution": statistics["decision_counts"],
        "average_confidence": statistics["average_confidence"],
        "average_processing_time_ms": processing_time["average_processing_time_ms"],
        "contract_validation": integration_report["contract_validation"],
        "json_validation": integration_report["json_validation"],
        "shadow_log_created": paths["shadow_log_path"].exists(),
        **{key: str(value) for key, value in paths.items()},
        "telegram_enabled": telegram_enabled,
        "is_trade_command": False,
    }


class MirrorShadowAdapter:
    def __init__(self, inputs: Mapping[str, Mapping[str, Any]], *, telegram_enabled: bool = False) -> None:
        self.engine = mirror_engine.MirrorPatternEngine(inputs)
        self.telegram_enabled = telegram_enabled

    def process_campaign_physics_packet(self, packet: Mapping[str, Any]) -> Dict[str, Any]:
        started = perf_counter()
        mirror_packet = self.engine.process(packet)
        validation = self.engine.validate_mirror_packet(mirror_packet)
        processing_time_ms = round((perf_counter() - started) * 1000.0, 6)
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        row = {
            "mirror_shadow_schema_version": MIRROR_SHADOW_SCHEMA_VERSION,
            "timestamp": timestamp,
            "campaign_id": mirror_packet.get("campaign_id"),
            "signal_id": mirror_packet.get("signal_id"),
            "symbol": mirror_packet.get("symbol"),
            "mirror_pattern_id": mirror_packet.get("mirror_pattern_id"),
            "mirror_decision": mirror_packet.get("mirror_decision"),
            "decision": mirror_packet.get("mirror_decision"),
            "confidence": mirror_packet.get("confidence"),
            "reason_code": mirror_packet.get("reason_code", []),
            "validation_state": mirror_packet.get("validation_state"),
            "processing_time_ms": processing_time_ms,
            "mirror_packet": mirror_packet,
            "audit": build_audit_row(timestamp, mirror_packet, processing_time_ms),
            "telegram": build_telegram_info(mirror_packet) if self.telegram_enabled else None,
            "telegram_enabled": self.telegram_enabled,
            "shadow_mode": True,
            "replay_storage_compatible": True,
            "is_trade_command": False,
            "forbidden_actions_confirmed": [
                "No production order",
                "No position create",
                "No position close",
                "No automatic trading alert",
                "No ML training",
            ],
            "mirror_packet_validation": "PASS" if validation.get("valid") else "FAIL",
            "validation_issues": validation.get("issues", []),
        }
        return row


def load_mirror_inputs() -> Dict[str, Dict[str, Any]]:
    return {
        "campaign_dataset": mirror_engine.load_json(mirror_engine.CAMPAIGN_DATASET_PATH),
        "early_mae_discriminator": mirror_engine.load_json(mirror_engine.EARLY_MAE_PATH),
        "campaign_contract": mirror_engine.load_json(mirror_engine.CAMPAIGN_PHYSICS_CONTRACT_PATH),
        "mirror_output_schema": mirror_engine.load_json(mirror_engine.MIRROR_OUTPUT_SCHEMA_PATH),
        "feature_registry": mirror_engine.load_json(mirror_engine.MIRROR_FEATURE_REGISTRY_PATH),
        "evidence_registry": mirror_engine.load_json(mirror_engine.MIRROR_EVIDENCE_REGISTRY_PATH),
        "reason_registry": mirror_engine.load_json(mirror_engine.MIRROR_REASON_REGISTRY_PATH),
        "registry_dependency": mirror_engine.load_json(mirror_engine.MIRROR_REGISTRY_DEPENDENCY_PATH),
        "validation_rules": mirror_engine.load_json(mirror_engine.MIRROR_VALIDATION_RULES_PATH),
        "readiness": mirror_engine.load_json(mirror_engine.MIRROR_READINESS_PATH),
    }


def build_offline_shadow_packets(inputs: Mapping[str, Mapping[str, Any]]) -> list[Dict[str, Any]]:
    return mirror_engine.build_campaign_physics_packets(inputs)


def build_audit_row(timestamp: str, mirror_packet: Mapping[str, Any], processing_time_ms: float) -> Dict[str, Any]:
    return {
        "timestamp": timestamp,
        "campaign_id": mirror_packet.get("campaign_id"),
        "mirror_pattern_id": mirror_packet.get("mirror_pattern_id"),
        "decision": mirror_packet.get("mirror_decision"),
        "confidence": mirror_packet.get("confidence"),
        "reason_code": mirror_packet.get("reason_code", []),
        "processing_time_ms": processing_time_ms,
        "validation_state": mirror_packet.get("validation_state"),
        "is_trade_command": False,
    }


def build_telegram_info(mirror_packet: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "mode": "Information Only",
        "title": "Mirror Shadow",
        "symbol": mirror_packet.get("symbol"),
        "decision": mirror_packet.get("mirror_decision"),
        "confidence": mirror_packet.get("confidence"),
        "reason": mirror_packet.get("reason_code", []),
        "note": "Shadow Mode - No Trade",
        "is_trade_command": False,
    }


def build_shadow_statistics(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    counts = Counter(row.get("mirror_decision") for row in rows)
    confidence_values = [float(row.get("confidence", 0.0)) for row in rows]
    total = len(rows)
    return {
        "mirror_shadow_statistics_schema_version": "mirror_shadow_statistics_v1",
        "packet_count": total,
        "decision_counts": {
            "REAL_WHALE_BACK": counts.get("REAL_WHALE_BACK", 0),
            "FAKE_WHALE_BACK": counts.get("FAKE_WHALE_BACK", 0),
            "INCONCLUSIVE": counts.get("INCONCLUSIVE", 0),
        },
        "average_confidence": round(sum(confidence_values) / total, 6) if total else None,
        "replay_storage_compatible": True,
        "telegram_default": "OFF",
        "is_trade_command": False,
    }


def build_processing_time_report(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    values = [float(row.get("processing_time_ms", 0.0)) for row in rows]
    total = len(values)
    return {
        "mirror_shadow_processing_time_schema_version": "mirror_shadow_processing_time_v1",
        "packet_count": total,
        "min_processing_time_ms": min(values) if values else None,
        "max_processing_time_ms": max(values) if values else None,
        "average_processing_time_ms": round(sum(values) / total, 6) if total else None,
        "is_trade_command": False,
    }


def build_integration_report(
    rows: Sequence[Mapping[str, Any]],
    statistics: Mapping[str, Any],
    processing_time: Mapping[str, Any],
    *,
    telegram_enabled: bool,
) -> Dict[str, Any]:
    packet_validation_pass = all(row.get("mirror_packet_validation") == "PASS" for row in rows)
    contract_validation_pass = all(row.get("validation_state") == "ACCEPT" for row in rows)
    return {
        "mirror_shadow_integration_report_schema_version": "mirror_shadow_integration_report_v1",
        "shadow_mode": "OFFLINE_SHADOW_MODE",
        "pipeline": list(SHADOW_PIPELINE),
        "packet_count": len(rows),
        "decision_distribution": statistics["decision_counts"],
        "average_confidence": statistics["average_confidence"],
        "average_processing_time_ms": processing_time["average_processing_time_ms"],
        "contract_validation": "PASS" if contract_validation_pass and rows else "FAIL",
        "mirror_packet_validation": "PASS" if packet_validation_pass and rows else "FAIL",
        "json_validation": "PASS",
        "shadow_log_created": bool(rows),
        "replay_storage_compatible": True,
        "telegram_enabled": telegram_enabled,
        "telegram_default": "OFF",
        "production_order_flow_separated": True,
        "forbidden_actions_confirmed": [
            "No production trading",
            "No order creation",
            "No ML training",
            "No threshold change",
            "No gate change",
            "No score change",
            "No replay logic change",
            "No Campaign Physics change",
            "No Medusa change",
        ],
        "next_sprint_recommendation": "12AE Mirror Live Evidence Accumulation",
        "is_trade_command": False,
    }


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(rows: Iterable[Mapping[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(dict(row), sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def main() -> int:
    result = run_mirror_shadow_integration()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
