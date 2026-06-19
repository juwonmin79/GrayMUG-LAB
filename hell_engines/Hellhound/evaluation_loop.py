from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional
from urllib import error, parse, request

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")


OUTCOME_TABLE = "hellhound_outcomes"
SHADOW_SIGNAL_TABLE = "hellhound_shadow_signals"
HYPOTHESES_TABLE = "hypotheses"
RESOLVED_RESULTS = {"SUCCESS", "FAIL", "INCONCLUSIVE"}
ALLOWED_HYPOTHESIS_STATUSES = {"active", "promotion_candidate", "retired"}
DEFAULT_PROMOTION_RULES = {
    "promotion_accuracy_gte": 0.70,
    "retire_accuracy_lt": 0.40,
    "min_resolved_count": 50,
}
LOCAL_EVALUATION_DATA_PATH = (
    Path(__file__).resolve().parent / "test_data" / "evaluation_loop_resolved_outcomes.json"
)

LOGGER = logging.getLogger("hellhound.evaluation_loop")


@dataclass(frozen=True)
class EvaluationResult:
    ok: bool
    dry_run: bool
    updated: bool
    skipped: bool
    message: str
    scoreboard: list[Dict[str, Any]]
    status_updates: list[Dict[str, Any]]


class EvaluationLoopError(RuntimeError):
    pass


def build_scoreboard(resolved_outcomes: Iterable[Mapping[str, Any]]) -> list[Dict[str, Any]]:
    groups: Dict[tuple[str, str, str], Dict[str, Any]] = {}
    signal_ids_by_group: Dict[tuple[str, str, str], set[str]] = {}

    for outcome in resolved_outcomes:
        result = str(outcome.get("result") or "").upper()
        if result not in RESOLVED_RESULTS:
            continue

        signal = _signal_for_outcome(outcome)
        pattern = str(
            outcome.get("pattern") or signal.get("pattern") or "UNKNOWN"
        ).upper()
        hypothesis = _hypothesis_for_outcome(outcome, signal, pattern)
        hypothesis_id = str(hypothesis.get("id") or "")
        hypothesis_name = str(hypothesis.get("name") or pattern)
        key = (hypothesis_id, hypothesis_name, pattern)

        if key not in groups:
            groups[key] = {
                "hypothesis_id": hypothesis_id or None,
                "hypothesis_name": hypothesis_name,
                "pattern": pattern,
                "signals_count": 0,
                "outcomes_count": 0,
                "resolved_count": 0,
                "success_count": 0,
                "fail_count": 0,
                "inconclusive_count": 0,
                "accuracy": None,
            }
            signal_ids_by_group[key] = set()

        group = groups[key]
        signal_id = outcome.get("shadow_signal_id") or signal.get("id")
        if signal_id:
            signal_ids_by_group[key].add(str(signal_id))
        group["outcomes_count"] += 1
        group["resolved_count"] += 1
        if result == "SUCCESS":
            group["success_count"] += 1
        elif result == "FAIL":
            group["fail_count"] += 1
        elif result == "INCONCLUSIVE":
            group["inconclusive_count"] += 1

    scoreboard = []
    for key, group in groups.items():
        denominator = group["success_count"] + group["fail_count"]
        group["signals_count"] = len(signal_ids_by_group[key])
        group["accuracy"] = (
            group["success_count"] / denominator if denominator else None
        )
        scoreboard.append(group)

    return sorted(scoreboard, key=lambda item: (item["pattern"], item["hypothesis_name"]))


def apply_promotion_rules(
    scoreboard: Iterable[Mapping[str, Any]],
    rules: Optional[Mapping[str, Any]] = None,
) -> list[Dict[str, Any]]:
    active_rules = _merge_rules(rules or _rules_from_env())
    updates = []
    for row in scoreboard:
        accuracy = row.get("accuracy")
        resolved_count = int(row.get("resolved_count") or 0)
        if accuracy is None:
            status = "active"
        elif (
            accuracy >= active_rules["promotion_accuracy_gte"]
            and resolved_count >= active_rules["min_resolved_count"]
        ):
            status = "promotion_candidate"
        elif (
            accuracy < active_rules["retire_accuracy_lt"]
            and resolved_count >= active_rules["min_resolved_count"]
        ):
            status = "retired"
        else:
            status = "active"

        updates.append(
            {
                "hypothesis_id": row.get("hypothesis_id"),
                "hypothesis_name": row.get("hypothesis_name"),
                "pattern": row.get("pattern"),
                "status": status,
                "accuracy": accuracy,
                "resolved_count": resolved_count,
            }
        )
    return updates


def run_evaluation_loop() -> EvaluationResult:
    supabase_url, supabase_key = _supabase_credentials()
    if not supabase_url or not supabase_key:
        LOGGER.warning("Supabase credentials missing; evaluation loop skipped")
        return EvaluationResult(
            ok=True,
            dry_run=_dry_run_enabled(),
            updated=False,
            skipped=True,
            message="missing Supabase environment; skipped evaluation loop",
            scoreboard=[],
            status_updates=[],
        )

    try:
        resolved_outcomes = _load_resolved_outcomes(
            supabase_url=supabase_url, supabase_key=supabase_key
        )
    except EvaluationLoopError as exc:
        LOGGER.error("Resolved outcome load failed: %s", exc)
        return EvaluationResult(
            ok=False,
            dry_run=_dry_run_enabled(),
            updated=False,
            skipped=False,
            message=str(exc),
            scoreboard=[],
            status_updates=[],
        )

    scoreboard = build_scoreboard(resolved_outcomes)
    status_updates = apply_promotion_rules(scoreboard)
    if _dry_run_enabled():
        _print_summary(scoreboard, status_updates)
        return EvaluationResult(
            ok=True,
            dry_run=True,
            updated=False,
            skipped=False,
            message=f"dry-run evaluated {len(scoreboard)} scoreboard rows",
            scoreboard=scoreboard,
            status_updates=status_updates,
        )

    try:
        _update_hypothesis_statuses(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            updates=status_updates,
        )
    except EvaluationLoopError as exc:
        LOGGER.error("Hypothesis status update failed: %s", exc)
        return EvaluationResult(
            ok=False,
            dry_run=False,
            updated=False,
            skipped=False,
            message=str(exc),
            scoreboard=scoreboard,
            status_updates=status_updates,
        )

    _print_summary(scoreboard, status_updates)
    return EvaluationResult(
        ok=True,
        dry_run=False,
        updated=True,
        skipped=False,
        message=f"updated {len(status_updates)} hypothesis statuses",
        scoreboard=scoreboard,
        status_updates=status_updates,
    )


def _load_resolved_outcomes(
    *, supabase_url: str, supabase_key: str
) -> list[Dict[str, Any]]:
    outcome_fields = "id,shadow_signal_id,symbol,evaluation_window,result"
    result_filter = "result=in.(SUCCESS,FAIL,INCONCLUSIVE)"
    endpoint = (
        f"{supabase_url.rstrip('/')}/rest/v1/{OUTCOME_TABLE}"
        f"?select={outcome_fields}&{result_filter}"
    )
    status, rows = _supabase_json(
        endpoint=endpoint,
        supabase_key=supabase_key,
        method="GET",
    )
    if status < 200 or status >= 300:
        raise EvaluationLoopError(f"unexpected Supabase status {status}")
    if not isinstance(rows, list):
        raise EvaluationLoopError("Supabase resolved outcomes response was not a list")

    signal_cache: Dict[str, Dict[str, Any]] = {}
    outcomes = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        outcome = dict(row)
        signal_id = outcome.get("shadow_signal_id")
        if signal_id:
            signal_id = str(signal_id)
            if signal_id not in signal_cache:
                signal_cache[signal_id] = _load_shadow_signal(
                    supabase_url=supabase_url,
                    supabase_key=supabase_key,
                    shadow_signal_id=signal_id,
                )
            outcome["shadow_signal"] = signal_cache[signal_id]
        outcomes.append(outcome)
    return outcomes


def _load_shadow_signal(
    *, supabase_url: str, supabase_key: str, shadow_signal_id: str
) -> Dict[str, Any]:
    signal_filter = parse.quote(f"eq.{shadow_signal_id}", safe="")
    endpoint = (
        f"{supabase_url.rstrip('/')}/rest/v1/{SHADOW_SIGNAL_TABLE}"
        "?select=id,symbol,pattern,target_feed,execution_guidance"
        f"&id={signal_filter}&limit=1"
    )
    status, rows = _supabase_json(
        endpoint=endpoint,
        supabase_key=supabase_key,
        method="GET",
    )
    if status < 200 or status >= 300:
        raise EvaluationLoopError(f"unexpected Supabase status {status}")
    if not isinstance(rows, list) or not rows:
        return {}
    signal = rows[0]
    return dict(signal) if isinstance(signal, Mapping) else {}


def _update_hypothesis_statuses(
    *, supabase_url: str, supabase_key: str, updates: list[Mapping[str, Any]]
) -> None:
    for update in updates:
        status = update.get("status")
        if status not in ALLOWED_HYPOTHESIS_STATUSES:
            raise EvaluationLoopError(f"invalid hypothesis status {status}")

        filter_path = _hypothesis_filter(update)
        if not filter_path:
            LOGGER.warning(
                "Skipping hypothesis status update without id or name for pattern %s",
                update.get("pattern"),
            )
            continue

        endpoint = f"{supabase_url.rstrip('/')}/rest/v1/{HYPOTHESES_TABLE}?{filter_path}"
        response_status, _ = _supabase_json(
            endpoint=endpoint,
            supabase_key=supabase_key,
            method="PATCH",
            body={"status": status},
            prefer="return=minimal",
        )
        if response_status < 200 or response_status >= 300:
            raise EvaluationLoopError(f"unexpected Supabase status {response_status}")


def _hypothesis_filter(update: Mapping[str, Any]) -> str:
    hypothesis_id = update.get("hypothesis_id")
    if hypothesis_id:
        return "id=" + parse.quote(f"eq.{hypothesis_id}", safe="")
    hypothesis_name = update.get("hypothesis_name")
    if hypothesis_name:
        return "name=" + parse.quote(f"eq.{hypothesis_name}", safe="")
    return ""


def _supabase_json(
    *,
    endpoint: str,
    supabase_key: str,
    method: str,
    body: Optional[Mapping[str, Any]] = None,
    prefer: Optional[str] = None,
) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer
    req = request.Request(endpoint, data=data, method=method, headers=headers)

    try:
        with request.urlopen(req, timeout=15) as response:
            text = response.read().decode("utf-8")
            return response.status, json.loads(text) if text else None
    except error.HTTPError as exc:
        safe_body = exc.read().decode("utf-8", errors="replace")[:500]
        raise EvaluationLoopError(
            f"Supabase HTTP {exc.code}: {_redact_secret_text(safe_body)}"
        ) from exc
    except error.URLError as exc:
        raise EvaluationLoopError(f"Supabase connection error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise EvaluationLoopError("Supabase evaluation loop timed out") from exc
    except json.JSONDecodeError as exc:
        raise EvaluationLoopError("Supabase response was not JSON") from exc


def _signal_for_outcome(outcome: Mapping[str, Any]) -> Dict[str, Any]:
    signal = outcome.get("shadow_signal")
    return dict(signal) if isinstance(signal, Mapping) else {}


def _hypothesis_for_outcome(
    outcome: Mapping[str, Any], signal: Mapping[str, Any], pattern: str
) -> Dict[str, Any]:
    direct = outcome.get("hypothesis")
    if isinstance(direct, Mapping):
        return dict(direct)

    for key in ("target_feed", "execution_guidance"):
        container = signal.get(key)
        if isinstance(container, Mapping):
            hypothesis = container.get("hypothesis")
            if isinstance(hypothesis, Mapping):
                return dict(hypothesis)

    name = outcome.get("hypothesis_name") or signal.get("hypothesis_name") or pattern
    return {"id": outcome.get("hypothesis_id") or signal.get("hypothesis_id"), "name": name}


def _merge_rules(rules: Mapping[str, Any]) -> Dict[str, float]:
    merged = dict(DEFAULT_PROMOTION_RULES)
    for key in merged:
        if key in rules:
            merged[key] = float(rules[key])
    return merged


def _rules_from_env() -> Dict[str, Any]:
    raw = os.environ.get("HELLHOUND_PROMOTION_RULES")
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        LOGGER.warning("HELLHOUND_PROMOTION_RULES is not valid JSON; defaults used")
        return {}
    return value if isinstance(value, dict) else {}


def _load_local_resolved_outcomes() -> list[Dict[str, Any]]:
    with LOCAL_EVALUATION_DATA_PATH.open("r", encoding="utf-8") as file:
        outcomes = json.load(file)
    if not isinstance(outcomes, list):
        raise ValueError("local evaluation data must be a JSON list")
    expanded = []
    for index, outcome in enumerate(outcomes):
        if not isinstance(outcome, Mapping):
            continue
        repeat_count = int(outcome.get("repeat_count") or 1)
        for repeat_index in range(repeat_count):
            row = dict(outcome)
            row.pop("repeat_count", None)
            if not row.get("id"):
                row["id"] = f"local-{index}-{repeat_index}"
            expanded.append(row)
    return expanded


def _print_summary(
    scoreboard: list[Mapping[str, Any]], status_updates: list[Mapping[str, Any]]
) -> None:
    print(
        json.dumps(
            {
                "scoreboard": scoreboard,
                "status_updates": status_updates,
            },
            indent=2,
            sort_keys=True,
        )
    )


def _dry_run_enabled() -> bool:
    raw = os.environ.get("EVALUATION_LOOP_DRY_RUN", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _local_mode_enabled() -> bool:
    raw = os.environ.get("EVALUATION_LOOP_LOCAL", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _supabase_credentials() -> tuple[Optional[str], Optional[str]]:
    return (
        os.environ.get("SUPABASE_URL"),
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY"),
    )


def _redact_secret_text(value: str) -> str:
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    anon_key = os.environ.get("SUPABASE_ANON_KEY")
    redacted = value
    for secret in (service_key, anon_key):
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if _local_mode_enabled():
        try:
            scoreboard = build_scoreboard(_load_local_resolved_outcomes())
            status_updates = apply_promotion_rules(scoreboard)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            LOGGER.error("Local evaluation data load failed: %s", exc)
            return 1
        _print_summary(scoreboard, status_updates)
        return 0

    result = run_evaluation_loop()
    if not result.ok and not result.skipped:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
