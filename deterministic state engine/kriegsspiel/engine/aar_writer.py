"""kriegsspiel/engine/aar_writer.py

Post-turn AAR LLM call. One neutral white-cell narrative per turn.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Optional

from .llm_planner import LLMBackend, LLMCallResult


PROMPT_VERSION_AAR = "aar_writer_v1"
REQUIRED_AAR_KEYS = {"overall", "blue_perspective", "red_perspective",
                     "key_events", "risks_next_turn"}


@dataclass
class AARResult:
    aar: Optional[dict]
    raw_llm_output: str
    parse_ok: bool
    failure_reason: Optional[str]
    latency_ms: int
    request_id: Optional[str]


def render_aar_prompt(template, *, run_id, turn, rulepack_id,
                      blue_intent, red_intent, blue_decisions, red_decisions,
                      post_combat_deltas, validation_issues):
    return (template
        .replace("{RUN_ID}", str(run_id))
        .replace("{TURN}", str(turn))
        .replace("{RULEPACK_ID}", str(rulepack_id))
        .replace("{BLUE_INTENT}", blue_intent or "(no intent provided)")
        .replace("{RED_INTENT}", red_intent or "(no intent provided)")
        .replace("{BLUE_DECISIONS}", _format_decisions(blue_decisions))
        .replace("{RED_DECISIONS}", _format_decisions(red_decisions))
        .replace("{POST_COMBAT_DELTAS}", _format_deltas(post_combat_deltas))
        .replace("{VALIDATION_ISSUES}", _format_issues(validation_issues))
    )


def parse_and_validate_aar(raw):
    if raw is None or not raw.strip():
        return None, "empty response"
    if "```" in raw:
        return None, "markdown fences in response"
    s = raw.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return None, "not a bare JSON object"
    try:
        parsed = json.loads(s)
    except json.JSONDecodeError as e:
        return None, f"json decode error: {e}"
    if not isinstance(parsed, dict):
        return None, "top-level not a dict"

    missing = REQUIRED_AAR_KEYS - set(parsed.keys())
    if missing:
        return None, f"missing required keys: {sorted(missing)}"
    for k in ("overall", "blue_perspective", "red_perspective"):
        v = parsed.get(k)
        if not isinstance(v, str) or not v.strip():
            return None, f"{k} is not a non-empty string"
    for k in ("key_events", "risks_next_turn"):
        v = parsed.get(k)
        if not isinstance(v, list):
            return None, f"{k} is not a list"
        if not all(isinstance(x, str) for x in v):
            return None, f"{k} contains non-string entries"

    cleaned = {
        "overall":          parsed["overall"][:2000],
        "blue_perspective": parsed["blue_perspective"][:1200],
        "red_perspective":  parsed["red_perspective"][:1200],
        "key_events":       [s[:300] for s in parsed["key_events"]][:8],
        "risks_next_turn":  [s[:300] for s in parsed["risks_next_turn"]][:8],
    }
    return cleaned, None


def write_aar(*, backend: LLMBackend, prompt_template, run_id, turn,
              rulepack_id, blue_intent, red_intent, blue_decisions,
              red_decisions, post_combat_deltas, validation_issues,
              timeout_s: float = 15.0,
              max_attempts: int = 2) -> AARResult:
    prompt = render_aar_prompt(
        prompt_template, run_id=run_id, turn=turn, rulepack_id=rulepack_id,
        blue_intent=blue_intent, red_intent=red_intent,
        blue_decisions=blue_decisions, red_decisions=red_decisions,
        post_combat_deltas=post_combat_deltas,
        validation_issues=validation_issues,
    )
    attempts = max(1, int(max_attempts))
    call_result: LLMCallResult = LLMCallResult(
        raw_text="", latency_ms=0, request_id=None, error="unknown")

    for attempt in range(1, attempts + 1):
        call_result = backend.call(prompt, timeout_s=timeout_s)
        if call_result.error and attempt < attempts and _is_retryable_llm_error(call_result.error):
            # Small fixed backoff to absorb transient provider-side 400/429/5xx failures.
            time.sleep(0.5)
            continue
        break

    if call_result.error:
        return AARResult(aar=None, raw_llm_output="", parse_ok=False,
                         failure_reason=f"llm_error: {call_result.error}",
                         latency_ms=call_result.latency_ms,
                         request_id=call_result.request_id)

    aar, err = parse_and_validate_aar(call_result.raw_text)
    if err is not None:
        return AARResult(aar=None, raw_llm_output=call_result.raw_text,
                         parse_ok=False, failure_reason=err,
                         latency_ms=call_result.latency_ms,
                         request_id=call_result.request_id)

    return AARResult(aar=aar, raw_llm_output=call_result.raw_text,
                     parse_ok=True, failure_reason=None,
                     latency_ms=call_result.latency_ms,
                     request_id=call_result.request_id)


def _format_decisions(decisions):
    if not decisions:
        return "  (none)"
    lines = []
    for d in decisions:
        action = d.get("action", "?")
        unit_id = d.get("unit_id", "?")
        target = d.get("target_id")
        rat = d.get("rationale") or ""
        if action == "ATTACK":
            line = f"  - {unit_id} ATTACK {target}"
        else:
            line = f"  - {unit_id} WAIT"
        if rat:
            line += f"  // {rat[:80]}"
        lines.append(line)
    return "\n".join(lines)


def _format_deltas(deltas):
    if not deltas:
        return "  (no unit changed strength or readiness this turn)"
    lines = []
    for d in deltas:
        lines.append(
            f"  - {d['unit_id']}: strength {d['strength_before']:.2f} -> "
            f"{d['strength_after']:.2f} (delta {d['strength_delta']:+.2f}); "
            f"readiness {d['readiness_before']} -> {d['readiness_after']}"
        )
    return "\n".join(lines)


def _format_issues(issues):
    if not issues:
        return "  (none -- all decisions accepted)"
    lines = []
    for i in issues[:10]:
        uid = i.get("unit_id") or "*"
        lines.append(f"  - {i.get('code')} ({uid}): {i.get('detail','')[:100]}")
    if len(issues) > 10:
        lines.append(f"  - ... ({len(issues) - 10} more issues truncated)")
    return "\n".join(lines)


def _is_retryable_llm_error(error_msg: str) -> bool:
    s = (error_msg or "").lower()
    if any(k in s for k in ("timeout", "timed out", "connection", "temporar", "rate limit")):
        return True
    # Handle HTTP-style failures surfaced in exception text, e.g. "400 Client Error".
    m = re.search(r"\b([45]\d{2})\b", s)
    if not m:
        return False
    code = int(m.group(1))
    return code == 400 or code == 408 or code == 409 or code == 429 or 500 <= code <= 599