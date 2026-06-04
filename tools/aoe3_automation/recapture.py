#!/usr/bin/env python3
"""Fast single-surface recapture for the ANW release-readiness site.

Overwrites the EXACT file the readiness site grid shows — no full run needed.
Manually navigate the game to the target screen, then run this tool.

Usage examples:
  # Recapture diplomacy screen for British (3-second countdown):
  python3 tools/aoe3_automation/recapture.py British diplomacy

  # Immediate capture (no countdown), skip site rebuild:
  python3 tools/aoe3_automation/recapture.py French hud --in 0 --no-rebuild

  # Auto-navigate to diplomacy, then capture:
  python3 tools/aoe3_automation/recapture.py Mayans diplomacy --auto

  # List all surfaces and their current resolved paths for a civ:
  python3 tools/aoe3_automation/recapture.py British --list
  python3 tools/aoe3_automation/recapture.py --list
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

ART_DIR = REPO / "artifacts" / "validation" / "visual_art"
SOCKET_PATH = "/tmp/AOE3DEHarness.sock"

# ---------------------------------------------------------------------------
# Surface table: key -> ordered candidate filenames
# ---------------------------------------------------------------------------

SURFACES: dict[str, list[str]] = {
    "lobby":       ["01_lobby.png"],
    "loading":     ["02_loading.png"],
    "hud":         ["02_hud_default.png", "03_hud.png"],
    "hero":        ["09_hero_selected.png"],
    "scoreboard":  ["03_scoreboard.png", "07_scoreboard_with_banter.png", "02_scoreboard.png"],
    "diplomacy":   ["04_diplomacy.png", "06_diplomacy.png", "01_diplomacy.png"],
    "homecity":    ["05_homecity_panel.png", "04_homecity_panel.png", "03_homecity.png"],
    "techtree":    ["05_tech_tree.png"],
    "allyhc":      ["06b_ai_homecity_via_diplo.png", "04_ally_homecity.png"],
    "escmenu":     ["06_esc_menu.png", "08_esc_menu.png"],
    "endgame":     ["07_endgame_screen.png", "09_postgame_results.png", "05_postgame.png"],
    "abandon":     ["07a_abandon_screen.png"],
    "awards":      ["20_postgame_awards.png"],
    "ageup2":      ["08_ageup_age2.png"],
    "ageup3":      ["08_ageup_age3.png"],
    "ageup4":      ["08_ageup_age4.png"],
    "ageup5":      ["08_ageup_age5.png"],
    "ai_chat":     ["ai_01_chat_portrait.png"],
    "ai_homecity": ["ai_02_homecity.png"],
    "ai_deck":     ["ai_03_deck.png"],
}

# Aliases: normalised-alias -> surface key
_ALIASES: dict[str, str] = {
    "aihomecity": "ai_homecity",
    "aihc": "ai_homecity",
    "aideck": "ai_deck",
    "score": "scoreboard",
    "diplo": "diplomacy",
    "hc": "homecity",
    "esc": "escmenu",
    "tech": "techtree",
    "age2": "ageup2",
    "age3": "ageup3",
    "age4": "ageup4",
    "age5": "ageup5",
}

# Populate reverse map: any candidate filename -> key
for _key, _candidates in SURFACES.items():
    for _fname in _candidates:
        _stem = re.sub(r"[-_ ]", "", _fname.lower().replace(".png", ""))
        _ALIASES.setdefault(_stem, _key)


def _normalise_surface(raw: str) -> str | None:
    """Return canonical surface key or None if unrecognised."""
    slug = re.sub(r"[-_ ]", "", raw.lower())
    if slug in SURFACES:
        return slug
    return _ALIASES.get(slug)


def _normalise_civ(raw: str) -> str:
    """Return ANWFoo token from 'Foo', 'ANWFoo', 'foo', etc."""
    if raw.upper().startswith("ANW"):
        rest = raw[3:]
        return "ANW" + rest[0].upper() + rest[1:] if rest else raw
    return "ANW" + raw[0].upper() + raw[1:]


# ---------------------------------------------------------------------------
# Path resolution (mirrors build_release_readiness_site._build_screenshot_index)
# ---------------------------------------------------------------------------

def _build_search_dirs(anw_token: str) -> list[Path]:
    """Return ordered search dirs for a civ token (batch_* first, then full/, then root)."""
    batch_dirs: list[Path] = []
    civ_root: Path | None = None

    if ART_DIR.exists():
        for d in sorted(ART_DIR.iterdir()):
            if not d.is_dir():
                continue
            m = re.match(r"^batch_\d+_(.+)$", d.name)
            if m and m.group(1) == anw_token:
                batch_dirs.append(d)
            elif d.name == anw_token:
                civ_root = d

    dirs: list[Path] = list(batch_dirs)
    if civ_root is not None:
        full = civ_root / "full"
        if full.is_dir():
            dirs.append(full)
        dirs.append(civ_root)
    return dirs


def _find_hit(search_dirs: list[Path], candidates: list[str]) -> Path | None:
    for d in search_dirs:
        for fname in candidates:
            p = d / fname
            if p.exists():
                return p
    return None


def _resolve_output(anw_token: str, surface_key: str) -> Path:
    """Return the path to write (existing hit or new ANWFoo/full/<first-candidate>)."""
    candidates = SURFACES[surface_key]
    search_dirs = _build_search_dirs(anw_token)
    hit = _find_hit(search_dirs, candidates)
    if hit is not None:
        return hit
    # No existing file — create under ANWFoo/full/
    dest = ART_DIR / anw_token / "full" / candidates[0]
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


# ---------------------------------------------------------------------------
# --list mode
# ---------------------------------------------------------------------------

def cmd_list(anw_token: str | None) -> None:
    if anw_token is None:
        print("Surface keys and candidate filenames:")
        for key, candidates in SURFACES.items():
            print(f"  {key:<14} -> {candidates}")
        return

    search_dirs = _build_search_dirs(anw_token)
    print(f"Surfaces for {anw_token}  (search dirs: {[str(d) for d in search_dirs]})\n")
    for key, candidates in SURFACES.items():
        hit = _find_hit(search_dirs, candidates)
        status = str(hit) if hit else "MISSING"
        print(f"  {key:<14} {status}")


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

def cmd_capture(
    anw_token: str,
    surface_key: str,
    countdown: int,
    auto: bool,
    rebuild: bool,
) -> None:
    # Game-alive check (only manage_game needed here, no harness required)
    from tools.aoe3_automation.manage_game import game_pids  # lazy import
    pids = game_pids()
    if not pids:
        print(
            "ERROR: AoE3 DE is not running.\n"
            "Launch the game first with:\n"
            "  python3 tools/aoe3_automation/manage_game.py open",
            file=sys.stderr,
        )
        sys.exit(1)

    # Lazy imports for capture/harness
    from tools.aoe3_automation import lobby_driver
    from tools.aoe3_automation import in_game_driver
    from tools.aoe3_automation.in_game_driver import (
        _click,
        DIPLOMACY_BTN,
        GEARS_BTN,
        set_harness_backend as igd_set_backend,
    )

    # Try harness socket
    try:
        from tools.aoe3_harness.harness_client import HarnessClient
        client = HarnessClient(SOCKET_PATH, timeout=5.0)
        client.connect(timeout=5.0)
        if client.state().ready == 1:
            lobby_driver.set_harness_backend(client)
            igd_set_backend(client)
            print("Harness socket connected.")
        else:
            client = None
    except Exception:
        client = None

    # Resolve output path
    out_path = _resolve_output(anw_token, surface_key)
    candidates = SURFACES[surface_key]
    print(f"Target file : {out_path}")
    print(f"Civ         : {anw_token}")
    print(f"Surface     : {surface_key}  (candidates: {candidates})")

    # --auto navigation
    AUTO_NAV = {"diplomacy": DIPLOMACY_BTN, "escmenu": GEARS_BTN}
    if auto:
        if surface_key in AUTO_NAV:
            btn = AUTO_NAV[surface_key]
            print(f"--auto: clicking {surface_key} button at {btn} …", file=sys.stderr)
            _click(*btn)
            time.sleep(1.5)
        else:
            print(
                f"Note: --auto has no known navigation for surface '{surface_key}'. "
                "Falling back to countdown.",
                file=sys.stderr,
            )

    # Countdown
    if countdown > 0:
        print(f"Capturing in {countdown}s — navigate the game now …", file=sys.stderr)
        for i in range(countdown, 0, -1):
            print(f"  {i}…", file=sys.stderr, flush=True)
            time.sleep(1)

    # Capture
    print("Capturing …", flush=True)
    written = lobby_driver.screenshot(out_path)
    print(f"Captured -> {written}")

    # Rebuild site
    if rebuild:
        print("Rebuilding readiness site …", flush=True)
        result = subprocess.run(
            [sys.executable, "tools/validation/build_release_readiness_site.py"],
            cwd=str(REPO),
        )
        if result.returncode == 0:
            print("Site rebuilt.")
        else:
            print(f"Site rebuild exited with code {result.returncode}.", file=sys.stderr)
    else:
        print("Site rebuild skipped (--no-rebuild).")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recapture a single surface for one civ against a running AoE3 DE game.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("civ", nargs="?", help="Civ name, e.g. British or ANWBritish")
    parser.add_argument("surface", nargs="?", help="Surface key, e.g. diplomacy or hud")
    parser.add_argument(
        "--in", dest="countdown", type=int, default=3, metavar="N",
        help="Countdown seconds before capture (default: 3; use 0 for immediate)",
    )
    parser.add_argument(
        "--auto", action="store_true",
        help="Perform auto-navigation click for diplomacy or escmenu before capturing",
    )
    parser.add_argument(
        "--no-rebuild", dest="rebuild", action="store_false", default=True,
        help="Skip rebuilding the readiness site after capture",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List resolved paths for all surfaces (no capture). Civ optional.",
    )

    args = parser.parse_args()

    if args.list:
        anw_token = _normalise_civ(args.civ) if args.civ else None
        cmd_list(anw_token)
        sys.exit(0)

    if not args.civ or not args.surface:
        parser.error("<civ> and <surface> are required unless --list is given")

    anw_token = _normalise_civ(args.civ)
    surface_key = _normalise_surface(args.surface)
    if surface_key is None:
        known = ", ".join(SURFACES.keys())
        print(
            f"ERROR: Unknown surface '{args.surface}'.\nKnown surfaces: {known}",
            file=sys.stderr,
        )
        sys.exit(1)

    cmd_capture(
        anw_token=anw_token,
        surface_key=surface_key,
        countdown=args.countdown,
        auto=args.auto,
        rebuild=args.rebuild,
    )


if __name__ == "__main__":
    main()
