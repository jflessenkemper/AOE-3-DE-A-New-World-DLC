# XS Sim Interpreter Coverage — Measurement Pass
<!-- Generated 2026-06-08 — read-only measurement pass, NO code changes -->

## (a) Implemented vs Missing Builtins

### Currently Implemented (54 total)
Source: `tools/xs_sim/builtins.py` BUILTINS dict + wildcard recorders

| Group | Functions |
|-------|-----------|
| XS array stdlib (13) | `xsArrayCreate{Int,Float,Bool,String}`, `xsArray{Set,Get}{Int,Float,Bool,String}`, `xsArrayGetSize` |
| Rule control (7) | `xsEnableRule`, `xsDisableRule`, `xsEnableSelf`, `xsDisableSelf`, `xsSetRuleMinIntervalSelf`, `xsGetTime`, `xsGetTimeSec` |
| Math (8) | `sqrt`, `abs`, `min`, `max`, `floor`, `ceil`, `sin`, `cos` |
| Echo/chat (6) | `aiEcho`, `aiChat`, `aiChatToAll`, `aiChatToAllies`, `aiChatToPlayer`, `xsChatData` |
| kb queries (7) | `kbGetAge`, `kbGetCiv`, `kbGetCivName`, `kbGetPlayerID`, `kbGetPop`, `kbGetPopCap`, `kbResourceGet` |
| Revolution | `civIsRevolution` |
| ai queries (3) | `aiGetMilitaryUnitCount`, `aiGetEconomyUnitCount`, `aiGetWorldDifficulty` |
| Action recorders (9) | `aiTaskUnitWork`, `aiTaskUnitMove`, `aiTaskUnitBuild`, `aiTaskUnitGather`, `aiPlanCreate`, `aiPlanDestroy`, `aiPlanSetActive`, `aiCommandUnit`, `aiTrainUnit` |

### Missing Builtins — Ranked by Call Frequency (top 40 of 390 total)

Scanned 66 files under `game/ai/**/*.xs`. "Files" = unique .xs files that call it.

| Rank | Count | Files | Name |
|------|-------|-------|------|
| 1 | 578 | 20 | `kbUnitCount` |
| 2 | 458 | 20 | `aiPlanSetVariableInt` |
| 3 | 292 | 11 | `kbTechGetStatus` |
| 4 | 222 | 23 | `kbUnitQueryExecute` |
| 5 | 214 | 25 | `kbBaseGetMainID` |
| 6 | 189 | 15 | `aiPlanAddUnitType` |
| 7 | 178 | 22 | `kbUnitQueryGetResult` |
| 8 | 173 | 14 | `aiPlanSetVariableFloat` |
| 9 | 155 | 3 | `kbUnitPickSetPreferenceFactor` |
| 10 | 145 | 23 | `kbUnitGetPosition` |
| 11 | 145 | 18 | `aiPlanSetDesiredPriority` |
| 12 | 135 | 23 | `kbBaseGetLocation` |
| 13 | 134 | 16 | `kbAreaGroupGetIDByPosition` |
| 14 | 132 | 16 | `aiPlanSetVariableVector` |
| 15 | 102 | 14 | `aiRandInt` |
| 16 | 97 | 19 | `kbGetBuildLimit` |
| 17 | 90 | 12 | `aiPlanGetIDByTypeAndVariableType` |
| 18 | 72 | 12 | `aiPlanGetVariableInt` |
| 19 | 72 | 8 | `kbUnitCostPerResource` |
| 20 | 69 | 8 | `kbUnitQuerySetUnitType` |
| 21 | 65 | 6 | `kbGetTechName` |
| 22 | 63 | 14 | `aiPlanSetVariableBool` |
| 23 | 59 | 7 | `kbUnitQueryResetResults` |
| 24 | 58 | 10 | `aiPlanGetActive` |
| 25 | 57 | 14 | `kbUnitGetProtoUnitID` |
| 26 | 55 | 10 | `aiPlanSetDesiredResourcePriority` |
| 27 | 54 | 3 | `kbGetProtoUnitID` |
| 28 | 53 | 8 | `kbUnitQueryCreate` |
| 29 | 51 | 13 | `kbAreaGetIDByPosition` |
| 30 | 50 | 15 | `aiPlanSetBaseID` |
| 31 | 41 | 9 | `xsVectorGetX` |
| 32 | 40 | 9 | `aiPlanGetState` |
| 33 | 39 | 9 | `xsVectorGetZ` |
| 34 | 36 | 9 | `kbAreAreaGroupsPassableByLand` |
| 35 | 30 | 6 | `xsIsRuleEnabled` |
| 36 | 30 | 7 | `kbGetMapXSize` |
| 37 | 28 | 9 | `xsVectorSet` |
| 38 | 27 | 6 | `kbAreaGetType` |
| 39 | 24 | 8 | `xsVectorNormalize` |
| 40 | 23 | 7 | `kbAreaGetCenter` |

Full list of all 390 missing builtins available via the scan script used to generate this doc.

### Critical Missing: `xsVector*` Family
These 8 vector functions are missing and called 147 times across 9 files — every wall strategy path uses them:

| Count | Name |
|-------|------|
| 41 | `xsVectorGetX` |
| 39 | `xsVectorGetZ` |
| 28 | `xsVectorSet` |
| 24 | `xsVectorNormalize` |
| 12 | `xsVectorLength` |
| 10 | `xsVectorGetY` |
| 4 | `xsVectorSetX` |
| 2 | `xsVectorSetZ` |

---

## (b) Interpreter Behaviour on Unknown Builtins

Source: `tools/xs_sim/builtins.py:229-236`, `tools/xs_sim/interpreter.py:84`

**Behaviour: warn-once + return typed zero. Does NOT throw.**

```python
# builtins.py:229-236
def call_builtin(name: str, args: list, gs: GameState, interp) -> Any:
    fn = BUILTINS.get(name)
    if fn is not None:
        return fn(args, gs, interp)
    # Unknown — record and return zero. Track once so output isn't spammed.
    interp.unknown_calls.setdefault(name, 0)
    interp.unknown_calls[name] += 1
    return _zero_for(name)   # 0, False, or "" based on name prefix
```

`_zero_for` heuristics (`builtins.py:22-31`):
- Names starting with `kbget/aiget/xsget` → `0` or `""` if "name"/"string" in name
- Names starting with `kbis/aiis/kbcan/aican/xsis` → `False`
- Everything else → `0`

This means:
- `kbAreaGetIDByPosition(pos)` → returns `0` (treated as area ID 0)
- `kbAreaGetType(0)` → returns `0` (could be `cAreaTypeLand` if that constant = 0)
- `kbAreaGetNumberBorderAreas(0)` → returns `0` (no borders → fallback path taken)
- `kbBaseGetMainID(cMyID)` → returns `0` (treated as base ID 0)
- `kbBaseGetLocation(cMyID, 0)` → returns `0` (integer, not vector — type mismatch)

**The type-zero return for vector-returning builtins is the most dangerous gap**: `kbBaseGetLocation` returns `0` (int) but the XS code assigns it to a `vector`. When that `0` is later passed to `xsVectorGetX(0)`, the interpreter hits `_eval(e.operand=0)` as a literal int and then tries vector arithmetic like `0 + shift * direction` → `TypeError: '<' not supported between instances of 'tuple' and 'int'`. This is the first actual runtime crash seen (confirmed via live probe, see §d).

---

## (c) kbArea / cAreaType Mock Plan

### Current State

| Function | In builtins.py? | In gamestate.py? | Notes |
|----------|-----------------|------------------|-------|
| `kbAreaGetIDByPosition(vec)` | NO (unknown → 0) | NO | Key entry point for all wall logic |
| `kbAreaGetType(areaID)` | NO (unknown → 0) | NO | Used 27× in 6 files |
| `kbAreaGetCenter(areaID)` | NO (unknown → 0) | NO | Returns vector; used 23× in 7 files |
| `kbAreaGetNumberTiles(areaID)` | NO (unknown → 0) | NO | Used 10× in 4 files |
| `kbAreaGetNumberBorderAreas(areaID)` | NO (unknown → 0) | NO | Used 11× in 5 files |
| `kbAreaGetBorderAreaID(areaID, idx)` | NO (unknown → 0) | NO | Used 11× in 5 files |
| `kbBaseGetMainID(playerID)` | NO (unknown → 0) | NO | Used 214× in 25 files |
| `kbBaseGetLocation(playerID, baseID)` | NO (unknown → 0) | NO | Used 135× in 23 files; returns vector |
| `kbBaseGetFrontVector(playerID, baseID)` | NO (unknown → 0) | NO | Returns vector |
| `cAreaTypeWater` | NOT in BUILTINS but treated as c-prefix const → `0` | NO | XS code uses `cAreaTypeWater` as constant; interp resolves `c`+upper → 0 |
| `cAreaTypeImpassableLand` | same → `0` | NO | 1 usage |
| `cAreaTypeLand` | same → `0` | NO | 1 usage |

**Key observation**: `cAreaTypeWater` is referenced as an identifier, not called as a function. The interpreter handles it at `interpreter.py:294`: names starting with `c` + uppercase → silently returns `0`. This means `cAreaTypeWater == 0` in the sim currently. If the actual game value is also 0, checks like `areaType == cAreaTypeWater` may accidentally pass. This needs an explicit constant assignment in `_DEFAULT_CONSTS`.

### Minimal Area-Graph Model

To make `anwDetectChokepointVector` and `anwDetectCoastVector` execute deterministically, `GameState` needs a flat area map:

```python
# Proposed addition to gamestate.py

@dataclass
class AreaInfo:
    area_id: int
    area_type: int          # 0=land, 1=water, 2=impassable, 3=cliff
    center: tuple           # (x, y, z) vector
    num_tiles: int
    border_area_ids: list   # list of ints

@dataclass  
class GameState:
    # ... existing fields ...
    
    # Area graph: dict[area_id -> AreaInfo]
    areas: dict = field(default_factory=dict)
    
    # Base info: dict[base_id -> (player_id, location_vector, front_vector)]
    bases: dict = field(default_factory=dict)
    
    # Map dimensions
    map_x_size: int = 256
    map_z_size: int = 256
```

The simplest deterministic fixture for wall-strategy testing:

```python
def scenario_coastal_with_area_graph() -> GameState:
    gs = scenario_coastal_age2()
    # Area 1: main land base
    gs.areas[1] = AreaInfo(1, 0, (100.0, 0.0, 100.0), 500, [2, 3])
    # Area 2: water to the north
    gs.areas[2] = AreaInfo(2, 1, (100.0, 0.0, 170.0), 200, [1])
    # Area 3: narrow choke pass to east
    gs.areas[3] = AreaInfo(3, 0, (160.0, 0.0, 100.0), 80, [1, 4])
    # Area 4: enemy side
    gs.areas[4] = AreaInfo(4, 0, (220.0, 0.0, 100.0), 400, [3])
    # Base 1: player 1 at area 1
    gs.bases[1] = {"player_id": 1, "location": (100.0, 0.0, 100.0), 
                   "front_vector": (1.0, 0.0, 0.0), "main": True}
    return gs
```

### Required builtins.py additions for wall-strategy sim

```python
def _kbAreaGetIDByPosition(args, gs, interp):
    pos = args[0]  # (x, y, z) tuple
    if not isinstance(pos, tuple) or not gs.areas:
        return -1
    # Find closest area center
    best_id, best_dist = -1, float('inf')
    for aid, info in gs.areas.items():
        dx = pos[0] - info.center[0]; dz = pos[2] - info.center[2]
        d = (dx*dx + dz*dz) ** 0.5
        if d < best_dist:
            best_dist, best_id = d, aid
    return best_id

def _kbAreaGetType(args, gs, interp):
    aid = int(args[0])
    info = gs.areas.get(aid)
    return info.area_type if info else 0

def _kbAreaGetCenter(args, gs, interp):
    aid = int(args[0])
    info = gs.areas.get(aid)
    return info.center if info else (0.0, 0.0, 0.0)

def _kbAreaGetNumberTiles(args, gs, interp):
    aid = int(args[0])
    info = gs.areas.get(aid)
    return info.num_tiles if info else 0

def _kbAreaGetNumberBorderAreas(args, gs, interp):
    aid = int(args[0])
    info = gs.areas.get(aid)
    return len(info.border_area_ids) if info else 0

def _kbAreaGetBorderAreaID(args, gs, interp):
    aid, idx = int(args[0]), int(args[1])
    info = gs.areas.get(aid)
    if info and 0 <= idx < len(info.border_area_ids):
        return info.border_area_ids[idx]
    return -1

def _kbBaseGetMainID(args, gs, interp):
    # args[0] = playerID
    for bid, b in gs.bases.items():
        if b.get("main"): return bid
    return 1  # fallback

def _kbBaseGetLocation(args, gs, interp):
    bid = int(args[1]) if len(args) > 1 else 1
    b = gs.bases.get(bid)
    return b["location"] if b else (0.0, 0.0, 0.0)

def _kbBaseGetFrontVector(args, gs, interp):
    bid = int(args[1]) if len(args) > 1 else 1
    b = gs.bases.get(bid)
    return b["front_vector"] if b else (0.0, 0.0, 0.0)
```

Also required in `_DEFAULT_CONSTS` (`interpreter.py:43-48`):
```python
"cAreaTypeWater": 1,        # confirm against engine — currently resolves to 0 via c-prefix fallback
"cAreaTypeImpassableLand": 2,
"cAreaTypeLand": 0,
"cAreaTypeCliff": 3,
"cInvalidVector": (-1.0, -1.0, -1.0),
```

And all `xsVector*` stdlib functions need implementing (8 functions, ~20 lines total):
```python
"xsVectorGetX": lambda a, gs, i: float(a[0][0]) if isinstance(a[0], tuple) else 0.0,
"xsVectorGetY": lambda a, gs, i: float(a[0][1]) if isinstance(a[0], tuple) else 0.0,
"xsVectorGetZ": lambda a, gs, i: float(a[0][2]) if isinstance(a[0], tuple) else 0.0,
"xsVectorSet":  lambda a, gs, i: (float(a[0]), float(a[1]), float(a[2])),
"xsVectorLength": lambda a, gs, i: (a[0][0]**2 + a[0][1]**2 + a[0][2]**2)**0.5 if isinstance(a[0], tuple) else 0.0,
# xsVectorNormalize, xsVectorSetX, xsVectorSetZ similarly
```

---

## (d) First Runtime Errors Observed

### Error 1 — TypeError in `_binop` when vector-returning unknown returns `0`
**File**: `interpreter.py:392`  
**Trigger**: `anwDetectChokepointVector(baseCenter=(-1.0,-1.0,-1.0), mainBaseID=-1)` after `kbBaseGetLocation` returns `0` and that `0` is placed in a vector variable, then compared with `cInvalidVector` tuple via `<`.  

```
TypeError: '<' not supported between instances of 'tuple' and 'int'
  File interpreter.py:335 _eval -> _binop
  File interpreter.py:392: if op == "<": return a < b
```

The comparison is actually `(baseCenter == cInvalidVector)` which is an equality check (`==`), not `<`. The `<` crash occurs in `anwGetForwardBiasedWallCenter` when `frontVec` (returned as `0` by missing `kbBaseGetFrontVector`) is compared numerically with a float in the biasing arithmetic.

**Root cause**: `kbBaseGetFrontVector` → `_zero_for` → returns `0` (int). The XS code then does `xsVectorGetX(frontVec) == 0.0` which passes through unknown `xsVectorGetX` → returns `0` (int). Then the next comparison `xsVectorGetZ(frontVec) == 0.0` also returns `0`, and short-circuit `||` proceeds into vector arithmetic on the raw `0` integer.

### Error 2 — Silent wrong logic: `cAreaTypeWater == 0` collision
**Files**: `aiBuildingsWalls.xs` many lines, e.g. line 278.  
When `cAreaTypeWater` resolves to `0` (via the c-prefix fallback in `interpreter.py:294`) AND `kbAreaGetType` also returns `0` (unknown builtin → `_zero_for` → `0`), the check `areaType == cAreaTypeWater` evaluates `0 == 0` → `True`. This makes every area look like water, causing every call to `anwGetForwardBiasedWallCenter` to enter the inland-correction loop and fall back to `baseCenter`. The function still returns a value (no crash), but the logic is wrong.

**Current behaviour during live probe**: `anwDetectChokepointVector(1, (100.0, 0.0, 100.0))` returns `(100.0, 0.0, 100.0)` (the fallback path) every time because `kbAreaGetIDByPosition` → `0`, `kbAreaGetNumberBorderAreas(0)` → `0`, so the "no borders" path is immediately taken. No crash, but no real chokepoint detection.

### Error 3 — `interp.echo` AttributeError in throwaway test scripts
**Not in interpreter itself** — `Interpreter` has no `.echo` attribute; echo lives on `gs.echo`. Cosmetic scripting mistake, not a real interpreter bug. Cite: `interpreter.py` (no `self.echo`) vs `gamestate.py:67` (`def log_echo`).

---

## (e) Recommended Fix Order

Priority ordered for reaching "wall-strategy code executes deterministically":

### P0 — Blocking: xsVector* stdlib (8 functions)
**Impact**: 147 calls, 9 files. Every wall-strategy path crashes or silently misbehaves.  
**Effort**: ~20 lines in `builtins.py`. Pure math on Python tuples.  
**Files to change**: `tools/xs_sim/builtins.py` BUILTINS dict.

### P1 — Blocking: cAreaType* constants and cInvalidVector in _DEFAULT_CONSTS
**Impact**: Fixes the `cAreaTypeWater==0` collision that makes all areas appear as water.  
**Effort**: 5 lines in `interpreter.py:_DEFAULT_CONSTS`.  
**Files to change**: `tools/xs_sim/interpreter.py`.

### P2 — Blocking: kbArea* family (6 functions) + AreaInfo model in GameState
**Impact**: The 6 kbArea functions called directly by `anwDetectChokepointVector` / `anwDetectCoastVector`. Without them the chokepoint and coast detectors always take the "no borders" fallback.  
**Effort**: ~60 lines: `AreaInfo` dataclass + `areas` dict + scenario builder in `gamestate.py`, 6 mock functions in `builtins.py`.  
**Files to change**: `tools/xs_sim/gamestate.py`, `tools/xs_sim/builtins.py`.

### P3 — High value: kbBase* family (kbBaseGetMainID, kbBaseGetLocation, kbBaseGetFrontVector)
**Impact**: Called 214/135/4 times across 25/23/4 files. Without these, `baseCenter` is always `0` (not a vector), causing the TypeError in `_binop`.  
**Effort**: ~20 lines. Read from `gs.bases` dict.  
**Files to change**: `tools/xs_sim/builtins.py`, `tools/xs_sim/gamestate.py` (add `bases` field).

### P4 — Broad coverage: aiPlan* action recorders (top missing: aiPlanSetVariableInt, aiPlanSetVariableFloat, aiPlanSetVariableVector, aiPlanAddUnitType, aiPlanSetDesiredPriority, aiPlanSetBaseID, aiPlanSetVariableBool)
**Impact**: 458+173+132+189+145+50+63 = 1210 calls across 14-20 files. These are action verbs, so returning `0` is acceptable for doctrine-only tests. However `aiPlanGetIDByTypeAndVariableType` (90 calls, 12 files) and `aiPlanGetActive` (58 calls) are query functions whose `0` return drives real branching in wall planners.  
**Effort**: ~30 lines. Add as `_record(name)` wildcard recorders (same pattern as existing `aiPlanCreate`/`aiPlanDestroy`); add query stubs that return configurable defaults from GameState.  
**Files to change**: `tools/xs_sim/builtins.py`.

### P5 — Noise reduction: kbUnitCount, kbTechGetStatus, kbUnitQuery* family
**Impact**: 578+292+222 = 1092 calls. These drive military-unit-count branching and tech-tree gates in nearly all leader files. Current `0` return causes all "if unit count > X" checks to fail, suppressing military plan activation.  
**Effort**: Medium. `kbUnitCount` reads from `gs.counts`. `kbTechGetStatus` needs a `gs.researched_techs` set. `kbUnitQuery*` needs a query-result store.  
**Files to change**: `tools/xs_sim/gamestate.py`, `tools/xs_sim/builtins.py`.

### P6 — Math completeness: aiRandInt, aiRandFloat, kbGetMapXSize, kbIsPlayerAlly, xsIsRuleEnabled
These are low-effort additions (2-5 lines each) that unblock specific rules in `core/*.xs`.

---

## Summary Table

| Step | Effort | Unblocks |
|------|--------|----------|
| P0: xsVector* (8 fns) | ~20 lines | Wall center computation; no more TypeError |
| P1: cAreaType* constants | 5 lines | Correct water/land type checks |
| P2: kbArea* (6 fns) + AreaInfo | ~60 lines | Real chokepoint/coast detection |
| P3: kbBase* (3 fns) + bases dict | ~20 lines | Valid baseCenter vector everywhere |
| P4: aiPlan* recorders + query stubs | ~30 lines | Wall plan creation visible in actions log |
| P5: kbUnitCount + kbTechGetStatus + kbUnitQuery* | ~80 lines | Military branching in leader rules |
| P6: aiRandInt, xsIsRuleEnabled, etc. | ~30 lines | Remaining noise builtins |

After P0–P3 (est. ~105 lines of new code), `anwDetectChokepointVector` and `anwDetectCoastVector` will execute their real logic paths deterministically on a fixture `GameState` with an area graph, producing a testable non-fallback chokepoint vector.
