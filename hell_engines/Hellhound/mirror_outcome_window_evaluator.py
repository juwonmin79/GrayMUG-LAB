"""
Mirror Outcome Window Evaluator (Sprint 12AO)

Computes Market Outcome from Replay-based supporting features.
No Label generation. No Live Outcome. No arbitrary time thresholds.
window_start = sample.created_at
window_end = last Replay observation (campaign_duration approximate)
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from statistics import mean, stdev
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


EVALUATOR_VERSION = "mirror_outcome_window_evaluator_v1"
MARKET_OUTCOME_CONTRACT_VERSION = "mirror_market_outcome_contract_v1"

OUTCOME_STATUS = ("COMPLETED", "INSUFFICIENT_REPLAY_DATA", "NO_PACKET_MATCH")

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
DEFAULT_DATASET_PATH = DEFAULT_OUTPUT_DIR / "mirror_dataset.jsonl"
DEFAULT_SOURCE_PATH = DEFAULT_OUTPUT_DIR / "mirror_shadow_log.jsonl"


def _canonical_hash(obj: Mapping[str, Any]) -> str:
    payload = json.dumps(dict(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_outcome_window(supporting_features: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Derive Market Outcome from Replay-level summary features.
    time_to_peak and time_to_trough require candle-level data → null.
    window_end is approximated from campaign_duration.
    """
    early_mae = supporting_features.get("early_mae")
    recovery_ratio = supporting_features.get("recovery_ratio")
    campaign_duration = supporting_features.get("campaign_duration")

    if any(v is None for v in (early_mae, recovery_ratio, campaign_duration)):
        return {
            "mfe": None,
            "mae": None,
            "return_pct": None,
            "time_to_peak": None,
            "time_to_trough": None,
            "window_duration": None,
            "status": "INSUFFICIENT_REPLAY_DATA",
            "completed": False,
        }

    mae_val = abs(float(early_mae))
    recovery = float(recovery_ratio)
    duration = float(campaign_duration)

    # return_pct: net % return from entry after full recovery
    # recovery_ratio=1.0 → returned to entry (0%), >1.0 → above entry (+), <1.0 → below entry (-)
    return_pct = round((recovery - 1.0) * mae_val, 6)

    # mfe: Maximum Favorable Excursion above entry (never negative)
    mfe = round(max(0.0, return_pct), 6)

    return {
        "mfe": mfe,
        "mae": round(mae_val, 6),
        "return_pct": return_pct,
        "time_to_peak": None,    # Requires candle-level timestamps
        "time_to_trough": None,  # Requires candle-level timestamps
        "window_duration": round(duration, 6),
        "status": "COMPLETED",
        "completed": True,
    }


def evaluate_sample_window(
    sample: Mapping[str, Any],
    packet: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Build a single window evaluation. Never mutates inputs."""
    sample_id = sample.get("sample_id")
    packet_hash = sample.get("packet_hash")
    decision = sample.get("decision")
    window_start = sample.get("created_at")

    if packet is None:
        market_outcome: Dict[str, Any] = {
            "mfe": None,
            "mae": None,
            "return_pct": None,
            "time_to_peak": None,
            "time_to_trough": None,
            "window_duration": None,
            "status": "NO_PACKET_MATCH",
            "completed": False,
        }
    else:
        supporting = packet.get("supporting_features") or {}
        market_outcome = compute_outcome_window(supporting)

    return {
        "sample_id": sample_id,
        "packet_hash": packet_hash,
        "decision": decision,
        "window_start": window_start,
        "market_outcome": market_outcome,
    }


def evaluate_dataset_windows(
    samples: Sequence[Mapping[str, Any]],
    packets: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Match samples to packets by packet_hash, evaluate each window."""
    packet_by_hash: Dict[str, Any] = {_canonical_hash(p): p for p in packets}
    return [
        evaluate_sample_window(s, packet_by_hash.get(s.get("packet_hash", "")))
        for s in samples
    ]


def validate_windows(evaluations: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    for i, ev in enumerate(evaluations):
        mo = ev.get("market_outcome") or {}
        sid = ev.get("sample_id")
        status = mo.get("status")

        if status not in OUTCOME_STATUS:
            issues.append({"index": i, "sample_id": sid, "issue": f"invalid_status: {status}"})

        if mo.get("completed"):
            for field in ("mfe", "mae", "return_pct", "window_duration"):
                if mo.get(field) is None:
                    issues.append({"index": i, "sample_id": sid, "issue": f"completed_but_{field}_null"})

            if mo.get("mfe") is not None and mo["mfe"] < 0:
                issues.append({"index": i, "sample_id": sid, "issue": "mfe_negative"})

            if mo.get("mae") is not None and mo["mae"] < 0:
                issues.append({"index": i, "sample_id": sid, "issue": "mae_negative"})

            if mo.get("window_duration") is not None and mo["window_duration"] < 0:
                issues.append({"index": i, "sample_id": sid, "issue": "window_duration_negative"})

        if not mo.get("completed") and status == "COMPLETED":
            issues.append({"index": i, "sample_id": sid, "issue": "status_completed_but_flag_false"})

    valid = not issues
    return {
        "window_validation_result": "PASS" if valid else "FAIL",
        "issue_count": len(issues),
        "issues": issues,
    }


def build_window_statistics(evaluations: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    completed = [ev for ev in evaluations if ev.get("market_outcome", {}).get("completed")]
    insufficient = [ev for ev in evaluations if ev.get("market_outcome", {}).get("status") == "INSUFFICIENT_REPLAY_DATA"]
    no_match = [ev for ev in evaluations if ev.get("market_outcome", {}).get("status") == "NO_PACKET_MATCH"]

    def _vals(key: str) -> List[float]:
        return [ev["market_outcome"][key] for ev in completed if ev["market_outcome"].get(key) is not None]

    mfe_vals = _vals("mfe")
    mae_vals = _vals("mae")
    ret_vals = _vals("return_pct")
    dur_vals = _vals("window_duration")

    def _stat(vals: List[float]) -> Optional[float]:
        return round(mean(vals), 6) if vals else None

    def _std(vals: List[float]) -> Optional[float]:
        return round(stdev(vals), 6) if len(vals) >= 2 else None

    return {
        "outcome_statistics_schema_version": "mirror_outcome_window_statistics_v1",
        "evaluator_version": EVALUATOR_VERSION,
        "total_count": len(evaluations),
        "completed_count": len(completed),
        "insufficient_data_count": len(insufficient),
        "no_match_count": len(no_match),
        "mfe_mean": _stat(mfe_vals),
        "mfe_stdev": _std(mfe_vals),
        "mfe_min": round(min(mfe_vals), 6) if mfe_vals else None,
        "mfe_max": round(max(mfe_vals), 6) if mfe_vals else None,
        "mae_mean": _stat(mae_vals),
        "mae_stdev": _std(mae_vals),
        "mae_min": round(min(mae_vals), 6) if mae_vals else None,
        "mae_max": round(max(mae_vals), 6) if mae_vals else None,
        "return_pct_mean": _stat(ret_vals),
        "return_pct_stdev": _std(ret_vals),
        "window_duration_mean": _stat(dur_vals),
        "time_to_peak_available": False,
        "time_to_trough_available": False,
        "candle_level_data_required": True,
        "is_trade_command": False,
    }


def run_mirror_outcome_window_evaluator(
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

    samples = list(source_samples) if source_samples is not None else dataset_contract.load_dataset(ds_path)
    packets = list(source_packets) if source_packets is not None else mirror_replay_harness.load_replay_packets(src_path)

    started = perf_counter()
    evaluations = evaluate_dataset_windows(samples, packets)
    elapsed_ms = round((perf_counter() - started) * 1000.0, 6)

    validation = validate_windows(evaluations)
    statistics = build_window_statistics(evaluations)

    completed_evals = [e for e in evaluations if e.get("market_outcome", {}).get("completed")]

    market_outcome_report = {
        "evaluator_version": EVALUATOR_VERSION,
        "market_outcome_contract_version": MARKET_OUTCOME_CONTRACT_VERSION,
        "dataset_contract_version": dataset_contract.DATASET_CONTRACT_VERSION,
        "contract_version": mirror_packet_contract.CONTRACT_VERSION,
        "sample_count": len(samples),
        "completed_count": statistics["completed_count"],
        "insufficient_data_count": statistics["insufficient_data_count"],
        "no_match_count": statistics["no_match_count"],
        "window_validation_result": validation["window_validation_result"],
        "mfe_mean": statistics["mfe_mean"],
        "mae_mean": statistics["mae_mean"],
        "return_pct_mean": statistics["return_pct_mean"],
        "window_duration_mean": statistics["window_duration_mean"],
        "time_to_peak_available": False,
        "time_to_trough_available": False,
        "elapsed_ms": elapsed_ms,
        "is_trade_command": False,
    }

    examples = completed_evals[:5] if completed_evals else evaluations[:5]

    _write_json(market_outcome_report, base / "mirror_market_outcome_report.json")
    _write_json(statistics, base / "mirror_market_outcome_statistics.json")
    _write_json({"examples": examples, "example_count": len(examples)}, base / "mirror_outcome_window_examples.json")

    return market_outcome_report


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main() -> int:
    result = run_mirror_outcome_window_evaluator()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result.get("window_validation_result") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
