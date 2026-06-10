#!/usr/bin/env python3
"""Guard against STALE / WRONG-CIV building-tour screenshots in a civ capture dir.

Why this validator exists (the 2026-06-10 Britain regression):
    The per-civ capture pipeline has two phases that write into the SAME
    ``artifacts/validation/visual_art/<civ>/full/`` directory:

      1. The main runner (`anw_visual_capture_runner`) captures the ~11 core
         UI surfaces (01_lobby … 10_ai_homecity) and records each in
         ``manifest.json`` under ``captures[]`` with a ``captured_ms`` stamp.
      2. The OPTIONAL building tour (`anw_building_tour.run_building_tour`,
         enabled with ``--buildings``) places structures in-game and writes
         ``building_NN.png`` + ``build_command_card.png``.  These are NOT
         recorded in the manifest.

    The building tour always runs AFTER the core captures within one session,
    so a healthy ``building_*.png`` is NEWER than every core surface.  When a
    capture run is repeated for a civ WITHOUT ``--buildings`` (core surfaces get
    overwritten fresh, building shots do not), the directory is left with
    building shots from a PREVIOUS, possibly DIFFERENT-CIV session.  That is
    exactly what happened to ANWBritish: its core surfaces were a correct fresh
    LONDON capture (13:03) while its ``building_*.png`` were stale shots from an
    earlier run that was playing as the **Khedivate of Egypt / Cairo**
    (12:32–12:43) — wrong-civ images shown under "British" on the readiness
    site.

    A whole building set that PREDATES the civ's own core-surface capture is the
    fingerprint of this contamination.  This validator flags it so a wrong-civ
    building set can never silently ship again.

Rule (per active civ with a capture dir):
    If ``building_*.png`` exist AND core-surface PNGs exist, then the NEWEST
    building shot must not be older than the OLDEST core surface.  If the entire
    building set predates the core capture, the building tour was not re-run in
    the current session → STALE (likely wrong-civ) → FAIL.

Exit codes:
    0 — all assertions pass (or no capture dirs / no building shots — degrade-pass)
    1 — one or more civs have a stale building-tour set
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VA = REPO_ROOT / "artifacts" / "validation" / "visual_art"

# Core-surface filename prefixes written by the main runner (NOT the tour).
_CORE_PREFIXES = ("01_", "02_", "03_", "04_", "05_", "06_", "07_", "08_",
                  "09_", "10_")
# Tolerance: building tour legitimately starts a little after core capture; a
# small clock skew either way is fine.  We only care about a WHOLESALE predate
# (the building set is from an entirely earlier session), so allow the newest
# building shot to be up to this many seconds OLDER than the oldest core surface
# before we treat it as stale.
_STALE_TOLERANCE_S = 120.0

FAIL = False


def fail(msg: str) -> None:
    global FAIL
    FAIL = True
    print(f"FAIL: {msg}", flush=True)


def ok(msg: str) -> None:
    print(f"OK:   {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"WARN: {msg}", flush=True)


def _newest_mtime(paths: list[Path]) -> float:
    return max(p.stat().st_mtime for p in paths)


def _oldest_mtime(paths: list[Path]) -> float:
    return min(p.stat().st_mtime for p in paths)


def main() -> int:
    global FAIL

    if not VA.is_dir():
        warn(f"No visual_art dir at {VA}; skipping (degrade-pass).")
        print("PASS (degraded — no capture corpus)", flush=True)
        return 0

    civ_dirs = sorted(d for d in VA.iterdir()
                      if d.is_dir() and not d.name.startswith(("_", "batch_")))
    checked = 0
    for civ_dir in civ_dirs:
        full = civ_dir / "full"
        if not full.is_dir():
            continue
        building_shots = sorted(full.glob("building_*.png"))
        if not building_shots:
            continue  # building tour not run for this civ — nothing to verify
        core = [p for p in full.iterdir()
                if p.is_file() and p.name.startswith(_CORE_PREFIXES)
                and p.suffix == ".png"]
        if not core:
            warn(f"{civ_dir.name}: building shots present but no core surfaces; "
                 "cannot compare freshness.")
            continue

        checked += 1
        newest_building = _newest_mtime(building_shots)
        oldest_core = _oldest_mtime(core)
        # Stale iff the WHOLE building set is older than the oldest core surface
        # (beyond tolerance): the building tour was not re-run this session.
        if newest_building < oldest_core - _STALE_TOLERANCE_S:
            gap_min = (oldest_core - newest_building) / 60.0
            fail(f"{civ_dir.name}: building tour is STALE — newest building shot "
                 f"predates the oldest core surface by {gap_min:.1f} min "
                 f"({len(building_shots)} building PNGs). The building tour was "
                 f"not re-run in the current capture session, so these are "
                 f"leftover (possibly WRONG-CIV) images. Re-capture with "
                 f"--buildings.")
        else:
            ok(f"{civ_dir.name}: {len(building_shots)} building shots are fresh "
               f"(captured with/after the core surfaces).")

    if checked == 0:
        warn("No civ has building-tour shots to verify; skipping (degrade-pass).")
        print("PASS (degraded — no building tours captured)", flush=True)
        return 0

    if FAIL:
        print("FAIL", flush=True)
        return 1
    print("PASS", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
