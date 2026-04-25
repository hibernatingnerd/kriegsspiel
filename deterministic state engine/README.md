# Deterministic State Engine (Simple Overview)

This folder contains the core backend logic for the Kriegsspiel hackathon prototype.

## What was done

- Built a deterministic world-state engine for a grid-based wargame scenario.
- Added strict data models for:
  - terrain cells and terrain grid
  - river crossings
  - units and unit templates
  - objectives and control zones
  - world state identity and timing
- Added invariant validation so invalid world states are rejected early.
- Added a complete Latgale 2027 scenario builder for demo/testing.
- Added tests for model rules and scenario consistency.
- Updated enum and template handling to support the V3 unit library shape.

## Why this matters

- The engine is reproducible: same input gives same result.
- The engine is auditable: world state is fully serializable to JSON.
- The engine is reliable for demos: tests pass and scenario loads correctly.

## Current status

- `test_state.py` passes.
- Scenario build works (`latgale_2027`) with 8 alive units at start.

This is the deterministic "source of truth" layer.  
LLM decisions should propose actions, but this engine should own final state updates.
