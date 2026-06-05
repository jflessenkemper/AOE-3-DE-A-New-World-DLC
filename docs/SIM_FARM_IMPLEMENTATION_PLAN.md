# ANW AI Simulation Farm — One-Shot Implementation Plan

**Status:** Implementation-ready. All load-bearing unknowns resolved by
binary RE + artifact inspection (2026-06-04). This doc is self-contained:
an implementation pass should not need to re-research anything.

**Goal:** A deterministic, scalable **AI-vs-AI simulation farm** that gives
*absolute certainty of how the ANW AI plays* across maps, player-counts,
and matchups — by driving and instrumenting the **real engine** (the only
faithful simulator), never by reimplementing it.

**Success criteria (Definition of Done):**
1. One command runs a sweep over a configurable matrix (civ × map ×
   opponent-slate × player-count × seed × difficulty) and produces a
   structured dataset + per-civ PASS/WARN/FAIL release report.
2. **Determinism proven:** the same seed re-run yields an identical probe
   stream (and identical replay), verified automatically.
3. Runs unattended (offscreen via gamescope), survives crashes, and scales
   horizontally (N parallel instances).

---

## 0. Ground truth (verified this session — do not re-derive)

| Fact | Evidence | Implication |
|---|---|---|
| Engine is **deterministic lockstep** | replay system + desync threads | seeded match ⇒ bit-identical; farm is rigorous, not approximate |
| **787-fn XS API embedded in exe** | `docs/engine/xs_api_reference.txt` | authoritative reference; no guessing signatures |
| `void aiRandSetSeed(int seed)` | xs_api_reference.txt | **determinism from script** |
| `WorldInfoRandomMapSeed`, `PrintSeedTaskProcessor` | binary strings | map seed settable + printable |
| `kbIsGameOver()`, `kbIsPlayerResigned(pid)`, `aiResign()`, `xsGetTime()` | xs_api_reference.txt | match lifecycle from script |
| `aiPlanSetVariableVector(planID,vi,vali,vec)` | xs_api_reference.txt | gate-placement lever (smart-walls stretch) |
| **developer mode already ON** | `…/Startup/user.cfg` (`developer`,`+ixsLog`,`+cxsLog`,`generateAIEchoesOutput`) | `aiEcho()`/`anwProbe()` already stream to `Age3Log.txt` + `Age3DEAIOutputPlayer<N>.txt` |
| DE has a **working AI-debug suite** | `AIDebug*Toggle` console cmds | live AI state available (corrects "Alt+Q broken" lore) |
| **No script/console game-speed cmd**; sim is fixed-rate lockstep, UI caps at "Fast" | binary (`mSpeedMultiplier`,`BGameSpeedCommand`,`FastForward`); console help has none | >Fast needs the hook; v1 uses "Fast" + parallelism |
| **Injection vehicle proven** (MinHook+pipe, **EAC-safe in skirmish**) | `artifacts/harness_design/phase2_dll_architecture.md`; `anw_hook.dll` on disk | speed-hook fallback is low-risk |
| xs_sim can't parse wall file | `aiBuildingsWalls.xs:1643` uses C++ lambda `[]()->bool{…}` | keep wall *math* in Python calibration layer; don't extend parser |

---

## 1. Reuse map (most of the farm already exists — build on it)

| Need | Existing asset | Gap to close |
|---|---|---|
| Launch + offscreen display | `smart_walls_sweep.py` (steam -applaunch, gamescope socket pairing, **never DISPLAY=:0**) | none — lift wholesale |
| Multi-AI setup (P2–P8) | `exhibition_runner.py::_build_opponent_slate()` + opponent roster | wire into farm config |
| Scenario mode | `exhibition_runner.py --use-scenario`; `Scenario/ANEWWORLD_TEST_ANWAI.age3Yscn` | confirm/repair load path |
| Lobby input | `tools/aoe3_automation/lobby_driver.py`, `anw_civ_picker_map.py`, `lobby_coords.json` | reuse |
| Match lifecycle | `smart_walls_sweep.py::run_match()` (wait mode-27, observe, crash-detect, resign, slice log) | generalize to N players, time-cap via `kbIsGameOver` |
| Telemetry parse | `parse_match_log.py` (`[ANWP v=2 t= p= civ= ldr= tag=]`), `validate_doctrine_compliance.py` | **tested on real log — works**; add aggregation |
| Probe emission | `game/ai/core/aiDoctrineProbes.xs` (`anwProbe`: milestone.*, comp.snapshot, posture.snapshot, wall.closure) | add `match.seed` + `match.over` probes |
| Doctrine PASS/FAIL | `validate_doctrine_compliance.py` | aggregate across matrix |

**Do not rebuild any of the above.** The farm is an orchestration + a few
XS additions on top.

---

## 2. Architecture

```
sweep config (matrix) ──► match driver ──► REAL ENGINE (gamescope, offscreen, "Fast")
   civ×map×slate×seed         │                 │  developer mode → Age3Log + per-player
                              │                 │  AI-vs-AI, seeded via aiRandSetSeed
                              ▼                 ▼
                        instance pool      .age3Yrec replay (recordgame)
                        (N parallel)             │
                              │                  ▼
                              └──► telemetry harvest (probes + replay cross-check)
                                         │
                                         ▼
                                  dataset (sqlite/JSON) ──► per-civ report + win-rate matrix
```

Tier split:
- **Logic oracle** (`xs_sim` + Python wall-math tests): ms-fast pre-flight; never judges outcomes.
- **Outcome oracle** (this farm): the real engine; the only source of behavioral truth.

---

## 3. Phases (exact files + commands + verification)

### Phase 0 — Determinism pre-flight (LIVE, fail-fast, ½ day) ⟵ do FIRST
The single thing that needs a live game before committing. Proves the whole
premise.
- **Add a seed hook (XS):** new `game/ai/core/anwFarmSeed.xs`, included from
  `aiLoaderStandard.xs::preInit()`:
  ```
  void anwApplyFarmSeed(void) {
     int seed = <read from a known location>;   // see note
     if (seed != 0) { aiRandSetSeed(seed);
        anwProbe("match.seed", "seed=" + seed); }
  }
  ```
  *Seed source options (pick at impl time, in order of preference):* (a) a
  scenario/RM parameter; (b) a tiny generated `.xs` constant file the driver
  writes per match (`anwFarmSeedValue.xs` with `int gANWFarmSeed = <n>;`),
  `#include`d — simplest & deterministic; (c) env via `aiEcho` round-trip.
  **Option (b) is the recommended default.**
- **Test:** run the SAME seed twice (2 matches, same civ/map/slate). Diff the
  `[ANWP v=2]` probe streams (ignoring wall-clock `t=` jitter is NOT allowed —
  game-ms `t=` must match). Diff the two `.age3Yrec`. 
- **Pass = identical streams.** If not identical, determinism needs the seed
  applied earlier (before map gen) — escalate to scenario-embedded seed.

### Phase 1 — `tools/sim_farm/` package (1–2 days)
- `tools/sim_farm/config.py` — matrix dataclasses (civs, maps, slates,
  player_counts, seeds, difficulty, observe_seconds).
- `tools/sim_farm/match.py` — generalize `smart_walls_sweep.run_match()`:
  N-player slate (from `_build_opponent_slate`), per-match seed file write
  (Phase 0b), `recordgame` enabled, end on `match.over` probe OR time-cap.
- `tools/sim_farm/driver.py` — sweep loop: iterate matrix, isolate Age3Log
  per match (truncate+slice as exhibition_runner does), retry-on-crash.
- Reuse `lobby_driver` for setup; **map variety:** prefer scenario-embedded
  map per matchup (generate scenario variants) OR fix lobby map-select
  (the typeahead is broken — calibrate tile coords like `_PICKER_ALASKA`
  for each target map; verify via Age3Log "MAP CODE").
- **Verify:** `python3 -m tools.sim_farm.driver --civs ANWGermans --maps Alaska --dry-run` enumerates matches; a single real `--limit 1` run produces a log slice with probes.

### Phase 2 — Telemetry harvest + dataset (1 day)
- `tools/sim_farm/harvest.py` — wrap `parse_match_log.parse_log()` per match;
  add **replay cross-check** via npm `@canyougiant/aoe3de-replay-parser`
  (node; optional — degrade gracefully if node absent).
- Write each match → row in `artifacts/sim_farm/dataset.sqlite` (or JSONL):
  keys = (civ, leader, map, slate_hash, player_count, seed, difficulty);
  values = probe tag counts, age-up ms, comp ratios, wall.closure stats,
  winner (from `kbIsGameOver`/replay), match duration.
- **Verify:** dataset row count == matches run; spot-check one row vs its log.

### Phase 3 — Scale + speed (1–2 days)
- **Parallelism:** instance pool. Each instance needs an isolated WINEPREFIX
  + gamescope socket + Age3Log path. **RISK + TEST:** confirm ≥2 prefixes
  run concurrently without Steam single-instance contention (Steam may
  serialize `-applaunch`; fallback = sequential per host, parallel across
  hosts/VMs). Spec K = min(physical cores/2, prefixes that boot clean).
- **Speed:** v1 runs at "Fast". v2 (optional, throughput only): rebuild the
  proven MinHook DLL to write `mSpeedMultiplier` past the clamp (scaffold in
  `phase2_dll_architecture.md`; EAC-safe in skirmish). Gate behind
  `--unlock-speed`; **never load in multiplayer.**
- **Verify:** N instances each produce an independent dataset shard; merge
  is deterministic.

### Phase 4 — Reporting (½ day)
- `tools/sim_farm/report.py` — aggregate dataset → (a) per-civ
  release-readiness via `validate_doctrine_compliance` thresholds, (b) a
  win-rate matrix (civ × difficulty / civ × opponent), (c) behavioral
  distributions (age-up, comp ratio, wall.closure) with the spec bands.
- Emit `artifacts/sim_farm/report.html` (reuse the readiness-site styling).
- **Verify:** report opens; every matrix cell populated or marked SKIP.

### Phase 5 (parallel, no game) — logic oracle
- Keep wall decision math in `tools/ai_design/wall_knob_calibration.py`; add
  `tools/ai_design/tests/test_wall_math.py` (chokepoint-gap selection,
  knob→wall-type, tier-by-age, closure arithmetic). **Do NOT** extend
  `xs_sim` for lambdas — out of scope.
- **Verify:** `python3 -m unittest tools.ai_design.tests.test_wall_math`.

---

## 4. Risks & mitigations (only two remain)

1. **Parallel instance isolation** (Steam single-instance). Mitigation:
   sequential-per-host + parallel-across-hosts; or non-Steam proton launch
   if DRM ticket can be satisfied (see `exhibition_runner` launch notes).
   *Not a feasibility risk — only a throughput risk.*
2. **Map variety** (lobby typeahead broken). Mitigation: scenario-embedded
   maps (preferred) or per-map tile-coord calibration. *Bounded.*

Everything else (determinism, telemetry, multi-AI, lifecycle, API) is
**already verified or already built.**

---

## 5. First command after "go"
```
# Phase 0 — prove determinism before building anything else:
python3 -m tools.sim_farm.preflight_determinism --civ ANWGermans --map Alaska --seed 12345 --runs 2
# expect: "DETERMINISM OK — probe streams identical"
```
If that passes, execute Phases 1→5 in order; each phase has a verify step
above. The farm is then a single `python3 -m tools.sim_farm.driver --config <matrix.yaml>`.
