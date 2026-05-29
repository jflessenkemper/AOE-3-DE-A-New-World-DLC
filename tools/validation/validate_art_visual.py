#!/usr/bin/env python3
"""Visual rendering verifier for ANW art (proof-of-concept harness).

Pipeline (per civ):

  1. Use ``ui_art_coords.json`` to know where each civ-specific asset lives
     on screen at 1920×1080.
  2. Take a fresh screenshot via ``gamescopectl screenshot``.
  3. Crop the screenshot at the documented (x, y, w, h).
  4. Compute the perceptual hash of the crop.
  5. Compute the perceptual hash of the EXPECTED source asset
     (resolved from ``art_inventory.json`` for the civ).
  6. Hamming-distance the two pHashes; classify PASS/WARN/FAIL.

Scope:

  * Designed as a HARNESS, not a full sweep. Run on 2-3 civs to prove the
    coords + comparison logic works.
  * Skip-able subsets: ``--lobby-only``, ``--hud-only``.
  * The caller is responsible for getting the game into the right UI state.
    Provide ``--no-screenshot`` to feed an existing PNG and just exercise
    the crop-and-compare path.

Default behaviour: assumes the game is already at the Skirmish lobby with
P1 set to the named civ (you set this up by hand or via lobby_driver). Run::

    python3 tools/validation/validate_art_visual.py --civ ANWBritish --lobby-only

prints a PASS/WARN/FAIL row per location.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable

REPO = Path(__file__).resolve().parents[2]
COORDS_FILE = Path(__file__).resolve().parent / "ui_art_coords.json"
INVENTORY_FILE = Path(__file__).resolve().parent / "art_inventory.json"
SCRATCH = Path("/tmp/anw_visual")
SCRATCH.mkdir(parents=True, exist_ok=True)

# Lazy imports
try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore

try:
    import imagehash  # type: ignore
except Exception:  # pragma: no cover
    imagehash = None  # type: ignore

# Reuse hashes from the static verifier
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_art_pixel_perfect import (  # noqa: E402
    PHASH_THRESHOLD_GOOD,
    PHASH_THRESHOLD_WARN,
    _phash,
)

# Skip these "kinds" — they're not civ-specific mod art
SKIP_KINDS = {"user_avatar_skip", "color_swatch_skip", "modal_chrome_skip"}


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------

def take_screenshot(out: Path) -> Path:
    """Drive gamescopectl to dump a 1920×1080 PNG to ``out``. Returns the
    path on success, raises on failure.
    """
    try:
        # Use the project's own gamescope detection so this works on Bazzite
        # rigs where DISPLAY changes per launch.
        sys.path.insert(0, str(REPO / "tools" / "aoe3_automation"))
        from gamescope_detect import get_both_env  # type: ignore
        env = get_both_env()
    except Exception:
        env = os.environ.copy()
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    subprocess.run(
        ["gamescopectl", "screenshot", str(out)],
        env=env, capture_output=True, timeout=15,
    )
    # gamescopectl returns rc=0 even when the file is written async — give it
    # a brief moment.
    for _ in range(20):
        if out.exists() and out.stat().st_size > 1000:
            return out
        time.sleep(0.1)
    if not out.exists():
        raise RuntimeError(f"screenshot did not appear at {out}")
    return out


# ---------------------------------------------------------------------------
# Crop + compare
# ---------------------------------------------------------------------------

def crop_box(im, box: dict) -> "Image.Image":
    """Crop an Image at the {x,y,w,h} dict from ui_art_coords.json."""
    x, y = box["x"], box["y"]
    w, h = box.get("w", 80), box.get("h", 80)
    return im.crop((x, y, x + w, y + h))


def expected_source_path(civ_record: dict, kind: str) -> str | None:
    """Resolve the expected on-disk source asset for a given coord 'kind'."""
    if kind in SKIP_KINDS:
        return None
    return civ_record.get(kind, "") or None


def compare_crops(crop_path: Path, source_path: Path) -> dict:
    a = _phash(crop_path)
    b = _phash(source_path)
    if a is None or b is None:
        return {"status": "WARN", "detail": "phash failed"}
    d = a - b
    if d <= PHASH_THRESHOLD_GOOD:
        return {"status": "PASS", "detail": f"phash dist={d}", "dist": d}
    if d <= PHASH_THRESHOLD_WARN:
        return {"status": "WARN", "detail": f"phash dist={d} (probably same)", "dist": d}
    return {"status": "FAIL", "detail": f"phash dist={d} (different art)", "dist": d}


def visual_check(
    civ_name: str,
    inventory: dict,
    coords: dict,
    screenshot_path: Path,
    sections: list[str],
) -> list[dict]:
    """For one civ + one screenshot, evaluate every (section.location) box
    listed in sections."""
    if Image is None:
        return [{"check": "visual", "status": "WARN",
                 "detail": "Pillow unavailable", "asset": civ_name}]
    rows: list[dict] = []
    civ_rec = inventory["civs"].get(civ_name)
    if civ_rec is None:
        return [{"check": "visual", "status": "FAIL",
                 "detail": f"civ {civ_name!r} not in art_inventory.json",
                 "asset": civ_name}]
    im = Image.open(screenshot_path)
    if im.size != (1920, 1080):
        rows.append({"check": "visual.dim_check", "status": "WARN",
                     "asset": civ_name,
                     "detail": f"screenshot is {im.size}, coords assume 1920x1080"})
    for section_name in sections:
        section = coords.get(section_name, {})
        for loc_name, loc in section.items():
            if loc_name.startswith("_"):
                continue
            if not isinstance(loc, dict) or "x" not in loc:
                continue
            kind = loc.get("kind", "")
            box_label = f"{section_name}.{loc_name}"
            if kind in SKIP_KINDS:
                rows.append({"check": "visual", "status": "PASS",
                             "asset": box_label, "civ": civ_name,
                             "detail": f"skipped (kind={kind})"})
                continue
            exp_rel = expected_source_path(civ_rec, kind)
            if not exp_rel:
                rows.append({"check": "visual", "status": "WARN",
                             "asset": box_label, "civ": civ_name,
                             "detail": f"no expected source for kind={kind!r}"})
                continue
            exp_path = REPO / exp_rel
            if not exp_path.exists():
                rows.append({"check": "visual", "status": "FAIL",
                             "asset": box_label, "civ": civ_name,
                             "detail": f"expected source missing: {exp_rel}"})
                continue
            crop = crop_box(im, loc)
            crop_path = SCRATCH / f"{civ_name}_{section_name}_{loc_name}.png"
            crop.save(crop_path)
            r = compare_crops(crop_path, exp_path)
            rows.append({"check": "visual", "asset": box_label, "civ": civ_name,
                         "status": r["status"], "detail": r["detail"],
                         "expected": str(exp_rel),
                         "crop": str(crop_path),
                         "confidence": loc.get("confidence", "")})
    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli(argv: Iterable[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--civ", action="append", default=[],
                    help="ANW civ name (can repeat). Default: ANWBritish")
    p.add_argument("--screenshot", default=None,
                    help="Use this PNG instead of taking a new screenshot")
    p.add_argument("--no-screenshot", action="store_true",
                    help="Don't take a screenshot; require --screenshot")
    p.add_argument("--lobby-only", action="store_true")
    p.add_argument("--hud-only", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true")
    args = p.parse_args(list(argv) if argv is not None else None)

    civs = args.civ or ["ANWBritish"]
    sections: list[str] = []
    if args.lobby_only:
        sections.append("skirmish_lobby")
    elif args.hud_only:
        sections.append("in_match_hud")
    else:
        sections = ["skirmish_lobby", "in_match_hud", "home_city"]

    coords = json.loads(COORDS_FILE.read_text(encoding="utf-8"))
    if not INVENTORY_FILE.exists():
        print("ERROR: art_inventory.json not present — run art_inventory.py first", file=sys.stderr)
        return 2
    inv = json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))

    # Screenshot
    if args.screenshot:
        shot = Path(args.screenshot)
        if not shot.exists():
            print(f"ERROR: screenshot {shot} not found", file=sys.stderr)
            return 2
    elif args.no_screenshot:
        print("ERROR: --no-screenshot requires --screenshot", file=sys.stderr)
        return 2
    else:
        shot = SCRATCH / "current.png"
        try:
            take_screenshot(shot)
        except Exception as e:
            print(f"ERROR: screenshot failed: {e}", file=sys.stderr)
            return 2

    all_rows: list[dict] = []
    for civ in civs:
        all_rows.extend(visual_check(civ, inv, coords, shot, sections))

    summary = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for r in all_rows:
        summary[r.get("status", "WARN")] = summary.get(r.get("status", "WARN"), 0) + 1

    if args.json:
        json.dump({"summary": summary, "rows": all_rows, "screenshot": str(shot)},
                  sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"=== Visual verifier (civs={civs}, sections={sections}) ===")
        print(f"screenshot: {shot}")
        print(f"PASS={summary.get('PASS', 0)}  WARN={summary.get('WARN', 0)}  FAIL={summary.get('FAIL', 0)}")
        for r in all_rows:
            print(f"  [{r['status']}] {r['civ']}/{r['asset']}: {r['detail']}")

    if summary.get("FAIL", 0):
        return 1
    if args.strict and summary.get("WARN", 0):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
