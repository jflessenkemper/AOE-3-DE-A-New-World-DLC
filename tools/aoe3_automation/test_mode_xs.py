#!/usr/bin/env python3
"""Toggle the cLLTestModeAutoResignMs override in the deployed mod.

When enabled, every AI player auto-resigns once `xsGetTime() >= threshold_ms`.
For 46-civ validation runs, this lets each match end deterministically at a
fixed game-time without any UI navigation. The engine declares the resign,
fires victory for the human player, and the harness only needs to navigate
the post-match screen back to the main menu.

This patches the *source* tree (not deployed) so a subsequent
`manage_game.py sync` will deploy the override. Always pair `enable()` with a
`disable()` in a finally block to leave the source tree clean.

Usage as library:
    from tools.aoe3_automation.test_mode_xs import enable, disable

    enable(threshold_ms=60000)         # AI auto-resigns at 60s game-time
    try:
        run_match_loop(...)
    finally:
        disable()                       # revert to production (cLL... = 0)

Usage as CLI:
    python3 test_mode_xs.py enable --threshold-ms 60000
    python3 test_mode_xs.py disable
    python3 test_mode_xs.py status
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

AI_HEADER = REPO_ROOT / "game" / "ai" / "aiHeader.xs"
BACKUP = REPO_ROOT / "game" / "ai" / ".aiHeader.xs.testmode_backup"

PATTERN = re.compile(
    r"^extern\s+int\s+cLLTestModeAutoResignMs\s*=\s*(\d+)\s*;",
    re.MULTILINE,
)


def current_threshold() -> int:
    """Return current cLLTestModeAutoResignMs value in source aiHeader.xs."""
    if not AI_HEADER.exists():
        raise FileNotFoundError(AI_HEADER)
    text = AI_HEADER.read_text()
    m = PATTERN.search(text)
    if not m:
        raise ValueError(
            f"could not find cLLTestModeAutoResignMs declaration in {AI_HEADER}"
        )
    return int(m.group(1))


def enable(threshold_ms: int = 60000) -> int:
    """Patch source aiHeader.xs to set cLLTestModeAutoResignMs = threshold_ms.

    Returns the previous value (so caller can restore exactly even if
    something is unusual).
    """
    if threshold_ms <= 0:
        raise ValueError(f"threshold_ms must be > 0; got {threshold_ms}")

    text = AI_HEADER.read_text()
    m = PATTERN.search(text)
    if not m:
        raise RuntimeError(
            f"cLLTestModeAutoResignMs not found in {AI_HEADER} — "
            "did the source format change?"
        )
    prev = int(m.group(1))

    # Backup once (we don't overwrite an existing backup)
    if not BACKUP.exists():
        shutil.copy2(AI_HEADER, BACKUP)

    # In-place substitution preserving the original whitespace/spacing
    new_text = PATTERN.sub(
        f"extern int cLLTestModeAutoResignMs = {threshold_ms};",
        text,
        count=1,
    )
    AI_HEADER.write_text(new_text)
    print(
        f"[test_mode_xs] enabled: cLLTestModeAutoResignMs {prev} -> {threshold_ms}",
        file=sys.stderr,
    )
    return prev


def disable() -> int:
    """Restore source aiHeader.xs to the pre-enable backup, or set value to 0.

    Returns the value that was just written.
    """
    if BACKUP.exists():
        shutil.copy2(BACKUP, AI_HEADER)
        BACKUP.unlink()
        v = current_threshold()
        print(
            f"[test_mode_xs] disabled (from backup): cLLTestModeAutoResignMs = {v}",
            file=sys.stderr,
        )
        return v

    # No backup; just zero the value
    text = AI_HEADER.read_text()
    new_text = PATTERN.sub("extern int cLLTestModeAutoResignMs = 0;", text, count=1)
    if new_text == text:
        print(
            "[test_mode_xs] disable: nothing to do (value already 0 / no decl)",
            file=sys.stderr,
        )
        return 0
    AI_HEADER.write_text(new_text)
    print(
        "[test_mode_xs] disabled: cLLTestModeAutoResignMs = 0 (no backup found)",
        file=sys.stderr,
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p_enable = sp.add_parser("enable", help="set threshold_ms in aiHeader.xs")
    p_enable.add_argument("--threshold-ms", type=int, default=60000)
    sp.add_parser("disable", help="restore aiHeader.xs to threshold = 0")
    sp.add_parser("status", help="print current threshold")
    args = ap.parse_args()

    if args.cmd == "enable":
        enable(args.threshold_ms)
    elif args.cmd == "disable":
        disable()
    elif args.cmd == "status":
        v = current_threshold()
        print(f"cLLTestModeAutoResignMs = {v}")
        if v > 0:
            print(f"  test mode ENABLED (auto-resign at {v} ms game-time)")
        else:
            print("  production mode (no auto-resign)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
