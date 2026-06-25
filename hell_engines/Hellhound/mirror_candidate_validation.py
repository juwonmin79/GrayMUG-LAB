from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Dict, Mapping, Optional, Sequence

try:
    from .mirror_contrast_dataset import analyze_case
except ImportError:
    from mirror_contrast_dataset import analyze_case


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
CONTRAST_DATASET_PATH = DEFAULT_OUTPUT_DIR / "mirror_contrast_dataset.json"
BTC_REPLAY_DATASET_PATH = DEFAULT_OUTPUT_DIR / "btc_replay_dataset.jsonl"
BTC_REPLAY_REPORT_PATH = DEFAULT_OUTPUT_DIR / "btc_replay_report.json"

CANDIDATES = ("score_slope", "rsi_persistence", "volume_delay")
SLOPE_WINDOWS = (2, 4, 8)
SUCCESS_TARGET = 10
FAILURE_TARGET = 10
SYMBOL_BUCKETS = {
    "BTCUSDT": "BTC",
    "ETHUSDT": "Major Alt",
    "SOLUSDT": "Major Alt",
    "BNBUSDT": "Major Alt",
    "XRPUSDT": "Major Alt",
    "ADAUSDT": "Major Alt",
    "DOGEUSDT": "Major Alt",
    "AVAXUSDT": "Major Alt",
    "LINKUSDT": "Major Alt",
}
FAILURE_ARCHETYPES = (
    "Fake Breakout",
    "Failed Accumulation",
    "Dead Cat Bounce",
    "Liquidity Sweep",
    "Bull Trap",
)


def run_mirror_candidate_validation(
    *,
    output_dir: Optional[Path | str] = None,
    contrast_dataset_path: Path | str = CONTRAST_DATASET_PATH,
    btc_replay_dataset_path: Path | str = BTC_REPLAY_DATASET_PATH,
    btc_replay_report_path: Path | str = BTC_REPLAY_REPORT_PATH,
) -> Dict[str, Any]:
    source_cases = load_source_cases(
        contrast_dataset_path=contrast_dataset_path,
        btc_replay_dataset_path=btc_replay_dataset_path,
        btc_replay_report_path=btc_replay_report_path,
    )
    samples = expand_replay_samples(source_cases)
    validation = build_candidate_validation(samples)
    statistics = build_candidate_statistics(samples)
    stability = build_candidate_stability(statistics)
    ranking = build_discriminator_ranking(stability, statistics)
    expansion = build_replay_expansion_report(samples, source_cases)

    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    paths = {
        "validation_path": base / "mirror_candidate_validation.json",
        "statistics_path": base / "mirror_candidate_statistics.json",
        "ranking_path": base / "mirror_discriminator_ranking.json",
        "stability_path": base / "mirror_candidate_stability.json",
        "expansion_report_path": base / "replay_expansion_report.json",
    }
    write_json(validation, paths["validation_path"])
    write_json(statistics, paths["statistics_path"])
    write_json(ranking, paths["ranking_path"])
    write_json(stability, paths["stability_path"])
    write_json(expansion, paths["expansion_report_path"])
    return {
        "mirror_candidate_validation_run_schema_version": "mirror_candidate_validation_run_v1",
        "success_count": sum(1 for row in samples if row["case_type"] == "success"),
        "failure_count": sum(1 for row in samples if row["case_type"] == "failure"),
        "verified": [row["candidate"] for row in ranking["ranking"] if row["verification"] == "Verified"],
        "not_verified": [row["candidate"] for row in ranking["ranking"] if row["verification"] == "Not Verified"],
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def load_source_cases(
    *,
    contrast_dataset_path: Path | str,
    btc_replay_dataset_path: Path | str,
    btc_replay_report_path: Path | str,
) -> list[Dict[str, Any]]:
    cases: list[Dict[str, Any]] = []
    contrast_path = Path(contrast_dataset_path)
    if contrast_path.exists():
        payload = load_json(contrast_path)
        for case in payload.get("cases", []):
            if isinstance(case, Mapping):
                cases.append(
                    {
                        "case_id": str(case.get("case_id")),
                        "case_type": str(case.get("case_type")),
                        "symbol": str(case.get("symbol")),
                        "rows": list(case.get("rows") or []),
                        "target": dict(case.get("target") or {}),
                        "sample_source": "outputs/mirror_contrast_dataset.json",
                    }
                )
    btc_rows = load_jsonl(btc_replay_dataset_path)
    btc_report = load_json(btc_replay_report_path) if Path(btc_replay_report_path).exists() else {}
    if btc_rows:
        target = dict(btc_report.get("target") or {})
        target.setdefault("symbol", "BTCUSDT")
        target.setdefault("case_type", "success")
        cases.append(
            {
                "case_id": "btc-replay-success-BTCUSDT",
                "case_type": "success",
                "symbol": "BTCUSDT",
                "rows": btc_rows,
                "target": target,
                "sample_source": "outputs/btc_replay_dataset.jsonl",
            }
        )
    return [case for case in cases if case["rows"]]


def expand_replay_samples(source_cases: Sequence[Mapping[str, Any]]) -> list[Dict[str, Any]]:
    selected: list[Dict[str, Any]] = []
    selected.extend(select_samples(source_cases, "success", SUCCESS_TARGET))
    selected.extend(select_samples(source_cases, "failure", FAILURE_TARGET))
    selected.sort(key=lambda row: (row["case_type"], row["sample_id"]))
    return selected


def select_samples(source_cases: Sequence[Mapping[str, Any]], case_type: str, target_count: int) -> list[Dict[str, Any]]:
    candidates: list[Dict[str, Any]] = []
    for source in source_cases:
        if source["case_type"] != case_type:
            continue
        rows = list(source.get("rows") or [])
        for anchor in eligible_anchor_indices(rows, source, case_type):
            sample = build_sample(source, rows, anchor)
            if sample is not None:
                candidates.append(sample)
    candidates.sort(key=lambda row: (-float(row["selection_score"]), row["symbol"], row["anchor_timestamp"]))
    if case_type == "failure":
        selected = balanced_take_failure_archetypes(candidates, target_count)
    else:
        selected = balanced_take(candidates, target_count)
    for index, sample in enumerate(selected, start=1):
        sample["sample_id"] = f"{case_type}-{index:02d}-{sample['symbol']}"
    return selected


def eligible_anchor_indices(rows: Sequence[Mapping[str, Any]], source: Mapping[str, Any], case_type: str) -> list[int]:
    anchors = []
    failure_by_archetype: Dict[str, list[int]] = {name: [] for name in FAILURE_ARCHETYPES}
    for index, row in enumerate(rows):
        if index < 12:
            continue
        if len(rows) - index < 12:
            continue
        ret24 = _number(row.get("return_24h"))
        ret4 = _number(row.get("return_4h"))
        mfe = _number(row.get("mfe_pct"))
        mae = _number(row.get("mae_pct"))
        if case_type == "success":
            threshold = 1.0 if source.get("symbol") == "BTCUSDT" else 3.0
            if ret24 is not None and ret24 >= threshold:
                anchors.append(index)
            elif mfe is not None and mfe >= threshold + 1.0:
                anchors.append(index)
        else:
            if ret4 is not None and ret24 is not None:
                failure_by_archetype.setdefault(failure_archetype(row), []).append(index)
    if case_type == "failure":
        selected = []
        for archetype in FAILURE_ARCHETYPES:
            selected.extend(thin_indices(failure_by_archetype.get(archetype) or [], limit=3))
        if len(selected) < 8:
            all_failure = []
            for values in failure_by_archetype.values():
                all_failure.extend(values)
            for index in thin_indices(sorted(set(all_failure)), limit=8):
                if index not in selected:
                    selected.append(index)
        return selected
    return thin_indices(anchors, limit=8)


def build_sample(source: Mapping[str, Any], source_rows: Sequence[Mapping[str, Any]], anchor_index: int) -> Optional[Dict[str, Any]]:
    start = max(0, anchor_index - 48)
    end = min(len(source_rows), anchor_index + 49)
    rows = [dict(row) for row in source_rows[start:end]]
    if len(rows) < 24:
        return None
    anchor = source_rows[anchor_index]
    target = {
        "symbol": source["symbol"],
        "case_type": source["case_type"],
        "accumulation_start": rows[0].get("timestamp"),
        "ignition_time": anchor.get("timestamp"),
        "local_peak_time": max(rows[anchor_index - start :], key=lambda row: _number(row.get("close")) or 0.0).get("timestamp"),
        "replay_end_time": rows[-1].get("timestamp"),
        "ignition_return_24h": anchor.get("return_24h"),
        "is_trade_command": False,
    }
    analysis = analyze_case(rows, target)
    candidate_metrics = candidate_metrics_from_analysis(rows, target, analysis)
    return {
        "sample_id": "",
        "source_case_id": source["case_id"],
        "sample_source": source["sample_source"],
        "case_type": source["case_type"],
        "symbol": source["symbol"],
        "asset_bucket": asset_bucket(str(source["symbol"])),
        "anchor_timestamp": anchor.get("timestamp"),
        "coverage_start": rows[0].get("timestamp"),
        "coverage_end": rows[-1].get("timestamp"),
        "failure_archetype": failure_archetype(anchor) if source["case_type"] == "failure" else None,
        "selection_score": abs(_number(anchor.get("return_24h")) or _number(anchor.get("mfe_pct")) or 0.0),
        "target": target,
        "candidate_metrics": candidate_metrics,
        "is_trade_command": False,
    }


def candidate_metrics_from_analysis(
    rows: Sequence[Mapping[str, Any]],
    target: Mapping[str, Any],
    analysis: Mapping[str, Any],
) -> Dict[str, Any]:
    temporal = analysis.get("temporal", {})
    features = temporal.get("features", {})
    score_slopes = features.get("hellhound_score", {}).get("slopes", {})
    rsi_persist = features.get("rsi_15m", {}).get("persistence", {})
    relation = analysis.get("sequence", {}).get("cross_feature_relation", {})
    delay = relation.get("lead_lag_candles", {}).get("hellhound_score_to_volume_ratio_ma20")
    pre_rows = [row for row in rows if str(row.get("timestamp")) < str(target.get("ignition_time"))]
    peak_after = rsi_peak_after_persistence(pre_rows)
    return {
        "score_slope": {
            "slope_2": score_slopes.get("2_candles"),
            "slope_4": score_slopes.get("4_candles"),
            "slope_8": score_slopes.get("8_candles"),
            "primary_value": score_slopes.get("4_candles"),
        },
        "rsi_persistence": {
            "increase_persistence": rsi_persist.get("max_increase_candles"),
            "decrease_persistence": rsi_persist.get("max_decrease_candles"),
            "peak_after_persistence": peak_after,
            "primary_value": rsi_persist.get("max_increase_candles"),
        },
        "volume_delay": {
            "delay_candles": delay,
            "state": volume_delay_state(delay),
            "primary_value": delay,
        },
        "is_trade_command": False,
    }


def build_candidate_validation(samples: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        "mirror_candidate_validation_schema_version": "mirror_candidate_validation_v1",
        "objective": "Validate whether score_slope, rsi_persistence, and volume_delay repeatedly separate success and failure replay samples.",
        "candidates": list(CANDIDATES),
        "sample_count": len(samples),
        "success_count": sum(1 for row in samples if row["case_type"] == "success"),
        "failure_count": sum(1 for row in samples if row["case_type"] == "failure"),
        "samples": list(samples),
        "rules": {
            "forbidden": [
                "Mirror Layer implementation",
                "Threshold change",
                "Hellhound Score change",
                "PROMOTE Gate change",
                "ML training",
                "Candidate promotion",
            ],
            "allowed": ["Replay", "Validation", "Statistics", "Candidate Discovery", "Evidence accumulation"],
        },
        "is_trade_command": False,
    }


def build_candidate_statistics(samples: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    stats = []
    for candidate in CANDIDATES:
        success_values = candidate_values(samples, candidate, "success")
        failure_values = candidate_values(samples, candidate, "failure")
        separation = separation_score(success_values, failure_values)
        direction = "success_higher" if safe_mean(success_values) >= safe_mean(failure_values) else "failure_higher"
        success_repeat, failure_repeat = repeat_rates(success_values, failure_values, direction)
        stats.append(
            {
                "candidate": candidate,
                "success": describe_values(success_values),
                "failure": describe_values(failure_values),
                "success_failure_separation": separation,
                "repeatability": {
                    "direction": direction,
                    "success_repeat_rate": success_repeat,
                    "failure_repeat_rate": failure_repeat,
                    "combined_repeat_rate": round((success_repeat + failure_repeat) / 2.0, 6),
                },
                "is_trade_command": False,
            }
        )
    return {
        "mirror_candidate_statistics_schema_version": "mirror_candidate_statistics_v1",
        "candidates": stats,
        "is_trade_command": False,
    }


def build_candidate_stability(statistics: Mapping[str, Any]) -> Dict[str, Any]:
    rows = []
    for stat in statistics.get("candidates", []):
        success = stat["success"]
        failure = stat["failure"]
        repeatability = stat["repeatability"]["combined_repeat_rate"]
        discrimination = min(float(stat["success_failure_separation"] or 0.0) / 2.0, 1.0)
        noise = noise_score(success, failure)
        stability_score = round((repeatability * 0.4) + (discrimination * 0.4) + (noise * 0.2), 6)
        rows.append(
            {
                "candidate": stat["candidate"],
                "repeatability": repeatability,
                "discrimination": round(discrimination, 6),
                "noise": noise,
                "mirror_candidate_stability_score": stability_score,
                "verification": verification_label(stability_score, repeatability, discrimination),
                "candidate_state": "Candidate Only",
                "is_trade_command": False,
            }
        )
    return {
        "mirror_candidate_stability_schema_version": "mirror_candidate_stability_v1",
        "candidates": rows,
        "is_trade_command": False,
    }


def build_discriminator_ranking(stability: Mapping[str, Any], statistics: Mapping[str, Any]) -> Dict[str, Any]:
    stat_by_candidate = {row["candidate"]: row for row in statistics.get("candidates", [])}
    rows = []
    for row in stability.get("candidates", []):
        stat = stat_by_candidate[row["candidate"]]
        rows.append(
            {
                "rank": 0,
                "candidate": row["candidate"],
                "mirror_candidate_stability_score": row["mirror_candidate_stability_score"],
                "repeatability": row["repeatability"],
                "discrimination": row["discrimination"],
                "noise": row["noise"],
                "success_failure_separation": stat["success_failure_separation"],
                "verification": row["verification"],
                "candidate_state": "Candidate Only",
                "evidence": {
                    "success_mean": stat["success"]["mean"],
                    "failure_mean": stat["failure"]["mean"],
                    "success_median": stat["success"]["median"],
                    "failure_median": stat["failure"]["median"],
                },
                "is_trade_command": False,
            }
        )
    rows.sort(key=lambda item: item["mirror_candidate_stability_score"], reverse=True)
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return {
        "mirror_discriminator_ranking_schema_version": "mirror_discriminator_ranking_v1",
        "ranking": rows,
        "new_candidates": discover_new_candidates(statistics),
        "promotion_decision": "Mirror promotion blocked unless at least one candidate is Verified.",
        "is_trade_command": False,
    }


def build_replay_expansion_report(samples: Sequence[Mapping[str, Any]], source_cases: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    by_source: Dict[str, int] = {}
    by_symbol: Dict[str, int] = {}
    by_bucket: Dict[str, int] = {}
    archetypes: Dict[str, int] = {}
    for sample in samples:
        by_source[sample["sample_source"]] = by_source.get(sample["sample_source"], 0) + 1
        by_symbol[sample["symbol"]] = by_symbol.get(sample["symbol"], 0) + 1
        by_bucket[sample["asset_bucket"]] = by_bucket.get(sample["asset_bucket"], 0) + 1
        if sample.get("failure_archetype"):
            archetypes[sample["failure_archetype"]] = archetypes.get(sample["failure_archetype"], 0) + 1
    return {
        "replay_expansion_report_schema_version": "replay_expansion_report_v1",
        "sample_source_priority": [
            "Existing replay dataset reuse: outputs/btc_replay_dataset.jsonl, outputs/mirror_contrast_dataset.json",
            "Hellhound real trade/outcome/MFE/MAE history if present",
            "Binance Historical OHLCV pull only if existing data cannot satisfy sample count",
        ],
        "sample_source": by_source,
        "source_case_count": len(source_cases),
        "replay_count": len(samples),
        "success_count": sum(1 for row in samples if row["case_type"] == "success"),
        "failure_count": sum(1 for row in samples if row["case_type"] == "failure"),
        "selection_rule": {
            "success": "Use existing replay rows with 24h forward return above asset-specific replay threshold, balanced by symbol.",
            "failure": "Use existing replay rows showing failed pop, weak/negative 24h follow-through, or sweep drawdown; assign replay archetype from observed return/MFE/MAE shape.",
            "no_same_symbol_concentration": "Balanced take uses round-robin symbol selection before filling any remaining slots.",
            "no_same_period_concentration": "Anchors are thinned across the source replay span before ranking.",
        },
        "selection_timestamp": now,
        "data_coverage": {
            "by_symbol": by_symbol,
            "by_asset_bucket": by_bucket,
            "failure_archetypes": archetypes,
            "coverage_start": min((str(row["coverage_start"]) for row in samples), default=None),
            "coverage_end": max((str(row["coverage_end"]) for row in samples), default=None),
        },
        "reason_for_binance_pull": "Not executed. Existing replay outputs met the minimum 10 success and 10 failure replay sample counts.",
        "is_trade_command": False,
    }


def balanced_take(candidates: Sequence[Mapping[str, Any]], target_count: int) -> list[Dict[str, Any]]:
    selected: list[Dict[str, Any]] = []
    by_symbol: Dict[str, list[Mapping[str, Any]]] = {}
    for row in candidates:
        by_symbol.setdefault(str(row["symbol"]), []).append(row)
    while len(selected) < target_count and any(by_symbol.values()):
        for symbol in sorted(by_symbol):
            if len(selected) >= target_count:
                break
            if by_symbol[symbol]:
                selected.append(dict(by_symbol[symbol].pop(0)))
    return selected


def balanced_take_failure_archetypes(candidates: Sequence[Mapping[str, Any]], target_count: int) -> list[Dict[str, Any]]:
    selected: list[Dict[str, Any]] = []
    used_keys = set()
    by_archetype: Dict[str, list[Mapping[str, Any]]] = {}
    for row in candidates:
        by_archetype.setdefault(str(row.get("failure_archetype")), []).append(row)
    for archetype in FAILURE_ARCHETYPES:
        rows = by_archetype.get(archetype) or []
        if rows:
            row = dict(rows.pop(0))
            selected.append(row)
            used_keys.add((row["source_case_id"], row["anchor_timestamp"]))
    for row in balanced_take(candidates, target_count * 2):
        key = (row["source_case_id"], row["anchor_timestamp"])
        if len(selected) >= target_count:
            break
        if key in used_keys:
            continue
        selected.append(row)
        used_keys.add(key)
    return selected[:target_count]


def candidate_values(samples: Sequence[Mapping[str, Any]], candidate: str, case_type: str) -> list[float]:
    values = []
    for sample in samples:
        if sample["case_type"] != case_type:
            continue
        value = sample.get("candidate_metrics", {}).get(candidate, {}).get("primary_value")
        parsed = _number(value)
        if parsed is not None:
            values.append(parsed)
    return values


def describe_values(values: Sequence[float]) -> Dict[str, Any]:
    return {
        "count": len(values),
        "mean": _round(mean(values)) if values else None,
        "median": _round(median(values)) if values else None,
        "standard_deviation": _round(stdev(values)) if len(values) > 1 else 0.0 if values else None,
        "min": _round(min(values)) if values else None,
        "max": _round(max(values)) if values else None,
    }


def separation_score(success_values: Sequence[float], failure_values: Sequence[float]) -> Optional[float]:
    if not success_values or not failure_values:
        return None
    success_sd = stdev(success_values) if len(success_values) > 1 else 0.0
    failure_sd = stdev(failure_values) if len(failure_values) > 1 else 0.0
    pooled = math.sqrt((success_sd**2 + failure_sd**2) / 2.0)
    if pooled == 0:
        return 0.0 if mean(success_values) == mean(failure_values) else 9.999999
    return _round(abs(mean(success_values) - mean(failure_values)) / pooled)


def repeat_rates(success_values: Sequence[float], failure_values: Sequence[float], direction: str) -> tuple[float, float]:
    combined = list(success_values) + list(failure_values)
    if not combined:
        return 0.0, 0.0
    pivot = median(combined)
    if direction == "success_higher":
        success_hits = sum(1 for value in success_values if value > pivot)
        failure_hits = sum(1 for value in failure_values if value <= pivot)
    else:
        success_hits = sum(1 for value in success_values if value < pivot)
        failure_hits = sum(1 for value in failure_values if value >= pivot)
    return (
        round(success_hits / len(success_values), 6) if success_values else 0.0,
        round(failure_hits / len(failure_values), 6) if failure_values else 0.0,
    )


def noise_score(success: Mapping[str, Any], failure: Mapping[str, Any]) -> float:
    scores = []
    for group in (success, failure):
        avg = abs(float(group.get("mean") or 0.0))
        sd = float(group.get("standard_deviation") or 0.0)
        if avg == 0.0:
            scores.append(0.5 if sd == 0.0 else 0.0)
        else:
            scores.append(max(0.0, 1.0 - min(sd / avg, 1.0)))
    return _round(mean(scores))


def verification_label(stability_score: float, repeatability: float, discrimination: float) -> str:
    if stability_score >= 0.6 and repeatability >= 0.6 and discrimination >= 0.25:
        return "Verified"
    return "Not Verified"


def discover_new_candidates(statistics: Mapping[str, Any]) -> list[Dict[str, Any]]:
    discovered = []
    for stat in statistics.get("candidates", []):
        if float(stat.get("success_failure_separation") or 0.0) >= 0.75:
            discovered.append(
                {
                    "candidate": f"{stat['candidate']}_directional_regime",
                    "source_candidate": stat["candidate"],
                    "candidate_state": "Candidate Only",
                    "evidence_score": stat["success_failure_separation"],
                    "note": "Exploratory ranking only; no Mirror feature implementation or promotion performed.",
                    "is_trade_command": False,
                }
            )
    discovered.sort(key=lambda row: row["evidence_score"], reverse=True)
    for index, row in enumerate(discovered, start=1):
        row["rank"] = index
    return discovered


def rsi_peak_after_persistence(rows: Sequence[Mapping[str, Any]]) -> int:
    values = [_number(row.get("rsi_15m")) for row in rows]
    series = [value for value in values if value is not None]
    if not series:
        return 0
    peak_index = max(range(len(series)), key=lambda index: series[index])
    count = 0
    for previous, current in zip(series[peak_index:], series[peak_index + 1 :]):
        if current <= previous:
            count += 1
        else:
            break
    return count


def volume_delay_state(delay: Any) -> str:
    parsed = _number(delay)
    if parsed is None:
        return "Missing"
    if parsed == 0:
        return "Overlap"
    if parsed > 0:
        return "Delay"
    return "Volume Leads"


def failure_archetype(row: Mapping[str, Any]) -> str:
    ret4 = _number(row.get("return_4h")) or 0.0
    ret24 = _number(row.get("return_24h")) or 0.0
    mfe = _number(row.get("mfe_pct")) or 0.0
    mae = _number(row.get("mae_pct")) or 0.0
    if ret4 >= 1.5 and ret24 < 0:
        return "Bull Trap"
    if mfe >= 3.0 and ret24 <= 0.5:
        return "Fake Breakout"
    if mae <= -7.0:
        return "Liquidity Sweep"
    if ret4 > 0 and ret24 < ret4 * 0.25:
        return "Dead Cat Bounce"
    return "Failed Accumulation"


def thin_indices(indices: Sequence[int], *, limit: int) -> list[int]:
    if len(indices) <= limit:
        return list(indices)
    if limit <= 1:
        return [indices[0]]
    step = (len(indices) - 1) / float(limit - 1)
    return [indices[round(index * step)] for index in range(limit)]


def asset_bucket(symbol: str) -> str:
    return SYMBOL_BUCKETS.get(symbol, "Mid Cap")


def safe_mean(values: Sequence[float]) -> float:
    return mean(values) if values else 0.0


def load_json(path: Path | str) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return dict(data) if isinstance(data, Mapping) else {}


def load_jsonl(path: Path | str) -> list[Dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    rows = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if isinstance(row, Mapping) and row.get("is_trade_command") is False:
                rows.append(dict(row))
    return rows


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: Optional[float]) -> Optional[float]:
    return round(float(value), 6) if value is not None else None


def main() -> int:
    result = run_mirror_candidate_validation()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
