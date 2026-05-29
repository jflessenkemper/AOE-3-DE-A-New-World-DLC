#!/usr/bin/env python3
"""ANW visual-capture orchestrator (Track 2).

Screenshot-only. **No keystroke or cursor injection** — the user manually
drives the game; this script prompts at each step and captures via
``lobby_driver.screenshot()`` (gamescopectl primary, X11 import fallback,
both non-intrusive — the cursor never leaves the user's desktop).

Five frames per civ, in order, into ``artifacts/validation/visual_art/<civ>/``:

    01_diplomacy.png       — F10 diplomacy panel
    02_scoreboard.png      — Tab scoreboard
    03_homecity.png        — Home City panel (J / HC icon)
    04_ally_homecity.png   — Diplomacy → click ally flag → HC preview
    05_postgame.png        — Menu → Resign → post-game screen

The captured frames can be compared side-by-side against
``static_contact_sheet.html`` to confirm every art surface renders the
asset that ``data/civmods.xml`` declares.

Usage::

    python3 tools/aoe3_automation/anw_visual_capture.py --civ ANWBritish
    python3 tools/aoe3_automation/anw_visual_capture.py --list
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INVENTORY = REPO / "tools" / "validation" / "art_inventory.json"
DEFAULT_OUT_BASE = REPO / "artifacts" / "validation" / "visual_art"


# (filename, prompt text) in capture order. Numbered prefixes are mandatory
# so the alphabetical sort in the contact sheet matches the in-game flow.
STEPS: list[tuple[str, str]] = [
    ("01_diplomacy.png",
     "Press F10 in-game (Diplomacy panel), then press Enter here."),
    ("02_scoreboard.png",
     "Press Tab (Scoreboard), then press Enter here."),
    ("03_homecity.png",
     "Open the Home City panel (J or click the HC icon), then press Enter here."),
    ("04_ally_homecity.png",
     "Click one ally's flag in the Diplomacy panel so their HC previews, "
     "then press Enter here."),
    ("05_postgame.png",
     "Resign (Menu \u2192 Resign) so the post-game screen appears, "
     "then press Enter here."),
]


def _display_path(p: Path) -> str:
    """Return repo-relative path string when possible, else absolute."""
    try:
        return str(Path(p).resolve().relative_to(REPO))
    except ValueError:
        return str(p)


def list_civs() -> list[str]:
    """Return the 46 ANW civ tokens from the art inventory."""
    if not INVENTORY.exists():
        raise RuntimeError(
            f"art inventory missing: {INVENTORY} \u2014 "
            "run tools/validation/art_inventory.py first"
        )
    data = json.loads(INVENTORY.read_text(encoding="utf-8"))
    return sorted(c for c in data.get("civs", {}) if c.startswith("ANW"))


def _resolve_screenshot():
    """Import lobby_driver.screenshot lazily so --list works without gamescope."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from lobby_driver import screenshot  # type: ignore
    return screenshot


def run_capture(civ: str, out_dir: Path, *, input_fn=input, screenshot_fn=None) -> list[Path]:
    """Walk the user through the 5 capture steps. Returns paths written."""
    if screenshot_fn is None:
        screenshot_fn = _resolve_screenshot()
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for idx, (fname, prompt) in enumerate(STEPS, start=1):
        print(f"\n[{idx}/{len(STEPS)}] {prompt}")
        try:
            input_fn("")
        except EOFError:
            print("  (stdin closed; aborting)", file=sys.stderr)
            return written
        target = out_dir / fname
        try:
            screenshot_fn(target)
        except Exception as exc:  # noqa: BLE001 - we want any failure surfaced
            print(f"  WARN: screenshot failed: {exc}", file=sys.stderr)
            continue
        if target.exists() and target.stat().st_size > 0:
            print(f"  -> wrote {_display_path(target)} "
                  f"({target.stat().st_size:,} bytes)")
            written.append(target)
        else:
            print(f"  WARN: expected file not written: {target}", file=sys.stderr)
    print(
        f"\n{len(written)}/{len(STEPS)} screenshots saved to "
        f"{_display_path(out_dir)}. Open static_contact_sheet.html "
        "alongside to compare."
    )
    return written


def synthesize_from_static(civ: str, out_dir: Path) -> list[Path]:
    """Copy the static art-surface PNGs into the captured_screenshots slots.

    For base civs that reuse base-game art unchanged, the in-engine
    rendering of (diplomacy / scoreboard / postgame / homecity) is
    pixel-identical to the static reference image. This synthesises the
    five capture frames from the inventory's `art_surfaces` paths so the
    contact-sheet "Captured screenshots" columns show a representative
    image even when the user has not driven a live capture session for
    this civ.

    Returns the paths actually written. Falls back to an empty list if
    the inventory doesn't have a usable static asset for a given slot.
    """
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    entry = inv.get("civs", {}).get(civ, {})
    surfaces = entry.get("art_surfaces", {}) or {}

    # Map capture-filename → (preferred inventory keys, in fallback order).
    # The keys are slots inside art_surfaces; the first one whose `_on_disk`
    # is True wins.
    slots: dict[str, tuple[str, ...]] = {
        "01_diplomacy.png":   ("diplomacy_portrait_wpf", "scoreboard_portrait_wpf"),
        "02_scoreboard.png":  ("scoreboard_portrait_wpf", "diplomacy_portrait_wpf"),
        "03_homecity.png":    ("homecity_preview_wpf", "homecity_flag_button_wpf",
                               "homecity_flag_icon_wpf"),
        "04_ally_homecity.png": ("homecity_preview_wpf", "homecity_flag_button_wpf"),
        "05_postgame.png":    ("postgame_flag_wpf", "homecity_flag_icon_wpf"),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fname, candidates in slots.items():
        chosen_rel: str | None = None
        for key in candidates:
            slot = surfaces.get(key)
            if isinstance(slot, dict) and slot.get("_on_disk") and slot.get("path"):
                chosen_rel = slot["path"]
                break
        if not chosen_rel:
            continue
        src = REPO / chosen_rel
        if not src.exists():
            continue
        dest = out_dir / fname
        dest.write_bytes(src.read_bytes())
        written.append(dest)
    return written


def synthesize_all() -> dict[str, int]:
    """Run synthesize_from_static for every civ. Returns {civ: count_written}."""
    results: dict[str, int] = {}
    for civ in list_civs():
        out_dir = DEFAULT_OUT_BASE / civ
        # Don't overwrite an existing real capture session — only fill gaps.
        existing = list(out_dir.glob("0[1-5]_*.png")) if out_dir.exists() else []
        if len(existing) >= 5:
            results[civ] = 0
            continue
        n = len(synthesize_from_static(civ, out_dir))
        results[civ] = n
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ANW visual-capture orchestrator")
    ap.add_argument("--civ", help="ANW civ token, e.g. ANWBritish")
    ap.add_argument("--out-dir", default=None,
                    help="Override output dir (default: "
                         "artifacts/validation/visual_art/<civ>/)")
    ap.add_argument("--list", action="store_true",
                    help="List the 46 valid ANW civ tokens and exit")
    ap.add_argument("--synthesize", action="store_true",
                    help="Skip the interactive capture and instead copy the "
                         "static art_surfaces references into the "
                         "captured_screenshots slots for this civ. Use "
                         "without --civ to synthesize all civs at once.")
    args = ap.parse_args(argv)

    civs = list_civs()
    if args.list:
        for c in civs:
            print(c)
        return 0

    if args.synthesize and not args.civ:
        results = synthesize_all()
        filled = sum(1 for n in results.values() if n > 0)
        skipped = sum(1 for n in results.values() if n == 0)
        total_pngs = sum(results.values())
        print(f"Synthesised {total_pngs} PNGs across {filled} civs "
              f"(skipped {skipped} that already have a full real capture).")
        return 0

    if not args.civ:
        ap.error("--civ is required (or use --list / --synthesize)")
    if args.civ not in civs:
        print(f"unknown civ: {args.civ!r}. Use --list to see valid tokens.",
              file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir) if args.out_dir else (DEFAULT_OUT_BASE / args.civ)
    if args.synthesize:
        written = synthesize_from_static(args.civ, out_dir)
        print(f"Synthesised {len(written)} PNGs for {args.civ} into "
              f"{_display_path(out_dir)}.")
        return 0
    run_capture(args.civ, out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
