#!/usr/bin/env python3
"""Static validator: no captured in-game surface is secretly a loading screen.

Bug this pins (regression reproduced 2026-06-09): the visual-capture runner's
speed path (HUD_SETTLE_CONFIRMED=3) fires the screenshot a few seconds after
``wait_for_splash_clear()`` reports the loading screen is gone.  At the time,
the splash detector only recognised the bright-globe splash (screen 1) and was
blind to AoE3's *second* loading screen — "Asset Preloading (Beta)", a dark,
blurry frame with a teal progress bar.  So the runner captured the
Asset-Preloading screen INTO ANWBritish/full/03_hud.png and 04_homecity_panel.png:
both "in-game" surfaces were actually loading screens.

The existing visual_capture_integrity validator did NOT catch this — it only
checks that PNGs are non-black, and a loading screen is non-black (mean_lum
~38).  This validator closes that gap by classifying every captured surface
with the SAME detector the runner uses (image_utils.is_splash_frame), so a
capture that lands on either loading screen is flagged RED.

Only the genuine loading-screen surface (``02_loading.png``) is allowed to be
a loading screen; every other full/ surface must be a real game/UI frame.

Usage:
    python3 tools/validation/validate_no_loading_screen_contamination.py

Exit codes:
    0 — no in-game surface is a loading screen (GREEN)
    1 — a surface that should be a real frame is a loading screen, or the
        detector/Pillow is unavailable so the check could not run (RED)
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ART = REPO / "artifacts" / "validation" / "visual_art"

# The only surface allowed to BE a loading screen (it is one by design).
ALLOWED_LOADING_SURFACES = {"02_loading.png"}
# Fixture/calibration frames preserved on purpose (prefixed); skip them.
SKIP_PREFIXES = ("_assetpreload_",)

sys.path.insert(0, str(REPO))
try:
    from tools.aoe3_automation.image_utils import (  # noqa: E402
        is_splash_frame,
        is_globe_splash_frame,
        is_asset_preloading_frame,
        _PIL_AVAILABLE,
    )
except Exception as exc:  # pragma: no cover
    print(f"FAIL — cannot import image_utils splash detector: {exc!r}")
    sys.exit(1)


def main() -> int:
    if not _PIL_AVAILABLE:
        print("FAIL — Pillow unavailable; cannot classify captured frames. "
              "Install Pillow so loading-screen contamination can be detected.")
        return 1
    if not ART.is_dir():
        print(f"FAIL — capture root not found: {ART.relative_to(REPO)}")
        return 1

    civ_dirs = sorted(d for d in ART.iterdir()
                      if d.is_dir() and d.name.startswith("ANW"))
    errors: list[str] = []
    checked = 0

    for d in civ_dirs:
        full = d / "full"
        if not full.is_dir():
            continue
        for png in sorted(full.glob("*.png")):
            name = png.name
            if name in ALLOWED_LOADING_SURFACES:
                continue
            if name.startswith(SKIP_PREFIXES):
                continue
            checked += 1
            if is_splash_frame(png):
                which = ("globe-splash" if is_globe_splash_frame(png)
                         else "asset-preloading"
                         if is_asset_preloading_frame(png) else "loading")
                errors.append(
                    f"{d.name}/full/{name} is a {which} screen, not a real "
                    f"in-game/UI frame (captured mid-load)")

    print("Loading-screen contamination check "
          "(no in-game surface is secretly a loading screen)")
    print(f"  capture dirs: {len(civ_dirs)}   surfaces classified: {checked}")
    print()

    if errors:
        print("FAIL — captured surface(s) are loading screens:")
        for e in errors:
            print(f"  {e}")
        return 1

    print(f"PASS — all {checked} non-loading surfaces are real game/UI frames.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
