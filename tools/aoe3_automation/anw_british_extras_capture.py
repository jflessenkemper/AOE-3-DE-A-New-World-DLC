#!/usr/bin/env python3
"""Interactive companion: capture 10 additional ANWBritish review surfaces.

The current British v2 capture set (14 surfaces) is great for visual
confirmation of the lobby / loading / HUD / diplomacy / postgame / minimap
slices.  The mod-author has asked for these additional surfaces to round
out the review template (BRITISH is the canonical template; once polished
the same labels can be captured for other stable civs):

    1. age_up_colonial_select      — Age II politician menu
    2. age_up_fortress_select      — Age III politician menu
    3. age_up_industrial_select    — Age IV politician menu
    4. age_up_imperial_select      — Age V politician menu (if reachable)
    5. age_advancement_banner      — cinematic "I HAVE REACHED ..." banner
    6. hero_tooltip                — hover over Explorer hero name
    7. saloon_menu                 — Saloon mercenary roster
    8. town_center_under_construction — TC build scaffolding visible
    9. treaty_lobby_pregame        — pre-game lobby (treaty mode setup)
   10. deck_builder_lobby_decks    — HC deck builder UI in the lobby

This script does NOT drive the game; the engine-state required (aging up,
hovering, building a Saloon, etc.) is reliably user-driven.  The script
sits in a wait-for-Enter loop, prompts the user to set up each game state,
and on Enter calls ``lobby_driver.screenshot()`` (gamescopectl primary +
X11 fallback — the same non-intrusive capture used for the original 14
surfaces).  No mouse-grab, no keystroke injection.

Run while the game is open and AoE3 is the focused window:

    python3 tools/aoe3_automation/anw_british_extras_capture.py
    python3 tools/aoe3_automation/anw_british_extras_capture.py --resume
    python3 tools/aoe3_automation/anw_british_extras_capture.py --only saloon_menu

Outputs:
- artifacts/validation/visual_art_v2/ANWBritish/full/NN_<surface>.png
- artifacts/validation/visual_art/ANWBritish/crops/<surface>.png (mirrored)
- artifacts/validation/visual_art/ANWBritish/thumbs/<surface>.webp
- artifacts/validation/visual_art/ANWBritish/manifest.json (updated in place)

The column site picks the new entries up automatically on the next push
to main (Pages workflow trigger already covers crops/** and thumbs/**).
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

V2_DIR = REPO / "artifacts/validation/visual_art_v2/ANWBritish/full"
OUT_DIR = REPO / "artifacts/validation/visual_art/ANWBritish"
MANIFEST = OUT_DIR / "manifest.json"

THUMB_MAX = 320


# ── Surface definitions ──────────────────────────────────────────────────────
# (index, surface_name, label, prompt-the-user, optional-secondary-prompt)
SURFACES: list[tuple[str, str, str, str]] = [
    (
        "15_age_up_colonial",
        "age_up_colonial_select",
        "Age II — Colonial politician selection",
        "In-game as British. When you have enough resources, click the\n"
        "  Town Center age-up button. The POLITICIAN SELECTION dialog will\n"
        "  appear with the Age II (Colonial) options. With it on screen,",
    ),
    (
        "16_age_up_fortress",
        "age_up_fortress_select",
        "Age III — Fortress politician selection",
        "After reaching Colonial, age up again. The Age III politician\n"
        "  options should appear (Viceroy / Engineer / etc.). With the\n"
        "  dialog on screen,",
    ),
    (
        "17_age_up_industrial",
        "age_up_industrial_select",
        "Age IV — Industrial politician selection",
        "From Fortress, age up to Industrial. The Industrial-age politician\n"
        "  options will appear (General, Black Duke, King's Musketeer, etc.).",
    ),
    (
        "18_age_up_imperial",
        "age_up_imperial_select",
        "Age V — Imperial politician selection (if reachable)",
        "Aging to Imperial. Skip with 's' if you don't have time to reach\n"
        "  Imperial age this session.",
    ),
    (
        "19_age_advancement_banner",
        "age_advancement_banner",
        "Age advancement cinematic banner",
        "RIGHT AFTER selecting a politician, the screen shows a black-and-\n"
        "  gold cinematic 'I HAVE REACHED ...' banner for a few seconds.\n"
        "  Catch it during the transition. (If you missed it, age up again\n"
        "  on the next age and try then.)",
    ),
    (
        "20_hero_tooltip",
        "hero_tooltip",
        "Hero / Explorer tooltip showing leader name",
        "Hover the mouse cursor over your Explorer unit on the map (don't\n"
        "  click — just hover so the tooltip appears with the hero's name).",
    ),
    (
        "21_saloon_menu",
        "saloon_menu",
        "Saloon mercenary roster menu",
        "Build a Saloon (or have one available from a card / age-up).\n"
        "  Click the Saloon to select it. The training panel shows the\n"
        "  mercenary roster (Highlanders, etc. for British).",
    ),
    (
        "22_tc_under_construction",
        "town_center_under_construction",
        "Town Center under construction (scaffolding visible)",
        "Queue a second Town Center via a Settler Wagon or HC card, OR\n"
        "  watch your starting TC if it's still building. The scaffolded\n"
        "  TC must be visible on screen.",
    ),
    (
        "23_treaty_lobby_pregame",
        "treaty_lobby_pregame",
        "Pre-game treaty-mode lobby UI",
        "Back out to the main menu. Start SKIRMISH → set up a new match\n"
        "  with TREATY enabled (or any pre-game lobby with civ slots\n"
        "  visible). The treaty-mode lobby screen, before clicking START,",
    ),
    (
        "24_deck_builder_lobby",
        "deck_builder_lobby_decks",
        "Home City deck builder (lobby) showing decks",
        "In the lobby for the British civ, open the HOME CITY tab so the\n"
        "  deck builder is visible (deck list on left, card slots on right,\n"
        "  card pool on the bottom). With the deck builder on screen,",
    ),
]


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def write_manifest(mf: dict) -> None:
    MANIFEST.write_text(json.dumps(mf, indent=2), encoding="utf-8")


def already_captured(mf: dict, surface_name: str) -> bool:
    for cap in mf.get("captures", []):
        for c in cap.get("crops", []):
            if c.get("name") == surface_name:
                # Verify the file actually exists on disk
                crop_rel = c.get("crop_path", "")
                if crop_rel and (OUT_DIR / crop_rel).exists():
                    return True
    return False


def write_thumb(src: Path, dest_webp: Path) -> None:
    with Image.open(src) as im:
        im = im.convert("RGBA")
        im.thumbnail((THUMB_MAX, THUMB_MAX), Image.LANCZOS)
        im.save(dest_webp, format="WEBP", quality=82, method=4)


def capture_surface(label_idx: str, surface_name: str, label: str,
                    prompt: str, *, skip_existing: bool) -> str:
    """Returns one of: 'captured', 'skipped_existing', 'user_skip', 'failed'."""
    print()
    print(f"=== {label_idx}: {label} ===")
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

    # Brief settle for any tooltip / banner to fully render before we capture.
    time.sleep(0.4)

    full_path = V2_DIR / f"{label_idx}_{surface_name}.png"
    full_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        lobby_driver.screenshot(full_path)
    except Exception as exc:
        print(f"  WARN: screenshot failed: {exc}")
        return "failed"

    # Mirror into visual_art/ANWBritish/ for the column site.
    crop_rel = f"crops/{surface_name}.png"
    thumb_rel = f"thumbs/{surface_name}.webp"
    crop_abs = OUT_DIR / crop_rel
    thumb_abs = OUT_DIR / thumb_rel
    crop_abs.parent.mkdir(parents=True, exist_ok=True)
    thumb_abs.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(full_path, crop_abs)
    write_thumb(full_path, thumb_abs)

    # Mirror full into visual_art too (parity with v2 dir).
    mirror_full = OUT_DIR / "full" / f"{label_idx}_{surface_name}.png"
    mirror_full.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(full_path, mirror_full)

    # Update manifest in place.
    mf = load_manifest()
    capture_entry = None
    for cap in mf.get("captures", []):
        if cap.get("label") == label_idx:
            capture_entry = cap
            break
    if capture_entry is None:
        capture_entry = {
            "label": label_idx,
            "full_path": f"full/{label_idx}_{surface_name}.png",
            "captured_ms": int(time.time() * 1000),
            "ocr_text": None,
            "crops": [],
        }
        mf.setdefault("captures", []).append(capture_entry)
    else:
        capture_entry["captured_ms"] = int(time.time() * 1000)
        capture_entry["full_path"] = f"full/{label_idx}_{surface_name}.png"

    # Replace any existing crop with this name, or append.
    crop_record = {
        "name": surface_name,
        "crop_region": [0, 0, 1920, 1080],
        "crop_path": crop_rel,
        "thumb_path": thumb_rel,
    }
    found = False
    for i, c in enumerate(capture_entry["crops"]):
        if c.get("name") == surface_name:
            capture_entry["crops"][i] = crop_record
            found = True
            break
    if not found:
        capture_entry["crops"].append(crop_record)

    # Mark the manifest as having real captures (not synthesised).
    mf["synthesised"] = False
    mf["status"] = "complete"
    write_manifest(mf)

    print(f"  ✓ captured {surface_name} → {full_path.name}")
    return "captured"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", action="append", default=[],
                    help="Capture only this surface_name. Repeatable.")
    ap.add_argument("--resume", action="store_true",
                    help="Skip surfaces already present in the manifest.")
    args = ap.parse_args(argv)

    if not MANIFEST.exists():
        print(f"ERROR: manifest not found at {MANIFEST}", file=sys.stderr)
        return 2

    targets = SURFACES
    if args.only:
        only = set(args.only)
        targets = [t for t in SURFACES if t[1] in only]
        if not targets:
            print(f"ERROR: no surfaces match --only {args.only}", file=sys.stderr)
            return 2

    print(f"ANWBritish extras capture — {len(targets)} surfaces queued")
    print(f"Output:   {OUT_DIR.relative_to(REPO)}")
    print(f"Manifest: {MANIFEST.relative_to(REPO)}")
    print()
    print("Make sure AoE3 DE is running and focused. The script will pause")
    print("before each capture; navigate to the requested in-game state, then")
    print("press Enter to take the screenshot.  's' skips a surface, 'q' quits.")

    mf = load_manifest()
    stats = {"captured": 0, "skipped_existing": 0, "user_skip": 0, "failed": 0}

    for label_idx, surface_name, label, prompt in targets:
        if args.resume and already_captured(mf, surface_name):
            print(f"  ⏭  {label_idx} {surface_name}: already captured — skipped")
            stats["skipped_existing"] += 1
            continue
        result = capture_surface(label_idx, surface_name, label, prompt,
                                 skip_existing=args.resume)
        stats[result] = stats.get(result, 0) + 1
        # Reload manifest in case the previous capture wrote it
        mf = load_manifest()

    print()
    print("=== Summary ===")
    for k, v in stats.items():
        print(f"  {k:20s} = {v}")
    print()
    print("Next steps:")
    print("  python3 tools/build_civ_columns.py")
    print("  git add -u 'artifacts/validation/visual_art/ANWBritish/*' "
          "a_new_world_columns.html")
    print("  git commit -m 'British: <N> new review-template captures'")
    print("  git push origin main")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
