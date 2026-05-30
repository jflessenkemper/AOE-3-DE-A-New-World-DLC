# Scenario-Authoring Playbook for 46-Civ Validation

This document gives a step-by-step path to author a custom scenario *in the in-game Scenario Editor* that will reliably load every ANW civ, fire the validation probes, and feed the existing pipeline (`validate_civ_behavior.py`) for a real per-civ pass/fail report.

The scenario approach is needed because **the lobby civ-picker doesn't reliably select ANW civs** — the picker shows the right civ display names, but the harness's scroll-and-click flow is timing-fragile and silently picks the wrong row in many cases. A scenario binary, by contrast, encodes the player→civ binding in its player table — once authored, it can't pick the wrong civ.

## What you'll build

Six small scenarios, each with **8 player slots** (the engine's max), pre-bound to 8 different ANW civs. Each scenario:

- Map: Small or Tiny (terrain doesn't matter for behavioral testing)
- All players: AI-controlled, Hard difficulty
- Each player slot bound to a specific ANW civ (set via the editor's Player UI)
- A handful of `trOutput()` triggers for matchstart/matchend markers
- The mod's existing `aiDoctrineProbes.xs` will fire automatically — no scenario triggers needed for civ behavior probes

| Scenario file | Player 1 | Player 2 | Player 3 | Player 4 | Player 5 | Player 6 | Player 7 | Player 8 |
|---|---|---|---|---|---|---|---|---|
| `ANW_Coverage_A.age3Yscn` | Argentines | Aztecs | BajaCalifornians | Barbary | Brazil | British | Californians | Canadians |
| `ANW_Coverage_B.age3Yscn` | CentralAmericans | Chileans | Chinese | Columbians | Dutch | Egyptians | Ethiopians | Finnish |
| `ANW_Coverage_C.age3Yscn` | French | FrenchCanadians | Germans | Haitians | Haudenosaunee | Hausa | Hungarians | Inca |
| `ANW_Coverage_D.age3Yscn` | Indians | Indonesians | Italians | Japanese | Lakota | Maltese | Mayans | Mexicans |
| `ANW_Coverage_E.age3Yscn` | NapoleonicFrance | Ottomans | Peruvians | Portuguese | RevFrance | RioGrande | Romanians | Russians |
| `ANW_Coverage_F.age3Yscn` | SouthAfricans | Spanish | Swedes | Texians | USA | Yucatan | (filler 1) | (filler 2) |

That's 46 ANW civs across 6 scenarios with 2 filler slots in the last one (use any base game civ — the validator only consumes probes from the 46 ANW civs).

## Step-by-step: authoring one scenario

### 1. Launch the game with developer mode active
The mod's `user.cfg` already has `developer`, `+ixsLog`, `+cxsLog` set, so just launch normally via `manage_game.py open`.

### 2. Open the Scenario Editor
- Main menu → Tools → Scenario Editor
- Click "New Scenario"

### 3. Set the map
- Map size: **Small** or **Tiny** (sub-200 area). Terrain doesn't matter; we just need an arena.
- Terrain: any simple flat preset
- Don't add native settlements, treasures, or trade routes — they're noise

### 4. Add player slots
- Open the **Players** tab
- Set total players to **8**
- For each player slot:
  - Set **Civilization** to the target ANW civ from the matrix above (e.g., "Argentina" for player 1)
  - Set **Player Type** to **AI**
  - Set **Team** to **2** (so all players are on the same team — this avoids them attacking each other immediately and keeps the match alive long enough for probes to fire)
  - Set **Difficulty** to **Hard**

### 5. Add the AI personality
For each player slot, set the **AI** dropdown to **the per-civ ANW personality** that the mod ships (e.g., `anwbritish.personality` for British). The ANW personality files are in `game/ai/anw_personalities/`. Without this step, the AI won't load the leader-specific doctrine knobs (`gLLBuildStyle` etc.).

> If the editor's AI dropdown only shows the default AI, the mod's personality registration may be incomplete — that's a separate mod-side issue. The `meta.boot` probe will tell you (it logs the chatset and buildStyle that did load).

### 6. (Optional) Add scenario triggers
The mod's `aiDoctrineProbes.xs` already emits all behavior probes per AI player. You don't strictly need scenario triggers. But if you want match-level milestones in the log, add these to the scenario:

| Trigger name | Condition | Effect (XS script) |
|---|---|---|
| Match Started | `Always` | `trOutput("[MATCH_START] t=" + xsGetTime());` |
| Auto Resign 60s | `Timer 60` | `aiResign(); trOutput("[AUTO_RESIGN] t=" + xsGetTime());` |
| Match Ended | `Game End` | `trOutput("[MATCH_END] t=" + xsGetTime());` |

### 7. Save the scenario
- File → Save As → `ANW_Coverage_A.age3Yscn`
- The editor saves to `~/.local/share/Steam/userdata/<steamid>/933110/remote/scenario@<NAME>.age3Yscn`

### 8. Verify it loads
- Main Menu → Load → Custom Scenario → select `ANW_Coverage_A` → Open
- Match should load. Watch for the 8 town centers spawning.

## Running validation against authored scenarios

Once you've authored all 6 scenarios, you collect a log slice from each run
and feed the directory to `run_full_validation.py --scenario-dir`. The new
`scenario_coverage.py` tool handles the gap detection and per-civ validator
fan-out so you don't have to concatenate or pre-process anything:

```bash
LOG="$HOME/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt"
SLICES="artifacts/scenario_runs"
mkdir -p "$SLICES"

for letter in A B C D E F ; do
    # 1. Truncate Age3Log.txt so the slice is clean
    :> "$LOG"
    # 2. Load ANW_Coverage_$letter in-game, let it run 60-120s, resign
    read -p "Load ANW_Coverage_$letter, then press Enter when match ends..."
    # 3. Save the slice
    cp "$LOG" "$SLICES/${letter}_log.txt"
done

# 4. One-command 46-civ report (coverage gaps + per-civ verdicts)
python3 tools/validation/run_full_validation.py --scenario-dir "$SLICES"
```

Exit code is 0 only when **all 46 civs are covered AND every validated civ
PASSes**. The JSON report at `artifacts/full_validation_runs/<ts>/scenario_coverage_report.json`
breaks down:

- Which civs are missing per scenario (so you know which to re-run)
- Which civs got unexpected verdicts (FAIL / WARN) and why
- The full per-civ check trace for further debugging

For a more focused single-shot run during scenario authoring (e.g. while
debugging why scenario A doesn't fire probes for one civ):

```bash
python3 tools/validation/scenario_coverage.py \
    --slice-dir "$SLICES" \
    --reference enriched_reference.json \
    --report report.json
```

## Why scenarios beat skirmish for testing

| Concern | Skirmish | Scenario |
|---|---|---|
| Civ binding accuracy | Fragile (picker scroll/click timing) | Hard-coded in scenario binary |
| Match length | Variable, AI-decided | Trigger-controlled (auto-resign at N seconds) |
| Player count | Up to 8 | Up to 8 |
| Test reproducibility | Depends on map/civ random | Deterministic |
| Setup time | ~30s of UI nav per match | ~5s scenario load |
| Author effort | Free (built-in lobby) | One-time scenario authoring |

For a 46-civ test the scenario approach trades ~2-4 hours of one-time authoring for fast, deterministic, reproducible runs forever after.

## Troubleshooting

### Editor: "AI personality" dropdown is empty / only shows base game AI
The mod's personality registration is incomplete. Check:
- `data/civmods.xml` has the civ entry with the right `<DisplayNameID>`
- `game/ai/anw_personalities/anw<civ>.personality` exists and is non-empty
- The personality file references `aiLoaderStandard` (or the mod's loader)
- The `<AINames>` block in `civmods.xml` for that civ lists the personality file

### Scenario fails to load with "Scenario X failed to load"
Most common cause: the scenario references content (units, techs, civs) that the current mod build doesn't define. Look for:
- Removed civs (we removed `ANWAmericansRev` and `ANWMexicansRev` — any old scenario using them will fail)
- Renamed protomods or techs

### Scenario loads but no probes in log
- Verify `cLLReplayProbes = true` in `game/ai/core/aiGlobals.xs` (line 535)
- Verify `xsEnableRule("llDoctrineProbes")` runs in `aiLoaderStandard.xs:postInit` — this enables the periodic snapshots
- Verify `meta.boot` fires within the first 5s — if not, the loader hit an XS error

## Files this document references

- `tools/aoe3_automation/anw_civ_picker_map.py` — picker index map (used by skirmish path; bypassed by scenario)
- `game/ai/anw_personalities/` — per-civ AI personality files
- `game/ai/aiLoaderStandard.xs` — the loader that fires the AI bootstrap + probes
- `game/ai/core/aiDoctrineProbes.xs` — periodic probe rule (every 30s game-time)
- `game/ai/core/aiUtilities.xs:llProbe` — the probe-emit helper
- `tools/validation/validate_civ_behavior.py` — what the resulting log gets validated against
