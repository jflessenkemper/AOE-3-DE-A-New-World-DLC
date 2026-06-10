# State Civs Playstyle Spec Gap

**Date:** 2026-06-08  
**Scope:** Read-only audit. playstyle_spec.json, .xs, and .py data files were NOT modified.  
**Validator failing:** `tools/validation/validate_per_civ_wall_knobs.py` — 4 civs in `CALIB_TO_SPEC` map have no matching key in `playstyle_spec.json`.

---

## A. playstyle_spec.json Schema

**File:** `/var/home/jflessenkemper/AOE-3-DE-A-New-World/playstyle_spec.json`  
Top-level shape (lines 1–4):
```json
{
  "schema_version": 1,
  "source": "a_new_world.html",
  "civs": { "<spec_key>": <civ_entry>, ... }
}
```

### Per-civ entry shape (derived from 3 existing entries: Argentines San Martin Revolution lines 5–146, Barbary Barbarossa Corsair Revolution lines 292–440, Californians Vallejo Revolution lines 1014–1152)

```
<spec_key>          string — JSON object key; convention = "<CivDisplayName> <Leader> Revolution"
                             or base-civ equivalent
civ_label           string — short display name (e.g. "Californians")
leader_label        string — full leader name (e.g. "Mariano Vallejo")
data_name           string — must equal the spec_key exactly
doctrine_label      string — short doctrine name shown in UI
doctrine_summary    string — one-line description
portrait_path       string — relative path to portrait PNG
doctrine_prose      string — multi-sentence flavour text (HTML-entity safe)
claims              object — all validator-checked fields:
  wall_strategy       int 0–5 (see enum below) — MUST match calibration.py strategy
  first_military_building   string enum: "barracks_or_stable" | "dock"
  expects_forward     bool   (optional — omit if false)
  expects_cavalry     bool   (optional)
  expects_infantry    bool   (optional)
  expects_naval       bool   (optional)
  first_barracks_before_ms  int (ms) — optional
  first_wall_before_ms      int (ms) — 0 = never; omit or set to non-zero for wall civs
  first_dock_before_ms      int (ms) — optional, naval civs only
  military_distance_band    [float, float] — [min, max] multipliers on base distance
  wall                object:
    strategy            int 0–5 — MUST equal claims.wall_strategy
    closure_pct_target  int 0–100 — 0 for MobileNoWalls, 100 for all others
    trigger_age         int 2–5 — 5 = never build walls
    tier_by_age         object {age_str: tier_str} — empty {} for MobileNoWalls
                        tier_str values seen: "palisade" | "stone" | "fortified"
    gate_count          int 0–5 — 0 for MobileNoWalls
    towers_every        int 0–8 — 0 for MobileNoWalls
    chokepoint          bool — true only for strategy=1 (ChokepointSegments)
    radius              int 0–28 — 0 for MobileNoWalls
  per_age             object keyed "1".."5":
    age "1" only:
      comp              {inf:[lo,hi], cav:[lo,hi], art:[lo,hi]}  float fractions
      posture           string "offensive" | "defensive" | "mixed"
      note              string (optional, usually "Discovery — economy / scouting")
      _source           string
    ages "2".."5" additionally have:
      ageup_by_ms       [int, int]  — [earliest, latest] age-up window
  _calibration        string — always "wall=real(knobs); per_age=derived from wired btBias values"
prose_overrides       array — always [] for these civs
```

### Wall strategy enum (source: `game/ai/aiHeader.xs` lines 202–207, also cited in `wall_strategy_gap.md` §1)

| Value | Name | Meaning |
|-------|------|---------|
| 0 | FortressRing | Full double ring, all sides, dense perimeter |
| 1 | ChokepointSegments | Segments only at terrain pinches |
| 2 | CoastalBatteries | Land-side ring + gun towers facing coast |
| 3 | FrontierPalisades | Quick wooden ring, more gates, low stone |
| 4 | UrbanBarricade | Tight compact inner ring + dense towers |
| 5 | MobileNoWalls | No perimeter — scouts + outposts only |

---

## B. Wall-Knob Calibration for the 4 State Civs

Source: `tools/ai_design/wall_knob_calibration.py` lines 114–141.  
All 4 entries are present and complete in the Python table. The XS has not been re-emitted (noted in `wall_strategy_gap.md` §3).

| Knob | ANWCalifornians | ANWCentralAmericans | ANWBajaCalifornians | ANWRioGrande |
|------|----------------|---------------------|---------------------|--------------|
| strategy | **5** (MobileNoWalls) | **3** (FrontierPalisades) | **2** (CoastalBatteries) | **3** (FrontierPalisades) |
| radius | 0 | 18 | 16 | 18 |
| gates | 0 | 3 | 2 | 3 |
| age2stone | 0 (false) | 0 (false) | 0 (false) | 0 (false) |
| trigger_age | 5 (never) | 2 | 2 | 2 |
| seg_len | 0 | 20 | 20 | 20 |
| towers | 0 | 4 | 4 | 3 |
| secondary | 2 | 1 | 1 | 5 |
| vils | 0 | 5 | 4 | 5 |
| fwd_bias | 0.0 | 0.4 | 0.3 | 0.5 |
| outer_ring | 0 | 4 | 4 | 4 |
| outposts | 4 | 3 | 3 | 4 |
| repair | 0 | 3 | 3 | 3 |
| closure_pct | 0 | 100 | 100 | 100 |
| no_water | 1 (true) | 1 (true) | 1 (true) | 1 (true) |
| doctrine (comment) | "Californio rancho cavalry — vaqueros & lancers, mobile raiding, coastal fallback" | "Federalist militia frontier palisade, cordillera-pass chokepoint fallback" | "Desert-coast guerrilla coastal defense, chokepoint ambush fallback" | "Northern-frontier federalist cavalry, raid-and-retreat, mobile fallback" |

Also confirmed by `leader_revolution_commanders.xs` explicit `gANWWallStrategy` assignments:
- **ANWCalifornians**: line 167 — `gANWWallStrategy = cANWWallStrategyMobileNoWalls;` (strategy 5) ✓
- **ANWBajaCalifornians**: line 104 — `gANWWallStrategy = cANWWallStrategyCoastalBatteries;` (strategy 2) ✓
- **ANWCentralAmericans**: line 189 — `gANWWallStrategy = cANWWallStrategyFrontierPalisades;` (strategy 3) ✓
- **ANWRioGrande**: line 498 — `gANWWallStrategy = cANWWallStrategyFrontierPalisades;` (strategy 3) ✓

Also confirmed by existing `playstyle_spec.json` entries (already present at correct keys):
- `"Californians Vallejo Revolution"` line 1014 → `wall_strategy: 5` ✓
- `"Baja Californians Alvarado Revolution"` line 870 → `wall_strategy: 2` ✓
- `"Central Americans Morazan Revolution"` line 1154 → `wall_strategy: 3` ✓
- `"Rio Grande Canales Revolution"` line 1298 → `wall_strategy: 3` ✓

---

## C. Root Cause of the 4 Validator Failures

The validator (`validate_per_civ_wall_knobs.py` lines 122–182) uses `CALIB_TO_SPEC` to cross-check each calibration token against a playstyle_spec key. The **4 state civ tokens are absent from `CALIB_TO_SPEC`** — they were added to `CALIBRATION` in `wall_knob_calibration.py` after the CALIB_TO_SPEC map was last updated.

When `CALIB_TO_SPEC.get(civ_token)` returns `None`, the validator records a `spec_mismatch` with:
```
expected: "<spec key for ANWCalifornians not found>"
actual:   5
```
This causes `FAIL` even though the spec entries already exist in `playstyle_spec.json` with the correct wall_strategy values.

**The spec JSON already has all 4 entries with correct wall strategies.** No edit to `playstyle_spec.json` is needed. Only `CALIB_TO_SPEC` in the validator needs 4 new lines. The proposed entries below are provided for completeness and human review of the full spec shape.

---

## D. Proposed playstyle_spec.json Entries (Complete — Ready to Paste)

These are based entirely on data already present in `playstyle_spec.json` (the existing entries at those keys), `wall_knob_calibration.py`, and `leader_revolution_commanders.xs`. All fields are **derived** unless marked **[GUESSED — needs review]**.

### Field derivation key

| Field | Derivation |
|-------|-----------|
| `wall_strategy`, `wall.*` | Derived from `wall_knob_calibration.py` CALIBRATION rows (lines 114–141) + `leader_revolution_commanders.xs` gANWWallStrategy assignments |
| `civ_label`, `leader_label`, `data_name`, `doctrine_label`, `doctrine_summary`, `portrait_path`, `doctrine_prose`, `claims.*_before_ms`, `military_distance_band`, `per_age` | Derived: all already exist in `playstyle_spec.json` at the correct spec keys (lines 870–1441). These entries can be copy-confirmed directly from the spec file. |
| `first_wall_before_ms` for MobileNoWalls | Set to 0 per pattern of all strategy=5 civs in spec (e.g. Californians Vallejo line 1025: `"first_wall_before_ms": 0`) |

---

### 1. ANWCalifornians → spec key `"Californians Vallejo Revolution"`

**Status: ALREADY IN SPEC at line 1014.** Entry is complete and correct.  
The validator just needs `CALIB_TO_SPEC["ANWCalifornians"] = "Californians Vallejo Revolution"`.

Confirmation (playstyle_spec.json line 1023): `"wall_strategy": 5` — matches calibration.py line 115 `strategy=5`.

Complete entry for reference (paste-ready):
```json
"Californians Vallejo Revolution": {
 "civ_label": "Californians",
 "leader_label": "Mariano Vallejo",
 "data_name": "Californians Vallejo Revolution",
 "doctrine_label": "Mobile Frontier Scatter",
 "doctrine_summary": "Wall-less cavalry swarm",
 "portrait_path": "resources/images/icons/singleplayer/cpai_avatar_mexicans_iturbide.png",
 "doctrine_prose": "Builds no walls at all. Spreads production wide, lives off trade and the map, and answers every threat with mounted mobility — hit-and-run cavalry that refuses to be pinned to a static line.",
 "claims": {
  "wall_strategy": 5,
  "first_military_building": "barracks_or_stable",
  "first_wall_before_ms": 0,
  "military_distance_band": [0.9, 1.3],
  "first_barracks_before_ms": 510000,
  "wall": {
   "strategy": 5, "closure_pct_target": 0, "trigger_age": 5,
   "tier_by_age": {}, "gate_count": 0, "towers_every": 0,
   "chokepoint": false, "radius": 0
  },
  "per_age": { ... }
 },
 "prose_overrides": []
}
```
> Full per_age block: copy from playstyle_spec.json lines 1041–1151 verbatim — already present and correct.

---

### 2. ANWCentralAmericans → spec key `"Central Americans Morazan Revolution"`

**Status: ALREADY IN SPEC at line 1154.** Entry is complete and correct.  
The validator just needs `CALIB_TO_SPEC["ANWCentralAmericans"] = "Central Americans Morazan Revolution"`.

Confirmation (playstyle_spec.json line 1163): `"wall_strategy": 3` — matches calibration.py line 122 `strategy=3`.

Key wall fields (derived from calibration.py lines 121–126 + spec lines 1171–1184):
```json
"wall": {
 "strategy": 3, "closure_pct_target": 100, "trigger_age": 2,
 "tier_by_age": {"2": "palisade", "3": "palisade", "4": "stone"},
 "gate_count": 3, "towers_every": 4, "chokepoint": false, "radius": 18
}
```
> Full entry: copy from playstyle_spec.json lines 1154–1297 verbatim.

---

### 3. ANWBajaCalifornians → spec key `"Baja Californians Alvarado Revolution"`

**Status: ALREADY IN SPEC at line 870.** Entry is complete and correct.  
The validator just needs `CALIB_TO_SPEC["ANWBajaCalifornians"] = "Baja Californians Alvarado Revolution"`.

Confirmation (playstyle_spec.json line 879): `"wall_strategy": 2` — matches calibration.py line 129 `strategy=2`.

Key wall fields (derived from calibration.py lines 128–133 + spec lines 887–900):
```json
"wall": {
 "strategy": 2, "closure_pct_target": 100, "trigger_age": 2,
 "tier_by_age": {"2": "palisade", "3": "stone", "4": "fortified"},
 "gate_count": 2, "towers_every": 4, "chokepoint": false, "radius": 16
}
```
> Full entry: copy from playstyle_spec.json lines 870–1013 verbatim.

---

### 4. ANWRioGrande → spec key `"Rio Grande Canales Revolution"`

**Status: ALREADY IN SPEC at line 1298.** Entry is complete and correct.  
The validator just needs `CALIB_TO_SPEC["ANWRioGrande"] = "Rio Grande Canales Revolution"`.

Confirmation (playstyle_spec.json line 1307): `"wall_strategy": 3` — matches calibration.py line 136 `strategy=3`.

Key wall fields (derived from calibration.py lines 135–140 + spec lines 1315–1328):
```json
"wall": {
 "strategy": 3, "closure_pct_target": 100, "trigger_age": 2,
 "tier_by_age": {"2": "palisade", "3": "palisade", "4": "stone"},
 "gate_count": 3, "towers_every": 4, "chokepoint": false, "radius": 18
}
```
> Full entry: copy from playstyle_spec.json lines 1298–1441 verbatim.

---

## E. Action Required (Validator Fix Only)

**No edit to `playstyle_spec.json` is needed.** All 4 entries exist with correct values.

The only fix needed is adding 4 lines to `CALIB_TO_SPEC` in `tools/validation/validate_per_civ_wall_knobs.py` (after line 182):

```python
"ANWCalifornians":       "Californians Vallejo Revolution",
"ANWCentralAmericans":   "Central Americans Morazan Revolution",
"ANWBajaCalifornians":   "Baja Californians Alvarado Revolution",
"ANWRioGrande":          "Rio Grande Canales Revolution",
```

After adding those 4 lines, also re-emit the XS (per `wall_strategy_gap.md` §8 action 1) to make the calibration runtime match:
```
python3 tools/ai_design/wall_knob_calibration.py --emit-xs > game/ai/core/aiWallKnobsByCiv.xs
```

Then re-run: `python3 -m tools.validation.validate_per_civ_wall_knobs` — should pass 44 civs.

---

## F. File References

| File | Purpose | Key Lines |
|------|---------|-----------|
| `/var/home/jflessenkemper/AOE-3-DE-A-New-World/playstyle_spec.json` | Spec — 4 entries already present | 870, 1014, 1154, 1298 |
| `/var/home/jflessenkemper/AOE-3-DE-A-New-World/tools/ai_design/wall_knob_calibration.py` | Source of truth for knob values | 114–141 (4 state civ entries) |
| `/var/home/jflessenkemper/AOE-3-DE-A-New-World/game/ai/leaders/leader_revolution_commanders.xs` | gANWWallStrategy explicit assignments | 104, 167, 189, 498 |
| `/var/home/jflessenkemper/AOE-3-DE-A-New-World/tools/validation/validate_per_civ_wall_knobs.py` | Validator — needs 4 CALIB_TO_SPEC entries | 122–182 (CALIB_TO_SPEC map) |
| `/var/home/jflessenkemper/AOE-3-DE-A-New-World/game/ai/aiHeader.xs` | Wall strategy enum definition | 202–207 |
| `/var/home/jflessenkemper/AOE-3-DE-A-New-World/.llm/release_program/wall_strategy_gap.md` | Prior gap audit, XS re-emit instructions | §3, §8 |
