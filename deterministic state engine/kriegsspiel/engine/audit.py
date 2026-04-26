"""kriegsspiel/engine/audit.py

JSONL audit log writer. Three record types:
  1. turn_plan    -- one per side per turn
  2. turn_aar     -- one per turn after combat
  3. turn_summary -- one per turn closing record
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def canonical_hash(obj: Any) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_turn_plan_record(
    *,
    run_id: str,
    turn: int,
    side: str,
    rulepack_id: str,
    engine_version: str,
    prompt_version: str,
    model: str,
    model_temperature: float,
    model_max_tokens: int,
    request_id: Optional[str],
    latency_ms: int,
    input_state_hash: str,
    input_summary: str,
    prompt_text_hash: str,
    raw_llm_output: str,
    parse_ok: bool,
    side_intent: Optional[str],
    final_decisions: list,
    validation_issues: list,
    fallback_scope: str,
    fallback_reason: Optional[str],
) -> dict:
    return {
        "record_type": "turn_plan",
        "timestamp_utc": now_utc_iso(),
        "run_id": run_id,
        "turn": turn,
        "side": side,
        "rulepack_id": rulepack_id,
        "engine_version": engine_version,
        "prompt_version": prompt_version,
        "model": model,
        "model_temperature": model_temperature,
        "model_max_tokens": model_max_tokens,
        "request_id": request_id,
        "latency_ms": latency_ms,
        "input_state_hash": input_state_hash,
        "input_summary": _truncate(input_summary, 4000),
        "prompt_text_hash": prompt_text_hash,
        "raw_llm_output": _truncate(raw_llm_output, 8192),
        "raw_output_truncated": len(raw_llm_output) > 8192,
        "parse_ok": parse_ok,
        "side_intent": _truncate(side_intent or "", 500) if side_intent else None,
        "final_decisions": final_decisions,
        "validation_issues": validation_issues,
        "fallback_scope": fallback_scope,
        "fallback_reason": fallback_reason,
    }


def build_turn_aar_record(
    *,
    run_id: str,
    turn: int,
    rulepack_id: str,
    engine_version: str,
    prompt_version: str,
    model: str,
    model_temperature: float,
    model_max_tokens: int,
    request_id: Optional[str],
    latency_ms: int,
    pre_combat_state_hash: str,
    post_combat_state_hash: str,
    raw_llm_output: str,
    parse_ok: bool,
    aar: Optional[dict],
    failure_reason: Optional[str],
    post_combat_deltas: list,
) -> dict:
    return {
        "record_type": "turn_aar",
        "timestamp_utc": now_utc_iso(),
        "run_id": run_id,
        "turn": turn,
        "rulepack_id": rulepack_id,
        "engine_version": engine_version,
        "prompt_version": prompt_version,
        "model": model,
        "model_temperature": model_temperature,
        "model_max_tokens": model_max_tokens,
        "request_id": request_id,
        "latency_ms": latency_ms,
        "pre_combat_state_hash": pre_combat_state_hash,
        "post_combat_state_hash": post_combat_state_hash,
        "raw_llm_output": _truncate(raw_llm_output, 8192),
        "raw_output_truncated": len(raw_llm_output) > 8192,
        "parse_ok": parse_ok,
        "aar": aar,
        "failure_reason": failure_reason,
        "post_combat_deltas": post_combat_deltas,
    }


def build_turn_summary_record(
    *,
    run_id: str,
    turn: int,
    rulepack_id: str,
    pre_turn_state_hash: str,
    post_turn_state_hash: str,
    actions_submitted: int,
    actions_attack: int,
    actions_wait: int,
    actions_fallback: int,
    units_destroyed: int,
    units_degraded: int,
    units_suppressed: int,
    invariant_check_passed: bool,
) -> dict:
    return {
        "record_type": "turn_summary",
        "timestamp_utc": now_utc_iso(),
        "run_id": run_id,
        "turn": turn,
        "rulepack_id": rulepack_id,
        "pre_turn_state_hash": pre_turn_state_hash,
        "post_turn_state_hash": post_turn_state_hash,
        "actions_submitted": actions_submitted,
        "actions_attack": actions_attack,
        "actions_wait": actions_wait,
        "actions_fallback": actions_fallback,
        "units_destroyed": units_destroyed,
        "units_degraded": units_degraded,
        "units_suppressed": units_suppressed,
        "invariant_check_passed": invariant_check_passed,
    }


class AuditLog:
    def __init__(self, run_id: str, base_dir: str = "audit_logs"):
        self.run_id = run_id
        self.path = Path(base_dir) / run_id / f"{run_id}_audit.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "a", encoding="utf-8", buffering=1)

    def write(self, record: dict) -> None:
        if "record_type" not in record:
            raise ValueError("audit record missing required 'record_type' field")
        line = json.dumps(record, default=str)
        self._fh.write(line + "\n")
        self._fh.flush()
        try:
            os.fsync(self._fh.fileno())
        except OSError:
            pass

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.close()

    def __enter__(self) -> "AuditLog":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def _truncate(s: str, max_len: int) -> str:
    if not s:
        return s
    return s if len(s) <= max_len else s[:max_len]


def post_combat_deltas(pre_snapshot: dict, world) -> list:
    deltas: list = []
    for unit_id, before in pre_snapshot.items():
        unit = world.units.get(unit_id)
        if unit is None:
            continue
        after_strength = float(unit.strength)
        rd = unit.readiness
        after_readiness = rd.value if hasattr(rd, "value") else str(rd)
        if (before["strength"] != after_strength
                or before["readiness"] != after_readiness):
            deltas.append({
                "unit_id": unit_id,
                "strength_before": before["strength"],
                "strength_after": after_strength,
                "readiness_before": before["readiness"],
                "readiness_after": after_readiness,
                "strength_delta": round(after_strength - before["strength"], 4),
            })
    return deltas


def snapshot_units_for_delta(world) -> dict:
    out: dict = {}
    for unit_id, unit in world.units.items():
        rd = unit.readiness
        out[unit_id] = {
            "strength": float(unit.strength),
            "readiness": rd.value if hasattr(rd, "value") else str(rd),
        }
    return out