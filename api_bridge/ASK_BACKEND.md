# Backend / Engine Asks

Four contracts the api_bridge needs from the engine team. Every other
gap (validation, scenario registry, snapshots, etc.) the bridge will
absorb on its own side.

The bridge isolates every engine touchpoint inside
`api_bridge/engine_facade.py`. Each ask below corresponds to a TODO
comment there or a stub elsewhere in `api_bridge/`.

Engine entry-point (today): `kriegsspiel.engine.state.WorldState`
Scenario factory: `kriegsspiel.scenarios.latgale_2027.build_latgale_world()`

---

## 1. Single `step()` method on `WorldState`

Currently `engine_facade.tick_one_turn` reaches into engine privates:

```python
attack_map = world._build_attack_map(safe_decisions)
world._resolve_attacks(attack_map)
world.turn += 1
world.timestamp_minutes = world.turn * world.minutes_per_turn
```

We want one public method that runs the full per-turn pipeline (movement →
combat → control update → turn advance):

```python
def step(self, decisions: list[UnitDecision]) -> StepResult:
    """Resolve one full turn. Returns events + per-unit deltas."""
```

`StepResult` shape we'd consume:

```
{
  "events":          [{type, unit_id?, target_id?, reason_code, ...}],
  "destroyed":       [unit_id, ...],
  "moves":           {unit_id: {from: [r,c], to: [r,c]}},
  "objectives_taken":[{objective_id, by}]
}
```

This kills the `_build_attack_map` / `_resolve_attacks` private-API
coupling.

---

## 2. Movement resolution

The engine accepts MOVE in the decision schema but never applies it.
Bridge currently flags MOVE orders as `move_not_implemented` in
`turn_log[].skipped`.

We need `step()` to honour `{action: "MOVE", target_position: [r, c]}`,
respecting:

- `terrain.movement_cost_ground`
- `RiverCrossing` integrity / control
- Stacking invariant from `validate_world_invariants`

Return move outcome (success/blocked/partial) in `StepResult.moves`.

---

## 3. RED order generation

Bridge currently fakes RED with `api_bridge/red_ai.py`
(nearest-target attack). Want:

```python
def generate_orders(world: WorldState, side: Side) -> list[UnitDecision]:
    """Deterministic OPFOR orders for one turn."""
```

OK if it's a simple heuristic. When this lands we'll delete
`api_bridge/red_ai.py`.

---

## 4. Victory / outcome status

Today the bridge guesses:

```python
def outcome(world, total_turns):
    if world.turn < total_turns: return "running"
    return "blue_win" if blue_holds >= 2 objectives else "red_win"
```

Want one engine call that knows the scenario's win conditions:

```python
def victory_status(world: WorldState) -> dict:
    """
    {
      "status": "running" | "blue_win" | "red_win" | "draw",
      "reason": "objective_threshold" | "time_limit" | "force_destruction" | ...,
    }
    """
```

This lets the bridge end games early on decisive outcomes (force
destruction, decapitation), not just at `turns_total`.

---

## What the bridge owns (don't worry about these)

- HTTP / FastAPI surface, request validation, error codes
- Session store (in-memory) and game_id assignment
- Epoch state machine (`awaiting_orders` ↔ `running` → `ended`)
- Projection from `WorldState` → JSON shapes the frontend consumes
- Scenario registry (3 hardwired for the demo)
- CORS, health check, AAR envelope

If you change anything in `kriegsspiel.engine` or
`kriegsspiel.scenarios.*` that affects these contracts, ping the bridge
team — the only file we'd need to touch is
`api_bridge/engine_facade.py`.
