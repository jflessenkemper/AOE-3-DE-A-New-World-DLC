# ANEWWORLD test loop — how to run an AI test session

Single source of truth for "how do I run the scenario and see if the AI
works correctly". One command from your shell, two clicks in the lobby,
walk away, come back to a PASS/FAIL report.

## The one command

```
python3 tools/validation/run_scenario_test.py
```

This will:

1. Snapshot the current state of `Game/AI/*.personality` (so we only report
   on *this session's* AI activity, not stale data from previous matches).
2. Copy `Scenario/ANEWWORLD.age3Yscn` from the repo into both Steam
   locations the engine reads from (the profile dir AND Steam Cloud's
   `userdata/.../remote/scenario@*` dir). Idempotent — skips if already
   identical.
3. Launch AoE3 DE via `steam://run/933110`.
4. Print on-screen instructions for the menu clicks you need to make.
5. Poll `Game/AI/` every 5 seconds for fresh personality writes.
6. When the match ends (60s of no new writes after the first), or you hit
   the timeout, or you Ctrl-C, invoke
   `tools/validation/validate_personality_vs_spec.py` and print a session-
   delta report showing PASS/FAIL for every civ that played.

## The two clicks

After the game launches:

1. Main menu → **Single Player** → **Skirmish**
2. Top of the map list → **Custom Maps** tab → **ANEWWORLD**
3. (Optional) change the civ in the human slot to whichever civ you want
   to test. The 8 AI slots will all play their assigned civ from the
   binary (currently all 8 are Spanish — see "Known limits" below).
4. **Start**

Then walk away. The script does the rest.

## What you'll see

```
Building baseline snapshot...
Baseline: 48 civs with prior data, 31 NO_DATA across 79 files — will report only fresh activity
Scenario staged: 147810 B at .../76561198170207043/Scenario/ANEWWORLD.age3Yscn
Scenario staged: 147810 B at .../userdata/.../remote/scenario@ANEWWORLD.age3Yscn
Game launching. Click: Single Player → Skirmish → Custom Maps → ANEWWORLD → Start.
Watching for personality writes…
[+0:01:23] anwspanish: match_ms=60000 ws=MobileNoWalls(5) bs=...
[+0:02:14] anwspanish: match_ms=120000 ws=MobileNoWalls(5) bs=ColonialPlazaRush
...
Match ended (60s idle since last write). Running validator...
PASS=14  FAIL=8  PREINIT_PASS=0  PREINIT_FAIL=0  NO_DATA=24

Session delta:
  anwspanish: PASS  ws=MobileNoWalls(5) match_ms=720000
Full report: artifacts/validation/personality_compliance.md
```

## CLI flags

| Flag | Purpose |
|---|---|
| `--no-baseline` | Skip the baseline snapshot (report everything, not just session-new). Useful when you've manually cleared `Game/AI/*.personality` and want a full fresh validation. |
| `--no-launch` | Don't run `steam://run/933110`; assume you'll start the game yourself. Useful when the game is already open. |
| `--timeout N` | Stop polling after N minutes (default 15). `--timeout 0` skips polling entirely — used for "what does the validator say right now?" dry-run. |

## Exit codes

- `0` — at least one fresh probe captured AND the validator returned 0
  (all civs that played, passed)
- `1` — fresh probes captured but the validator returned non-zero
  (at least one civ FAILED its wall-strategy claim)
- `2` — timeout reached with no fresh probes (the pipeline is broken,
  or the AI never started writing — check that the mod is enabled and
  the lobby's leader-key drop-down is set to the correct one)

## Known limits (current state, 2026-05-12)

These are blockers I've documented while building this loop. They define
the boundary of what "easily and fully" can mean *today*:

### 1. No CLI auto-load

There is no public Steam command-line flag to auto-load a custom scenario.
The user has to click through the lobby (`Single Player → Skirmish →
Custom Maps → ANEWWORLD`). This is engine-level — `lobby_driver.py` *can*
do it via cursor automation, but that's off-limits per project policy.

If the engine ever gains a `+autoloadscenario` uservar or similar, the
single source to update is in `run_scenario_test.py` near the
`launch_game()` function.

### 2. One civ at a time, partially

The ANEWWORLD binary has 8 player slots, ALL assigned to Spanish. The
runtime AI dispatch fires on `civmods.xml` `<AINames>` per-slot, so all
8 slots will exercise `anwspanish.personality` only. To test other civs,
you change the **human slot's civ** in the lobby — that doesn't change
the AI civs, but it does mean you can play Spain vs. Spain, or French vs.
7-Spanish-AI, etc.

For per-civ AI testing on the OTHER 45 civs, you currently have to
**manually set each AI slot's civ in the lobby drop-down**. This is the
"manual lobby setup" path the user has used to get the 13 existing PASS
records (British, Canadians, Dutch, Germans, etc.).

### 3. Multi-civ scenario rewrite is engine-blocked

`tools/validation/scenario_emitter.py` *would* programmatically swap the
8 AI slot civs to make e.g. `ANEWWORLD_British.age3Yscn`. The emitter
produces structurally valid binaries (round-trip + 16/16 unit tests pass)
but the engine rejects emitter output as "INVALID FILE". Nine hypotheses
have been tested and disproven (CRC, Adler32, zlib parameters, Steam
Cloud manifest, etc.) — see
`tools/validation/SCENARIO_EMITTER_NOTES.md` for the full investigation
log. Unblocking this requires reverse-engineering the engine's load-time
integrity check in `AoE3DE_s.exe` via Ghidra/IDA (estimated ~days).

### 4. Triggers (`[AGEUP]`, `[UNITS_TRAINED]`, etc.) don't fire

The scenario binary has no embedded triggers. Existing trigger injection
tools (`tools/validation/scenario_trigger_builder.py`,
`trigger_injector.py`) are admitted stubs. The personality channel
captures the data we actually need (wall_strategy, build_style, age,
match_ms, score) WITHOUT triggers, so this is a documentation gap rather
than a functional one. If we ever need richer in-match telemetry (unit
counts, building placements, card shipments), we'd need to either:

- Add triggers via the in-game Scenario Editor (manual, one-time)
- Pivot to RMS-based testing (`RandMaps/anwtest.xs`) where
  `rmCreateTrigger` / `rmAddTriggerEffect` are officially documented
- Reverse-engineer the binary trigger format (research-shaped)

## Why this design

- **Personality channel over trigger output.** AoE3 DE FINAL_RELEASE
  builds strip `aiEcho()` from `Age3Log.txt`. The only data path that
  survives is `aiPersonalitySetPlayerUserVar()` → `Game/AI/<leader>.personality`
  XML uservars. The validator I built for that path
  (`validate_personality_vs_spec.py`) is the source of truth.

- **File-watching over cursor automation.** Cursor-grabbing tools (kwin,
  Claude Preview, Claude-in-Chrome) are explicitly forbidden by the user.
  Polling the personality dir for new writes is non-intrusive, robust to
  unexpected game state, and works whether the user plays the match or
  observes.

- **Idempotent staging.** Re-running the script is cheap — file copies
  short-circuit on identical mtime/size, so you can run it repeatedly
  while iterating on XS changes.

## See also

- `tools/validation/validate_personality_vs_spec.py` — the validator
- `tools/validation/SCENARIO_EMITTER_NOTES.md` — multi-civ blocker
  investigation
- `tools/playtest/probes_from_replay.py` — personality-file parser
- `artifacts/validation/personality_compliance.md` — latest validator
  output
