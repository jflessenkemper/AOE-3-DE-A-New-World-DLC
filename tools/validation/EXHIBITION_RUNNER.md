# Exhibition Runner: Full Civ Sweep Validation

## What It Does

The exhibition runner automates full-mod testing by launching 48 exhibition matches (one per civ), capturing logs, and generating a pass/fail report. Each match is a 1v1 AI match on Hard difficulty with the test civ facing Napoleon (a good stress test for every AI doctrine).

**Why?** Manual testing 48 civs is impractical. This tool lets you know within ~2.5 hours whether all leaders load, decks activate, and core AI plans (escort, rout, ransom) fire.

## Quick Start

### Prerequisites

- Steam is running
- Age of Empires 3: DE is installed at `~/.local/share/Steam/steamapps/common/Age of Empires 3 DE/`
- The Legendary Leaders mod is enabled in your mod list
- Python 3.10+

### First Run: Dry Run

```bash
python3 tools/validation/exhibition_runner.py --dry-run
```

This prints a plan of 48 civs without launching the game.

### Real Sweep (Unattended)

```bash
python3 tools/validation/exhibition_runner.py --match-seconds 180
```

This will:
1. Loop through all 48 civs
2. For each, truncate the log, launch a match, wait 180 seconds, kill the game, parse the log
3. After all matches, write `tools/validation/exhibition_report.md`
4. Report: `44/48 ✅` or similar

**Estimated time:** 48 civs × 3 min = ~2.5 hours. You can leave it running.

## Launch Methods

The tool tries **two launch backends** in order; if both fail, it falls back to `--manual-launch`:

### Backend 1: Steam URL (Recommended)

```bash
xdg-open 'steam://run/933110'
```

**Pros:** Clean, matches Steam client behavior  
**Cons:** Undocumented; may not start matches automatically

### Backend 2: Proton (Fallback)

```bash
proton run ~/.local/share/Steam/steamapps/common/Age\ of\ Empires\ 3\ DE/bin/x64/Ay3Main.exe
```

**Pros:** Direct control  
**Cons:** Requires proton installed; mod load order may differ

### Backend 3: Manual Launch (`--manual-launch`)

```bash
python3 tools/validation/exhibition_runner.py --manual-launch --match-seconds 180
```

**Flow:**
1. Script prints: `[MANUAL] Start a 1v1 AI match: British vs ANWNapoleonicFrance (Hard, ANEWWORLD scenario)`
2. You manually start the game and queue the match with those exact civ/difficulty/scenario
3. Script sleeps for 180s
4. Script kills the game and parses the log
5. Repeat for next civ

This is slower (manual overhead) but 100% reliable.

## Command-Line Options

```
--dry-run                 Print plan without launching (good for testing)
--match-seconds N         Duration per match in seconds (default: 180)
--difficulty LEVEL        Game difficulty (default: Hard)
--manual-launch           Wait for you to start matches manually
--start-from CIV_ID       Resume from this civ (e.g., homecityfrench)
--only CIV_ID [CIV_ID...] Test only these civs (space-separated)
--output PATH             Report output path (default: tools/validation/exhibition_report.md)
```

### Examples

```bash
# Test just two civs
python3 tools/validation/exhibition_runner.py --only homecitybritish anwhomecitynapoleon

# Resume from French (handy if a run was interrupted)
python3 tools/validation/exhibition_runner.py --start-from homecityfrench

# Manual mode with shorter matches
python3 tools/validation/exhibition_runner.py --manual-launch --match-seconds 120
```

## Interpreting the Report

The report is a markdown table: `tools/validation/exhibition_report.md`

| Column | Meaning |
|--------|---------|
| **Civ** | Civilization name |
| **Leader** | The renamed leader unit |
| **Rename** | ✅ Leader name appears in log |
| **Deck** | ✅ Deck activated ("Legendary Leaders" in log) |
| **Escort** | ✅ Explorer escort plan created |
| **Ransom** | ✅ Explorer ransom queued after loss |
| **Rout** | ✅ AI rout system fired (ai-rout-start or ai-rout-blocked) |
| **Suites** | Number of runtime suites that passed (e.g., 2/2) |
| **Status** | PASS if all checks passed, FAIL + reason otherwise |

### What Each Check Means

- **Rename:** The leader's display name was set correctly (should appear in the log at least once)
- **Deck:** The mod's Legendary Leaders deck was activated
- **Escort:** The AI created an escort plan to protect the leader
- **Ransom:** When the leader fell, ransom was queued (important for recovery)
- **Rout:** Non-elite units broke and retreated under fire (core AI feature)
- **Suites:** Runtime validation suites (`ai_rout_bootstrap`, `ai_rout_lane`) passed

A civ is **PASS** only if all 6 checks pass.

### Example Report Output

```
## Civs Needing Review

- **British** (homecitybritish): deck not loaded, rout plan never fired
- **Hausa** (homecityhausa): leader name not found
```

This tells you exactly what to fix for each failed civ.

## Troubleshooting

### Game won't start

**Symptom:** Script times out on first match, log stays empty

**Fixes:**
1. Verify Steam is running: `ps aux | grep steam`
2. Check mod is enabled in launcher
3. Try `--manual-launch` to verify the game works
4. Check `~/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age\ of\ Empires\ 3\ DE/Logs/Age3Log.txt` exists

### Log not appearing or stays empty after match

**Symptom:** Script finishes but report shows all civs failed with "log is empty"

**Fixes:**
1. Run a manual match first, verify log updates
2. Check the two possible log paths:
   - `~/.steam/steam/steamapps/...` (primary)
   - `~/.local/share/Steam/steamapps/...` (fallback)
3. Ensure game is actually running before script kills it

### Civ selection fails in-game

**Symptom:** Manual mode: you can't find the civ in the civ picker

**Fixes:**
1. Some revolution civs may not be selectable in Skirmish (confirm in vanilla first)
2. If a standard civ is missing, check mod installation: `~/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age\ of\ Empires\ 3\ DE/76561198170207043/mods/local/Legendary\ Leaders\ AI/`

### Match runs but leader name doesn't appear in log

**Symptom:** Rename check fails

**Fixes:**
1. Verify leader name mapping in `tools/cardextract/rename_explorers.py`
2. Run `python3 tools/cardextract/rename_explorers.py` to re-inject leader strings
3. Rebuild the mod if strings aren't updating

## How the Tool Works (Advanced)

1. **Discovery:** Loads all 48 civ_ids from `tools/cardextract/civ_themes.py`
2. **Per-civ loop:**
   - Truncate `Age3Log.txt`
   - Launch the game (or wait for manual start)
   - Sleep for `--match-seconds`
   - Force-kill the game process
   - Read log delta
   - Parse for leader name, "Legendary Leaders", escort/ransom/rout markers
   - Run formal validation suites (`ai_rout_bootstrap`, `ai_rout_lane`)
   - Save per-civ result
3. **Report:** Markdown table + failure summary
4. **Resilience:** Per-civ try/except so one bad civ doesn't abort the sweep; `--start-from` for resuming

## Performance Notes

- **Per-match overhead:** ~10-15s (truncate, launch, kill, parse)
- **Match time:** Configurable (default 180s ensures AI has time to engage)
- **Total sweep:** 48 × 195s ≈ 2.5 hours
- **Log parsing:** ~50-100ms per match

To speed up a test run:
```bash
python3 tools/validation/exhibition_runner.py --match-seconds 60 --only homecitybritish anwhomecitynapoleon
```

## Further Reading

- `tools/validation/validate_runtime_logs.py` - the log parser
- `tools/validation/runtime_specs/legendary_runtime_suites.json` - suite definitions
- `tools/cardextract/civ_themes.py` - civ configuration
- `tools/cardextract/rename_explorers.py` - leader name mappings
