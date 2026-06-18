from __future__ import annotations

from dataclasses import asdict
from typing import Dict

from research.integration.state_schema import CoreState, HoundState, LeadLineState, WardState
from research.targeting.core_target_feed import build_core_target_feed as _build_core_target_feed
from research.targeting.hound_hunt_feed import build_hound_hunt_feed as _build_hound_hunt_feed
from research.targeting.target_schema import (
    CoreTargetFeed,
    HoundHuntFeed,
    TargetPipelinePayload,
    WardRiskFeed,
)
from research.targeting.ward_risk_feed import build_ward_risk_feed as _build_ward_risk_feed


def build_core_target_feed(
    core_state: CoreState,
    lead_line_state: LeadLineState,
) -> Dict:
    return asdict(_build_core_target_feed(core_state, lead_line_state))


def build_ward_risk_feed(
    ward_state: WardState,
    lead_line_state: LeadLineState,
) -> Dict:
    return asdict(_build_ward_risk_feed(ward_state, lead_line_state))


def build_hound_hunt_feed(
    hound_state: HoundState,
    lead_line_state: LeadLineState,
    top_n: int = 12,
) -> Dict:
    return asdict(_build_hound_hunt_feed(hound_state, lead_line_state, top_n=top_n))


def build_target_pipeline_payload(
    core_state: CoreState,
    ward_state: WardState,
    hound_state: HoundState,
    lead_line_state: LeadLineState,
    top_n: int = 12,
) -> Dict:
    core_feed: CoreTargetFeed = _build_core_target_feed(core_state, lead_line_state)
    ward_feed: WardRiskFeed = _build_ward_risk_feed(ward_state, lead_line_state)
    hound_feed: HoundHuntFeed = _build_hound_hunt_feed(
        hound_state,
        lead_line_state,
        top_n=top_n,
    )

    payload = TargetPipelinePayload(
        timestamp=lead_line_state.timestamp,
        mode=lead_line_state.mode,
        source="target_intelligence_pipeline",
        core=core_feed,
        ward=ward_feed,
        hound=hound_feed,
    )
    return asdict(payload)
