# Playstyle Spec v2 — per-age + walling, difficulty-aware, testable

**Goal:** each nation has a *verifiable, unique* per-age and walling doctrine
that (a) stays historically accurate, (b) is competitive (no wasteful/random
play), and (c) scales with AI difficulty — all checkable by the sim farm.

## Design principle: style is fixed, intensity scales with difficulty

The spec stores each nation's doctrine at **full strength (Expert)**. The
engine (`anwDifficultyScale.xs`) scales *execution intensity* by difficulty
and reports it via the `meta.difficulty` probe (`intensity` 25→100). The
validator scales the **expected** band by that same intensity before
comparing to observed probes. So one band per civ covers every difficulty —
no 40×6 duplication, and the check is automatically difficulty-aware.

```
spec (Expert bands)  ──intensity%──►  expected band for this match's difficulty
observed probes      ───────────────►  comp.snapshot / event.age_up / wall.* 
                       compare → PASS / WARN / FAIL
```

Difficulty changes *how completely* a nation executes its doctrine, never
*which* doctrine. A MobileNoWalls civ never grows walls on Expert; a turtle
never drops them on Sandbox.

## Per-civ `claims` additions

```jsonc
"claims": {
  // ... existing whole-game milestones stay (back-compat) ...

  "wall": {                       // REAL values from wall_knob_calibration.py
    "strategy": 0,                // cANWWallStrategy* enum (style — fixed)
    "closure_pct_target": 100,    // Expert closure %; scaled down by difficulty
    "trigger_age": 2,             // first age a wall is laid
    "tier_by_age": {"2":"stone","3":"stone","4":"fortified"},
    "gate_count": 3,
    "towers_every": 8,            // tower interleave (0 = none)
    "chokepoint": false,          // true => segment-at-pinch, not full ring
    "radius": 14
  },

  "per_age": {                    // bands at Expert; validator scales by intensity
    "2": { "ageup_by_ms": [300000, 480000],
           "comp": {"inf":[0.40,0.70], "cav":[0.15,0.45], "art":[0.00,0.15]},
           "primary_unit": "musketeer", "posture": "defensive" },
    "3": { "ageup_by_ms": [600000, 900000],
           "comp": {"inf":[0.35,0.60], "cav":[0.25,0.55], "art":[0.05,0.25]},
           "primary_unit": "uhlan", "posture": "offensive" },
    "4": { "comp": {"inf":[0.35,0.65], "cav":[0.20,0.50], "art":[0.10,0.30]},
           "posture": "offensive" }
  },

  "_calibration": "wall=real(knobs); per_age=intent-seeded → refine via sim-farm"
}
```

### Field provenance (what's grounded vs. to-calibrate)
- **`wall.*`** — emitted verbatim from `tools/ai_design/wall_knob_calibration.py`
  (the actual designed per-nation wall doctrine). Grounded, testable today via
  `wall.closure` / `wall.chokepoint` / `wall.tier` / `wall.gate` probes.
- **`per_age.posture`** — derived from the civ's `military_distance_band` +
  `expects_forward`. Grounded.
- **`per_age.comp` / `ageup_by_ms`** — *intent-seeded* from the leader file's
  per-age `bt*` lean (cav/inf/art bias) and rush/boom classification, then
  **refined by the farm** from clean 1v1 competitive matches. Provisional until
  calibrated; never fabricated-precise.

## How each requirement is met
- **Verifiable** — every field maps to an emitted probe the validator checks.
- **Unique per nation** — `wall` comes from the 40-row knob table; `per_age`
  from each leader's bespoke bias rules.
- **Difficulty-scaling** — `anwDifficultyScale.xs` + intensity-scaled bands.
- **Competitive, not wasteful/random** — bands assert composition *discipline*
  and timing windows; the farm flags civs that drift outside them so we tune.
- **Historically accurate** — bands *encode* the historical doctrine (Frederick
  Age-3 cavalry, British Age-2 stone coastal) as ranges, not prose.

## Rollout
1. Migration adds `wall` (real) + `per_age` (skeleton) to all 40 civs.
2. Validator reads `per_age`/`wall`, scales by `meta.difficulty` intensity.
3. Sim farm runs clean seeded 1v1s per difficulty → tightens `per_age` bands
   from observed distributions. Spec ⇄ farm refine each other.
