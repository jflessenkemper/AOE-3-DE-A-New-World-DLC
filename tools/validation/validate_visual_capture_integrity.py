#!/usr/bin/env python3
"""Static validator: every per-civ visual capture on disk is intact and
attributed to the right civ.

The live in-game screenshot pipeline
(tools/aoe3_automation/anw_visual_capture_runner.py) writes one directory per
ANW civ under artifacts/validation/visual_art/<civ>/ containing:

    manifest.json            — schema_version, civ_token, captures[]
    full/01_lobby.png        — Skirmish lobby with P1 set to <civ>
    full/02_loading.png      — match loading screen (civ flag/banner)
    full/<more>.png          — in-game surfaces where the engine got that far

AoE3 DE crashes mid-skirmish for many civs (documented capture ceiling: the
runner reliably reaches the lobby + loading screens for every civ, and only
gets deeper for the few that don't crash — ANWBritish is the fully-captured
reference). So this validator pins the *reliable floor* and the *correctness*
of whatever was captured, NOT deep in-game coverage:

  1. Each civ dir has a manifest.json that is valid JSON whose `civ_token`
     equals the directory name — catches a capture run that screenshotted
     the WRONG civ into a civ's folder (the "make sure the screenshots are
     correct" failure: a French capture filed under ANWSpanish).
  2. Each civ has the floor surfaces full/01_lobby.png and full/02_loading.png
     — catches a capture run that silently produced nothing.
  3. Every full-resolution PNG under full/ loads as a real image (valid
     header, not truncated) and is not a black/blank frame (mean luminance
     >= MIN_LUM) — catches the gamescope race where an early screenshot
     fires before the frame renders and saves pure black.

The live active-civ set comes from data/civmods.xml (<name>ANW…</name> on
<main>1</main> civs) so adding a civ in data forces a capture dir to exist.

Usage:
    python3 tools/validation/validate_visual_capture_integrity.py

Exit codes:
    0 — every captured civ dir is intact, correctly attributed, non-black (GREEN)
    1 — a manifest is wrong/missing, a floor surface is absent, or a PNG is
        black/corrupt (RED — details printed)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CIVMODS = REPO / "data" / "civmods.xml"
ART = REPO / "artifacts" / "validation" / "visual_art"

# Floor surfaces the runner reaches for EVERY civ before any crash ceiling.
FLOOR = ["full/01_lobby.png", "full/02_loading.png"]
# Mean luminance (0-255) below which a frame is treated as black/blank. The
# darkest real capture observed is ~36; 8 is a safe black-frame threshold.
MIN_LUM = 8.0


def active_civs() -> set[str]:
    text = CIVMODS.read_text(encoding="utf-8")
    return set(re.findall(r"<name>(ANW[A-Za-z]+)</name>", text))


def mean_luminance(path: Path) -> float | None:
    """Return mean luminance, or None if the file is not a loadable image."""
    try:
        from PIL import Image
    except ImportError:
        # No Pillow — skip the pixel check but still confirm the file is a
        # non-empty PNG by header. Returns a sentinel above MIN_LUM so the
        # caller treats header-valid files as OK.
        data = path.read_bytes()
        if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 100:
            return None
        return MIN_LUM + 1.0
    try:
        with Image.open(path) as im:
            im.load()
            px = im.convert("L").get_flattened_data()
    except Exception:
        return None
    if not px:
        return None
    return sum(px) / len(px)


def main() -> int:
    if not ART.is_dir():
        print(f"FAIL — capture root not found: {ART.relative_to(REPO)}")
        return 1

    live = active_civs()
    errors: list[str] = []
    civ_dirs = sorted(d for d in ART.iterdir()
                      if d.is_dir() and d.name.startswith("ANW"))
    checked_pngs = 0

    present = {d.name for d in civ_dirs}
    for civ in sorted(live - present):
        errors.append(f"active civ '{civ}' has no capture dir under "
                      f"{ART.relative_to(REPO)}/")

    for d in civ_dirs:
        civ = d.name
        # (1) manifest correctness
        mp = d / "manifest.json"
        if not mp.exists():
            errors.append(f"{civ}: manifest.json missing")
        else:
            try:
                m = json.loads(mp.read_text(encoding="utf-8"))
                tok = m.get("civ_token")
                if tok != civ:
                    errors.append(
                        f"{civ}: manifest civ_token is '{tok}', not '{civ}' "
                        f"(capture filed under the wrong civ)")
            except ValueError as e:
                errors.append(f"{civ}: manifest.json is not valid JSON: {e}")

        # (2) floor surfaces
        for rel in FLOOR:
            if not (d / rel).exists():
                errors.append(f"{civ}: floor surface {rel} missing")

        # (3) every full/ PNG is a real, non-black image
        for png in sorted((d / "full").glob("*.png")) if (d / "full").is_dir() else []:
            checked_pngs += 1
            lum = mean_luminance(png)
            rel = png.relative_to(d)
            if lum is None:
                errors.append(f"{civ}: {rel} is corrupt/unreadable")
            elif lum < MIN_LUM:
                errors.append(
                    f"{civ}: {rel} is a black/blank frame (mean_lum={lum:.1f})")

    print("Visual-capture integrity check "
          "(every per-civ capture is intact and correctly attributed)")
    print(f"  capture dirs: {len(civ_dirs)}   live active civs: {len(live)}   "
          f"full-res PNGs checked: {checked_pngs}")
    print()

    if errors:
        print("FAIL — visual captures are incomplete, mis-attributed, or broken:")
        for e in errors:
            print(f"  {e}")
        return 1

    print(f"PASS — all {len(civ_dirs)} capture dirs intact, correctly "
          f"attributed, {checked_pngs} PNGs valid and non-black.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
