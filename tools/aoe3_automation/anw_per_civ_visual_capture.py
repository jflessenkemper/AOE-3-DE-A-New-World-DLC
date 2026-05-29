#!/usr/bin/env python3
"""Per-civ visual confirmation capture runner.

Generalized from anw_british_extras_capture.py. Drives the same wait-for-Enter
loop, but parameterised on `--civ <ANWToken>`. Captures the 10 extra-template
surfaces (age-ups 2-5, age-advancement banner, hero tooltip, saloon menu,
TC under construction, treaty lobby, deck builder) into the target civ's
visual_art directory.

Usage
-----
    # Interactive (default): user drives the game; script captures on Enter
    python3 tools/aoe3_automation/anw_per_civ_visual_capture.py --civ ANWBritish

    # Resume — skip surfaces that already have a crop on disk
    python3 tools/aoe3_automation/anw_per_civ_visual_capture.py --civ ANWFrench --resume

    # Subset
    python3 tools/aoe3_automation/anw_per_civ_visual_capture.py --civ ANWBritish \
        --only age_up_colonial_select,age_up_fortress_select,age_up_industrial_select,age_up_imperial_select

Output paths (mirrors anw_british_extras_capture.py exactly so the column
site picks them up identically):
- artifacts/validation/visual_art_v2/<civ>/full/NN_<surface>.png
- artifacts/validation/visual_art/<civ>/crops/<surface>.png
- artifacts/validation/visual_art/<civ>/thumbs/<surface>.webp
- artifacts/validation/visual_art/<civ>/full/NN_<surface>.png
- artifacts/validation/visual_art/<civ>/manifest.json (created if absent)

If the manifest doesn't exist for the target civ, a minimal stub is
generated so subsequent runs of build_civ_columns.py still validate.

This script does NOT drive the game — the engine state required (aging up,
hovering an Explorer, building a Saloon, etc.) is reliably user-driven.
Use the harness in `tools/aoe3_automation/in_game_driver.py` if you need
auto-drive helpers.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.aoe3_automation import lobby_driver  # noqa: E402
from tools.aoe3_automation.anw_civ_picker_map import ANW_TO_PICKER_INDEX  # noqa: E402

THUMB_MAX = 320

CIV_LABELS = {
    "ANWArgentines": "Argentines",
    "ANWAztecs": "Aztecs",
    "ANWBarbary": "Barbary States",
    "ANWBrazil": "Brazil",
    "ANWBritish": "British",
    "ANWCanadians": "Canadians",
    "ANWChileans": "Chileans",
    "ANWChinese": "Chinese",
    "ANWColumbians": "Gran Colombians",
    "ANWDutch": "Dutch",
    "ANWEgyptians": "Egyptians",
    "ANWEthiopians": "Ethiopians",
    "ANWFinnish": "Finns",
    "ANWFrench": "French",
    "ANWGermans": "Germans",
    "ANWHaitians": "Haitians",
    "ANWHaudenosaunee": "Haudenosaunee",
    "ANWHausa": "Hausa",
    "ANWHungarians": "Hungarians",
    "ANWInca": "Inca",
    "ANWIndians": "Marathas",
    "ANWIndonesians": "Indonesians",
    "ANWItalians": "Italians",
    "ANWJapanese": "Japanese",
    "ANWLakota": "Lakota",
    "ANWMaltese": "Maltese",
    "ANWMayans": "Maya",
    "ANWMexicans": "Mexicans",
    "ANWNapoleonicFrance": "French Empire",
    "ANWOttomans": "Ottomans",
    "ANWPeruvians": "Peruvians",
    "ANWPortuguese": "Portuguese",
    "ANWRevFrance": "French Republic",
    "ANWRomanians": "Romanians",
    "ANWRussians": "Russians",
    "ANWSouthAfricans": "South Africans",
    "ANWSpanish": "Spanish",
    "ANWSwedes": "Swedes",
    "ANWTexians": "Texians",
    "ANWUSA": "United States",
}

# (index, surface_name, label, prompt-the-user)
SURFACES: list[tuple[str, str, str, str]] = [
    (
        "15_age_up_colonial",
        "age_up_colonial_select",
        "Age II — Colonial politician selection",
        "In-game as {civ_label}. When you have enough food, click the\n"
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
        "  Catch it during the transition.",
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
        "  mercenary roster (varies by civ).",
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
        "In the lobby for the {civ_label} civ, open the HOME CITY tab so the\n"
        "  deck builder is visible (deck list on left, card slots on right,\n"
        "  card pool on the bottom). With the deck builder on screen,",
    ),
]


def paths_for(civ: str) -> dict[str, Path]:
    return {
        "v2": REPO / f"artifacts/validation/visual_art_v2/{civ}/full",
        "out": REPO / f"artifacts/validation/visual_art/{civ}",
        "manifest": REPO / f"artifacts/validation/visual_art/{civ}/manifest.json",
    }


def ensure_manifest(civ: str, manifest_path: Path) -> dict:
    """Load or create a minimal manifest stub for this civ."""
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    stub = {
        "schema_version": 1,
        "status": "in_progress",
        "civ_token": civ,
        "civ_label": CIV_LABELS.get(civ, civ.replace("ANW", "")),
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host_perspective": True,
        "host_civ_token": None,
        "synthesised": False,
        "match_id": f"{civ.lower()}_real_{int(time.time())}",
        "captures": [],
    }
    manifest_path.write_text(json.dumps(stub, indent=2), encoding="utf-8")
    return stub


def write_manifest(manifest_path: Path, mf: dict) -> None:
    manifest_path.write_text(json.dumps(mf, indent=2), encoding="utf-8")


def already_captured(mf: dict, out_dir: Path, surface_name: str) -> bool:
    for cap in mf.get("captures", []):
        for c in cap.get("crops", []):
            if c.get("name") == surface_name:
                crop_rel = c.get("crop_path", "")
                if crop_rel and (out_dir / crop_rel).exists():
                    return True
    return False


def write_thumb(src: Path, dest_webp: Path) -> None:
    with Image.open(src) as im:
        im = im.convert("RGBA")
        im.thumbnail((THUMB_MAX, THUMB_MAX), Image.LANCZOS)
        im.save(dest_webp, format="WEBP", quality=82, method=4)


def capture_surface(
    civ: str,
    civ_label: str,
    paths: dict[str, Path],
    label_idx: str,
    surface_name: str,
    label: str,
    prompt: str,
    *,
    autonomous: bool = False,
    settle_seconds: float = 0.4,
) -> str:
    """Returns one of: 'captured', 'skipped_existing', 'user_skip', 'failed'."""
    print()
    print(f"=== {civ} :: {label_idx}: {label} ===")
    print(f"  {prompt.format(civ_label=civ_label).replace(chr(10), chr(10) + '  ')}")
    print()
    if not autonomous:
        print("  [Enter] = capture now    [s] = skip this surface    [q] = quit")
        try:
            choice = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "user_skip"
        if choice == "q":
            sys.exit(0)
        if choice == "s":
            return "user_skip"
    else:
        # In autonomous mode the caller has already set up the game state;
        # we just settle briefly then capture.
        print(f"  [autonomous] settling {settle_seconds}s then capturing")

    time.sleep(settle_seconds)

    full_path = paths["v2"] / f"{label_idx}_{surface_name}.png"
    full_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        lobby_driver.screenshot(full_path)
    except Exception as exc:
        print(f"  WARN: screenshot failed: {exc}")
        return "failed"

    crop_rel = f"crops/{surface_name}.png"
    thumb_rel = f"thumbs/{surface_name}.webp"
    crop_abs = paths["out"] / crop_rel
    thumb_abs = paths["out"] / thumb_rel
    crop_abs.parent.mkdir(parents=True, exist_ok=True)
    thumb_abs.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(full_path, crop_abs)
    write_thumb(full_path, thumb_abs)

    mirror_full = paths["out"] / "full" / f"{label_idx}_{surface_name}.png"
    mirror_full.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(full_path, mirror_full)

    mf = json.loads(paths["manifest"].read_text(encoding="utf-8"))
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

    mf["synthesised"] = False
    mf["status"] = "complete" if len(mf["captures"]) >= 10 else "in_progress"
    write_manifest(paths["manifest"], mf)

    print(f"  ✓ captured {surface_name} → {full_path.name}")
    return "captured"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--civ", required=True,
                    help=f"ANW civ token (e.g. ANWBritish). Valid: {', '.join(sorted(ANW_TO_PICKER_INDEX))}")
    ap.add_argument("--only", default="",
                    help="Comma-separated surface names to capture (default: all)")
    ap.add_argument("--resume", action="store_true",
                    help="Skip surfaces already on disk")
    ap.add_argument("--autonomous", action="store_true",
                    help="Skip the wait-for-Enter loop; assume caller has set up state")
    ap.add_argument("--settle-seconds", type=float, default=0.4,
                    help="Settle time before each capture in autonomous mode")
    args = ap.parse_args(argv)

    civ = args.civ
    if civ not in ANW_TO_PICKER_INDEX:
        print(f"ERROR: unknown civ '{civ}'. Valid: {', '.join(sorted(ANW_TO_PICKER_INDEX))}",
              file=sys.stderr)
        return 2

    civ_label = CIV_LABELS.get(civ, civ.replace("ANW", ""))
    paths = paths_for(civ)
    ensure_manifest(civ, paths["manifest"])

    targets = SURFACES
    if args.only:
        only = {s.strip() for s in args.only.split(",")}
        targets = [t for t in SURFACES if t[1] in only]
        if not targets:
            print(f"ERROR: no surfaces match --only {args.only}", file=sys.stderr)
            return 2

    print(f"=== Per-civ visual capture: {civ} ({civ_label}) ===")
    print(f"Output:   {paths['out'].relative_to(REPO)}")
    print(f"Manifest: {paths['manifest'].relative_to(REPO)}")
    print(f"Surfaces queued: {len(targets)}")
    print()
    if not args.autonomous:
        print("Make sure AoE3 DE is running and focused. The script pauses before")
        print("each capture; navigate to the requested in-game state and press Enter.")

    mf = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    stats = {"captured": 0, "skipped_existing": 0, "user_skip": 0, "failed": 0}

    for label_idx, surface_name, label, prompt in targets:
        if args.resume and already_captured(mf, paths["out"], surface_name):
            print(f"  ⏭  {label_idx} {surface_name}: already captured — skipped")
            stats["skipped_existing"] += 1
            continue
        result = capture_surface(
            civ, civ_label, paths, label_idx, surface_name, label, prompt,
            autonomous=args.autonomous, settle_seconds=args.settle_seconds,
        )
        stats[result] = stats.get(result, 0) + 1
        mf = json.loads(paths["manifest"].read_text(encoding="utf-8"))

    print()
    print("=== Summary ===")
    for k, v in stats.items():
        print(f"  {k:20s} = {v}")
    print()
    print("Next steps:")
    print(f"  python3 tools/build_civ_columns.py")
    print(f"  # Confirm {civ} captures appear in a_new_world_columns.html")

    return 0


if __name__ == "__main__":
    sys.exit(main())
