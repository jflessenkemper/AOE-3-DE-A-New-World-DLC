#!/usr/bin/env python3
"""Static validator: the visual-capture runner must re-wire the harness after
every AoE3 relaunch.

Bug this pins (reproduced 2026-06-09): anw_visual_capture_runner.py drives the
live game and clicks through the AOE3DEHarness control socket (wired once at
startup by `_wire_harness()`). When a civ run relaunches the game — either via
`--force-relaunch-between-civs` or the defensive `aoe3_dead_pre_civ` path — it
`pkill`s AoE3 and starts a fresh process. The persistent harness socket from
`_wire_harness()` belonged to the DEAD process, so every click after the first
relaunch raises `[Errno 32] Broken pipe` and the civ fails at `click_skirmish`.
In the original 4-civ force-relaunch run this silently lost 3 of 4 civs (only
civ #0, which ran before any relaunch, succeeded). The fix is to call
`_wire_harness()` again immediately after each successful relaunch.

This validator locks that fix: every gating relaunch call site
(`if not _relaunch_aoe3()`) in the runner must be followed, within a small
line window, by a `_wire_harness()` re-wire — so a future edit can't drop the
re-wire and silently reintroduce the broken-pipe data loss.

Usage:
    python3 tools/validation/validate_harness_rewire_after_relaunch.py

Exit codes:
    0 — every relaunch site re-wires the harness (GREEN)
    1 — a relaunch site is missing its post-relaunch re-wire, or the runner
        file is unreadable (RED — details printed)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / "tools" / "aoe3_automation" / "anw_visual_capture_runner.py"

# A gating relaunch: the runner relaunches and bails the civ if it fails.
RELAUNCH_RE = re.compile(r"if\s+not\s+_relaunch_aoe3\s*\(")
REWIRE_RE = re.compile(r"_wire_harness\s*\(")
# How many lines after a relaunch site the re-wire must appear within. The
# re-wire is normally 5-8 lines down (past the `continue` failure branch).
WINDOW = 15

# Second guard (2026-06-09): inside _relaunch_aoe3() the function dismisses the
# weekly popup via harness MOVE/CLICK *before* returning to the caller, so the
# socket must be re-wired BEFORE that dismiss — otherwise every relaunch fires a
# broken-pipe (Errno 32) on a dead socket and the click silently degrades to
# xdotool (observed mid-run on the 33-civ deep sweep). This asserts the
# in-function _dismiss_weekly_popup() call is preceded, within REWIRE_BACK lines,
# by a _wire_harness() call inside _relaunch_aoe3's body.
RELAUNCH_DEF_RE = re.compile(r"^def\s+_relaunch_aoe3\s*\(")
ANY_DEF_RE = re.compile(r"^def\s+\w")
DISMISS_CALL_RE = re.compile(r"^\s*_dismiss_weekly_popup\s*\(\s*\)")
REWIRE_BACK = 12


def main() -> int:
    if not RUNNER.exists():
        print(f"FAIL — runner not found: {RUNNER.relative_to(REPO)}")
        return 1

    lines = RUNNER.read_text(encoding="utf-8").splitlines()
    sites = [i for i, ln in enumerate(lines) if RELAUNCH_RE.search(ln)]

    errors: list[str] = []
    for i in sites:
        window = lines[i + 1: i + 1 + WINDOW]
        if not any(REWIRE_RE.search(w) for w in window):
            errors.append(
                f"line {i + 1}: relaunch site has no _wire_harness() re-wire "
                f"within {WINDOW} lines — clicks will hit a broken pipe after "
                f"this relaunch")

    # Second guard: in-function popup dismiss must be preceded by a re-wire.
    relaunch_body: list[int] = []
    in_relaunch = False
    for i, ln in enumerate(lines):
        if RELAUNCH_DEF_RE.search(ln):
            in_relaunch = True
            continue
        if in_relaunch and ANY_DEF_RE.search(ln):
            in_relaunch = False
        if in_relaunch:
            relaunch_body.append(i)
    body_set = set(relaunch_body)
    dismiss_in_relaunch = [i for i in relaunch_body if DISMISS_CALL_RE.search(lines[i])]
    for i in dismiss_in_relaunch:
        back = [lines[j] for j in range(max(0, i - REWIRE_BACK), i) if j in body_set]
        if not any(REWIRE_RE.search(b) for b in back):
            errors.append(
                f"line {i + 1}: _dismiss_weekly_popup() inside _relaunch_aoe3 has "
                f"no _wire_harness() re-wire within the preceding {REWIRE_BACK} "
                f"lines — the popup dismiss will click through the dead pre-relaunch "
                f"socket (broken pipe, Errno 32)")

    print("Harness re-wire check (every game relaunch re-wires the harness socket)")
    print(f"  runner: {RUNNER.relative_to(REPO)}")
    print(f"  gating relaunch sites found: {len(sites)}")
    print(f"  in-function popup-dismiss sites found: {len(dismiss_in_relaunch)}")
    print()

    if not sites:
        # No gating relaunch sites at all is itself suspicious — the pattern
        # the validator guards has been renamed/removed; fail loudly so the
        # validator gets updated rather than silently passing on nothing.
        print("FAIL — no `if not _relaunch_aoe3()` sites found; the relaunch "
              "pattern changed and this validator needs updating.")
        return 1

    if not dismiss_in_relaunch:
        # The in-function popup dismiss moved/renamed — fail loudly rather than
        # silently pass the second guard on zero findings (false green).
        print("FAIL — no _dismiss_weekly_popup() call found inside _relaunch_aoe3; "
              "the in-function popup-dismiss pattern changed and this validator's "
              "second guard needs updating.")
        return 1

    if errors:
        print("FAIL — relaunch site(s) missing post-relaunch harness re-wire:")
        for e in errors:
            print(f"  {e}")
        return 1

    print(f"PASS — all {len(sites)} relaunch sites re-wire the harness "
          f"within {WINDOW} lines.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
