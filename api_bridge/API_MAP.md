# Kriegsspiel API Map

Base URL: `http://localhost:8000`  
Run: `uvicorn api_bridge.main:app --reload --port 8000`

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Server liveness check |
| POST | `/game/start` | Start a new game session |
| GET | `/game/{game_id}` | Current game state |
| POST | `/game/{game_id}/action` | Submit BLUE decision for current turn |
| GET | `/game/{game_id}/report` | After-action report |

---

## GET `/health`

**Response `200`**
```json
{ "status": "ok", "sessions": 2 }
```

---

## POST `/game/start`

**Request**
```json
{ "scenario": "latgale_2027" }
```
> `scenario` is optional — defaults to `"latgale_2027"`.

**Response** → `GameStateOut` (see below)

---

## GET `/game/{game_id}`

**Response** → `GameStateOut`

---

## POST `/game/{game_id}/action`

**Request**
```json
{
  "decision_key": "hold",
  "note": "Holding northern line — await RED commitment"
}
```

**Valid `decision_key` values**

| Key | Label |
|-----|-------|
| `hold` | HOLD FORWARD |
| `reorient_fires` | REORIENT FIRES |
| `commit_reserve` | COMMIT RESERVE |
| `elastic_defense` | ELASTIC DEFENSE |
| `counter_battery` | COUNTER-BATTERY |
| `mass_fires_deep` | STRIKE DEEP |
| `ew_suppress` | EW SUPPRESS |
| `cyber_strike` | CYBER STRIKE |
| `consolidate` | CONSOLIDATE |
| `withdraw` | WITHDRAW LOCALLY |

**Response** → `GameStateOut` (updated state after resolution)

**Errors**
- `404` — game_id not found
- `400` — unknown decision_key
- `409` — game already ended

---

## GET `/game/{game_id}/report`

**Response** → `AAROut` (see below)

---

## Schemas

### `GameStateOut`

```
game_id          str           short UUID, e.g. "cf07214e"
scenario         str           "latgale_2027"
status           str           "running" | "blue_win" | "red_win"
turn             int           current turn number (0-indexed from engine)
turns_total      int           10
blue_force       ForceOut
red_force        ForceOut
objectives       ObjectiveOut[]
map              MapOut
turn_log         TurnRecordOut[]
pending_decision PendingDecisionOut | null   null when game ended
```

### `ForceOut`

```
side             str           "BLUE" | "RED"
combat_power     float         0–100, mean unit strength × 100
units            UnitOut[]
```

### `UnitOut`

```
unit_id          str           e.g. "BLUE-MNV-001-A"
side             str           "BLUE" | "RED"
unit_type        str           "MNV" | "FRS" | "ENB"
position         [row, col]    int[2] — primary 2D map input
strength         float         0.0–1.0
readiness        str           "FULLY_OPERATIONAL" | "DEGRADED" | "SUPPRESSED" | "DESTROYED"
posture          str           "DEFENSIVE" | "OFFENSIVE"
dug_in           bool
```

### `ObjectiveOut`

```
id               str           "OBJ-REZEKNE" | "OBJ-DAUGAVPILS" | "OBJ-KRASLAVA"
name             str           human-readable name
position         [row, col]    int[2] — for map markers
controlled_by    str           "BLUE" | "RED" | "NEUTRAL"
weight           float         victory-point weight
```

### `MapOut`

```
rows             int           16
cols             int           16
km_per_cell      float         5.0
cells            TerrainCellOut[]   sparse — OPEN cells omitted
```

### `TerrainCellOut`

```
row              int
col              int
terrain          str           "FOREST" | "WATER" | "URBAN" | "IMPASSABLE"
```

### `TurnRecordOut`

```
turn             int           turn number this record covers
blue_action      str           label of BLUE decision taken
red_action       str           label of RED response
narrative        str           Claude adjudicator text (stub: plain string)
doctrine_refs    str[]         citation keys, e.g. ["FM 3-90 §3.4"]
blue_cp_after    float         BLUE combat power after resolution
red_cp_after     float         RED combat power after resolution
unit_positions   { unit_id: [row, col] }   full position snapshot — use for map replay
```

### `PendingDecisionOut`

```
turn             int
context          str           situation summary for this decision window
options          DecisionOptionOut[]
```

### `DecisionOptionOut`

```
key              str           decision_key to POST back
label            str           display label
consequence_hint str           one-line effect summary
```

### `AAROut`

```
game_id          str
outcome          str           "running" | "blue_win" | "red_win"
turns_played     int
blue_cp_final    float
red_cp_final     float
objectives_held  str[]         objective IDs controlled by BLUE at game end
turn_log         TurnRecordOut[]
```

---

## 2D Map rendering notes

All position data is `[row, col]` on a **16 × 16 grid at 5 km/cell**.

- `UnitOut.position` — current unit position, updated each turn
- `TurnRecordOut.unit_positions` — full snapshot per turn for replay scrubbing
- `ObjectiveOut.position` — fixed objective marker locations
- `MapOut.cells` — static terrain layer (sparse, send once on game start)

RED starts east (cols 14–15), BLUE starts west (cols 2–4).
Row 0 is north, row 15 is south.
