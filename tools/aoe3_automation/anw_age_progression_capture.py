#!/usr/bin/env python3
"""Interactive companion: capture per-age base overviews and army compositions.

Seven surfaces covering the full age progression from Colonial through Imperial:

    1. base_overview_colonial      — base layout after aging to Colonial (Age II)
    2. army_composition_colonial   — army units visible in Colonial Age
    3. base_overview_fortress      — base layout after aging to Fortress (Age III)
    4. army_composition_fortress   — army units visible in Fortress Age
    5. base_overview_industrial    — base layout after aging to Industrial (Age IV)
    6. army_composition_imperial   — army in Imperial Age
    7. base_overview_imperial      — base layout after aging to Imperial (Age V)

This script does NOT drive the game; the engine-state required (aging up,
mustering an army, zooming out, etc.) is reliably user-driven.  The script
sits in a wait-for-Enter loop, prompts the user to set up each game state,
and on Enter calls ``lobby_driver.screenshot()`` (gamescopectl primary +
X11 fallback — the same non-intrusive capture used for all other runners).
No mouse-grab, no keystroke injection.

Run while the game is open and AoE3 is the focused window:

    python3 tools/aoe3_automation/anw_age_progression_capture.py
    python3 tools/aoe3_automation/anw_age_progression_capture.py --civ ANWBritish
    python3 tools/aoe3_automation/anw_age_progression_capture.py --resume
    python3 tools/aoe3_automation/anw_age_progression_capture.py --force

Outputs:
- artifacts/validation/visual_art/{civ}/crops/<surface>.png
- artifacts/validation/visual_art/{civ}/thumbs/<surface>.webp
- artifacts/validation/visual_art/{civ}/manifest.json (updated in place)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

# PIL is used to generate the thumb webp.
from PIL import Image

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.aoe3_automation import lobby_driver  # noqa: E402

THUMB_MAX = 320


# ── Capture slot definitions ─────────────────────────────────────────────────
# (id, surface_name, age_label, prompt_text)
CAPTURE_SLOTS: list[tuple[int, str, str, str]] = [
    (
        21,
        "base_overview_colonial",
        "Age II Colonial",
        "Age to Colonial, zoom out to show your full base.\n"
        "  Use the scroll wheel / zoom key to pull back until most\n"
        "  of your base is visible on screen.",
    ),
    (
        22,
        "army_composition_colonial",
        "Age II Colonial",
        "Assemble your Colonial-Age army on screen.\n"
        "  Train or move your units so the main Colonial-Age force\n"
        "  is clearly visible (Musketeers, Pikemen, Dragoons, etc.).",
    ),
    (
        23,
        "base_overview_fortress",
        "Age III Fortress",
        "Age to Fortress, zoom out to show your full base.\n"
        "  Wait for the age-up to complete, then pull back the camera\n"
        "  so your expanded Fortress-Age base is visible.",
    ),
    (
        24,
        "army_composition_fortress",
        "Age III Fortress",
        "Assemble your Fortress-Age army on screen.\n"
        "  Train the Fortress-Age core units (Grenadiers, Hussars,\n"
        "  Artillery, etc.) and group them in view.",
    ),
    (
        25,
        "base_overview_industrial",
        "Age IV Industrial",
        "Age to Industrial, zoom out to show your full base.\n"
        "  After the Industrial age-up completes, pull the camera\n"
        "  back to show your full base layout.",
    ),
    (
        26,
        "army_composition_imperial",
        "Age V Imperial",
        "Age to Imperial, muster your final army on screen.\n"
        "  Train or recall your late-game force and ensure they are\n"
        "  visible (Imperial-Age units, Guard upgrades, heavy artillery).",
    ),
    (
        27,
        "base_overview_imperial",
        "Age V Imperial",
        "Zoom out to show your full Imperial-Age base.\n"
        "  Pull the camera back so the complete Imperial base layout\n"
        "  (all districts, walls, landmarks) is visible.",
    ),
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def out_dir(civ: str) -> Path:
    return REPO / "artifacts/validation/visual_art" / civ


def manifest_path(civ: str) -> Path:
    return out_dir(civ) / "manifest.json"


def load_manifest(civ: str) -> dict:
    mp = manifest_path(civ)
    if not mp.exists():
        # Seed a minimal manifest so the file exists for future writes.
        seed: dict = {"civ_token": civ, "captures": []}
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(json.dumps(seed, indent=2), encoding="utf-8")
        return seed
    return json.loads(mp.read_text(encoding="utf-8"))


def write_manifest(civ: str, mf: dict) -> None:
    manifest_path(civ).write_text(json.dumps(mf, indent=2), encoding="utf-8")


def already_captured(mf: dict, surface_name: str, civ: str) -> bool:
    """Return True if the crop file for *surface_name* already exists on disk."""
    for cap in mf.get("captures", []):
        for c in cap.get("crops", []):
            if c.get("name") == surface_name:
                crop_rel = c.get("crop_path", "")
                if crop_rel and (out_dir(civ) / crop_rel).exists():
                    return True
    return False


def write_thumb(src: Path, dest_webp: Path) -> None:
    with Image.open(src) as im:
        im = im.convert("RGBA")
        im.thumbnail((THUMB_MAX, THUMB_MAX), Image.LANCZOS)
        im.save(dest_webp, format="WEBP", quality=82, method=4)


def capture_surface(
    slot_id: int,
    surface_name: str,
    age_label: str,
    prompt: str,
    civ: str,
    *,
    force: bool,
) -> str:
    """Prompt the user, take a screenshot, save crops/thumbs, update manifest.

    Returns one of: 'captured', 'skipped_existing', 'user_skip', 'failed'.
    """
    base = out_dir(civ)
    crop_rel = f"crops/{surface_name}.png"
    thumb_rel = f"thumbs/{surface_name}.webp"
    crop_abs = base / crop_rel
    thumb_abs = base / thumb_rel

    # --- pre-flight: skip if already done and not forcing ---
    mf = load_manifest(civ)
    if not force and already_captured(mf, surface_name, civ):
        print(f"  --  {slot_id:02d}_{surface_name}: already captured — skipped"
              " (use --force to recapture)")
        return "skipped_existing"

    # --- user prompt ---
    print()
    print(f"=== [{slot_id}] {age_label} — {surface_name.replace('_', ' ').title()} ===")
    print(f"  {prompt.replace(chr(10), chr(10) + '  ')}")
    print()
    print("  [Enter] = capture now    [s] = skip this surface    [q] = quit")
    try:
        choice = input("  > ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "user_skip"
    if choice == "q":
        sys.exit(0)
    if choice == "s":
        return "user_skip"

    # Brief settle so any animation / tooltip has fully rendered.
    time.sleep(0.4)

    # --- screenshot ---
    full_dir = base / "full"
    full_dir.mkdir(parents=True, exist_ok=True)
    full_path = full_dir / f"{slot_id:02d}_{surface_name}.png"

    try:
        lobby_driver.screenshot(full_path)
    except Exception as exc:
        print(f"  WARN: screenshot failed: {exc}")
        return "failed"

    # --- crop + thumb ---
    crop_abs.parent.mkdir(parents=True, exist_ok=True)
    thumb_abs.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(full_path, crop_abs)
    write_thumb(full_path, thumb_abs)

    # --- manifest update ---
    mf = load_manifest(civ)

    # Find or create the capture entry for this slot id.
    capture_entry = None
    for cap in mf.get("captures", []):
        if cap.get("id") == slot_id:
            capture_entry = cap
            break
    if capture_entry is None:
        capture_entry = {
            "id": slot_id,
            "name": surface_name,
            "captured_ms": int(time.time() * 1000),
            "crops": [],
        }
        mf.setdefault("captures", []).append(capture_entry)
    else:
        capture_entry["captured_ms"] = int(time.time() * 1000)
        capture_entry["name"] = surface_name

    crop_record = {
        "name": surface_name,
        "crop_path": crop_rel,
        "thumb_path": thumb_rel,
    }
    # Replace any existing crop entry with this name, or append.
    found = False
    for i, c in enumerate(capture_entry["crops"]):
        if c.get("name") == surface_name:
            capture_entry["crops"][i] = crop_record
            found = True
            break
    if not found:
        capture_entry["crops"].append(crop_record)

    mf["synthesised"] = False
    mf["status"] = "complete"
    write_manifest(civ, mf)

    print(f"  captured {slot_id:02d}_{surface_name} -> {full_path.name}")
    return "captured"


# ── Entry point ───────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--civ",
        default="ANWBritish",
        help="Civ token to capture for (default: ANWBritish)",
    )
    ap.add_argument(
        "--resume",
        action="store_true",
        help="Skip surfaces already present on disk (same as default; kept for parity).",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Re-capture even if the crop file already exists on disk.",
    )
    ap.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="SURFACE",
        help="Capture only this surface_name. Repeatable.",
    )
    args = ap.parse_args(argv)

    civ = args.civ
    base = out_dir(civ)
    mp = manifest_path(civ)

    targets = CAPTURE_SLOTS
    if args.only:
        only = set(args.only)
        targets = [t for t in CAPTURE_SLOTS if t[1] in only]
        if not targets:
            print(f"ERROR: no capture slots match --only {args.only}", file=sys.stderr)
            return 2

    print(f"ANW age progression capture — civ: {civ}  ({len(targets)} surfaces queued)")
    print(f"Output:   {base.relative_to(REPO)}")
    print(f"Manifest: {mp.relative_to(REPO)}")
    print()
    print("Make sure AoE3 DE is running and focused. The script will pause")
    print("before each capture; navigate to the requested in-game state, then")
    print("press Enter to take the screenshot.  's' skips a surface, 'q' quits.")

    stats: dict[str, int] = {
        "captured": 0,
        "skipped_existing": 0,
        "user_skip": 0,
        "failed": 0,
    }

    for slot_id, surface_name, age_label, prompt in targets:
        result = capture_surface(
            slot_id,
            surface_name,
            age_label,
            prompt,
            civ,
            force=args.force,
        )
        stats[result] = stats.get(result, 0) + 1

    print()
    print("=== Summary ===")
    for k, v in stats.items():
        print(f"  {k:20s} = {v}")
    print()
    print("Next steps:")
    print("  python3 tools/build_civ_columns.py")
    print(f"  git add -u 'artifacts/validation/visual_art/{civ}/*'")
    print(f"  git commit -m '{civ}: age progression captures (base overviews + army compositions)'")
    print("  git push origin main")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
