# ANEWWORLD — AI Test Scenario Runbook

**File:** `Scenario/ANEWWORLD.age3Yscn` (370,389 bytes, 8 player slots)
**Built from:** stock `Bombard_Brawl.age3Yscn` carrier via
`tools/validation/scenario_emitter.py emit-anewworld`

## 2026-05-13 update — Bombard_Brawl carrier + CRC32 trailer

Two prior issues now resolved:

1. **`INVALID FILE` modal solved.** The engine's Custom Scenario load gate
   validates a CRC32 trailer over `file_bytes_with_trailer_zeroed` (stored
   little-endian as the last 4 bytes). The emitter previously inherited
   the carrier's stale trailer; it now recomputes the trailer on every
   emit. Verified 4/4 against real files in
   `tools/validation/SCENARIO_TRAILER_ANALYSIS.md`.
2. **Template body is gate-rejected — root cause known.** Even with a
   correct CRC32 trailer, `Scenario/_test_template.age3Yscn` is rejected
   because **it is a quick-save, not a scenario**: body version `0x69`
   (105) is 2 above the stock-scenario maximum (103), J1 section
   version 338 is 14 above the max (324), and BP record version `0xfc`
   (252) is 39 above max (`0xd5`). Its version fingerprint matches
   `QuickSavegame.age3Yscn` exactly. The engine reads `body[6:10]`
   first, finds a format it doesn't know how to load, and rejects with
   "INVALID FILE" before ever reaching the trailer. Full diagnosis:
   `tools/validation/TEMPLATE_BODY_REJECTION_FORENSICS.md`. The
   canonical carrier is now stock **`Bombard_Brawl.age3Yscn`**
   (body version 54), which loads cleanly. The emitter auto-resolves
   the carrier in this order:
     1. `--template <path>` if supplied.
     2. `~/.local/share/Steam/steamapps/common/AoE3DE/Game/Campaign/
         ScoreChallenges/Bombard_Brawl.age3Yscn` (default).
     3. `tools/validation/_carrier_bb.age3Yscn` (repo fallback).

Pre-flight trailer check (cheapest validation before launching the game):

```bash
python3 tools/validation/scenario_emitter.py validate-trailer \
    Scenario/ANEWWORLD.age3Yscn \
    Scenario/coverage/ANW_Coverage_*.age3Yscn
```

Expected output: `OK: <path>` per file with matching
`expected_trailer == actual_trailer`.

## What this scenario tests

A single match exercises **all six smart-wall doctrines** at once. Eight
civ slots are pre-bound in the scenario binary, so the lobby civ-picker
is bypassed entirely. You launch the scenario, the engine reads the
bindings, and seven AI players each load their leader-specific XS code
with comprehensive telemetry on.

| Slot | Civ            | Role          | Wall doctrine        | AI loader          |
|------|----------------|---------------|----------------------|--------------------|
| P1   | ANWBritish     | **HUMAN obs** | FortressRing         | (none)             |
| P2   | ANWAztecs      | AI            | ChokepointSegments   | aiLoaderStandard   |
| P3   | ANWMaltese     | AI            | CoastalBatteries     | aiLoaderStandard   |
| P4   | ANWRussians    | AI            | FrontierPalisades    | aiLoaderStandard   |
| P5   | ANWUSA         | AI            | UrbanBarricade       | aiLoaderStandard   |
| P6   | ANWLakota      | AI            | MobileNoWalls        | aiLoaderStandard   |
| P7   | ANWFrench      | AI            | FortressRing         | aiLoaderStandard   |
| P8   | ANWJapanese    | AI            | MobileNoWalls        | aiLoaderStandard   |

Slot 1 is a human observer seat so you can watch the AI from inside the
game. If you want a fully headless run (all 8 slots AI), regenerate with
a custom matrix:

```bash
python3 tools/validation/scenario_emitter.py emit \
    --template ~/.local/share/Steam/steamapps/common/AoE3DE/Game/Campaign/ScoreChallenges/Bombard_Brawl.age3Yscn \
    --matrix '{"ANEWWORLD":["ANWBritish","ANWAztecs","ANWMaltese","ANWRussians","ANWUSA","ANWLakota","ANWFrench","ANWJapanese"]}' \
    --out-dir Scenario/ \
    --ai aiLoaderStandard
python3 tools/validation/scenario_emitter.py validate-trailer Scenario/ANEWWORLD.age3Yscn
```

## How to regenerate the scenario

```bash
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World

# Default: BB carrier auto-resolved, CRC32 trailer auto-computed.
python3 tools/validation/scenario_emitter.py emit-anewworld \
    --out Scenario/ANEWWORLD.age3Yscn

# Verify before copying:
python3 tools/validation/scenario_emitter.py validate-trailer \
    Scenario/ANEWWORLD.age3Yscn

# Mirror to the live install so the engine can load it
cp Scenario/ANEWWORLD.age3Yscn \
   "/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/mods/local/A New World/Scenario/ANEWWORLD.age3Yscn"
```

`emit-anewworld` derives from a known-good carrier (default: stock
`Bombard_Brawl.age3Yscn`) so the container length invariants stay correct
and the CRC32 trailer always matches the freshly-emitted body. The old
v2-builder bug (mismatched outer_size/body_size) and the 2026-05-13
stale-trailer bug cannot return — both invariants are enforced inside
`pack_scenario(recompute_trailer=True)` (the default).

## 46-civ playbook coverage matrix

For comprehensive AI testing across **all 46 ANW civs**, the emitter
ships a 6-scenario playbook (8 civ slots each, 46 unique civs + 2
fillers in the final scenario):

```bash
python3 tools/validation/scenario_emitter.py emit-playbook \
    --out-dir Scenario/coverage
```

Produces `ANW_Coverage_A.age3Yscn` through `ANW_Coverage_F.age3Yscn`
in `Scenario/coverage/`. Each file:

  - Player 1 = human observer seat
  - Players 2..8 = AI under `aiLoaderStandard`
  - CRC32 trailer auto-computed (engine-validated)
  - Built from the same `Bombard_Brawl.age3Yscn` carrier

Civ coverage (matrix labels A..F):

| Label | Slots P1..P8 (P1 always human) |
|-------|-------------------------------|
| A | Argentines, Aztecs, BajaCalifornians, Barbary, Brazil, British, Californians, Canadians |
| B | CentralAmericans, Chileans, Chinese, Columbians, Dutch, Egyptians, Ethiopians, Finnish |
| C | French, FrenchCanadians, Germans, Haitians, Haudenosaunee, Hausa, Hungarians, Inca |
| D | Indians, Indonesians, Italians, Japanese, Lakota, Maltese, Mayans, Mexicans |
| E | NapoleonicFrance, Ottomans, Peruvians, Portuguese, RevFrance, RioGrande, Romanians, Russians |
| F | SouthAfricans, Spanish, Swedes, Texians, USA, Yucatan, British*, French* |

(`*` = filler so all 8 slots are bound — observation pipeline only
consumes probes from the first 6 unique civs in F).

Mirror to the mod dir before loading in-engine:

```bash
mkdir -p "$MOD/Scenario/coverage"
cp Scenario/coverage/ANW_Coverage_*.age3Yscn "$MOD/Scenario/coverage/"
```

where `$MOD` is your `.../mods/local/A New World` path.

## Verifying the scenario binary

```bash
# Cheapest check (engine-equivalent load gate, no game launch needed):
python3 tools/validation/scenario_emitter.py validate-trailer Scenario/ANEWWORLD.age3Yscn

# Full inspection (BP records + civ bindings + length invariants):
python3 tools/validation/scenario_emitter.py inspect Scenario/ANEWWORLD.age3Yscn
python3 tools/validation/scenario_binary.py validate Scenario/ANEWWORLD.age3Yscn  # → "OK"
```

Expected output:
- `file_size=370389` (≈ BB carrier size + a few bytes for new hcnames)
- `BP records: 9` (1 Gaia + 8 players)
- No `WARN` lines (length invariants intact)
- `OK: Scenario/ANEWWORLD.age3Yscn  expected_trailer=32521506 actual_trailer=32521506`

## Loading the scenario in-engine (manual)

1. Launch AoE3 DE through Steam with the **A New World** mod enabled.
2. From the main menu: **Single Player → Custom Scenario**.
3. Select **ANEWWORLD** from the scenario list.
4. The scenario auto-binds 8 civs; do NOT override civ picks in the
   lobby (the engine reads bindings from the scenario binary).
5. Start the match.

**If `INVALID FILE` dialog appears:**

The 2026-05-13 root cause (stale CRC32 trailer) is now permanently fixed
in the emitter. If you still see this modal on a freshly-emitted file,
diagnose in this order:

1. **Re-run validate-trailer.** If it reports BAD, the file was
   tampered after emission. Re-emit:
   ```bash
   python3 tools/validation/scenario_emitter.py emit-anewworld \
       --out Scenario/ANEWWORLD.age3Yscn
   python3 tools/validation/scenario_emitter.py validate-trailer \
       Scenario/ANEWWORLD.age3Yscn
   ```
2. **Check the carrier.** The default carrier resolution walks the
   stock-install path first. If you moved or deleted
   `~/.local/share/Steam/steamapps/common/AoE3DE/Game/Campaign/
   ScoreChallenges/Bombard_Brawl.age3Yscn`, the emitter falls back
   to the repo-local `tools/validation/_carrier_bb.age3Yscn` — make
   sure that file is present and CRC32-valid.
3. **Mirror to the mod dir.** The engine's Custom Scenario picker
   reads from BOTH the user-Scenario dir AND the mod-Scenario dir.
   Make sure your fresh emit is in
   `.../mods/local/A New World/Scenario/ANEWWORLD.age3Yscn` and not
   shadowed by a stale copy.
4. **(Resolved)** Do NOT use `_test_template.age3Yscn` as the
   carrier — its body fingerprint identifies it as a v105 quick-save,
   not a v103-or-lower stock scenario. Diagnosis:
   `tools/validation/TEMPLATE_BODY_REJECTION_FORENSICS.md`.
5. **(Last resort)** Tail the log during the load attempt:
   ```bash
   python3 tools/validation/watch_scenario_load.py \
       --expect-civs ANWBritish ANWAztecs ANWMaltese --timeout-s 180
   ```

## What gets captured during the match

Every AI emits **`[LLP v=2]` probe lines** to `Age3Log.txt` covering
the user's six trigger-spec requirements **plus** much more. No
scenario-side triggers are needed — the AI scripts are fully
self-instrumented.

| User-spec trigger        | AI probe(s)                                                  |
|--------------------------|--------------------------------------------------------------|
| Age-up detection         | `compliance.age`, `meta.gameover finalAge=`                  |
| Unit training            | `comp.snapshot` (vil/inf/cav/arty/warship every 60s)         |
| Building placement       | `compliance.bldg`, `plan.build_snap`, `milestone.first_*`    |
| Card shipment            | `compliance.ship`                                            |
| Trade route              | `posture.snapshot tposts=`                                   |
| Game end                 | `meta.gameover lost= finalAge= score=`                       |

Additional telemetry beyond the spec:

| Probe tag                | What it captures                                             |
|--------------------------|--------------------------------------------------------------|
| `meta.boot`              | Leader, wall strategy, build style, bias matrix at t=0       |
| `meta.setup`             | Game mode, difficulty, team, player count, start age         |
| `meta.leader_init`       | Per-leader init confirmation                                 |
| `telem.heartbeat`        | Age/resources/pop/army/score every 60s                       |
| `mil.plan_snap`          | Combat/attack/defend/explore plan counts                     |
| `plan.build_snap`        | Build/wall/repair/gather/research plans + TC/house count     |
| `navy.fleet_snap`        | Naval inventory + transport plans                            |
| `econ.snap`              | Detailed economic state                                      |
| `compliance.*`           | 17+ deep-doctrine compliance probes (anchor, profile, bldg,  |
|                          | army, placement, terrain, age, combat, econ, ship, placeAll, |
|                          | wallGeom, diplo, rules, tactics, ...)                        |
| `wall.coast`             | Coastline-exploitation vector + waterBorders count           |
| `wall.chokepoint`        | Real chokepoint detection vector + cached flag               |
| `wall.water_fix`         | Inland-walk fixup when forward-bias lands in water           |
| `wall.closure`           | Per-ring coverage % every 60s                                |
| `wall.escalate`          | Priority + villager escalation when coverage < 60% at 4 min  |
| `wall.reemit`            | Plan re-emission when the original ring is destroyed         |
| `event.*`                | Personality / style / terrain / heading / strongpoint events |

## Where logs land

```
~/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt
```

The Logs directory may also have a per-steamid subfolder. The
`tools/validation/exhibition_runner.py` infrastructure copies these
logs into `artifacts/validation/ai_playstyle/` after a run.

## Generating the AI test report after a match

```bash
# 1. Run the scenario in-engine (manually). Resign when you're done
#    observing — gameOverHandler() fires on resign and writes the
#    final meta.gameover + personality-file probe.
#
# 2. Copy the log so we don't race with a live game:
cp ~/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age\ of\ Empires\ 3\ DE/Logs/Age3Log.txt \
   /tmp/anw_test_run.log

# 3. Generate the per-civ AI compliance report:
python3 tools/validation/validate_doctrine_compliance.py \
    --logs /tmp/anw_test_run.log \
    --out artifacts/validation/anw_test_report.txt \
    --html artifacts/validation/anw_test_report.html \
    --json artifacts/validation/anw_test_report.json \
    --allow-fail

# 4. Open the HTML report (one page per civ, PASS/FAIL per claim):
xdg-open artifacts/validation/anw_test_report.html
```

The validator cross-checks every probe stream against
`playstyle_spec.json`'s structured per-civ claims and emits PASS / WARN /
FAIL per assertion. UNKNOWN means the probe stream doesn't carry enough
data to judge — typically due to a too-short observation window.

## Headless / matrix mode — path to 100% AI coverage

The repo has **40 resolvable ANW civs** (45 in `playstyle_spec.json` minus 5
stubs without `civmods.xml` entries: Californians, Central Americans,
French Canadians, Rio Grande, Yucatan — see
`artifacts/validation/civ_art_audit.md`). The exhibition runner now skips
those stubs by default, so the 100%-coverage denominator is **40/40**.

For the all-40-civ coverage matrix, use the exhibition runner:

```bash
# Cold start (~3.3h at 180s/civ + ~95s cold-relaunch per civ)
python3 tools/validation/exhibition_runner.py --match-seconds 180

# Resume after a crash / interrupted run:
python3 tools/validation/exhibition_runner.py --resume

# Retry civs that previously FAILed/ERRORed (default --resume skips them):
python3 tools/validation/exhibition_runner.py --resume --retry-failed

# Auto-retry transient crashes up to N times per civ within one invocation:
python3 tools/validation/exhibition_runner.py --max-attempts 3

# Combine everything for a hands-off 100%-coverage chase:
python3 tools/validation/exhibition_runner.py --resume --retry-failed --max-attempts 3
```

The checkpoint file is written at
`artifacts/validation/ai_playstyle/exhibition_checkpoint.json` after every
attempt (PASS, FAIL, or ERROR). A subsequent `--resume` skips PASS civs
unconditionally; `--retry-failed` re-enrolls FAIL/ERROR civs into the run.

The runner uses **the single canonical `ANEWWORLD.age3Yscn`** for every
match; it walks the 46-civ roster built at import time (`ANW_ROSTER`)
and varies the matchup by re-emitting the scenario with different civ
bindings per match (via `scenario_emitter.set_player_bindings`). Each
re-emit recomputes the CRC32 trailer automatically through
`pack_scenario(recompute_trailer=True)`, so the engine's load gate
accepts every freshly-emitted file. The cold-relaunch fix landed
earlier in this session (`fb17a8f`) so each match starts from a
deterministic mode-1 state.

The static 6-scenario coverage playbook (`Scenario/coverage/
ANW_Coverage_A..F.age3Yscn`) is an alternative for **non-runner**
manual exploration — useful when the runner can't be started or when
the user wants to play through specific civ matchups by hand.

**2026-05-19 — these 6 carriers are FROZEN.** They are NOT auto-regenerated
on matrix changes. They were last rebuilt 2026-05-19 against the 40-civ
roster (5 × 8 primaries + 1 × 8 fillers). Regenerate only when explicitly
asked. The runner uses `Scenario/ANEWWORLD.age3Yscn` exclusively.

Note: as of 2026-05-13 the engine's load gate is resolved at the
binary level (CRC32 trailer). Any remaining `INVALID FILE` rejections
are body-content issues — try BB as the carrier (the default).

## Files involved

| File                                                                     | Purpose                                          |
|--------------------------------------------------------------------------|--------------------------------------------------|
| `Scenario/ANEWWORLD.age3Yscn`                                            | The canonical 8-civ AI test scenario (BB-derived)|
| `Scenario/coverage/ANW_Coverage_A..F.age3Yscn`                           | 46-civ playbook coverage matrix                  |
| `~/.local/share/Steam/.../AoE3DE/Game/Campaign/ScoreChallenges/Bombard_Brawl.age3Yscn` | Stock carrier (default for emit)         |
| `Scenario/_test_template.age3Yscn`                                       | DEPRECATED carrier — v105 quick-save, gate-rejects |
| `tools/validation/TEMPLATE_BODY_REJECTION_FORENSICS.md`                  | Root-cause diagnosis of why _test_template fails |
| `Scenario/ANEWWORLD_AI_TEST_RUNBOOK.md`                                  | This document                                    |
| `Scenario/ANEWWORLD_TRIGGER_SPECIFICATION.md`                            | Original (binary-trigger) spec — superseded      |
| `tools/validation/scenario_emitter.py`                                   | Binary patcher: `emit-anewworld`/`emit-playbook`/`validate-trailer` |
| `tools/validation/scenario_emitter_tests.py`                             | 28 pytest cases (parser, emitter, trailer, carrier) |
| `tools/validation/SCENARIO_TRAILER_ANALYSIS.md`                          | CRC32 trailer reverse-engineering notes          |
| `tools/validation/validate_scenario_binary.py`                           | Container/length-invariant validator             |
| `tools/validation/validate_doctrine_compliance.py`                       | Probe-stream consumer + per-civ AI report        |
| `game/ai/aiLoaderStandard.xs`                                            | AI entry point; enables all probes + heartbeats  |
| `game/ai/core/aiDoctrineProbes.xs`                                       | milestone.first_* + comp.snapshot + posture.*    |
| `game/ai/core/aiCore.xs::gameOverHandler`                                | meta.gameover + personality-file write           |
| `game/ai/core/aiBuildingsWalls.xs`                                       | wall.coast / wall.chokepoint / wall.closure etc. |

## Why scenario-side binary triggers are not needed

The AI is fully self-instrumented in XS. Every metric in the original
`ANEWWORLD_TRIGGER_SPECIFICATION.md` — age-up, unit count, building
placement, card shipments, trade routes, game-end — is emitted as a
probe by the AI scripts themselves. There is no need to author trigger
graphs in the binary scenario; we'd be re-implementing telemetry that
already exists in `aiDoctrineProbes.xs` + `aiLoaderStandard.xs` +
`gameOverHandler`.

The scenario file's only job is to bind 8 ANW civs to 8 player slots
and load them with `aiLoaderStandard`. Everything else is XS.
