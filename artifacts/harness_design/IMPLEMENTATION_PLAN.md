# ANW Test Harness — Implementation Plan

**Version:** 1.1 — 2026-05-28  
**Status:** Ready for one-shot implementation  
**Author:** Synthesis agent (Claude Sonnet 4.6)

## Summary

This document is the **self-contained working brief** for a one-shot implementation agent to build the ANW test harness end-to-end. It synthesises three read-only design documents (listed below) and resolves all open risks. The implementing agent does **not** need to re-read the source docs — every path, constant, exact diff, and command is reproduced here. The three source docs are reference material only:

Phase 0 + Phase 1 are implemented in approximately **~585 LOC** (up from ~525; the additional ~60 LOC are the new `capture.py` module). Visual verification of all 40 civ UI surfaces is covered by Phase 1 + manual UI navigation; Phase 2 only required for fully programmatic UI driving.

- `artifacts/harness_design/phase0_xs_edits.md` — per-AI demuxed log channel design
- `artifacts/harness_design/phase1_system_verification.md` — system readiness audit
- `artifacts/harness_design/pipeline_audit.md` — tool inventory + UX target

**Repo root:** `/var/home/jflessenkemper/AOE-3-DE-A-New-World/`  
All paths below are absolute unless stated otherwise.

---

## Option A vs Option B Resolution (Phase 0)

**RESOLVED: Option A (user.cfg only, zero XS changes).**

Source: AoE3 DE official patch notes for Update 61213, quoted verbatim in the community forum thread at `https://forums.ageofempires.com/t/ai-modding-guide-and-resources/198299`:

> *"You can now generate text files with all the aiEchoes per AI of the previous game you played by putting `generateAIEchoesOutput` in your user.cfg. Text files will be named like 'Age3DEAIOutputPlayer1.txt'."*

This confirms that `generateAIEchoesOutput` (note: **no `=1`** — it is a bare token, not a key=value pair) causes existing `aiEcho()` calls to be automatically written to per-player files. No separate `aiEchoPlayer()` API exists. A grep of the entire `game/ai/` tree for `aiEchoPlayer`, `aiEchoToPlayer`, and `xsEchoData` returned **zero matches** — the API does not exist in the codebase or the engine surface exposed to this codebase.

**There was a bug** (the files were created but remained empty) that was confirmed fixed in a subsequent 2022 patch. The current game version is well past that fix.

**Important syntax note:** The flag is a bare token (`generateAIEchoesOutput`), not `generateAIEchoesOutput=1`. The `=1` form used in some earlier notes in the design docs is incorrect. Use the bare token in `user.cfg`.

**Conditional Option B** (Step 0.3 below) is documented as a fallback only. Execute it only if Step 0.5 smoke test shows per-AI files are not created after adding the bare token.

---

## Phase 0 — Per-AI Demuxed Doctrine Logging

### Step 0.1 — Add `generateAIEchoesOutput` to `user.cfg`

**File:**
```
/var/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Startup/user.cfg
```

**Current contents (verbatim):**
```
developer

// appended by ensure_dev_mode():
+ixsLog
+cxsLog
```

**New contents (add one line):**
```
developer

// appended by ensure_dev_mode():
+ixsLog
+cxsLog
generateAIEchoesOutput
```

**Verification:**
```bash
grep -c "generateAIEchoesOutput" \
  "$HOME/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Startup/user.cfg"
# Expected: 1
```

---

### Step 0.2 — Patch `_DEV_CFG_CONTENT` in `log_capture.py`

This is the **critical persistence fix**. `ensure_dev_mode()` regenerates `user.cfg` from `_DEV_CFG_CONTENT` on clean runs. Without patching this constant, every harness invocation will silently overwrite `user.cfg` and remove the demux flag.

**File:** `/var/home/jflessenkemper/AOE-3-DE-A-New-World/tools/aoe3_automation/log_capture.py`

**Lines to change:** 71–93 (`_DEV_CFG_CONTENT` constant) and 69 (`_REQUIRED_TOKENS` tuple).

**Old `_REQUIRED_TOKENS` (line 69):**
```python
_REQUIRED_TOKENS: tuple[str, ...] = ("developer", "+ixsLog", "+cxsLog")
```

**New `_REQUIRED_TOKENS`:**
```python
_REQUIRED_TOKENS: tuple[str, ...] = ("developer", "+ixsLog", "+cxsLog", "generateAIEchoesOutput")
```

**Old `_DEV_CFG_CONTENT` (lines 71–93):**
```python
_DEV_CFG_CONTENT = """\
// user.cfg -- personal developer overrides for Legendary Leaders AI probe capture
//
// These three tokens together enable aiEcho() probe output to Age3Log.txt:
//   developer  -- engine developer mode
//   +ixsLog    -- XS info-level logging (overrides "//+ixsLog" in game.cfg:85)
//   +cxsLog    -- XS console-XS logging (overrides "//+cxsLog" in game.cfg:87)
//
// Without ALL THREE, aiEcho() calls are silently dropped and [LLP v=2 ...]
// lines never appear in the log file.  The bare "developer" token alone is
// INSUFFICIENT: dev mode toggles UI/keybinds but does not route XS output.
//
// Mechanism: AoE3 DE reads game.cfg, then production.cfg (FINAL builds), then
// the user's Startup/user.cfg as +/- overrides.  See game.cfg line 84:
//   "XS setup - for correct default handling of messages -
//    to turn off +XYZ add -XYZ to your user.cfg"
//
// Remove this file to revert to production mode.

developer
+ixsLog
+cxsLog
"""
```

**New `_DEV_CFG_CONTENT`:**
```python
_DEV_CFG_CONTENT = """\
// user.cfg -- personal developer overrides for Legendary Leaders AI probe capture
//
// These four tokens together enable aiEcho() probe output to Age3Log.txt
// and per-AI demuxed output to Age3DEAIOutputPlayer<N>.txt:
//   developer              -- engine developer mode
//   +ixsLog                -- XS info-level logging (overrides "//+ixsLog" in game.cfg:85)
//   +cxsLog                -- XS console-XS logging (overrides "//+cxsLog" in game.cfg:87)
//   generateAIEchoesOutput -- demux aiEcho() per AI player to Age3DEAIOutputPlayer<N>.txt
//
// Without developer+ixsLog+cxsLog, aiEcho() calls are silently dropped.
// generateAIEchoesOutput is a bare token (NOT key=value); it was added in
// Update 61213 and fixed (empty-file bug) in a subsequent 2022 patch.
//
// Remove this file to revert to production mode.

developer
+ixsLog
+cxsLog
generateAIEchoesOutput
"""
```

Also update `_has_all_tokens` — the function itself needs no change because it checks for membership in `_REQUIRED_TOKENS`, which we just updated. Verify the logic still holds:

```bash
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
python3 -c "
from tools.aoe3_automation.log_capture import _REQUIRED_TOKENS, _has_all_tokens
print('tokens:', _REQUIRED_TOKENS)
test = 'developer\n+ixsLog\n+cxsLog\ngenerateAIEchoesOutput\n'
print('has_all:', _has_all_tokens(test))
"
# Expected:
# tokens: ('developer', '+ixsLog', '+cxsLog', 'generateAIEchoesOutput')
# has_all: True
```

---

### Step 0.3 — (CONDITIONAL) XS fallback for Option B

**Execute this step only if Step 0.5 shows per-AI files are NOT created.**

If the bare `generateAIEchoesOutput` token does not produce files, the engine may require an explicit `aiEchoPlayer(playerID, message)` call. In that case, edit `llProbe()` in:

**File:** `/var/home/jflessenkemper/AOE-3-DE-A-New-World/game/ai/core/aiUtilities.xs`  
**Lines:** 287–292

**Old text (verbatim, starting at line 287):**
```xs
   aiEcho(line);
   aiChat(1, line);
   if (cMyID != 1)
   {
      aiChat(cMyID, line);
   }
```

**New text:**
```xs
   aiEcho(line);
   aiEchoPlayer(cMyID, line);   // demux to Age3DEAIOutputPlayer<cMyID>.txt
   aiChat(1, line);
   if (cMyID != 1)
   {
      aiChat(cMyID, line);
   }
```

After any XS edit, validate:
```bash
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
python3 tools/validation/validate_xs_scripts.py
# Expected: exit 0
```

---

### Step 0.4 — Deploy mod

```bash
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
python3 tools/deploy_to_mod.py
# Expected: exit 0; prints UPDATE/NEW for any changed files
```

If Option B XS edit was made, re-verify XS clean first (Step 0.3 verification above).

---

### Step 0.5 — Smoke test: verify per-AI files appear

This is the **gate check** between Option A and Option B.

**Manual steps:**
1. Ensure no stale AoE3 processes are running:
   ```bash
   pkill -f "AppId=933110" 2>/dev/null; sleep 2
   pgrep -af "AoE3DE_s.exe"  # must return empty
   ```
2. Launch AoE3 via Steam (normal launch, not harness — Steam handles Proton at this stage).
3. Start a skirmish with at least 2 AI players (any map, any civs; the `generateAIEchoesOutput` flag is engine-level and civ-agnostic).
4. Let the match run for at least 5 game-minutes (enough for `llProbe` calls to fire).
5. Exit to main menu or resign. Close the game.
6. Check for per-AI files:

```bash
LOG_DIR="$HOME/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs"
ls -la "$LOG_DIR"/Age3DEAIOutputPlayer*.txt 2>/dev/null || echo "NO PER-AI FILES — Option B required"
```

**If files exist, Option A succeeded.** Verify probe content:
```bash
grep "\[LLP v=2" "$LOG_DIR"/Age3DEAIOutputPlayer*.txt | head -20
# Expected: probe lines like [LLP v=2 t=... p=2 civ=... ldr=... tag=...]
```

**If files do not exist**, execute Step 0.3, redeploy (Step 0.4), rerun this smoke test.

**Note on file location:** The Phase 1 audit also found an `AI/` subdirectory at:
```
.../Games/Age of Empires 3 DE/76561198170207043/Game/AI/
```
If `Logs/` shows no files, also check that path:
```bash
AI_DIR="$HOME/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Game/AI"
ls -la "$AI_DIR"/Age3DEAIOutputPlayer*.txt 2>/dev/null || echo "not here either"
```
If files appear there instead of `Logs/`, update all path constants accordingly before proceeding.

---

### Step 0.6 — Retarget `validate_doctrine_compliance.py`

**File:** `/var/home/jflessenkemper/AOE-3-DE-A-New-World/tools/validation/validate_doctrine_compliance.py`

**Change 1: Replace `_auto_discover_logs` (lines 1302–1309)**

**Old text:**
```python
def _auto_discover_logs(root: Path) -> list[Path]:
    """Return every match.log under the conventional artifact root.

    Sorted to keep the report deterministic between invocations on the same
    set of inputs."""
    if not root.exists():
        return []
    return sorted(root.rglob("match.log"))
```

**New text:**
```python
def _auto_discover_logs(root: Path) -> list[Path]:
    """Return every match.log and Age3DEAIOutputPlayer*.txt under the
    conventional artifact root. match.log is the primary source;
    per-player files are included as supplementary (defense in depth).
    Sorted to keep the report deterministic between invocations."""
    if not root.exists():
        return []
    paths: list[Path] = []
    # Primary: per-match slices of Age3Log.txt
    paths.extend(sorted(root.rglob("match.log")))
    # Supplementary: per-AI demuxed output (Phase 0 addition)
    paths.extend(sorted(root.rglob("Age3DEAIOutputPlayer*.txt")))
    return paths
```

**Change 2: Add `--ai-logs` CLI flag** (insert after the `--logs` argument definition, around line 1320)

**Insert after the `--logs` `add_argument` block:**
```python
    ap.add_argument("--ai-logs", type=Path, nargs="+", default=None,
                    help="explicit Age3DEAIOutputPlayer*.txt files to also scan "
                         "(supplementary to --logs; both are parsed)")
```

**Insert in the log_paths resolution block (around line 1379, after `log_paths = args.logs if args.logs else ...`):**
```python
    if args.ai_logs:
        log_paths = list(log_paths) + list(args.ai_logs)
```

No change to `parse_probes()` is required — it already handles any list of Paths and the `[LLP v=2]` regex is file-source-agnostic.

**Verification:**
```bash
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
python3 tools/validation/validate_doctrine_compliance.py --help | grep "ai-logs"
# Expected: shows the --ai-logs flag
```

---

### Step 0.7 — Acceptance: run validator against per-AI output

After Step 0.5 confirms per-AI files exist:

```bash
LOG_DIR="$HOME/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs"
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
python3 tools/validation/validate_doctrine_compliance.py \
  --ai-logs "$LOG_DIR"/Age3DEAIOutputPlayer*.txt \
  --allow-empty \
  --json /tmp/phase0_acceptance.json
```

Expected: validator runs, finds `[LLP v=2]` probes, writes JSON. If the smoke-test match ran for at least 5 game-minutes with a full 7-AI civ load, expect PASS for those civs.

Also run against the archived hubtest pass log to confirm existing data path is unbroken:
```bash
python3 tools/validation/validate_doctrine_compliance.py \
  --allow-empty \
  --json /tmp/phase0_regression.json
# Expected: same results as before Phase 0 changes (match.log paths still discovered)
```

---

## Phase 1 — Steam-Free, Gamescope-Free Harness

### Target layout

All new files live under:
```
/var/home/jflessenkemper/AOE-3-DE-A-New-World/tools/aoe3_harness/
```

New files in this package:
- `__init__.py`
- `launch.py`
- `supervisor.py`
- `log_tail.py`
- `scenario_runner.py`
- `validator.py`
- `cli.py`
- `state.json` (initial)
- `capture.py` — non-cursor-grab screenshot module for visual verification

### Dependency: clear Steam launch options

The current Steam `LaunchOptions` for AppID 933110 is:
```
env WINEDEBUG=+file PROTON_LOG=1 PROTON_LOG_DIR=/home/jflessenkemper gamescope -W 1920 -H 1080 -w 1920 -h 1080 --xwayland-count 1 -- %command%
```

The harness bypasses Steam entirely via `umu-run`, so this field can be left as-is (harmless when Steam is not used to launch). **Do not clear it** — it is the user's working fallback for manual sessions.

### Process cleanup before any harness launch

```bash
# Kill stale AoE3 wrappers before a harness run:
pkill -f "AppId=933110" 2>/dev/null; sleep 2
pgrep -af "AoE3DE_s.exe"  # must return empty before proceeding
```

### .age3Yscn scenario selection

The following `.age3Yscn` files already exist in:
```
/var/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Scenario/
```

Confirmed present files relevant to this harness:
- `ANEWWORLD.age3Yscn` — primary ANW map, used by existing hubtest
- `ANEWWORLD_TEST_ANWAI.age3Yscn` — AI-specific test variant
- `legendary-leaders-ai.age3Yscn` — LL AI test scenario
- `Legendary Leaders Test.age3Yscn` — alternate LL test

**Recommendation:** Use `ANEWWORLD.age3Yscn` for all 6 passes. This is the map already proven by `hubtest_archive_log.sh`. The harness sets the AI player slots (7 civs) programmatically via the `-scenario` launch argument.

**Caveats:** The existing scenarios may have hardcoded AI slot assignments baked into the scenario file itself. If pass civs don't match baked slots, the scenario will load but AI personalities won't match the intended civ set. The harness supervisor should use a **generic 7-AI-slot scenario** and confirm that the correct `.personality` files are being loaded. The user should verify scenario slot configuration manually in the scenario editor at least once before the first full automated run.

**One-time bake procedure (if needed):** Launch AoE3 via Steam. Navigate Single Player → Scenario Editor. Open `ANEWWORLD.age3Yscn`. Verify 7 AI slots are set to "Any AI" (not hardcoded civs). Save. Exit editor and close game. This canonicalises the slot config for harness use.

### Pass-to-Civ map (from `hubtest_archive_log.sh`)

```python
PASS_CIVS = {
    1: ["ANWCanadians", "ANWAztecs", "ANWBarbary", "ANWBrazil", "ANWGermans", "ANWArgentines", "ANWChileans"],
    2: ["ANWHaitians", "ANWBritish", "ANWHausa", "ANWItalians", "ANWColumbians", "ANWChinese", "ANWIndonesians"],
    3: ["ANWDutch", "ANWRomanians", "ANWMexicans", "ANWHaudenosaunee", "ANWEgyptians", "ANWMayans", "ANWPortuguese"],
    4: ["ANWRussians", "ANWRevFrance", "ANWHungarians", "ANWEthiopians", "ANWSouthAfricans", "ANWUSA", "ANWJapanese"],
    5: ["ANWFinnish", "ANWLakota", "ANWFrench", "ANWNapoleonicFrance", "ANWInca", "ANWSpanish", "ANWIndians"],
    6: ["ANWSwedes", "ANWMaltese", "ANWTexians", "ANWOttomans", "ANWPeruvians"],
}
```

Passes 1–5: 7 civs each (fills all AI slots). Pass 6: 5 civs (slots 6–7 vacant or filled with any non-test civ).

---

### File: `tools/aoe3_harness/__init__.py`

```python
"""ANW Test Harness — umu-run-based, gamescope-free probe capture pipeline.

Public API:
    from tools.aoe3_harness.launch import launch_game, kill_stale
    from tools.aoe3_harness.supervisor import run_pass
    from tools.aoe3_harness.validator import validate_pass
"""

__version__ = "0.1.0"
```

---

### File: `tools/aoe3_harness/launch.py`

```python
"""Game launch via umu-run (gamescope-free, Steam-independent).

Environment contract:
  - /usr/bin/umu-run v1.4.0 (verified installed on Bazzite)
  - WINEPREFIX: ~/.local/share/Steam/steamapps/compatdata/933110/pfx
  - PROTONPATH: ~/.local/share/Steam/steamapps/common/Proton - Experimental
  - GAMEID: 933110
  - STEAM_COMPAT_CLIENT_INSTALL_PATH: ~/.local/share/Steam  (must be set explicitly;
    not in the shell environment by default)

Key constants (verified paths):
  UMU_RUN      = Path("/usr/bin/umu-run")
  EXE_PATH     = Path("~/.local/share/Steam/steamapps/common/AoE3DE/AoE3DE_s.exe")
  WINEPREFIX   = Path("~/.local/share/Steam/steamapps/compatdata/933110/pfx")
  PROTONPATH   = Path("~/.local/share/Steam/steamapps/common/Proton - Experimental")
  GAMEID       = "933110"
  STEAM_COMPAT = Path("~/.local/share/Steam")

Fallback direct Proton invocation (if umu-run fails):
  SLR_ENTRY    = ~/.local/share/Steam/steamapps/common/SteamLinuxRuntime_4/_v2-entry-point
  PROTON_BIN   = ~/.local/share/Steam/steamapps/common/Proton - Experimental/proton
  The full fallback command is documented in phase1_system_verification.md §2.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional


def kill_stale() -> bool:
    """Kill any stale AoE3 DE processes from previous runs.

    Returns True if any processes were killed, False if none were running.
    Must be called before launch_game() to avoid double-launch.
    """
    ...  # pkill -f "AppId=933110"; sleep 2; verify pgrep empty


def build_env(extra: Optional[dict] = None) -> dict:
    """Build the subprocess environment for umu-run.

    Sets WINEPREFIX, PROTONPATH, GAMEID, STEAM_COMPAT_CLIENT_INSTALL_PATH.
    Merges with os.environ and any caller-supplied overrides.
    """
    ...


def launch_game(
    scenario: Optional[str] = None,
    extra_args: Optional[list[str]] = None,
    dry_run: bool = False,
) -> subprocess.Popen:
    """Launch AoE3 DE via umu-run.

    Args:
        scenario: Optional scenario filename (without path) to pass as
                  -scenario <name> to AoE3DE_s.exe.
        extra_args: Additional args appended after the exe path.
        dry_run: If True, print the command but do not execute.

    Returns:
        subprocess.Popen handle for the launched process.

    Raises:
        FileNotFoundError: if umu-run or AoE3DE_s.exe is missing.
        RuntimeError: if stale AoE3 processes are still running after kill_stale().
    """
    ...


def wait_for_exit(proc: subprocess.Popen, timeout: float = 1800.0) -> int:
    """Wait for the game process to exit, with a timeout.

    Returns the process exit code. Raises TimeoutError if timeout exceeded.
    """
    ...
```

> **Screenshot precondition — borderless windowed mode required**
>
> `launch.py` must include a preflight check before calling `umu-run`. Steps:
> 1. Read the AoE3 UserProfile.xml at:
>    `/var/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Player/UserProfile.xml`
>    (check the `76561198170207043/` path first; also probe the `Startup/` sibling if absent)
> 2. Parse the display-mode XML element (expected tag name `<displaymode>` or similar — grep the file to confirm the exact tag). Acceptable values: `"windowed"` or `"borderless windowed"`.
> 3. If exclusive fullscreen is detected: **log a clearly visible warning** that screenshots captured via `capture.py` will fail because DXVK direct-scanout bypasses the compositor. Recommend the user change Video Settings → Display Mode in-game. **Do not block the launch** — the harness continues, but the flag is set on the returned object so callers can conditionally skip screenshot steps.
>
> Rationale: in borderless windowed mode, Plasma's compositor composites the game window normally and `import -window <wid>` (ImageMagick X11) can read the pixels. In exclusive fullscreen, DXVK takes a direct scanout path that makes the framebuffer invisible to compositor-level tools. This is why `capture.py` uses `import -window` rather than a desktop-level grab — the latter would capture an empty black frame in fullscreen.

---

### File: `tools/aoe3_harness/supervisor.py`

```python
"""Per-pass orchestration: truncate log, wait for match, archive results.

Absorbs the logic of tools/validation/hubtest_archive_log.sh.

State file: tools/aoe3_harness/state.json (schema defined at bottom of this file).

Key constants:
  AGE3_LOG_PATH = Path("~/.local/share/Steam/steamapps/compatdata/933110/pfx/
                        drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt")
  AI_OUTPUT_GLOB = "Age3DEAIOutputPlayer*.txt"   # same Logs/ directory
  ARTIFACT_ROOT = Path("artifacts/validation/ai_playstyle/")
  MATCH_DURATION_S = 1260   # 21 minutes; matches hubtest_archive_log.sh

STATE_SCHEMA = {
    "last_run_ts": "ISO8601 string",
    "passes_complete": [1, 2, ...],          # list of completed pass numbers
    "passes_archive": {
        "1": "artifacts/validation/ai_playstyle/hubtest_pass1_<ts>/",
        ...
    },
    "civ_coverage": {
        "ANWBritish": {"probes": 42, "status": "PASS"},
        ...
    },
}
"""

import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tools.aoe3_automation.log_capture import snapshot_offset, read_since, AGE3_LOG_PATH
from tools.aoe3_harness.launch import launch_game, kill_stale, wait_for_exit


PASS_CIVS: dict[int, list[str]] = {
    1: ["ANWCanadians", "ANWAztecs", "ANWBarbary", "ANWBrazil", "ANWGermans", "ANWArgentines", "ANWChileans"],
    2: ["ANWHaitians", "ANWBritish", "ANWHausa", "ANWItalians", "ANWColumbians", "ANWChinese", "ANWIndonesians"],
    3: ["ANWDutch", "ANWRomanians", "ANWMexicans", "ANWHaudenosaunee", "ANWEgyptians", "ANWMayans", "ANWPortuguese"],
    4: ["ANWRussians", "ANWRevFrance", "ANWHungarians", "ANWEthiopians", "ANWSouthAfricans", "ANWUSA", "ANWJapanese"],
    5: ["ANWFinnish", "ANWLakota", "ANWFrench", "ANWNapoleonicFrance", "ANWInca", "ANWSpanish", "ANWIndians"],
    6: ["ANWSwedes", "ANWMaltese", "ANWTexians", "ANWOttomans", "ANWPeruvians"],
}

MATCH_DURATION_S = 1260   # 21 minutes; matches hubtest_archive_log.sh
ARTIFACT_ROOT = Path(__file__).resolve().parents[2] / "artifacts" / "validation" / "ai_playstyle"
STATE_PATH = Path(__file__).resolve().parent / "state.json"
SCENARIO_FILE = "ANEWWORLD.age3Yscn"


def run_pass(
    pass_number: int,
    dry_run: bool = False,
    skip_launch: bool = False,
) -> Path:
    """Run one hub-test pass end-to-end.

    Steps:
      1. Validate pass_number is in PASS_CIVS.
      2. Kill stale AoE3 processes.
      3. Snapshot Age3Log.txt byte offset.
      4. Also snapshot offsets for any existing Age3DEAIOutputPlayer*.txt files.
      5. Launch game via launch.launch_game(scenario=SCENARIO_FILE).
      6. Print the civ list for this pass (user sets up lobby manually).
      7. Sleep MATCH_DURATION_S.
      8. Archive Age3Log.txt delta to artifacts/validation/ai_playstyle/hubtest_passN_<ts>/Age3Log.txt.
      9. Also copy per-AI files (full file, not delta) to the same archive dir.
      10. Emit probe-count summary (grep for [LLP v=2], milestone.first_wall_segment,
          milestone.first_barracks, posture.snapshot).
      11. Update state.json.
      12. Return the archive directory Path.

    Args:
        pass_number: 1–6.
        dry_run: Print steps but do not execute game launch or log mutations.
        skip_launch: For re-archiving an already-running match (advanced use).
    """
    ...


def archive_pass(pass_number: int, log_content: str, ai_log_paths: list[Path]) -> Path:
    """Write the archived pass directory and return its path."""
    ...


def update_state(pass_number: int, archive_dir: Path, civ_results: dict) -> None:
    """Read state.json, update, and write back atomically."""
    ...


def probe_summary(log_content: str) -> dict:
    """Return counts of key probe tag types in the log content."""
    ...
```

---

### File: `tools/aoe3_harness/log_tail.py`

```python
"""Async tail of Age3Log.txt and per-AI output files.

Used by supervisor.py to provide live probe feedback during a match,
and to detect a match-complete marker if one is added in the future.

NOTE: Phase 0 does not require a completion marker — the match runs for
MATCH_DURATION_S and supervisor waits that fixed duration. This module
is a quality-of-life enhancement and preparation for Phase 1 event-driven
completion detection.

Key paths:
  AGE3_LOG_PATH — from log_capture module
  AI_OUTPUT_DIR — same Logs/ directory, glob Age3DEAIOutputPlayer*.txt
"""

import threading
import time
from pathlib import Path
from typing import Callable, Optional


def tail_file(
    path: Path,
    callback: Callable[[str], None],
    poll_interval: float = 0.5,
    stop_event: Optional[threading.Event] = None,
) -> threading.Thread:
    """Tail a file and call callback for each new line.

    Returns a daemon thread. Caller must set stop_event to stop tailing.
    """
    ...


def tail_all(
    callback: Callable[[str, str], None],  # (filename, line)
    poll_interval: float = 0.5,
    stop_event: Optional[threading.Event] = None,
) -> list[threading.Thread]:
    """Tail Age3Log.txt and all Age3DEAIOutputPlayer*.txt in parallel.

    Returns a list of daemon threads.
    """
    ...
```

---

### File: `tools/aoe3_harness/scenario_runner.py`

```python
"""Per-pass scenario setup helpers.

Manages the scenario file selection, pass-civ printing, and match lifecycle.

Scenario file location:
  /var/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/
  pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Scenario/ANEWWORLD.age3Yscn

The harness does NOT automate the lobby (no xdotool; Wine ignores X11 synthetic events).
The user manually sets up the 7-AI lobby after the game launches. The supervisor
prints the civ list and waits.
"""

from pathlib import Path
from typing import Optional

SCENARIO_DIR = Path(
    "/var/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110"
    "/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE"
    "/76561198170207043/Scenario"
)


def print_pass_setup_instructions(pass_number: int, civs: list[str]) -> None:
    """Print the civ list and lobby setup instructions for the user.

    Called after game launch, before the sleep timer starts.
    """
    ...


def verify_scenario_exists(filename: str = "ANEWWORLD.age3Yscn") -> bool:
    """Verify the target scenario file is present in the Scenario directory.

    Raises FileNotFoundError if missing (supervisor should abort).
    """
    ...
```

---

### File: `tools/aoe3_harness/validator.py`

```python
"""Wrapper around validate_doctrine_compliance.py for harness integration.

Thin subprocess wrapper so the harness CLI can call validation without
importing the (large) validator module directly.

Key paths:
  VALIDATOR_SCRIPT = tools/validation/validate_doctrine_compliance.py
  DEFAULT_ARTIFACT_ROOT = artifacts/validation/ai_playstyle/
"""

import subprocess
import sys
from pathlib import Path

VALIDATOR_SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "validation" / "validate_doctrine_compliance.py"
RELEASE_SITE_SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "validation" / "build_release_readiness_site.py"


def validate_pass(
    pass_number: Optional[int] = None,
    archive_dir: Optional[Path] = None,
    ai_log_paths: Optional[list[Path]] = None,
    allow_empty: bool = True,
    allow_fail: bool = False,
    json_out: Optional[Path] = None,
    html_out: Optional[Path] = None,
) -> int:
    """Run validate_doctrine_compliance.py on a pass archive or auto-discovery.

    Args:
        pass_number: If provided, discovers logs under hubtest_passN_*/
        archive_dir: Explicit archive dir (overrides pass_number discovery)
        ai_log_paths: Per-AI files to include via --ai-logs
        allow_empty: Pass --allow-empty (default True for harness use)
        allow_fail: Pass --allow-fail
        json_out: Path for --json output
        html_out: Path for --html output (None = harness default)

    Returns:
        subprocess exit code (0=pass, 1=fail, 2=error)
    """
    ...


def build_release_site() -> int:
    """Invoke build_release_readiness_site.py and return exit code."""
    ...
```

---

### File: `tools/aoe3_harness/cli.py`

```python
"""ANW Test Harness — single-command CLI entry point.

Usage:
  python3 -m tools.aoe3_harness.cli deploy [--check] [--dry-run]
  python3 -m tools.aoe3_harness.cli run --pass N [--dry-run]
  python3 -m tools.aoe3_harness.cli run --all-passes [--dry-run]
  python3 -m tools.aoe3_harness.cli validate [--civ TOKEN] [--allow-fail]
  python3 -m tools.aoe3_harness.cli report
  python3 -m tools.aoe3_harness.cli gate
  python3 -m tools.aoe3_harness.cli status

Subcommands:
  deploy    Run deploy_to_mod.py (and optionally validate_xs_scripts.py with --check)
  run       Truncate log, launch game, wait MATCH_DURATION_S, archive, validate
  validate  Re-run doctrine compliance on existing archived logs (no game launch)
  report    Rebuild release_readiness_site.html from current artifacts
  gate      Run run_all_validators.py (full static gate, no game)
  status    Print state.json summary: which passes complete, civ coverage

All subcommands accept --dry-run (passed through to deploy/launch).
"""

import argparse
import sys
from pathlib import Path


def cmd_deploy(args: argparse.Namespace) -> int:
    """Deploy mod; optionally run XS static checks first."""
    ...


def cmd_run(args: argparse.Namespace) -> int:
    """Run one or all passes via supervisor.run_pass()."""
    ...


def cmd_validate(args: argparse.Namespace) -> int:
    """Re-validate existing archived logs."""
    ...


def cmd_report(args: argparse.Namespace) -> int:
    """Rebuild release_readiness_site.html."""
    ...


def cmd_gate(args: argparse.Namespace) -> int:
    """Run full static validation gate."""
    ...


def cmd_status(args: argparse.Namespace) -> int:
    """Print state.json summary."""
    ...


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="python3 -m tools.aoe3_harness.cli",
        description="ANW Test Harness — gamescope-free probe capture pipeline",
    )
    ap.add_argument("--dry-run", action="store_true", help="print actions without executing")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_deploy = sub.add_parser("deploy", help="deploy mod + optional XS check")
    p_deploy.add_argument("--check", action="store_true", help="run validate_xs_scripts.py first")

    p_run = sub.add_parser("run", help="run one or all passes")
    run_grp = p_run.add_mutually_exclusive_group(required=True)
    run_grp.add_argument("--pass", dest="pass_number", type=int, choices=range(1, 7))
    run_grp.add_argument("--all-passes", action="store_true")

    p_val = sub.add_parser("validate", help="re-validate archived logs")
    p_val.add_argument("--civ", action="append", default=[], help="filter to civ token")
    p_val.add_argument("--allow-fail", action="store_true")

    sub.add_parser("report", help="rebuild release readiness site")
    sub.add_parser("gate", help="run full static validator gate")
    sub.add_parser("status", help="show pass completion status")

    args = ap.parse_args()
    dispatch = {
        "deploy": cmd_deploy, "run": cmd_run, "validate": cmd_validate,
        "report": cmd_report, "gate": cmd_gate, "status": cmd_status,
    }
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
```

---

### File: `tools/aoe3_harness/state.json` (initial)

```json
{
  "last_run_ts": null,
  "passes_complete": [],
  "passes_archive": {},
  "civ_coverage": {}
}
```

---

### File: `tools/aoe3_harness/capture.py`

**Absolute path:** `/var/home/jflessenkemper/AOE-3-DE-A-New-World/tools/aoe3_harness/capture.py`  
**LOC budget:** ~60 LOC  

```python
"""
capture.py — screenshot the AoE3 game window without grabbing the cursor.

User constraint: no Claude Preview / kwin MCP / Claude-in-Chrome — those move the
real cursor. We use `import -window <wid>` (ImageMagick X11) as primary and
`grim -g "x,y wxh"` (Wayland portal) as fallback. Both are pure pixel reads.

This requires AoE3 to be in borderless windowed mode (NOT exclusive fullscreen),
otherwise DXVK direct-scanout bypasses Plasma's compositor and the pixels are
invisible to standard tools. The harness's launcher must verify this in user
config before launching; see launch.py.
"""

def find_aoe3_window() -> int | None:
    """Return AoE3 X11 window id, or None if not found.

    Uses: xdotool search --class 'AoE3DE_s' or xwininfo -root -tree
    parsed for the window with title containing 'Age of Empires III'.
    """

def capture_window(wid: int, out_path: Path) -> bool:
    """Capture AoE3 window pixels via `import -window <wid> <out_path>`.

    Returns True on success. Does NOT focus, raise, or move the window.
    """

def capture_region(x: int, y: int, w: int, h: int, out_path: Path) -> bool:
    """Wayland-portal fallback via `grim -g "{x},{y} {w}x{h}" <out_path>`.

    Only used when find_aoe3_window() fails (e.g. nested compositor scenario).
    """

def wait_for_ui_state(window_title_substring: str, timeout_s: int = 30) -> bool:
    """Poll xwininfo until AoE3's window title contains substring.

    Used by the manual-nav + auto-capture flow: user navigates to a UI state
    (e.g. home-city picker), the title may not change but we can poll for
    workflow timing if needed.
    """
```

**Verification command:**
```bash
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
python3 -c "from tools.aoe3_harness.capture import find_aoe3_window; print(find_aoe3_window())"
# Expected: prints an integer window id when AoE3 is running, or None when not
```

---

### Phase 1 verification commands

```bash
# 1. Confirm harness package is importable
cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
python3 -c "import tools.aoe3_harness; print(tools.aoe3_harness.__version__)"
# Expected: 0.1.0

# 2. Deploy subcommand (dry-run)
python3 -m tools.aoe3_harness.cli --dry-run deploy --check
# Expected: prints XS check command + deploy command, exits 0

# 3. Status subcommand
python3 -m tools.aoe3_harness.cli status
# Expected: prints "No passes complete" or state summary

# 4. Validate subcommand (offline — no game needed)
python3 -m tools.aoe3_harness.cli validate --allow-fail
# Expected: runs against existing artifacts; exits 0

# 5. Gate subcommand
python3 -m tools.aoe3_harness.cli gate
# Expected: same result as python3 tools/validation/run_all_validators.py
```

---

## Phase 2 — DLL Injection (BUILT 2026-05-29, live-game test deferred)

**Status:** Static verification PASSED (17/17). Hardening pass complete 2026-05-29.
**Version bump:** `tools/aoe3_harness/__init__.py` → 0.2.0

### Files added in Phase 2

| File | Purpose | LOC |
|------|---------|-----|
| `tools/aoe3_harness/dll/minhook/` | MinHook vendored as git submodule | — |
| `tools/aoe3_harness/dll/build.sh` | Build script (hello/hook/all/clean, --verbose) | ~190 |
| `tools/aoe3_harness/dll/anw_hook.c` | DllMain + worker thread + named pipe server | ~460 |
| `tools/aoe3_harness/dll/anw_dxgi_hook.c` | DXGI Present hook (always-on, vtable[8] verified) | ~290 |
| `tools/aoe3_harness/dll/anw_dxgi_hook.h` | DXGI hook public API | ~55 |
| `tools/aoe3_harness/dll/anw_hook.dll` | Built PE32+ DLL (x86-64) | — |
| `tools/aoe3_harness/dll/static_verify.sh` | 17-check static verification (--quiet mode) | ~140 |
| `tools/aoe3_harness/dll_client.py` | Python DllClient with Wine pipe socket bridge | ~334 |
| `tools/aoe3_harness/cli.py` | +input key/keydown/keyup/click/move/state, dll verify/status | +130 |
| `tools/aoe3_harness/tests/test_dll_client.py` | Unit tests: 41 tests, 100% line coverage | ~310 |
| `tools/aoe3_harness/README.md` | Package overview: build, verify, test, pitfalls | — |
| `artifacts/harness_design/phase2_verification_checklist.md` | Live-game test checklist | — |

### DLL build results (static verification)

```
tools/aoe3_harness/dll/hello_anw.dll: PE32+ executable for MS Windows 5.02 (DLL), x86-64, 19 sections
tools/aoe3_harness/dll/anw_hook.dll:  PE32+ executable for MS Windows 5.02 (DLL), x86-64, 19 sections
```

Imports: KERNEL32.dll, USER32.dll, msvcrt.dll
dxgi.dll and d3d11.dll are loaded at runtime via GetProcAddress (not static imports).

### Hardening pass (2026-05-29) — changes applied

1. **DXGI vtable index verified and hook enabled.**
   Source: `/usr/x86_64-w64-mingw32/sys-root/mingw/include/dxgi.h`, struct
   `IDXGISwapChainVtbl`. Slot-by-slot count confirms `IDXGISwapChain::Present =
   vtable[8]` (IUnknown:3 + IDXGIObject:4 + IDXGIDeviceSubObject:1 = 8 base
   slots).  The `#ifdef DXGI_HOOK_ENABLED` guards are removed; hook is always-on.
   Runtime NULL checks added for vtable and vtable[8] with log messages.

2. **Thread safety: g_pipe_handle data race fixed.**
   `g_pipe_handle` is written by the worker thread and read by DllMain detach.
   Fixed by routing all accesses through `atomic_pipe_set` / `atomic_pipe_get`
   (InterlockedExchangePointer). See audit comment block in `anw_hook.c`.

3. **Python unit tests: 41 tests, 100% line coverage.**
   `tools/aoe3_harness/tests/test_dll_client.py` using `unittest.mock`.
   All socket calls mocked; no game or Wine needed to run tests.

4. **build.sh hardened.**
   `clean` target, `--verbose` flag, distrobox/MinGW pre-flight checks,
   AoE3-running guard (`pgrep --exact`).

5. **static_verify.sh updated.**
   Now 17 checks (added `Present_hook` symbol check). Added `--quiet` mode,
   pre-flight artifact-missing warning, artifact-ordering note.

6. **Verification checklist polished.**
   Added "Before You Start", "Where to Find Logs", "What failure means" per
   section, "Rollback Instructions" section.

7. **README.md created.**
   Package overview, build/test/CLI quick-reference, pitfalls table.

### MinHook requires `-DUNICODE -D_UNICODE`

MinGW15's `hook.c` calls `GetModuleHandle(L"ntdll.dll")` which resolves to
`GetModuleHandleA` without UNICODE defined, causing a pointer-type error.
Fixed by adding both defines to the build command (present in build.sh).

### Named pipe serves multiple commands per session

The architecture doc implies one command per connection, but the implementation
keeps the connection open until EOF or QUIT. This matches the Python client's
usage pattern (one DllClient instance, multiple method calls).

### What is still deferred to live-game verification

The following require the game running with the DLL injected:

- Section 1: hello_anw.dll load test (`/tmp/anw_dll.log` appears)
- Section 2: anw_hook.dll load + DXGI hook confirm (log shows "Present hook installed")
- Section 3: STATE command over Unix socket
- Section 4: KEY injection (in-game unit response)
- Section 5: CLICK injection (coordinate calibration)
- Section 6: SCREENSHOT — hook fires (`[DXGI] Present_hook fired` in log), but
  the staging texture → Map → write BGRA pixel capture block is still a TODO
  in `Present_hook()` (see `anw_dxgi_hook.c`). Completing it requires verifying
  the D3D11 API calls work against the live DXVK swap-chain.
- Section 7: EAC guard test (multiplayer lobby)

See `artifacts/harness_design/phase2_verification_checklist.md`.

---

## Phase 2 — DLL Injection (original deferred section)

**Decision point:** Implement only if Phase 0+1 do not provide sufficient state visibility or if input automation into the game process is required (e.g. automated lobby setup without manual intervention).

**When to do this:**
- Phase 1 `run --pass N` still requires manual lobby setup (human clicks). Phase 2 provides automated lobby input via SendInput inside the Wine process.
- Phase 0 per-AI files provide probe data but not render-frame state or memory reads. Phase 2 d3d11/dxgi hooks provide frame timing and HUD state.
- **Phase 2 also becomes mandatory if** you want fully programmatic visual coverage of all 40 civ UI surfaces (home-city picker, AI picker, diplomacy, scoreboard) WITHOUT user clicking through them. The capture path from Phase 1 only delivers pixels; clicking through 40 menu states still requires user input because Wine ignores xdotool. Phase 2's `SendInput`-from-DLL solves this. For the immediate visual verification need (single click-through pass), Phase 1 is sufficient.

**Toolchain:** Distrobox `gs-build` (Fedora 43, ID `4d4878c05d81`) carries `mingw64-gcc`. Verify before starting:
```bash
distrobox enter gs-build -- dnf list mingw64-gcc mingw64-binutils
```

**Architecture sketch:**
- MinHook + d3d11/dxgi vtable hook DLL dropped into `windows/system32/` in the Proton prefix (physical file, not symlink — symlinks are shadowed by physical files in Wine's DLL search).
- Named pipe IPC channel `\\.\pipe\anwhook` — runtime socket path derived at supervisor startup from prefix inode (see `phase1_system_verification.md §7` for Python derivation code).
- SendInput calls for lobby automation (Wine process-internal; xdotool against Xwayland does NOT work — Wine ignores external X11 synthetic events by design).

**Estimated effort:** 3–5 engineering days. Complexity: High. User must choose depth before starting:
- **Option A (minimal):** Frame hook + named pipe only (no SendInput). Provides state visibility, not input control.
- **Option B (medium):** Add SendInput for lobby button clicks. Enables semi-automated passes.
- **Option C (full):** Complete lobby automation matching `exhibition_runner.py` fidelity but wine-process-internal.

Do not write code skeletons for Phase 2 here. Design happens in a separate session.

---

## Phase 3 — Headless CI (DEFERRED, Optional)

Pending Phase 1 stability. When Phase 1 produces reliable per-pass probe archives across all 6 passes without crashes, evaluate Xvfb + lavapipe (Mesa software renderer) for a fully headless CI pipeline. AoE3 DE uses d3d11; lavapipe's d3d11 via DXVK translation is functional but slower. A 21-minute game-time match at 1x speed requires the renderer to keep up; benchmarking is required before committing to this path. Xvfb setup: `Xvfb :99 -screen 0 1920x1080x24 &` + `DISPLAY=:99 LIBGL_ALWAYS_SOFTWARE=1 ...`.

---

## Files to Deprecate (Move to `tools/_archive/`)

From `pipeline_audit.md §12`:

| File | Reason |
|------|--------|
| `tools/aoe3_automation/afk_driver.py` | Superseded by exhibition_runner.py |
| `tools/aoe3_automation/afk_driver_v2.py` | Superseded |
| `tools/aoe3_automation/afk_driver_v2_full.py` | Superseded |
| `tools/aoe3_automation/anw_doctrine_capture_runner.py` | Superseded by Phase 1 harness |
| `tools/aoe3_automation/civ_matrix_driver.py` (v1 only, NOT v2) | Superseded by v2 |
| `tools/aoe3_automation/run_six_civ_oneshot*.py` (all three variants) | Early experiments |
| `tools/aoe3_automation/ei_inject*` | Dead libei injection experiment |
| `game/ai/core/aihcccards_orig.xs` | Stale backup copy; move or delete |

**Keep:** `tools/aoe3_automation/civ_matrix_driver_v2.py`, `lobby_driver.py`, `in_game_driver.py`, `gamescope_detect.py`, `log_capture.py`, `game_ctl.py`, `exhibition_runner.py`, `manage_game.py`.

---

## Verification Checklist (End-to-End)

A human can read through this list to confirm the implementation is complete.

- [ ] `user.cfg` contains `generateAIEchoesOutput` (bare token, no `=1`)
- [ ] `log_capture.py` `_REQUIRED_TOKENS` includes `"generateAIEchoesOutput"`
- [ ] `log_capture.py` `_DEV_CFG_CONTENT` includes `generateAIEchoesOutput` line
- [ ] `ensure_dev_mode()` self-test passes: `python3 -c "from tools.aoe3_automation.log_capture import _REQUIRED_TOKENS; assert 'generateAIEchoesOutput' in _REQUIRED_TOKENS"`
- [ ] Per-AI files appear in Proton `Logs/` dir after a match with `generateAIEchoesOutput` active
- [ ] Per-AI files contain `[LLP v=2]` probe lines (not just headers or empty)
- [ ] `validate_doctrine_compliance.py --help` shows `--ai-logs` flag
- [ ] `_auto_discover_logs` picks up both `match.log` and `Age3DEAIOutputPlayer*.txt` from artifact root
- [ ] `tools/aoe3_harness/__init__.py` importable without errors
- [ ] `python3 -m tools.aoe3_harness.cli --help` prints all subcommands
- [ ] `python3 -m tools.aoe3_harness.cli --dry-run deploy --check` exits 0
- [ ] `python3 -m tools.aoe3_harness.cli run --pass 1` launches game without gamescope
- [ ] Game process is a child of `umu-run`, not `gamescope`
- [ ] Game terminates cleanly (exit code 0 or user-initiated)
- [ ] Probe data archived to `artifacts/validation/ai_playstyle/hubtest_pass1_<ts>/`
- [ ] Archive dir contains `Age3Log.txt` (delta) and any `Age3DEAIOutputPlayer*.txt` copies
- [ ] `python3 -m tools.aoe3_harness.cli validate` runs against archived pass and produces output
- [ ] PASS/FAIL JSON written to archive dir or `artifacts/validation/`
- [ ] `python3 -m tools.aoe3_harness.cli report` runs `build_release_readiness_site.py` successfully
- [ ] HTML report visible at `artifacts/validation/release_readiness_site.html`
- [ ] `state.json` updated with pass 1 completion, civ coverage, timestamp
- [ ] Deprecated files moved to `tools/_archive/`
- [ ] All 6 passes run (40-civ coverage complete)
- [ ] `python3 -m tools.aoe3_harness.cli gate` exits 0 (all static validators pass)
- [ ] AoE3 launched in borderless windowed mode (preflight passed — `launch.py` did not emit a fullscreen-screenshot warning)
- [ ] `tools/aoe3_harness/cli.py capture --civ <X> --surface homecity_picker` produces a non-empty PNG that visually shows the expected civ selected

---

## Open Questions for the User (Parking Lot)

1. **Phase 2 depth choice:** Options A (frame hook only), B (+ lobby SendInput), or C (full exhibition_runner parity via Wine-internal input). This decision gates whether Phase 2 is worth the 3–5 day investment or if Phase 1 manual lobby is acceptable long-term.

2. **Release readiness site refresh cadence:** Should `build_release_readiness_site.py` be run automatically after each pass (inside `run --pass N`) or only on explicit `report` command? The site is slow to build on full 40-civ data. Recommend: build automatically only after `--all-passes` completes; manual `report` otherwise.

3. **Per-AI file per-match isolation:** `Age3DEAIOutputPlayer<N>.txt` is append-only (like `Age3Log.txt`). The current plan copies the full file to the archive dir but the validator will see probes from ALL prior matches, not just the current pass. This is acceptable for now (probes from any match are valid evidence), but if per-match isolation becomes important, extend `log_capture.py`'s offset-snapshot technique to these files and archive only the delta. This is a ~20-LOC addition to `supervisor.py`.

4. **Scenario slot configuration:** Confirm that `ANEWWORLD.age3Yscn` has generic "Any AI" slots (not hardcoded personalities) so the harness civ list matches what the engine actually loads. One manual scenario editor check recommended before first automated run.

5. **`PROTON_LOG=1` during harness runs:** The current Steam launch options include `PROTON_LOG=1 PROTON_LOG_DIR=/home/jflessenkemper`. Should the harness also set these? They produce a `proton_<date>.log` which can be useful for diagnosing launch failures but adds I/O overhead. Recommend enabling only during debugging runs.

---

## Appendix: Key Absolute Paths Reference

| Name | Absolute Path |
|------|---------------|
| `user.cfg` | `/var/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Startup/user.cfg` |
| `Age3Log.txt` | `/var/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt` |
| Per-AI output (expected) | `/var/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3DEAIOutputPlayer<N>.txt` |
| Scenario dir | `/var/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Scenario/` |
| Mod deploy target | `/var/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/mods/local/A New World` |
| `log_capture.py` | `/var/home/jflessenkemper/AOE-3-DE-A-New-World/tools/aoe3_automation/log_capture.py` |
| `validate_doctrine_compliance.py` | `/var/home/jflessenkemper/AOE-3-DE-A-New-World/tools/validation/validate_doctrine_compliance.py` |
| `hubtest_archive_log.sh` | `/var/home/jflessenkemper/AOE-3-DE-A-New-World/tools/validation/hubtest_archive_log.sh` |
| `aiUtilities.xs` | `/var/home/jflessenkemper/AOE-3-DE-A-New-World/game/ai/core/aiUtilities.xs` |
| `umu-run` | `/usr/bin/umu-run` (v1.4.0) |
| `AoE3DE_s.exe` | `/var/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/AoE3DE_s.exe` |
| `WINEPREFIX` | `/var/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/933110/pfx` |
| `PROTONPATH` | `/var/home/jflessenkemper/.local/share/Steam/steamapps/common/Proton - Experimental` |
| Distrobox gs-build | Fedora 43, ID `4d4878c05d81` |
| Harness package | `/var/home/jflessenkemper/AOE-3-DE-A-New-World/tools/aoe3_harness/` |
| Artifact root | `/var/home/jflessenkemper/AOE-3-DE-A-New-World/artifacts/validation/ai_playstyle/` |

---

## Phase 3 — "Until Perfect" Hardening (2026-05-29)

**Status: COMPLETE — all static work delivered**
**Base commits:** `03b6c5d` / `08a9625`

### Completed Items

| Item | File(s) | Status |
|------|---------|--------|
| DXGI staging-texture pixel pipeline (BMP output) | `dll/anw_dxgi_hook.c` | IMPLEMENTED — live-game DXVK validation pending |
| Inline BMP encoder (no libpng dependency) | `dll/anw_dxgi_hook.c` | IMPLEMENTED |
| D3D11 type forward-declarations (d3d11.h absent) | `dll/anw_dxgi_hook.c` | IMPLEMENTED |
| `dxgi_screenshot_hresult()` API for error reporting | `dll/anw_dxgi_hook.h`, `dll/anw_hook.c` | IMPLEMENTED |
| SCREENSHOT poll interval named constant (1ms) | `dll/anw_hook.c` | IMPLEMENTED |
| Hot-reload XS watcher (`inotify_simple` + poll fallback) | `hotreload.py` | IMPLEMENTED |
| Screenshot diff + heatmap module | `diff.py` | IMPLEMENTED |
| Screenshot diff unit tests (8 test cases) | `tests/test_diff.py` | IMPLEMENTED |
| Git-bisect doctrine regression wrapper | `bisect.py` | IMPLEMENTED |
| CLI: `hotreload start` subcommand | `cli.py` | IMPLEMENTED |
| CLI: `diff <before> <after> [--output]` subcommand | `cli.py` | IMPLEMENTED |
| CLI: `bisect --probe --civ --target --good --bad` | `cli.py` | IMPLEMENTED |
| `static_verify.sh` expanded: 16 → 20 checks | `dll/static_verify.sh` | IMPLEMENTED |
| README updated (hotreload, diff, bisect sections; 20 PASS note) | `README.md` | UPDATED |

### Design Decisions Taken Without Input

1. **d3d11.h absent** — MinGW cross-toolchain on this host has no D3D11 headers.
   Forward-declared all required D3D11 types manually, using MSDN SDK field
   ordering.  Vtable slot counts verified against MSDN reference documentation.
   Alternative (using distrobox to pull mingw64-directx-headers) would require
   a rebuild; the forward-declaration approach avoids that dependency.

2. **BMP output format** — Chose BMP (54-byte header + raw pixels) over raw BGRA
   because BMP is self-describing (width/height/format in header) and viewable
   without a custom reader.  Python `DllClient.screenshot()` docstring updated to
   say "BMP output" rather than "raw BGRA".

3. **`dxgi_screenshot_hresult()` added** — The original SCREENSHOT command could
   only report "OK" or "timeout".  Added a shared HRESULT store so the pipe
   command can report the actual D3D11 error code when the pipeline fails
   (e.g. `ERR HRESULT 0x887a0005` = DXGI_ERROR_DEVICE_REMOVED).

4. **ERR string changed** — `ERR DXGI_NOT_IMPLEMENTED` renamed to
   `ERR DXGI_NOT_INSTALLED` to accurately reflect the condition (hook not
   installed because D3D device creation failed in headless env).

5. **inotify_simple fallback** — Hot-reload uses inotify_simple if available,
   falls back to 1s polling.  `inotify_simple` was not added to requirements.txt
   (not confirmed as present in the env); the fallback is always available.

### Still Deferred to Live-Game

- DXVK staging texture pipeline correctness (Map() returns valid BGRA/RGBA pixels)
- Confirm `DXGI_FORMAT_B8G8R8A8_UNORM` vs `DXGI_FORMAT_R8G8B8A8_UNORM` for AoE3 back-buffer
  (relevant if BMP colors appear swapped — swap R/B channels in write_bmp() if needed)
- `exhibition_runner` non-interactive mode (required for `git bisect run` full automation)
- Screenshot/diff validation with actual game frames
