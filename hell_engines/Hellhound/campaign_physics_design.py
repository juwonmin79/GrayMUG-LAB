from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "outputs"
CAMPAIGN_DATASET_PATH = DEFAULT_OUTPUT_DIR / "campaign_replay_dataset.json"
DISCRIMINATOR_PATH = DEFAULT_OUTPUT_DIR / "early_mae_discriminator.json"
STATISTICS_PATH = DEFAULT_OUTPUT_DIR / "early_mae_statistics.json"
SUMMARY_PATH = DEFAULT_OUTPUT_DIR / "campaign_physics_summary.json"

LAYER_ORDER = ("Snapshot", "Lead Line", "Campaign Physics", "Mirror Pattern", "ML", "Medusa Board")
CANDIDATES = ("early_mae", "recovery_ratio", "initial_drawdown_velocity", "campaign_duration")


def run_campaign_physics_design(
    *,
    output_dir: Optional[Path | str] = None,
    campaign_dataset_path: Path | str = CAMPAIGN_DATASET_PATH,
    discriminator_path: Path | str = DISCRIMINATOR_PATH,
    statistics_path: Path | str = STATISTICS_PATH,
    summary_path: Path | str = SUMMARY_PATH,
) -> Dict[str, Any]:
    inputs = {
        "campaign_replay_dataset": load_json(campaign_dataset_path),
        "early_mae_discriminator": load_json(discriminator_path),
        "early_mae_statistics": load_json(statistics_path),
        "campaign_physics_summary": load_json(summary_path),
    }
    layer = build_layer_definition(inputs)
    dependencies = build_dependencies(layer)
    flow = build_feature_flow(layer, dependencies)
    report = build_design_report(layer, dependencies, flow, inputs)

    base = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    paths = {
        "layer_path": base / "campaign_physics_layer.json",
        "dependencies_path": base / "campaign_physics_dependencies.json",
        "feature_flow_path": base / "campaign_feature_flow.json",
        "design_report_path": base / "campaign_physics_design_report.json",
    }
    write_json(layer, paths["layer_path"])
    write_json(dependencies, paths["dependencies_path"])
    write_json(flow, paths["feature_flow_path"])
    write_json(report, paths["design_report_path"])
    return {
        "campaign_physics_design_run_schema_version": "campaign_physics_design_run_v1",
        "design_status": report["design_status"],
        "verified": report["verified"],
        "not_verified": report["not_verified"],
        **{key: str(value) for key, value in paths.items()},
        "is_trade_command": False,
    }


def build_layer_definition(inputs: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    summary = inputs["campaign_physics_summary"]
    ranking = {row["candidate"]: row for row in summary.get("candidate_ranking", [])}
    candidates = [candidate_definition(name, ranking.get(name, {})) for name in CANDIDATES]
    return {
        "campaign_physics_layer_schema_version": "campaign_physics_layer_v1",
        "layer_name": "Campaign Physics",
        "design_status": "VERIFIED" if summary.get("evidence_level") == "VERIFIED" else "PARTIAL",
        "purpose": "Represent Campaign-level physical behavior before Mirror Pattern interpretation.",
        "position": {
            "order": list(LAYER_ORDER),
            "previous_layer": "Lead Line",
            "current_layer": "Campaign Physics",
            "next_layer": "Mirror Pattern",
            "reason_before_mirror": (
                "Campaign Physics describes measurable campaign movement and recovery from replayable market/outcome rows. "
                "Mirror Pattern should consume these physical facts instead of inventing pattern meaning directly from raw feature lines."
            ),
        },
        "candidates": candidates,
        "forbidden_actions": [
            "No Mirror Pattern implementation",
            "No ML training",
            "No threshold change",
            "No gate change",
            "No Hellhound Score change",
            "No Replay mutation",
            "No Production code change",
        ],
        "is_trade_command": False,
    }


def candidate_definition(name: str, evidence: Mapping[str, Any]) -> Dict[str, Any]:
    definitions = {
        "early_mae": {
            "meaning": "Maximum adverse excursion observed before or at campaign ignition.",
            "calculation_time": "After campaign replay window is available; in live mode updates from start until ignition.",
            "inputs": ["campaign start_time", "ignition_time", "mae_pct time series"],
            "output": "early_mae percentage value",
            "usage": "Primary Campaign Physics discriminator for distinguishing healthy early absorption from failed campaigns.",
            "dependencies": ["Replay rows or live campaign rows with mae_pct", "Campaign boundaries"],
            "campaign_position": "Pre-Accumulation through Ignition",
            "replayable": True,
            "real_time_calculable": True,
        },
        "recovery_ratio": {
            "meaning": "Peak favorable excursion divided by absolute Early MAE.",
            "calculation_time": "After peak MFE is observed; in live mode provisional until campaign peak/end.",
            "inputs": ["early_mae", "peak_mfe"],
            "output": "recovery_ratio = peak_mfe / abs(early_mae)",
            "usage": "Measures whether the campaign recovered and expanded enough to justify the initial drawdown.",
            "dependencies": ["early_mae", "peak_mfe"],
            "campaign_position": "Ignition through Expansion/Distribution or Failure",
            "replayable": True,
            "real_time_calculable": True,
        },
        "initial_drawdown_velocity": {
            "meaning": "Speed of early adverse movement from campaign start to Early MAE.",
            "calculation_time": "When Early MAE timestamp is known; live value updates while early drawdown evolves.",
            "inputs": ["early_mae", "time_to_early_mae"],
            "output": "initial_drawdown_velocity = early_mae / max(time_to_early_mae, 0.25h)",
            "usage": "Secondary risk physics candidate; 12S did not prove it as a stable discriminator.",
            "dependencies": ["early_mae", "time_to_early_mae"],
            "campaign_position": "Pre-Accumulation through Ignition",
            "replayable": True,
            "real_time_calculable": True,
        },
        "campaign_duration": {
            "meaning": "Elapsed hours between campaign start and campaign end.",
            "calculation_time": "After campaign end; live mode can expose elapsed duration as provisional.",
            "inputs": ["start_time", "end_time"],
            "output": "campaign_duration hours",
            "usage": "Context metric only; 12S reconfirmed it is not a discriminator.",
            "dependencies": ["Campaign boundaries"],
            "campaign_position": "Whole Campaign",
            "replayable": True,
            "real_time_calculable": True,
        },
    }
    item = dict(definitions[name])
    item.update(
        {
            "candidate": name,
            "evidence_verdict": evidence.get("verdict", "NOT_ENOUGH_EVIDENCE"),
            "evidence_rank": evidence.get("rank"),
            "evidence_score": evidence.get("candidate_score"),
            "feature_dependency": item.pop("dependencies"),
            "mirror_dependency": False,
            "ml_dependency": False,
            "is_trade_command": False,
        }
    )
    return item


def build_dependencies(layer: Mapping[str, Any]) -> Dict[str, Any]:
    edges = [
        {"from": "Snapshot", "to": "Lead Line", "dependency_type": "context"},
        {"from": "Lead Line", "to": "Campaign Physics", "dependency_type": "campaign_candidate_context"},
        {"from": "Campaign Physics", "to": "Mirror Pattern", "dependency_type": "physics_features"},
        {"from": "Mirror Pattern", "to": "ML", "dependency_type": "future_training_features"},
        {"from": "ML", "to": "Medusa Board", "dependency_type": "future_decision_surface"},
    ]
    candidate_edges = [
        {"from": "campaign_boundaries", "to": "early_mae"},
        {"from": "mae_pct_time_series", "to": "early_mae"},
        {"from": "early_mae", "to": "recovery_ratio"},
        {"from": "peak_mfe", "to": "recovery_ratio"},
        {"from": "early_mae", "to": "initial_drawdown_velocity"},
        {"from": "time_to_early_mae", "to": "initial_drawdown_velocity"},
        {"from": "campaign_boundaries", "to": "campaign_duration"},
    ]
    return {
        "campaign_physics_dependencies_schema_version": "campaign_physics_dependencies_v1",
        "layer_edges": edges,
        "candidate_edges": candidate_edges,
        "dependency_diagram": "Snapshot -> Lead Line -> Campaign Physics -> Mirror Pattern -> ML -> Medusa Board",
        "cycle_check": {
            "has_cycle": has_cycle(edges),
            "candidate_has_cycle": has_cycle(candidate_edges),
        },
        "independence": {
            "mirror_required": False,
            "ml_required": False,
            "production_required": False,
        },
        "is_trade_command": False,
    }


def build_feature_flow(layer: Mapping[str, Any], dependencies: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "campaign_feature_flow_schema_version": "campaign_feature_flow_v1",
        "layer_diagram": list(LAYER_ORDER),
        "dependency_diagram": dependencies["dependency_diagram"],
        "flow": [
            {"stage": "Snapshot", "output": "raw feature state and campaign row context"},
            {"stage": "Lead Line", "output": "campaign observation priority and context"},
            {"stage": "Campaign Physics", "output": "early_mae, recovery_ratio, initial_drawdown_velocity, campaign_duration"},
            {"stage": "Mirror Pattern", "output": "future pattern interpretation using Campaign Physics input"},
            {"stage": "ML", "output": "future trained models only after evidence is sufficient"},
            {"stage": "Medusa Board", "output": "future display/decision surface"},
        ],
        "candidate_outputs": [
            {
                "candidate": row["candidate"],
                "output": row["output"],
                "replayable": row["replayable"],
                "real_time_calculable": row["real_time_calculable"],
            }
            for row in layer["candidates"]
        ],
        "is_trade_command": False,
    }


def build_design_report(
    layer: Mapping[str, Any],
    dependencies: Mapping[str, Any],
    flow: Mapping[str, Any],
    inputs: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    verified = [row["candidate"] for row in layer["candidates"] if row["evidence_verdict"] == "VERIFIED"]
    not_verified = [row["candidate"] for row in layer["candidates"] if row["evidence_verdict"] != "VERIFIED"]
    cycle_free = not dependencies["cycle_check"]["has_cycle"] and not dependencies["cycle_check"]["candidate_has_cycle"]
    replayable = all(row["replayable"] for row in layer["candidates"])
    realtime = all(row["real_time_calculable"] for row in layer["candidates"])
    independent = not dependencies["independence"]["mirror_required"] and not dependencies["independence"]["ml_required"]
    status = "VERIFIED" if cycle_free and replayable and realtime and independent and verified else "PARTIAL"
    return {
        "campaign_physics_design_report_schema_version": "campaign_physics_design_report_v1",
        "design_status": status,
        "layer_diagram": " -> ".join(flow["layer_diagram"]),
        "dependency_diagram": dependencies["dependency_diagram"],
        "verified": verified,
        "not_verified": not_verified,
        "validation": {
            "no_circular_dependency": cycle_free,
            "replayable": replayable,
            "real_time_calculable": realtime,
            "independent_without_mirror": independent,
        },
        "why_campaign_physics_before_mirror": layer["position"]["reason_before_mirror"],
        "input_evidence": {
            "campaign_count": inputs["campaign_replay_dataset"].get("campaign_count"),
            "success_campaign_count": inputs["campaign_replay_dataset"].get("success_campaign_count"),
            "failure_campaign_count": inputs["campaign_replay_dataset"].get("failure_campaign_count"),
            "campaign_physics_evidence_level": inputs["campaign_physics_summary"].get("evidence_level"),
        },
        "next_sprint_recommendation": (
            "Review Campaign Physics Layer design and decide whether to add more Campaign evidence before any Mirror Pattern design."
        ),
        "forbidden_actions_confirmed": layer["forbidden_actions"],
        "is_trade_command": False,
    }


def has_cycle(edges: Sequence[Mapping[str, str]]) -> bool:
    graph: Dict[str, list[str]] = {}
    for edge in edges:
        graph.setdefault(str(edge["from"]), []).append(str(edge["to"]))
        graph.setdefault(str(edge["to"]), [])
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for child in graph.get(node, []):
            if visit(child):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def load_json(path: Path | str) -> Dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    data = json.loads(file_path.read_text(encoding="utf-8"))
    return dict(data) if isinstance(data, Mapping) else {}


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    result = run_campaign_physics_design()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
