# Kriegsspiel API Map (v0.2 — epoch model)

Base URL: `http://localhost:8000`
Run: `uvicorn api_bridge.main:app --reload --port 8000`

---

## Concept

**Epoch** = a configurable batch of engine turns between BLUE decision
points. The bridge simulates `epoch_size` turns per epoch, then pauses
in `awaiting_orders` until BLUE submits a per-unit order list.

```
status flow:  awaiting_orders ──▶ (BLUE POSTs orders) ──▶ running ──▶ awaiting_orders
                                                                        │
                                                                        └─▶ ended
```

Within one epoch, BLUE's submitted orders are reused unchanged across
every turn; RED reacts each turn (currently a stub — nearest-target
attack — see ASK_BACKEND.md).

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET    | `/health`                           | Liveness + open session count |
| POST   | `/games`                            | Create new game |
| GET    | `/games/{id}`                       | Full current state |
| GET    | `/games/{id}/orders/template`       | Valid actions per BLUE unit (next epoch) |
| POST   | `/games/{id}/orders`                | Submit BLUE orders → advance one epoch |
| GET    | `/games/{id}/aar`                   | After-action report (any time, but useful when ended) |

---

## POST `/games`

```json
{
  "scenario":    "latgale_2027",
  "epoch_size":  2,
  "turns_total": 10,
  "seed":        1729
}
```

`scenario`, `epoch_size`, `turns_total`, `seed` all optional. Returns
`GameStateOut` with `status: "awaiting_orders"` and the first
`pending_orders` template populated.

---

## POST `/games/{id}/orders`

```json
{
  "orders": [
    {"unit_id": "BLUE-MNV-001-A", "action": "ATTACK", "target_id": "RED-MNV-006-A"},
    {"unit_id": "BLUE-MNV-002-A", "action": "ATTACK", "target_id": "RED-MNV-005-A"},
    {"unit_id": "BLUE-FRS-001-A", "action": "WAIT"},
    {"unit_id": "BLUE-ENB-001-A", "action": "MOVE", "target_position": [4, 6]}
  ],
  "note": "Hold north, screen south, reposition ENB"
}
```

**Rules**
- Every alive BLUE unit *should* be present; missing units default to WAIT.
- `action` ∈ `WAIT | ATTACK | MOVE`.
- `ATTACK` requires `target_id` of an alive enemy.
- `MOVE` requires `target_position`. **Currently a no-op** — the engine
  has no movement resolution yet (see ASK_BACKEND.md). The order is
  recorded in `skipped` with reason `move_not_implemented`.
- Submitting orders for non-BLUE / unknown unit_ids → `400`.
- Submitting when status is `running` or `ended` → `409`.

Response: updated `GameStateOut`. Status will be either
`awaiting_orders` (next epoch ready) or `ended`.

---

## Schemas

### `GameStateOut`
```
game_id              str
scenario             str
status               "awaiting_orders" | "running" | "ended"
outcome              "running" | "blue_win" | "red_win"
turn                 int       current engine turn
turns_total          int
epoch                int       epochs completed
epoch_size           int       turns per epoch
next_epoch_at_turn   int       bridge will pause here
blue_force           ForceOut
red_force            ForceOut  (currently unfiltered — fog-of-war TBD)
objectives           ObjectiveOut[]
map                  MapOut    static; safe to cache after first call
epoch_log            EpochRecordOut[]
pending_orders       OrdersTemplateOut | null
```

### `UnitOut`
```
unit_id     str
side        "BLUE" | "RED"
unit_type   "MNV" | "FRS" | "ENB"
template_id str
position    [row, col]
strength    float (0.0–1.0)
readiness   "FULLY_OPERATIONAL" | "DEGRADED" | "SUPPRESSED" | "DESTROYED"
posture     "OFFENSIVE" | "DEFENSIVE" | "MOVING" | "SCREENING" | "RESUPPLYING"
dug_in      bool
is_alive    bool
```

### `OrdersTemplateOut`
```
epoch     int      next epoch index
turn      int      current engine turn
units     UnitOrderOption[]
```

### `UnitOrderOption`
```
unit_id          str
can_wait         bool
can_attack       bool
can_move         bool       false until engine ships movement
valid_attack_ids str[]      enemy unit_ids visible to BLUE
```

### `EpochRecordOut`
```
epoch        int
turn_start   int
turn_end     int
note         str       BLUE commander's note for this epoch
turns        TurnRecordOut[]
```

### `TurnRecordOut`
```
turn            int
blue_action     str       summary, e.g. "ATTACK×2, WAIT×2"
red_action      str
note            str
narrative       str       filled by adjudicator (other team) — empty for now
doctrine_refs   str[]     filled by adjudicator
blue_cp_after   float     0–100, mean alive-unit strength × 100
red_cp_after    float
destroyed       str[]     unit_ids destroyed this turn
skipped         dict[]    [{unit_id, reason}, ...] — illegal/no-op orders
unit_positions dict       {unit_id: [row, col]}
```

### `MapOut`
```
rows         int
cols         int
km_per_cell  float
cells        TerrainCellOut[]   sparse — OPEN cells omitted
```

---

## 2D map rendering

All positions are `[row, col]` on a 16×16 grid at 5 km/cell (Latgale
scenario). Row 0 = north, row 15 = south. RED starts east (cols 14–15),
BLUE starts west (cols 2–4).

- `UnitOut.position` — current position, updated each epoch
- `TurnRecordOut.unit_positions` — full per-turn snapshot (replay scrubber)
- `ObjectiveOut.position` — fixed marker locations
- `MapOut.cells` — static terrain layer (sparse)

---

## Known limitations

See `ASK_BACKEND.md` for the contract gaps we're waiting on the
backend/engine team to close.
