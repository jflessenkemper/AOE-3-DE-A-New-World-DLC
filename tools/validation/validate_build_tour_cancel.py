#!/usr/bin/env python3
"""Guard against ESC-menu pause bug in anw_building_tour.py.

WHY THIS EXISTS
---------------
tools/aoe3_automation/anw_building_tour.py had an unconditional _key("Escape")
in the per-cell loop (line 203) intended to clear placement-mode ghosts. When no
ghost is pending (normal case after placing a building), pressing Escape opens
the in-game ESC menu instead, which PAUSES the game and derails the tour.

The fix: replace _key("Escape") with _rclick(*spot, delay=0.3), which:
  - Cancels a pending placement ghost if one exists (right-click = RTS primary command).
  - If no ghost is pending, it issues a harmless move-order on empty ground.
  - Never opens the ESC menu (the bug that derailed the tour).

This validator asserts that:
  1. anw_building_tour.py DOES call _rclick(x, y, ...) in its placement-cancel logic.
  2. anw_building_tour.py does NOT contain _key("Escape") or _key(VK_ESCAPE) that
     would reintroduce the ESC-menu pause bug.

If either condition fails, we exit non-zero with a clear message (FAIL).
If both pass, we exit 0 with PASS.

Usage::

    python3 tools/validation/validate_build_tour_cancel.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOUR_SCRIPT = REPO_ROOT / "tools" / "aoe3_automation" / "anw_building_tour.py"


def main() -> int:
    if not TOUR_SCRIPT.exists():
        print(f"ERROR: {TOUR_SCRIPT} not found", file=sys.stderr)
        return 2

    try:
        text = TOUR_SCRIPT.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"ERROR: could not read {TOUR_SCRIPT}: {e}", file=sys.stderr)
        return 2

    # Check 1: _rclick( is present (the fix).
    has_rclick = bool(re.search(r'_rclick\s*\(', text))

    # Check 2: no _key("Escape") or _key(VK_ESCAPE) that reintroduces the bug.
    # Match patterns like _key("Escape"), _key('Escape'), _key(VK_ESCAPE), etc.
    has_esc_bug = bool(re.search(
        r'_key\s*\(\s*(?:["\']Escape["\']|VK_ESCAPE)',
        text
    ))

    # Assess result.
    if not has_rclick:
        print(
            f"FAIL: {TOUR_SCRIPT.relative_to(REPO_ROOT)} does not call _rclick(...) "
            f"— the placement-cancel fix was not applied.",
            file=sys.stderr
        )
        return 1

    if has_esc_bug:
        print(
            f"FAIL: {TOUR_SCRIPT.relative_to(REPO_ROOT)} still contains "
            f"_key(\"Escape\") or _key(VK_ESCAPE) — the ESC-menu pause bug "
            f"would be reintroduced.",
            file=sys.stderr
        )
        return 1

    print(f"PASS: {TOUR_SCRIPT.relative_to(REPO_ROOT)} uses _rclick placement-cancel "
          f"and does not contain _key(Escape) ESC-menu pause bug.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
