#!/usr/bin/env python3
"""Guard against capture scripts that call _screenshot_raw without registering
the harness backend.

WHY THIS EXISTS
---------------
`in_game_driver._screenshot_raw()` has two paths:
  (a) reliable  — compositor-framebuffer SCREENSHOT command via harness socket,
                  active only when `set_harness_backend()` has been called.
  (b) fragile   — xdotool-PrintScreen fallback, returns False on this rig.

A script that imports from `in_game_driver` or `lobby_driver` and calls the
bare free function `_screenshot_raw(` WITHOUT also calling `set_harness_backend`
will silently fail every capture at runtime. This is the exact bug that made
every anw_building_tour.py capture return FAILED.

By contrast, instance methods like `c.screenshot(...)` on a HarnessClient, or
custom `snap(...)` wrappers around them, are safe—they do NOT require backend
registration.

This validator statically scans every `tools/aoe3_automation/*.py` to detect
only the bare `_screenshot_raw(` pattern in STANDALONE-runnable scripts (those
with an `if __name__ == "__main__"` guard) and exits non-zero if any offender
is found. Library-only modules with no entry point are skipped — they are
always invoked from a parent runner that registers the backend.

Usage::

    python3 tools/validation/validate_capture_backend.py
    python3 tools/validation/validate_capture_backend.py --list
    python3 tools/validation/validate_capture_backend.py --dir /path/to/aoe3_automation
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCAN_DIR = REPO_ROOT / "tools" / "aoe3_automation"

# ---- patterns -----------------------------------------------------------------

# Imports that indicate a script drives the game via the automation drivers.
RE_DRIVER_IMPORT = re.compile(
    r'(?:from\s+tools\.aoe3_automation\.|import\s+)'
    r'(?:in_game_driver|lobby_driver)'
)

# Bare _screenshot_raw call (not preceded by ., indicating it's the free function).
RE_CAPTURE_CALL = re.compile(
    r'(?<!\.)_screenshot_raw\s*\('
)

# Backend registration — direct call OR assignment pattern used by wrappers.
RE_SET_BACKEND = re.compile(r'\bset_harness_backend\s*\(')

# Scripts that import set_harness_backend from in_game_driver count as
# potentially registering it (they will call it from a wrapper/fixture).
RE_IMPORT_SET_BACKEND = re.compile(
    r'from\s+tools\.aoe3_automation\.in_game_driver\s+import[^;#\n]*set_harness_backend'
)

# A standalone-runnable script has a __main__ guard. Library-only modules (no
# entry point) are ALWAYS invoked from a parent runner that registers the
# backend, so they must NOT be flagged — enforcing registration on them is a
# false positive (e.g. av_probe.py, imported by matrix_runner.py).
RE_ENTRYPOINT = re.compile(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]')


def _scan_file(path: Path) -> dict:
    """Return analysis dict for one file.

    Keys:
        drives_game   - imports in_game_driver or lobby_driver
        has_capture   - calls bare _screenshot_raw()
        has_backend   - calls or imports set_harness_backend
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"drives_game": False, "has_capture": False, "has_backend": False}

    drives_game = bool(RE_DRIVER_IMPORT.search(text))
    has_capture = bool(RE_CAPTURE_CALL.search(text))
    has_backend = bool(
        RE_SET_BACKEND.search(text) or RE_IMPORT_SET_BACKEND.search(text)
    )
    runnable = bool(RE_ENTRYPOINT.search(text))
    return {
        "drives_game": drives_game,
        "has_capture": has_capture,
        "has_backend": has_backend,
        "runnable": runnable,
    }


def scan_dir(scan_dir: Path) -> list[dict]:
    """Scan all .py files in scan_dir; return list of result dicts."""
    results = []
    for path in sorted(scan_dir.glob("*.py")):
        if path.name.startswith("__"):
            continue
        info = _scan_file(path)
        info["path"] = path
        # In scope only if it drives the game, calls a capture helper, AND is
        # standalone-runnable. Library-only modules (no __main__) are skipped:
        # their callers register the backend, so flagging them is a false positive.
        info["in_scope"] = (
            info["drives_game"] and info["has_capture"] and info["runnable"]
        )
        # Offender = in scope but never registers the backend.
        info["offender"] = info["in_scope"] and not info["has_backend"]
        results.append(info)
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--dir", type=Path, default=DEFAULT_SCAN_DIR,
        help="Directory to scan (default: tools/aoe3_automation)",
    )
    ap.add_argument(
        "--list", action="store_true",
        help="Print every scanned script with PASS/FAIL/SKIP status.",
    )
    args = ap.parse_args()

    if not args.dir.is_dir():
        print(f"ERROR: scan directory not found: {args.dir}", file=sys.stderr)
        return 2

    results = scan_dir(args.dir)
    offenders = [r for r in results if r["offender"]]
    in_scope  = [r for r in results if r["in_scope"]]

    if args.list:
        print(f"Scanned {len(results)} scripts in {args.dir}:")
        for r in results:
            if r["in_scope"]:
                status = "FAIL" if r["offender"] else "PASS"
            else:
                status = "SKIP"
            rel = r["path"].relative_to(REPO_ROOT)
            print(f"  [{status}] {rel}")
        print()

    if offenders:
        print(
            f"FAIL: {len(offenders)} capture script(s) call a screenshot helper "
            f"without registering the harness backend — screenshots will silently "
            f"fall back to the broken xdotool-PrintScreen path at runtime:"
        )
        for r in offenders:
            rel = r["path"].relative_to(REPO_ROOT)
            print(
                f"  {rel}: calls screenshot helper but never calls "
                f"set_harness_backend() — all captures will silently FAIL on this rig"
            )
        return 1

    scanned_msg = f"{len(in_scope)} in-scope script(s)" if in_scope else "no in-scope scripts"
    print(f"PASS: {scanned_msg} — all register the harness backend before capturing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
