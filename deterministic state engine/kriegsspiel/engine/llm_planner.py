"""kriegsspiel/engine/llm_planner.py

Per-side LLM decision pipeline. Plugs into existing engine without
modifying it. Produces list[dict] in the shape the engine already consumes.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Optional


ALLOWED_ACTIONS = {"ATTACK", "WAIT"}
ALLOWED_DECISION_KEYS = {
    "unit_id",
    "action",
    "target_id",
    "target_position",
    "rationale",
}
REQUIRED_DECISION_KEYS = {"unit_id", "action"}
ALLOWED_TOP_LEVEL_KEYS = {"side_intent", "decisions"}
REQUIRED_TOP_LEVEL_KEYS = {"side_intent", "decisions"}

PROMPT_VERSION = "turn_planner_simple_v1"


@dataclass
class ValidationIssue:
    code: str
    unit_id: Optional[str] = None
    detail: str = ""

    def to_dict(self) -> dict:
        return {"code": self.code, "unit_id": self.unit_id, "detail": self.detail}


@dataclass
class PlannerResult:
    side: str
    side_intent: Optional[str]
    final_decisions: list
    issues: list
    fallback_scope: str = "NONE"
    fallback_reason: Optional[str] = None
    raw_llm_output: str = ""
    parse_ok: bool = False
    latency_ms: int = 0
    request_id: Optional[str] = None
    input_state_hash: str = ""
    input_summary: str = ""
    prompt_text_hash: str = ""


@dataclass
class LLMCallResult:
    raw_text: str
    latency_ms: int
    request_id: Optional[str] = None
    error: Optional[str] = None


class LLMBackend:
    model_name: str = "unknown"
    temperature: float = 0.0
    max_tokens: int = 1024

    def call(self, prompt: str, *, timeout_s: float = 15.0) -> LLMCallResult:
        raise NotImplementedError


class AnthropicBackend(LLMBackend):
    """Anthropic Claude Messages API."""

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        temperature: float = 0.0,
        max_tokens: int = 2048,
        base_url: str = "https://api.anthropic.com",
        api_version: str = "2023-06-01",
        system_prompt: Optional[str] = None,
        use_json_prefill: bool = True,
    ):
        self.model_name = f"anthropic/{model}"
        self._model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = base_url
        self.api_version = api_version
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.system_prompt = system_prompt
        self.use_json_prefill = use_json_prefill

    def call(self, prompt: str, *, timeout_s: float = 15.0) -> LLMCallResult:
        if not self.api_key:
            return LLMCallResult(raw_text="", latency_ms=0, error="ANTHROPIC_API_KEY not set")

        messages = [{"role": "user", "content": prompt}]
        if self.use_json_prefill:
            # Optional prefill to nudge strict JSON.
            messages.append({"role": "assistant", "content": "{"})

        body: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.system_prompt:
            body["system"] = self.system_prompt

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "content-type": "application/json",
        }
        url = f"{self.base_url}/v1/messages"

        t0 = time.perf_counter()
        try:
            try:
                import requests  # type: ignore

                resp = requests.post(url, json=body, headers=headers, timeout=timeout_s)
                resp.raise_for_status()
                data = resp.json()
            except ImportError:
                import urllib.request

                req = urllib.request.Request(
                    url, data=json.dumps(body).encode(), headers=headers, method="POST"
                )
                with urllib.request.urlopen(req, timeout=timeout_s) as r:
                    data = json.loads(r.read().decode())
        except Exception as e:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            return LLMCallResult(raw_text="", latency_ms=latency_ms, error=f"{type(e).__name__}: {e}"[:500])

        latency_ms = int((time.perf_counter() - t0) * 1000)

        try:
            request_id = data.get("id")
            content = data["content"]
            text_block = next(
                (b for b in content if isinstance(b, dict) and b.get("type") == "text"),
                None,
            )
            if text_block is None:
                return LLMCallResult(
                    raw_text="",
                    latency_ms=latency_ms,
                    request_id=request_id,
                    error="no text block in response content",
                )
            raw = text_block.get("text", "")
        except (KeyError, IndexError, TypeError, StopIteration) as e:
            return LLMCallResult(
                raw_text="",
                latency_ms=latency_ms,
                error=f"Unexpected response shape: {e}",
            )

        completed = raw
        if self.use_json_prefill and not raw.startswith("{"):
            completed = "{" + raw

        if data.get("stop_reason") == "max_tokens":
            return LLMCallResult(
                raw_text=completed,
                latency_ms=latency_ms,
                request_id=request_id,
                error=f"hit max_tokens={self.max_tokens}; response likely truncated",
            )

        return LLMCallResult(raw_text=completed, latency_ms=latency_ms, request_id=request_id)


class StubBackend(LLMBackend):
    """Returns canned responses. Used in tests and offline runs."""

    model_name = "stub"

    def __init__(self, fixed_response=None, fail_with: Optional[str] = None):
        self.fixed_response = fixed_response
        self.fail_with = fail_with

    def call(self, prompt: str, *, timeout_s: float = 15.0) -> LLMCallResult:
        if self.fail_with:
            return LLMCallResult(raw_text="", latency_ms=1, error=self.fail_with)
        if isinstance(self.fixed_response, dict):
            return LLMCallResult(raw_text=json.dumps(self.fixed_response), latency_ms=1, request_id="stub-0")
        if isinstance(self.fixed_response, str):
            return LLMCallResult(raw_text=self.fixed_response, latency_ms=1, request_id="stub-0")
        return LLMCallResult(
            raw_text='{"side_intent":"stub","decisions":[]}',
            latency_ms=1,
            request_id="stub-0",
        )


def build_situation_summary(world, side) -> str:
    side_str = _side_str(side)
    enemy_str = "RED" if side_str == "BLUE" else "BLUE"

    my_alive = [u for u in world.units.values() if _side_str(u.side) == side_str and not _is_destroyed(u)]
    enemy_alive = [u for u in world.units.values() if _side_str(u.side) == enemy_str and not _is_destroyed(u)]

    detected_enemies = _enemies_detected_by_side(world, side_str, enemy_str)
    objectives = list(getattr(world, "objectives", {}).values())
    held_by_me = [o for o in objectives if _objective_held_by(o) == side_str]
    contested = [o for o in objectives if _objective_held_by(o) not in (side_str, enemy_str)]

    terrain_ctx = _terrain_context(world)
    readiness_counts = _readiness_counts(my_alive)

    parts: list[str] = []
    parts.append(
        f"Turn {world.turn}: {side_str} has {len(my_alive)} alive units; {enemy_str} has {len(enemy_alive)} alive units."
    )
    if held_by_me:
        parts.append(f"{side_str} currently holds: {', '.join(_obj_name(o) for o in held_by_me)}.")
    if contested:
        parts.append(f"Contested or neutral: {', '.join(_obj_name(o) for o in contested)}.")
    if detected_enemies:
        top = sorted(detected_enemies.items(), key=lambda kv: -kv[1])[:3]
        top_str = "; ".join(f"{eid} (score {score:.2f})" for eid, score in top)
        parts.append(f"{side_str} detection this turn covers {len(detected_enemies)} {enemy_str} units. Strongest: {top_str}.")
    else:
        parts.append(f"{side_str} has no detected {enemy_str} units this turn.")

    if my_alive:
        avg_my_str = sum(float(u.strength) for u in my_alive) / len(my_alive)
        parts.append(f"{side_str} average strength: {avg_my_str:.2f}.")
        parts.append(f"{side_str} readiness mix: {readiness_counts}.")
    parts.append(
        f"Map {terrain_ctx['grid_size'][0]}x{terrain_ctx['grid_size'][1]}, passable ratio {terrain_ctx['passable_ratio']:.2f}."
    )
    return " ".join(parts)


def build_llm_input(world, side) -> dict:
    side_str = _side_str(side)
    enemy_str = "RED" if side_str == "BLUE" else "BLUE"

    my_units = [u for u in world.units.values() if _side_str(u.side) == side_str and not _is_destroyed(u)]
    enemy_units_alive = [u for u in world.units.values() if _side_str(u.side) == enemy_str and not _is_destroyed(u)]

    detected = _enemies_detected_by_side(world, side_str, enemy_str)
    visible_enemy_ids = set(detected.keys())

    your_units = [_unit_brief(u) for u in my_units]
    visible_enemies = [
        {**_unit_brief(u), "detection_score": round(detected[u.unit_id], 3)}
        for u in enemy_units_alive
        if u.unit_id in visible_enemy_ids
    ]
    listed_enemies = [_unit_brief(u) for u in enemy_units_alive]

    summary = build_situation_summary(world, side)
    terrain_context = _terrain_context(world)
    objectives = _objectives_brief(world)

    bundle = {
        "run_id": _identity_field(world, "run_id", default="unknown"),
        "turn": int(world.turn),
        "side": side_str,
        "rulepack_id": _identity_field(world, "rulepack_id", default="krg_v0_1"),
        "engine_version": _identity_field(world, "engine_version", default="0.1.0"),
        "your_units": your_units,
        "visible_enemies": visible_enemies,
        "listed_enemies": listed_enemies,
        "situation_summary": summary,
        "terrain_context": terrain_context,
        "objectives": objectives,
        "rules_snapshot": {
            "allowed_actions": sorted(ALLOWED_ACTIONS),
            "attack_target_must_be_alive_enemy": True,
            "target_position_supported": False,
        },
    }
    bundle["input_state_hash"] = _short_hash(bundle)
    return bundle


def render_planner_prompt(template: str, bundle: dict) -> str:
    your_units_str = _format_unit_list(bundle["your_units"])
    visible_enemies_str = _format_enemy_list(bundle["visible_enemies"]) or "  (none detected this turn)"
    listed_enemies_str = _format_unit_list(bundle["listed_enemies"]) or "  (none alive)"
    terrain_context_str = json.dumps(bundle.get("terrain_context", {}), sort_keys=True)
    objectives_str = json.dumps(bundle.get("objectives", []), sort_keys=True)
    rules_snapshot_str = json.dumps(bundle.get("rules_snapshot", {}), sort_keys=True)

    return (
        template.replace("{RUN_ID}", str(bundle["run_id"]))
        .replace("{TURN}", str(bundle["turn"]))
        .replace("{SIDE}", str(bundle["side"]))
        .replace("{RULEPACK_ID}", str(bundle["rulepack_id"]))
        .replace("{SIDE_SITUATION_SUMMARY}", str(bundle["situation_summary"]))
        .replace("{YOUR_UNITS}", your_units_str)
        .replace("{VISIBLE_ENEMIES}", visible_enemies_str)
        .replace("{LISTED_ENEMIES}", listed_enemies_str)
        .replace("{TERRAIN_CONTEXT}", terrain_context_str)
        .replace("{OBJECTIVES}", objectives_str)
        .replace("{RULES_SNAPSHOT}", rules_snapshot_str)
    )


def parse_planner_json(raw: str):
    if raw is None or not raw.strip():
        return None, "empty response"
    if "```" in raw:
        return None, "response contains markdown fences"
    s = raw.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return None, f"not a bare JSON object (starts {s[:30]!r}, ends {s[-30:]!r})"
    try:
        return json.loads(s), None
    except json.JSONDecodeError as e:
        return None, f"json decode error: {e}"


def validate_and_normalize(world, side, parsed, *, parse_error=None, llm_error=None):
    side_str = _side_str(side)
    issues: list[ValidationIssue] = []

    if llm_error is not None:
        return _whole_side_fallback(world, side_str, reason="LLM_CALL_ERROR", detail=llm_error, issues=issues)
    if parsed is None:
        return _whole_side_fallback(world, side_str, reason="LLM_NOT_JSON", detail=parse_error or "parse failed", issues=issues)
    if not isinstance(parsed, dict):
        return _whole_side_fallback(world, side_str, reason="LLM_SCHEMA_INVALID", detail="top-level not a dict", issues=issues)

    missing_top = REQUIRED_TOP_LEVEL_KEYS - set(parsed.keys())
    if missing_top:
        return _whole_side_fallback(
            world,
            side_str,
            reason="LLM_SCHEMA_INVALID",
            detail=f"missing top-level keys: {sorted(missing_top)}",
            issues=issues,
        )

    extra_top = set(parsed.keys()) - ALLOWED_TOP_LEVEL_KEYS
    if extra_top:
        issues.append(ValidationIssue(code="VAL_EXTRA_TOP_KEY", detail=f"unknown top-level keys ignored: {sorted(extra_top)}"))

    raw_decisions = parsed.get("decisions")
    if not isinstance(raw_decisions, list):
        return _whole_side_fallback(world, side_str, reason="LLM_SCHEMA_INVALID", detail="decisions is not a list", issues=issues)

    raw_intent = parsed.get("side_intent")
    side_intent = raw_intent.strip()[:500] if isinstance(raw_intent, str) and raw_intent.strip() else None
    if side_intent is None:
        issues.append(ValidationIssue(code="VAL_MISSING_INTENT", detail="side_intent missing or non-string; logged as null"))

    alive_by_id = {u.unit_id: u for u in world.units.values() if not _is_destroyed(u)}
    side_alive_ids = {u.unit_id for u in alive_by_id.values() if _side_str(u.side) == side_str}
    seen_unit_ids: set[str] = set()
    accepted: dict[str, dict] = {}

    for idx, item in enumerate(raw_decisions):
        if not isinstance(item, dict):
            issues.append(ValidationIssue(code="VAL_ITEM_NOT_OBJECT", detail=f"decisions[{idx}] is not an object"))
            continue

        item_keys = set(item.keys())
        missing_req = REQUIRED_DECISION_KEYS - item_keys
        if missing_req:
            issues.append(
                ValidationIssue(code="VAL_MISSING_REQUIRED", unit_id=item.get("unit_id"), detail=f"missing required keys: {sorted(missing_req)}")
            )
            continue

        unknown = item_keys - ALLOWED_DECISION_KEYS
        if unknown:
            issues.append(ValidationIssue(code="VAL_UNKNOWN_KEY", unit_id=item.get("unit_id"), detail=f"unknown keys ignored: {sorted(unknown)}"))
            item = {k: v for k, v in item.items() if k in ALLOWED_DECISION_KEYS}

        unit_id = item["unit_id"]
        if not isinstance(unit_id, str) or not unit_id:
            issues.append(ValidationIssue(code="VAL_BAD_UNIT_ID", detail=f"decisions[{idx}].unit_id not a non-empty string"))
            continue
        if unit_id not in world.units:
            issues.append(ValidationIssue(code="VAL_UNIT_NOT_FOUND", unit_id=unit_id, detail=f"{unit_id} is not in world.units"))
            continue

        unit = world.units[unit_id]
        if _is_destroyed(unit):
            issues.append(ValidationIssue(code="VAL_UNIT_DEAD", unit_id=unit_id, detail=f"{unit_id} is DESTROYED; cannot act"))
            continue
        if _side_str(unit.side) != side_str:
            issues.append(ValidationIssue(code="VAL_WRONG_SIDE", unit_id=unit_id, detail=f"{unit_id} is {_side_str(unit.side)}, not {side_str}"))
            continue
        if unit_id in seen_unit_ids:
            issues.append(ValidationIssue(code="VAL_DUPLICATE_DECISION", unit_id=unit_id, detail="duplicate decision; first wins"))
            continue
        seen_unit_ids.add(unit_id)

        action = item.get("action")
        target_id = item.get("target_id")
        target_position = item.get("target_position")

        if action not in ALLOWED_ACTIONS:
            issues.append(ValidationIssue(code="VAL_BAD_ACTION", unit_id=unit_id, detail=f"action {action!r} not allowed; -> WAIT"))
            accepted[unit_id] = _wait_decision(unit_id, rationale="fallback: bad action")
            continue

        if target_position is not None:
            issues.append(
                ValidationIssue(code="VAL_TARGET_POSITION_UNSUPPORTED", unit_id=unit_id, detail="target_position must be null; stripped")
            )
            target_position = None

        if action == "WAIT":
            if target_id is not None:
                issues.append(ValidationIssue(code="VAL_INCONSISTENT_TARGET", unit_id=unit_id, detail=f"WAIT must have target_id=null; got {target_id!r}"))
                target_id = None
            accepted[unit_id] = {
                "unit_id": unit_id,
                "action": "WAIT",
                "target_id": None,
                "target_position": None,
                "rationale": _clean_rationale(item.get("rationale")),
            }
            continue

        # ATTACK
        if not isinstance(target_id, str) or not target_id:
            issues.append(ValidationIssue(code="VAL_ATTACK_MISSING_TARGET", unit_id=unit_id, detail="ATTACK requires non-empty target_id; -> WAIT"))
            accepted[unit_id] = _wait_decision(unit_id, rationale="fallback: missing target")
            continue

        if target_id not in world.units:
            issues.append(ValidationIssue(code="VAL_TARGET_NOT_FOUND", unit_id=unit_id, detail=f"target_id {target_id!r} not in world.units; -> WAIT"))
            accepted[unit_id] = _wait_decision(unit_id, rationale="fallback: unknown target")
            continue

        target = world.units[target_id]
        if _is_destroyed(target):
            issues.append(ValidationIssue(code="VAL_TARGET_DESTROYED", unit_id=unit_id, detail=f"target {target_id} is DESTROYED; -> WAIT"))
            accepted[unit_id] = _wait_decision(unit_id, rationale="fallback: target destroyed")
            continue
        if _side_str(target.side) == side_str:
            issues.append(ValidationIssue(code="VAL_FRIENDLY_FIRE", unit_id=unit_id, detail=f"target {target_id} is friendly; -> WAIT"))
            accepted[unit_id] = _wait_decision(unit_id, rationale="fallback: friendly fire")
            continue

        accepted[unit_id] = {
            "unit_id": unit_id,
            "action": "ATTACK",
            "target_id": target_id,
            "target_position": None,
            "rationale": _clean_rationale(item.get("rationale")),
        }

    missing = side_alive_ids - set(accepted.keys())
    for uid in sorted(missing):
        issues.append(ValidationIssue(code="VAL_MISSING_DECISION", unit_id=uid, detail="no decision provided; injected synthetic WAIT"))
        accepted[uid] = _wait_decision(uid, rationale="fallback: no decision from LLM")

    any_fallbacks = any(d["rationale"] and d["rationale"].startswith("fallback:") for d in accepted.values())
    scope = "PER_ITEM" if any_fallbacks else "NONE"
    final_decisions = [accepted[uid] for uid in sorted(accepted.keys())]
    return side_intent, final_decisions, issues, scope, None


def apply_decisions_to_world(world, side, side_decisions: list) -> None:
    if not hasattr(world, "unit_decision_list") or world.unit_decision_list is None:
        world.unit_decision_list = []
    world.unit_decision_list.extend(side_decisions)


def plan_unit(world, unit, side_str, *, backend: LLMBackend, prompt_template: str, timeout_s: float = 15.0) -> dict:
    """Get a single decision for a single unit."""
    bundle = build_llm_input(world, side_str)
    # narrow the bundle to just this unit's perspective
    bundle["your_units"] = [u for u in bundle["your_units"] if u["unit_id"] == unit.unit_id]
    bundle["acting_unit_id"] = unit.unit_id
    prompt = render_planner_prompt(prompt_template, bundle)

    call_result = backend.call(prompt, timeout_s=timeout_s)

    if call_result.error:
        return _wait_decision(unit.unit_id, rationale=f"fallback: {call_result.error}")

    parsed, parse_err = parse_planner_json(call_result.raw_text)
    if parsed is None:
        return _wait_decision(unit.unit_id, rationale=f"fallback: {parse_err}")

    decisions = parsed.get("decisions", [])
    for d in decisions:
        if d.get("unit_id") == unit.unit_id:
            action = d.get("action")
            target_id = d.get("target_id")

            if action not in ALLOWED_ACTIONS:
                return _wait_decision(unit.unit_id, rationale="fallback: bad action")
            if action == "ATTACK":
                if not target_id or target_id not in world.units:
                    return _wait_decision(unit.unit_id, rationale="fallback: invalid target")
                target = world.units[target_id]
                if _is_destroyed(target) or _side_str(target.side) == side_str:
                    return _wait_decision(unit.unit_id, rationale="fallback: invalid target")
            return {
                "unit_id": unit.unit_id,
                "action": action,
                "target_id": target_id if action == "ATTACK" else None,
                "target_position": None,
                "rationale": _clean_rationale(d.get("rationale")),
            }

    return _wait_decision(unit.unit_id, rationale="fallback: no decision returned")


def plan_side(world, side, *, backend: LLMBackend, prompt_template: str, timeout_s: float = 15.0) -> PlannerResult:
    side_str = _side_str(side)
    alive_units = [
        u for u in world.units.values()
        if _side_str(u.side) == side_str and not _is_destroyed(u)
    ]

    all_decisions = []
    all_issues = []

    for unit in sorted(alive_units, key=lambda u: u.unit_id):
        decision = plan_unit(world, unit, side_str, backend=backend, prompt_template=prompt_template, timeout_s=timeout_s)
        all_decisions.append(decision)

    any_fallbacks = any(d["rationale"] and d["rationale"].startswith("fallback:") for d in all_decisions)
    scope = "PER_ITEM" if any_fallbacks else "NONE"

    bundle = build_llm_input(world, side)

    return PlannerResult(
        side=side_str,
        side_intent=f"{side_str} per-unit planning ({len(alive_units)} units)",
        final_decisions=all_decisions,
        issues=all_issues,
        fallback_scope=scope,
        fallback_reason=None,
        raw_llm_output="",
        parse_ok=True,
        latency_ms=0,
        request_id=None,
        input_state_hash=bundle["input_state_hash"],
        input_summary=bundle["situation_summary"],
        prompt_text_hash="",
    )


# ---------- internal helpers ----------

def _whole_side_fallback(world, side_str, *, reason, detail, issues):
    issues.append(ValidationIssue(code=reason, detail=detail))
    decisions: list = []
    for u in sorted(world.units.values(), key=lambda x: x.unit_id):
        if _is_destroyed(u):
            continue
        if _side_str(u.side) != side_str:
            continue
        decisions.append(_wait_decision(u.unit_id, rationale=f"fallback: {reason}"))
    return None, decisions, issues, "WHOLE_SIDE", reason


def _wait_decision(unit_id, *, rationale=None):
    return {
        "unit_id": unit_id,
        "action": "WAIT",
        "target_id": None,
        "target_position": None,
        "rationale": rationale,
    }


def _side_str(side):
    return side.value if hasattr(side, "value") else str(side)


def _is_destroyed(unit):
    rd = unit.readiness
    rd_str = rd.value if hasattr(rd, "value") else str(rd)
    return rd_str == "DESTROYED"


def _enemies_detected_by_side(world, side_str, enemy_str):
    out: dict[str, float] = {}
    for u in world.units.values():
        if _side_str(u.side) != side_str or _is_destroyed(u):
            continue
        obs = getattr(u, "observes", None) or {}
        for enemy_id, score in obs.items():
            target = world.units.get(enemy_id)
            if target is None or _is_destroyed(target):
                continue
            if _side_str(target.side) != enemy_str:
                continue
            out[enemy_id] = max(out.get(enemy_id, 0.0), float(score))
    return out


def _unit_brief(unit):
    pos = list(unit.position) if isinstance(unit.position, tuple) else unit.position
    rd = unit.readiness
    posture = unit.posture
    domain = getattr(unit, "domain", None)

    return {
        "unit_id": unit.unit_id,
        "template_id": getattr(unit, "template_id", ""),
        "side": _side_str(unit.side),
        "position": pos,
        "strength": round(float(unit.strength), 3),
        "readiness": rd.value if hasattr(rd, "value") else str(rd),
        "posture": posture.value if hasattr(posture, "value") else str(posture),
        "dug_in": bool(getattr(unit, "dug_in", False)),
        "domain": domain.value if hasattr(domain, "value") else (str(domain) if domain is not None else None),
    }


def _terrain_context(world) -> dict:
    terrain = getattr(world, "terrain", None)
    if terrain is None:
        return {"grid_size": [0, 0], "passable_ratio": 0.0, "base_counts": {}}

    h = int(getattr(terrain, "height", 0))
    w = int(getattr(terrain, "width", 0))
    total = max(1, h * w)
    passable = 0
    base_counts: dict[str, int] = {}

    for r in range(h):
        for c in range(w):
            cell = terrain.cell_at((r, c))
            b = cell.base.value if hasattr(cell.base, "value") else str(cell.base)
            base_counts[b] = base_counts.get(b, 0) + 1
            if b not in {"WATER", "IMPASSABLE"}:
                passable += 1

    return {
        "grid_size": [h, w],
        "passable_ratio": round(passable / total, 3),
        "base_counts": base_counts,
    }


def _objectives_brief(world) -> list[dict]:
    out = []
    for obj in getattr(world, "objectives", {}).values():
        held = getattr(obj, "held_by", None) or getattr(obj, "controlled_by", None)
        held_by = held.value if hasattr(held, "value") else str(held or "NEUTRAL")
        cell = getattr(obj, "cell", None)
        out.append(
            {
                "name": str(getattr(obj, "name", "") or getattr(obj, "objective_id", "?")),
                "cell": list(cell) if isinstance(cell, tuple) else cell,
                "weight": float(getattr(obj, "weight", 0.0)),
                "held_by": held_by,
            }
        )
    return out


def _objective_held_by(obj):
    held = getattr(obj, "held_by", None) or getattr(obj, "controlled_by", None)
    if held is None:
        return "NEUTRAL"
    return held.value if hasattr(held, "value") else str(held)


def _obj_name(obj):
    return str(getattr(obj, "name", "") or getattr(obj, "objective_id", "?"))


def _identity_field(world, name, default=None):
    ident = getattr(world, "identity", None)
    if ident is None:
        return default
    return getattr(ident, name, default)


def _readiness_counts(units) -> dict:
    counts: dict[str, int] = {}
    for u in units:
        rd = u.readiness.value if hasattr(u.readiness, "value") else str(u.readiness)
        counts[rd] = counts.get(rd, 0) + 1
    return counts


def _short_hash(obj):
    import hashlib

    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def _format_unit_list(units):
    if not units:
        return "  (none)"
    lines = []
    for u in units:
        domain = f" domain={u['domain']}" if u.get("domain") else ""
        lines.append(
            f"  - {u['unit_id']} ({u.get('template_id', '')}) "
            f"pos={u['position']} str={u['strength']} "
            f"rd={u['readiness']} posture={u['posture']}"
            f"{' dug-in' if u.get('dug_in') else ''}{domain}"
        )
    return "\n".join(lines)


def _format_enemy_list(enemies):
    if not enemies:
        return ""
    lines = []
    for e in enemies:
        score = e.get("detection_score", 0.0)
        domain = f" domain={e['domain']}" if e.get("domain") else ""
        lines.append(
            f"  - {e['unit_id']} pos={e['position']} str={e['strength']} "
            f"rd={e['readiness']} detected (score={score}){domain}"
        )
    return "\n".join(lines)


def _clean_rationale(s):
    if not isinstance(s, str):
        return None
    s = re.sub(r"\s+", " ", s.strip())
    return s[:200] if s else None