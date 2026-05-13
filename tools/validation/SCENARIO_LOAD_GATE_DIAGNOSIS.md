# Scenario load gate — diagnosis (2026-05-13)

Read-only follow-up to `scenario_load_bypass.md` (2026-05-08). No game launched,
no production scenario modified. Investigation only.

## TL;DR (read this first)

1. **The "Goldberg Steam Emu" plan was already tried — and it FAILED.**
   On 2026-05-11 a Goldberg `steam_api64.dll` (1,452,032 bytes, Aug 2019,
   `goldberg_emu` markers present) was installed and *triggered AoE3 DE's
   integrity guard*: "Fatal Error: one or more game files is invalid.
   Error code: 0x5". Game wouldn't even reach the lobby. The 1.4 MB
   Goldberg DLL still sits parked as
   `steam_api64.dll.emulator-backup` (mtime 2026-05-11 20:45) and
   `tools/validation/check_steam_api_integrity.py` was added the same day
   to detect this incident class. **Do NOT redo Goldberg.** It is a hard
   no-go for this title.
2. **The current `steam_api64.dll` is the legitimate Valve SDK** — md5
   `8fe4f5f3feefc50f25c5a1cd8485ba98`, byte-identical to `.original`,
   288 032 bytes, Valve signature present, no emulator markers,
   `check_steam_api_integrity.py` reports PASS.
3. **`Unlock Error - Inventory Extended:-1` is benign** — confirmed by
   `docs/RELEASE_READINESS_2026-05-09.md`:
   > "No engine-side errors in Age3Log other than the standard
   > `Unlock Error - Inventory Extended:-1` which is normal when the
   > player isn't signed into a Microsoft account / launching offline."
   The cross-check that `scenario_load_bypass.md` flagged as "must run
   before further RE" was implicitly answered in the 05-09 release-
   readiness doc. The line appears on every offline / not-MS-signed-in
   boot and has nothing to do with scenario loading. We have been
   chasing a red herring.
4. **The current `Age3Log.txt` shows the game booted but never attempted
   a scenario load.** It ends at "APregame : EnterMode : End" / "Account
   Event - New State: LoggedIn" — pregame UI is up, no Skirmish click
   happened, no `loadScenario` line. There is **no in-the-log evidence
   of `INVALID FILE`, scenario rejection, or any failure beyond the
   benign Inventory line** in the most recent run. Whatever rejection
   happened previously was not captured by this log.
5. **The accepted current project stance is "give up on custom binary
   scenario loading"** — `docs/STATE_OF_THE_MOD.md:16`:
   > "Custom scenario binary loading | RED — Arxan integrity check
   > rejects all custom binaries. Cannot bypass without engine modding.
   > Workaround: in-game Scenario Editor only."
   and `docs/SESSION_HANDOFF_2026-05-09.md:128-129`:
   > "Goldberg DLL hijack — Arxan kills the game on launch. Don't.
   > Scenario emitter — engine rejects all custom binaries. Use Scenario
   > Editor manually if scenarios are needed."

The bypass document's plan (drop Goldberg in) is **out of date and was
empirically refuted** between 2026-05-08 (when it was written) and
2026-05-11 (when Goldberg was tested + rolled back).

## Steam-API surface — current state (read-only audit)

| File | Size | mtime | md5 | Active? |
|------|------|-------|-----|---------|
| `steam_api64.dll` | 288 032 | 2026-05-11 20:45 | `8fe4f5f3…` | **YES — Valve SDK** |
| `steam_api64.dll.original` | 288 032 | 2026-05-08 18:03 | `8fe4f5f3…` | backup (identical) |
| `steam_api64.dll.emulator-backup` | 1 452 032 | 2026-05-11 20:45 | `e29133a9…` | parked — IS Goldberg, contains `Goldberg SteamEmu` marker |
| `steam_appid.txt` | 6 B | 2026-05-13 18:14 | – | `933110\n` |
| `steam_settings/DLC.txt` | 357 B | 2026-05-11 18:46 | – | 5 DLC IDs |
| `steam_settings/` | – | 2026-05-11 18:46 | – | dir |

Notes:

- `steam_appid.txt` AND `steam_settings/` still on disk despite Goldberg
  itself being reverted. Harmless against the genuine Valve DLL (it
  ignores both), but they are residue from the failed 05-11 Goldberg
  test and could confuse a future investigator.
- `check_steam_api_integrity.py` PASS confirms current state is clean.
- The genuine Valve SDK 288 KB DLL imports the 12-function interface
  `scenario_load_bypass.md` lists; nothing about that import surface
  has changed.

## Age3Log.txt — current evidence

Only ONE log present:

```
/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/
  pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/
  Logs/Age3Log.txt              (2698 B, mtime 2026-05-13 18:15)
```

No per-user-folder `Logs/` subdirectories exist. No rotated `Age3Log.*`
backups present. Full content (47 lines):

```
... (memory report)
PreGame  9518:  Account Event - New State: AttemptingLogIn, …
PreGame  9557:  startGame : Sign In SUCCESS
PreGame  9557:  User folder id: 76561198170207043
PreGame  9564:  Version: 100.15.59076.0 (386756)
PreGame  14159:  Enabled Mods:
PreGame  14159:    4 "A New World" Crc: 3365997125 …
PreGame  14290:  Game locale: English
PreGame  52592:  Data patch 28.0.2 crc 1248332430
PreGame  65337:  Game startup complete (65.32 sec)!
PreGame  65367:  APregame : EnterMode : Start
...
PreGame  65466:  ModeTrack -- entering mode 1 (Pregame) from mode 0 (<Invalid>)
PreGame  65489:  APregame : EnterMode : End
PreGame  68896:  Account Event - New State: LoggedIn, …
PreGame  75560:  Unlock Error - Inventory Extended:-1
```

Verdict: the run reached pregame UI, signed in, mod load OK
("4 'A New World' Crc: 3365997125"), and stopped. No scenario load was
attempted, no `INVALID FILE` line was emitted in this session.

This means the current "still rejects" claim is **not visible in the
current log** — to capture the actual rejection event the user must
launch the game and attempt to load `ANEWWORLD.age3Yscn` while we tail
the log via `tools/validation/watch_scenario_load.py`.

## user.cfg state

`~/.../76561198170207043/Startup/user.cfg`:

```
developer
+ixsLog
+cxsLog
```

No scenario-specific or bypass flags. (Production-side `game.cfg`
includes `validatechecksum`, `noPregameScenario`, `noPregameRecording`
— none of those tokens exist in the engine binary as console-command
strings, so they're best-effort defaults from older builds.)

`persistenty.cfg` contains only UI window positions.

## Engine binary state — diff vs 2026-05-08

Re-ran `tools/validation/inspect_engine_binary.py` against the on-disk
`AoE3DE_s.exe` (`Mar 18 18:49`, 57 929 776 B, same file as 05-08).

- **No new gate strings discovered.** Section entropies unchanged
  (.text 7.994 / .text-2 7.981 — both packed).
- All the `Scenario`-related strings are command-table identifiers
  (`loadScenario`, `uiScenarioLoad`, `loadCampaignScenario`,
  `loadTutorial`, `uiOpenScenarioBrowser`, …) — these are the names of
  XS functions that the engine binds, not gate names. They confirm a
  console-driven `loadScenario(<stringFilename>)` exists, but its body
  is in the encrypted `.text` so we cannot statically follow what it
  does after the open.
- The string `invalidFileDialog` / `InvalidFileDialog-prompt` (the UI
  template names) exist in the engine, but the localized text "INVALID
  FILE" does NOT appear in any extracted `Game/` xml/xmb — meaning the
  prompt body is resolved from a locale stringtable, not embedded
  literally. (Worth a follow-up to find the stringtable entry but
  unlikely to change diagnosis.)
- `signature` / `signature failure` / `signature was an unexpected
  length` strings exist in the binary but live entirely in the
  OpenSSL / xboxlive / reliclink HTTPS sub-library
  (`d:\projects\age3\source\extlib\reliclink\…openssl\…`) — NOT in a
  scenario-load code path. They are TLS cert handling, not file
  integrity check.
- `WinTrust` / `bcrypt` / `Crypt32` are imported, but again only for
  HTTPS / xboxlive token validation, not scenario file signing.
- No new candidate bypass tokens (`noinventory`, `skipsignature`,
  `nodrm`, etc.) found.

Conclusion: the engine on disk is the same packed Arxan-protected
binary as 05-08, and static analysis still cannot see the gate.

## Scenario file byte-level diff

First 100 bytes of every scenario file in play:

| File | Size | Bytes 0-3 | Bytes 4-7 (decompressed size) | Bytes 8-9 (zlib hdr) |
|------|------|-----------|-------------------------------|----------------------|
| Bombard_Brawl.age3Yscn (stock, loads) | 369 942 | `6c 33 33 74` (l33t) | `eb 46 7e 00` | `78 9c` |
| ANEWWORLD.age3Yscn (production, fresh) | 161 053 | `6c 33 33 74` | `16 3c 28 00` | `78 9c` |
| ANEWWORLD.age3Yscn (mod-deployed) | 161 053 | `6c 33 33 74` | `16 3c 28 00` | `78 9c` | (md5-equal to production)
| _test_template.age3Yscn (template) | 160 246 | `6c 33 33 74` | `f2 3b 28 00` | `78 9c` |
| legendary-leaders-ai.age3Yscn (legacy in user-Scenario dir) | 160 246 | `6c 33 33 74` | `f2 3b 28 00` | `78 9c` |
| (legacy) ANEWWORLD in user-Scenario dir | 147 810 | `6c 33 33 74` | `b9 08 28 00` | `78 da` |

Observations:

- All headers are `l33t` + uint32-LE decompressed size + zlib stream —
  exactly per `docs/wiki/file-formats/l33t.md`.
- The freshly-rebuilt ANEWWORLD differs from Bombard_Brawl only in
  expected ways: smaller decompressed size (because we used a
  template stripped down from the 8 MB Bombard_Brawl original) and a
  different compressed stream.
- One historical curio: the legacy user-Scenario-dir copy of
  ANEWWORLD uses zlib header `78 da` (BEST_COMPRESSION level) while
  every freshly-emitted file uses `78 9c` (DEFAULT). The bypass doc
  notes "zlib encoder variants (level/memLevel/strategy)" already
  ruled out, but it's worth confirming the deployed file does NOT use
  `78 da`. Current deployed file uses `78 9c` — fine.

**There is no high-entropy region near the file start that looks like a
signature or hash trailer.** The zlib stream begins at offset 8 with
the expected `78 9c` header — what follows is compressed payload, not a
manifest. The bypass-doc's earlier ruling-out of CRC32/Adler32/file-
size/zero/dup-header trailers still holds.

## Deployment audit

The freshly-built scenario is correctly deployed:

```
~/.../76561198170207043/mods/local/A New World/Scenario/
    ANEWWORLD.age3Yscn      161 053 B   mtime 2026-05-13 18:54
    _test_template.age3Yscn 160 246 B   mtime 2026-05-13 18:54
```

The mod-dir copy is byte-identical to the production-tree copy at
`/var/home/jflessenkemper/AOE-3-DE-A-New-World/Scenario/ANEWWORLD.age3Yscn`
(both 161 053 B, identical first 100 bytes).

**There is also a stale legacy copy** at
`~/.../76561198170207043/Scenario/ANEWWORLD.age3Yscn` (147 810 B,
mtime 2026-05-06, zlib header `78 da`). This is *not* the file the user
would target via "mod local Scenario" in the picker, but if the engine
ever resolves the scenario name from the user-data Scenario dir as a
fallback, this older / smaller / differently-encoded file could be the
one being loaded and rejected. Worth verifying which path the picker
uses.

## What's actually new since 2026-05-08

Files added/changed after `scenario_load_bypass.md` (2026-05-08 17:47)
that bear on this investigation:

| Path | Date | Why it matters |
|------|------|----------------|
| `tools/validation/PATH_B_NOTES.md` | 2026-05-08 19:49 | OCR-driven lobby picker work; documents the *real* current blocker (picker UI, not scenario load) |
| `tools/aoe3_automation/install_goldberg_for_scenarios.sh` | 2026-05-08 19:49 | Helper script (DOES `--apply` Goldberg — DO NOT RUN. Empirically refuted 05-11.) |
| `tools/validation/check_steam_api_integrity.py` | 2026-05-11 20:49 | Detector that flags any non-Valve `steam_api64.dll`. Created in response to the 05-11 Goldberg incident. |
| `docs/STATE_OF_THE_MOD.md` | post-05-08 | Records the "Arxan integrity check rejects all custom binaries. Cannot bypass" verdict. |
| `docs/SESSION_HANDOFF_2026-05-09.md` | 2026-05-09 | Says "Goldberg DLL hijack — Arxan kills the game on launch. Don't." |
| `docs/RELEASE_READINESS_2026-05-09.md` | 2026-05-09 | Confirms "Inventory Extended:-1" is benign / a normal offline-account log line. |

The investigative trajectory between 05-08 and today:

1. 05-08: bypass-doc proposes Goldberg.
2. 05-11: Goldberg installed → game refuses to launch with "0x5"
   fatal error → engine hash-checks `steam_api64.dll` itself, so the
   DLL hijack is detected and blocked by Arxan-style integrity guards.
   Goldberg rolled back; integrity-check validator created.
3. 05-09 onwards: project accepted that custom binary scenario load is
   not achievable and moved to "use Scenario Editor manually" / focus
   on the lobby-picker validation Path B.
4. 05-13 today: scenario binary emitter rebuilt the file (container
   validates clean) but the engine-side gate has not been tested
   afresh; old conclusion stands until proven otherwise.

## What we did NOT do this session (and why)

- **No game launch.** User constraint and prior conclusion both block
  it from this seat.
- **No `loadScenario` CLI flag test.** Could not find a documented
  command-line argument; `loadScenario` is a console / XS function,
  not an `argv` flag. The engine `--scenario` / `+loadScenario` /
  `+scenario` strings do NOT appear in the binary's string table.
- **No Bombard_Brawl symlink-into-user-dir experiment.** That was
  step 7 of the brief; without launching the game it can't be
  validated, and *modifying user-data scenario dirs* is exactly the
  surface that already showed mixed state (stale legacy copy). We
  recommend the user run this experiment manually after deciding the
  next step (see below).

## Next step the user should take

The diagnostic question — "is `INVALID FILE` still happening at all?"
— **cannot be answered from the available logs.** The current
`Age3Log.txt` does not record a scenario-load attempt.

Three concrete options, in increasing effort:

### Option A — verify the current state by trying once more (RECOMMENDED)

1. Make sure the in-game cfg has *not* changed (it hasn't — verified).
2. Launch via Steam, sit in the lobby, open Scenario Editor or
   Skirmish → Custom Scenario, pick "A New World / ANEWWORLD".
3. Tail the log with `tools/validation/watch_scenario_load.py
   --expect-civs ANWArgentines ANWBritish ANWFrench --timeout-s 180`
   in another terminal BEFORE clicking OPEN.
4. Three possible outcomes:
   - **PASS** (≥1 ANW civ emits `meta.boot`): the rebuild fixed it.
     Done.
   - **FAIL with `INVALID FILE`**: confirms the gate is still live. Now
     we have a fresh log to diff against a known-good skirmish log
     (capture one first, even from a vanilla map). That diff is the
     next step the bypass-doc asked for and never got.
   - **FAIL with `Scenario … failed to load`** but no `INVALID FILE`
     dialog: the rebuild changed the failure mode — probably a
     mod-content reference (renamed civ/tech) — and the path is
     workable.

This is ~5 minutes of user time and is the empirical answer we don't
yet have. **Do this before any further engine work.**

### Option B — remove the legacy file before retesting

There's a stale 2026-05-06 / 147 810 B / `78 da` copy of ANEWWORLD at
`~/.../76561198170207043/Scenario/ANEWWORLD.age3Yscn`. If the picker
resolves scenario by name and falls through to that dir, it would
load the old file and our fresh build never gets a chance.

```bash
mv "${HOME}/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Scenario/ANEWWORLD.age3Yscn" \
   "${HOME}/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Scenario/ANEWWORLD.legacy_20260506.age3Yscn"
```

Do this BEFORE Option A so the freshly-rebuilt mod-dir file is the
unambiguous target.

### Option C — drop a known-good first-party scenario into the user
### scenario dir and see if the engine loads it

This isolates "is it the file's bytes?" vs "is it the path the engine
allows?". Read-only on `Bombard_Brawl.age3Yscn` (stays untouched in
its install dir):

```bash
# Copy stock first-party scenario into the user-data Scenario dir:
cp -p "${HOME}/.local/share/Steam/steamapps/common/AoE3DE/Game/Campaign/ScoreChallenges/Bombard_Brawl.age3Yscn" \
      "${HOME}/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Scenario/Bombard_Brawl.age3Yscn"

# And into the mod's scenario dir:
cp -p "${HOME}/.local/share/Steam/steamapps/common/AoE3DE/Game/Campaign/ScoreChallenges/Bombard_Brawl.age3Yscn" \
      "${HOME}/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/mods/local/A New World/Scenario/Bombard_Brawl.age3Yscn"
```

Then attempt to load "Bombard_Brawl" from each location:

- **If the user-Scenario-dir copy loads but the mod-Scenario-dir copy
  does NOT** → the engine refuses to load scenarios out of mod dirs.
  Diagnosis: the gate is path-based, not bytes-based. Workaround:
  emit our scenario into the user-data Scenario dir instead of the
  mod's.
- **If both load** → the engine accepts known-good binaries from both
  paths; our custom scenario's *bytes* are the rejected thing, not
  the path. Diagnosis: there's a content-level gate (per-record
  validation, or maybe a CRC over the player table) we haven't found
  yet.
- **If neither loads** → the gate is independent of file content and
  rejects scenarios as a class. Most likely diagnosis given that
  Bombard_Brawl is shipped by the game and works from `Campaign/`:
  the engine restricts scenario load by source dir (Campaign-only
  for non-developer mode), and *no* user-supplied path will work.
  Would need engine modding.

This is a 30-second copy-and-click test and is the single best
diagnostic we can give the user before any further static / dynamic
work.

### Option D — DO NOT consider

- Re-installing Goldberg. Empirically refuted 2026-05-11. The engine's
  hash check on its own `steam_api64.dll` is the very first thing it
  does and Arxan-guards it.
- Wine-debugger memory patch. Multi-day. Out of scope.
- Searching the binary for newer string gates. Already done; nothing
  new since 05-08.

## Concrete one-liner the user should run RIGHT NOW (no game launch)

```bash
# Sanity-check the current state of the Steam-API surface and stale-
# scenario residue. Should print PASS on the integrity check and show
# the legacy file's presence:

python3 /var/home/jflessenkemper/AOE-3-DE-A-New-World/tools/validation/check_steam_api_integrity.py
ls -la "${HOME}/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Scenario/"
```

Then proceed with Option B (rename legacy) → Option C (Bombard_Brawl
sanity test) → Option A (retry ANEWWORLD with log-watcher), in that
order.

## Open questions left for next session

1. Where does the engine resolve scenario names from?
   `<install>/Game/Campaign/*` vs `<userdata>/Scenario/*` vs
   `<mod>/Scenario/*` — precedence and allowlist unknown.
2. Body of the `InvalidFileDialog-prompt` localized string — find it
   in the locale stringtable; nearby refs may name the gate.
3. Has `validate_scenario_binary.py` validated the inner `BG/FH`
   tree, or just the `l33t+zlib` container? Container OK does not
   imply inner-field consistency.
4. Does loading from Steam Cloud `~/.local/share/Steam/userdata/
   209941315/933110/remote/scenario@ANEWWORLD.age3Yscn` work? The
   install_goldberg helper references that path.

No code changes. No scenarios touched. No game launched.
