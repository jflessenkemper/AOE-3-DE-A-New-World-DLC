# ANEWWORLD — AI Test Scenario Runbook

**File:** `Scenario/ANEWWORLD.age3Yscn` (161,053 bytes, 8 player slots)
**Built from:** `Scenario/_test_template.age3Yscn` via `tools/validation/scenario_emitter.py emit-anewworld`

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
game. If you want a fully headless run (all 8 slots AI), regenerate with:

```bash
python3 tools/validation/scenario_emitter.py emit \
    --template Scenario/_test_template.age3Yscn \
    --matrix '{"ANEWWORLD":["ANWBritish","ANWAztecs","ANWMaltese","ANWRussians","ANWUSA","ANWLakota","ANWFrench","ANWJapanese"]}' \
    --out-dir Scenario/ \
    --ai aiLoaderStandard
```

## How to regenerate the scenario from the template

```bash
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
python3 tools/validation/scenario_emitter.py emit-anewworld \
    --template Scenario/_test_template.age3Yscn \
    --out Scenario/ANEWWORLD.age3Yscn

# Mirror to the live install so the engine can load it
cp Scenario/ANEWWORLD.age3Yscn \
   "/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/mods/local/A New World/Scenario/ANEWWORLD.age3Yscn"
```

`emit-anewworld` always re-derives from `_test_template.age3Yscn` (known
clean) so the container length invariants stay correct — the old
v2-builder bug (mismatched outer_size/body_size) cannot return.

## Verifying the scenario binary

```bash
python3 tools/validation/scenario_emitter.py inspect Scenario/ANEWWORLD.age3Yscn
python3 tools/validation/scenario_binary.py validate Scenario/ANEWWORLD.age3Yscn  # → "OK"
```

Expected output:
- `file_size=161053 body_size=2636822 outer_size=2636822 inner_size=2636815`
- `BP records: 9` (1 Gaia + 8 players)
- No `WARN` lines (length invariants intact)
- `OK: Scenario/ANEWWORLD.age3Yscn` from the binary validator

## Loading the scenario in-engine (manual)

1. Launch AoE3 DE through Steam with the **A New World** mod enabled.
2. From the main menu: **Single Player → Custom Scenario**.
3. Select **ANEWWORLD** from the scenario list.
4. The scenario auto-binds 8 civs; do NOT override civ picks in the
   lobby (the engine reads bindings from the scenario binary).
5. Start the match.

**If `INVALID FILE` dialog appears:**

The engine's scenario-load gate has rejected the file. Per the prior
investigation in `tools/validation/scenario_load_bypass.md`, this is
likely the Arxan-protected Steam Inventory / DRM check, not a
binary-format problem (our validator confirms the structure is clean).
The documented workaround is the Goldberg Steam Emu replacement
`steam_api64.dll` — see `scenario_load_bypass.md` § "Recommended next
step" for the exact procedure. Capture `Age3Log.txt` first so we can
diff successful skirmish vs failed scenario load.

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

## Headless / matrix mode (no human required)

For the all-46-civ coverage matrix, use the exhibition runner with
`cLLTestModeAutoResignMs` set so each AI auto-resigns at a wall-clock
threshold:

```bash
python3 tools/validation/exhibition_runner.py --civs all
```

This drives the game via `tools/aoe3_automation/manage_game.py`,
swapping civs into the playbook scenarios (`ANW_Coverage_A..F`), and
captures probes from every AI in every match. The cold-relaunch fix
landed earlier in this session (`fb17a8f`) so each match starts from a
deterministic mode-1 state.

## Files involved

| File                                                                     | Purpose                                          |
|--------------------------------------------------------------------------|--------------------------------------------------|
| `Scenario/ANEWWORLD.age3Yscn`                                            | The canonical 8-civ AI test scenario             |
| `Scenario/_test_template.age3Yscn`                                       | Known-clean carrier with 9 BP slots              |
| `Scenario/ANEWWORLD_AI_TEST_RUNBOOK.md`                                  | This document                                    |
| `Scenario/ANEWWORLD_TRIGGER_SPECIFICATION.md`                            | Original (binary-trigger) spec — superseded      |
| `tools/validation/scenario_emitter.py`                                   | Binary patcher + `emit-anewworld` subcommand     |
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
