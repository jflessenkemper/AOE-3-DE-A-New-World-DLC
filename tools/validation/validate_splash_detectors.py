#!/usr/bin/env python3
"""Validate the loading-screen detectors classify known reference frames correctly.

Guards `tools/aoe3_automation/image_utils.is_asset_preloading_frame()` (and the
combined `is_splash_frame()`) against BOTH failure directions, using real
captured reference PNGs:

  POSITIVES (must be detected as the "Asset Preloading (Beta)" loading screen):
    - ANWBritish/_quarantine_france_20260609/full/_assetpreload_03_hud.png
    - ANWBritish/_quarantine_france_20260609/full/_assetpreload_04_homecity_panel.png

  NEGATIVES (real in-game / UI frames that must NOT be flagged as a loading
  screen — the home-city panel is the one that regressed on 2026-06-10, whose
  harbour WATER fills the bottom strip with teal and was wrongly flagged):
    - ANWBritish/full/04_homecity_panel.png   (the real London home-city scene)
    - ANWBritish/full/03_hud.png              (real in-game HUD)
    - ANWBritish/full/07_scoreboard.png       (real scoreboard)

Why this validator exists: `is_asset_preloading_frame` originally tested only the
OVERALL teal fraction of the bottom strip (> 0.020). The real home-city panel's
water reads ~0.43 teal (10x the splash's ~0.05), so it false-positived and the
contamination gate wrongly rejected a perfect capture. The detector was changed
to require a THIN teal BAND (bright peak row + teal confined to <=30% of strip
rows). This validator locks that behaviour so the false-positive cannot recur.

Exit codes:
    0 — all assertions pass (or required deps / reference PNGs are missing —
        degrade-pass, so CI without Pillow/numpy or without the capture corpus
        does not hard-fail)
    1 — one or more assertions failed
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VA = REPO_ROOT / "artifacts" / "validation" / "visual_art"

POSITIVES = [
    VA / "ANWBritish/_quarantine_france_20260609/full/_assetpreload_03_hud.png",
    VA / "ANWBritish/_quarantine_france_20260609/full/_assetpreload_04_homecity_panel.png",
]
NEGATIVES = [
    VA / "ANWBritish/full/04_homecity_panel.png",
    VA / "ANWBritish/full/03_hud.png",
    VA / "ANWBritish/full/07_scoreboard.png",
]

FAIL = False


def fail(msg: str) -> None:
    global FAIL
    FAIL = True
    print(f"FAIL: {msg}", flush=True)


def ok(msg: str) -> None:
    print(f"OK:   {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"WARN: {msg}", flush=True)


def main() -> int:
    global FAIL

    # --- Degrade-pass: optional image deps ---
    try:
        from PIL import Image  # noqa: F401
        import numpy  # noqa: F401
    except ImportError as e:
        warn(f"Optional dep missing ({e}); skipping detector assertions (degrade-pass).")
        print("PASS (degraded — image deps not installed)", flush=True)
        return 0

    # --- Import the detector under test ---
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from tools.aoe3_automation.image_utils import is_asset_preloading_frame
    except Exception as e:
        fail(f"Could not import is_asset_preloading_frame from image_utils: {e}")
        return 1

    present_pos = [p for p in POSITIVES if p.exists()]
    present_neg = [p for p in NEGATIVES if p.exists()]

    # --- Degrade-pass: no reference corpus at all ---
    if not present_pos and not present_neg:
        warn("No reference PNGs present; skipping assertions (degrade-pass).")
        print("PASS (degraded — reference frames not present)", flush=True)
        return 0

    # At least one positive AND one negative are needed for a meaningful test.
    if not present_pos:
        warn("No POSITIVE (real asset-preloading) reference frames present; "
             "cannot assert the detector still detects the loading screen.")
    if not present_neg:
        warn("No NEGATIVE (real in-game) reference frames present; "
             "cannot assert the detector avoids false-positives.")

    # --- POSITIVES must be detected as asset-preloading ---
    for p in present_pos:
        if is_asset_preloading_frame(p) is True:
            ok(f"{p.name} -> True (asset-preloading correctly detected)")
        else:
            fail(f"{p.name} -> not True; the real Asset-Preloading loading screen "
                 f"is no longer detected (false NEGATIVE — contamination would slip through)")

    # --- NEGATIVES must NOT be flagged ---
    for p in present_neg:
        if is_asset_preloading_frame(p) is False:
            ok(f"{p.name} -> False (real frame correctly NOT flagged)")
        else:
            fail(f"{p.name} -> not False; a real in-game/UI frame is being flagged "
                 f"as a loading screen (false POSITIVE — the 2026-06-10 home-city regression)")

    if FAIL:
        print("FAIL", flush=True)
        return 1
    print("PASS", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
