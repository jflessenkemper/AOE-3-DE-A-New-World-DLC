#!/usr/bin/env python3
"""AoE3 DE screen-state classifier and main-menu recovery helper.

Provides:
    detect_screen_state(shot_path=None) -> str
    ensure_at_main_menu(driver, *, max_attempts=3) -> bool

Kept as a separate module to avoid circular imports:
  in_game_driver lazy-imports lobby_driver inside resign(), so
  lobby_driver must not import in_game_driver at module level.
  This file sits at the same package level and imports from both.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Optional, Union

# ---------------------------------------------------------------------------
# New OCR crop coordinates (all tuned at 1920x1080)
# None of these exist in any existing driver; all are new.
# ---------------------------------------------------------------------------
# Home City screen — "HOME CITY" or civ-name banner top-centre
HC_TITLE_CROP        = (400,  30, 1000,  80)
# Tech Tree — "TECHNOLOGY TREE" header.
# VERIFIED 2026-06-09: the TT screen is a full-page overlay. The title
# "TECHNOLOGY TREE" appears in the LEFT panel at approximately x=100-450,
# y=50-105. The original (600,30,1300,90) pointed at the empty dark centre
# of the tree layout and never read anything useful.
TECH_TREE_TITLE_CROP = (100,  50,  450, 105)
# Diplomacy/Player Summary panel — "PLAYER SUMMARY" header.
# VERIFIED 2026-06-09: the Player Summary dialog centres on screen.
# The header "PLAYER SUMMARY" appears at y≈200-260 (not y=30-85 which reads
# the resource bar). Crop (350,200,1150,260) reliably reads "PLAYER SUMMARY".
DIPLOMACY_TITLE_CROP = (350, 200, 1150, 260)
# Post-game — "YOU ABANDON YOUR TOWN" / "GAME SUMMARY" / "VICTORY" text.
# VERIFIED 2026-06-09: the defeat overlay "YOU ABANDON YOUR TOWN" appears
# centred around y=495-550. The original (550,30,1400,90) read the resource
# bar and found nothing. Crop (350,490,1200,560) reliably reads "abandon".
POST_GAME_TITLE_CROP = (350, 490, 1200, 560)
# Age-up politician dialog — "SELECT A [AGE] AGE POLITICIAN" banner
# This banner sits roughly centre-screen just above the portrait row.
AGE_UP_TITLE_CROP    = (420, 465, 1500, 545)
# Loading / Asset Preloading splash — text in upper-centre area
LOADING_TITLE_CROP   = (650,  45, 1270, 115)
# Single Player Skirmish setup lobby — "SINGLE PLAYER SKIRMISH" header.
# VERIFIED 2026-06-09: top-left header at y≈50-100.
# The lobby_driver MATCH_SETUP / GAME_OPTIONS OCR crops are for the
# MULTIPLAYER lobby, which uses a different header. For single-player
# skirmish we read the "SINGLE PLAYER SKIRMISH" text at top-left.
SKIRMISH_SETUP_TITLE_CROP = (50, 50, 700, 100)

# ESC / pause menu — re-calibrated probe.
# Doc 02 confirmed that (1750, 100) is unreliable (falls on score panel).
# The ESC menu panel renders from x=ESC_MENU_X=1830 in the real coord map.
# We probe at (1830, 200) — mid-panel, avoids score row and Gear icon row.
ESC_MENU_PROBE_XY = (1830, 200)
ESC_MENU_PROBE_THRESHOLD = 90  # R+G+B > 90 → brown panel rendered
# Raised from 60→90: at threshold=60, dark-background pixels (sum≈65) caused
# false-positive pause_menu on in_game/HC/lobby. True ESC panel sum≈127 (brown);
# non-pause backgrounds sum≈65. Threshold=90 cleanly separates them.

# ---------------------------------------------------------------------------
# Lobby crop aliases — re-imported at call time from lobby_driver to stay in
# sync with any future crop adjustments there.  Must be defined at module
# scope (before the functions that reference them) so they are available when
# detect_screen_state() is called.
# ---------------------------------------------------------------------------
try:
    from tools.aoe3_automation.lobby_driver import (
        MATCH_SETUP_HEADER_CROP as MATCH_SETUP_HEADER_CROP_TUPLE,
        GAME_OPTIONS_HEADER_CROP as GAME_OPTIONS_HEADER_CROP_TUPLE,
    )
except ImportError:
    # Fallback literals if lobby_driver not importable (e.g. running validator
    # in isolation). These match lobby_driver.py lines 826-827.
    MATCH_SETUP_HEADER_CROP_TUPLE  = (700,  30, 1220,  95)
    GAME_OPTIONS_HEADER_CROP_TUPLE = (1380, 130, 1880, 195)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _take_probe_shot(probe_path: str = "/tmp/.aoe3_state_probe.png") -> Optional[Path]:
    """Capture a gamescopectl screenshot and return the Path once stable.

    Returns None if gamescopectl fails or the file never stabilises.
    Never raises.
    """
    p = Path(probe_path)
    try:
        # Dynamic env resolution — same pattern as in_game_driver._get_gs_env()
        try:
            from tools.aoe3_automation.gamescope_detect import get_gs_env
            env = get_gs_env()
        except Exception:
            import os
            env = {**os.environ,
                   "GAMESCOPE_WAYLAND_DISPLAY": "gamescope-0",
                   "WAYLAND_DISPLAY": "gamescope-0"}

        subprocess.run(
            ["gamescopectl", "screenshot", str(p)],
            env=env, capture_output=True, check=False, timeout=8,
        )
        # gamescopectl writes async — wait for file to stabilise
        deadline = time.time() + 3.0
        last_sz = -1
        stable = 0
        while time.time() < deadline:
            try:
                sz = p.stat().st_size
            except OSError:
                sz = 0
            if sz > 100_000 and sz == last_sz:
                stable += 1
                if stable >= 2:
                    break
            else:
                stable = 0
            last_sz = sz
            time.sleep(0.15)
        return p if p.exists() and p.stat().st_size > 100_000 else None
    except Exception:
        return None


def _ocr(crop_box: tuple, shot_path: Path) -> str:
    """Thin wrapper: delegates to lobby_driver._ocr_text + _normalise_ocr.

    Returns "" (never raises) if tesseract / Pillow unavailable.
    """
    try:
        from tools.aoe3_automation.lobby_driver import _ocr_text, _normalise_ocr
        raw = _ocr_text(crop_box, shot_path)
        return _normalise_ocr(raw)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_screen_state(
    shot_path: Optional[Union[str, Path]] = None,
) -> str:
    """Classify the current AoE3 DE UI state from a screenshot.

    Args:
        shot_path: path to an existing PNG, or None to take a fresh probe
                   screenshot via gamescopectl.

    Returns one of:
        "main_menu", "skirmish_setup", "civ_picker", "in_game", "pause_menu",
        "home_city", "diplomacy", "tech_tree", "post_game", "loading",
        "age_up_dialog", "unknown"

    Check order (cheapest/most-unambiguous first):
        1.  Pixel (200,15)  — hud_visible  [1 pixel read]
        2.  Pixel (1830,200) — esc_panel_visible  [1 pixel read]
        3a. If NOT hud_visible → OCR lobby header crops → skirmish_setup
        3b. If NOT hud_visible → OCR post-game / loading / age-up crops
        3c. If NOT hud_visible → fall through to main_menu (elimination)
        4a. If hud_visible AND esc_panel → pause_menu
        4b. If hud_visible AND NOT esc_panel → OCR in-game overlay crops
            (home_city → tech_tree → diplomacy → age_up_dialog → in_game)

    Never raises. Returns "unknown" on any unhandled exception or if
    tesseract is unavailable and pixel probes are inconclusive.
    """
    try:
        from PIL import Image
    except ImportError:
        return "unknown"

    # --- Acquire screenshot ------------------------------------------------
    if shot_path is not None:
        p = Path(shot_path)
    else:
        p = _take_probe_shot()
    if p is None or not p.exists():
        return "unknown"

    # --- Read the two anchor pixels ----------------------------------------
    try:
        with Image.open(p) as im:
            im.load()
            # Import verified constants from in_game_driver (deferred to avoid
            # circular import at module level)
            from tools.aoe3_automation.in_game_driver import (
                HUD_PROBE_XY, HUD_THRESHOLD,
            )
            hud_px = im.getpixel(HUD_PROBE_XY)
            hud_sum = sum(hud_px[:3])
            esc_px = im.getpixel(ESC_MENU_PROBE_XY)
            esc_sum = sum(esc_px[:3])
    except Exception:
        return "unknown"

    hud_visible = hud_sum > HUD_THRESHOLD           # > 280
    esc_visible = esc_sum > ESC_MENU_PROBE_THRESHOLD  # > 60

    # =========================================================================
    # Branch A: HUD resource bar NOT visible
    #   Possible states: main_menu, skirmish_setup, civ_picker,
    #                    post_game, loading, age_up_dialog (rare: dim overlay),
    #                    tech_tree (full-page overlay, dims HUD region)
    # =========================================================================
    if not hud_visible:
        # Check for single-player skirmish lobby first (positive OCR hit).
        # VERIFIED 2026-06-09: Single Player Skirmish has header at y≈50-100.
        # Also works when the civ-picker overlay is on top (lobby header still visible).
        sk = _ocr(SKIRMISH_SETUP_TITLE_CROP, p)
        if "singleplayer" in sk or "skirmish" in sk or "singleplayerskirmish" in sk:
            return "skirmish_setup"

        # Multiplayer lobby (MATCH SETUP / GAME OPTIONS headers).
        # These are multiplayer-only headers and rarely appear in ANW automation,
        # but check them for completeness.
        ms = _ocr(MATCH_SETUP_HEADER_CROP_TUPLE, p)
        go = _ocr(GAME_OPTIONS_HEADER_CROP_TUPLE, p)
        if "matchset" in ms or "gameoption" in go:
            return "skirmish_setup"

        # Tech Tree: full-page overlay that dims the HUD probe region.
        # VERIFIED 2026-06-09: "TECHNOLOGY TREE" text at top-left, y≈50-105.
        tt = _ocr(TECH_TREE_TITLE_CROP, p)
        if "technology" in tt or "techtree" in tt or "chnology" in tt:
            return "tech_tree"

        # Post-game screen — "YOU ABANDON YOUR TOWN" or "VICTORY" overlay.
        # VERIFIED 2026-06-09: defeat text at y≈490-560.
        pg = _ocr(POST_GAME_TITLE_CROP, p)
        if any(kw in pg for kw in ("abandon", "score", "summary", "result", "awards",
                                    "victory", "defeat", "endgame", "gamesummary")):
            return "post_game"

        # Loading / asset preloading splash
        ld = _ocr(LOADING_TITLE_CROP, p)
        if "loading" in ld or "assetpreload" in ld or "preload" in ld:
            return "loading"

        # Age-up dialog: CAN appear without a bright resource bar IF the
        # dimming overlay is very dark. Check the distinctive banner text.
        au = _ocr(AGE_UP_TITLE_CROP, p)
        if ("selecta" in au and "age" in au) or "politician" in au:
            return "age_up_dialog"

        # Disambiguation: main_menu vs sub-screens that share the harbour backdrop
        # (Home City, Tools, News, Story Mode from main menu).
        # All of these have a "BACK" or "MAIN MENU" link at top-left (y~13)
        # and NO match-setup header. We return "main_menu" for all of them:
        # from the runner's perspective, the fix is identical (ESC-out is safe,
        # click_skirmish is possible after one navigation).
        # Finer discrimination (e.g. distinguishing HC standalone from main-menu)
        # is not needed for the runner precondition.
        return "main_menu"

    # =========================================================================
    # Branch B: HUD resource bar IS visible
    #   Possible states: in_game, pause_menu, home_city (in-game H overlay),
    #                    tech_tree, diplomacy, age_up_dialog
    # =========================================================================

    # Fastest check: ESC panel pixel
    if esc_visible:
        return "pause_menu"

    # HUD visible, no ESC panel → check in-game overlays (OCR, most specific first)
    hc = _ocr(HC_TITLE_CROP, p)
    if "homecity" in hc or ("home" in hc and "city" in hc):
        return "home_city"

    tt = _ocr(TECH_TREE_TITLE_CROP, p)
    if "technology" in tt or "techtree" in tt or "chnology" in tt:
        return "tech_tree"

    dip = _ocr(DIPLOMACY_TITLE_CROP, p)
    # VERIFIED 2026-06-09: "PLAYER SUMMARY" header at y≈200-260.
    if "playersummary" in dip or "playersumm" in dip or "diplomacy" in dip or "tribute" in dip:
        return "diplomacy"

    # Post-game defeat overlay: "YOU ABANDON YOUR TOWN" appears centred on screen
    # while the resource bar is still visible (HUD probe stays lit).
    # VERIFIED 2026-06-09: defeat text at y≈490-560, even with HUD probe=516.
    pg = _ocr(POST_GAME_TITLE_CROP, p)
    if any(kw in pg for kw in ("abandon", "victory", "defeat", "endgame",
                                "gamesummary", "youabandon")):
        return "post_game"

    # Age-up politician dialog: HUD still lit (dimming partial), banner present
    au = _ocr(AGE_UP_TITLE_CROP, p)
    if ("selecta" in au and "age" in au) or "politician" in au:
        return "age_up_dialog"

    # Plain in-game HUD
    return "in_game"


def ensure_at_main_menu(
    driver,  # GameDriver instance (in_game_driver.GameDriver)
    *,
    max_attempts: int = 3,
) -> bool:
    """Verify we are on the main menu; if not, attempt state-aware recovery.

    Routing table:
        main_menu      → already there, return True immediately
        in_game        → driver.resign() (ESC→RESIGN→YES→menu), then verify
        age_up_dialog  → driver.resign() (age-up keeps game alive), then verify
        pause_menu     → ESC to close panel, then driver.resign(), then verify
        post_game      → driver.ensure_main_menu(retries=8) [ESC-spam]
        loading        → wait 12 s for splash to clear, then ESC-spam
        tech_tree      → driver.ensure_main_menu(retries=6) [ESC-spam]
        diplomacy      → driver.ensure_main_menu(retries=6) [ESC-spam]
        home_city      → driver.ensure_main_menu(retries=6) [ESC-spam]
        skirmish_setup → ESC×3 (close picker/lobby) → Return (confirm leave)
        civ_picker     → ESC×3 (close picker → lobby) → Return (confirm leave)
        unknown        → driver.ensure_main_menu(retries=8) [best effort]

    Args:
        driver: a GameDriver instance (from in_game_driver). Used for
                driver.resign(), driver.ensure_main_menu().
        max_attempts: how many detect→recover cycles to try before giving up.

    Returns:
        True if detect_screen_state() == "main_menu" at any point.
        False if max_attempts exhausted without landing on main_menu.

    Never raises.
    """
    # Deferred import to avoid circular-import at module level:
    # in_game_driver lazy-imports lobby_driver inside resign().
    from tools.aoe3_automation.in_game_driver import _key  # module-level fn

    for attempt in range(max_attempts):
        state = detect_screen_state()
        if state == "main_menu":
            return True

        try:
            if state in ("in_game", "age_up_dialog"):
                # Full resign sequence: ESC → RESIGN → YES → main menu
                driver.resign()
                time.sleep(2.5)

            elif state == "pause_menu":
                # ESC closes the pause panel, then resign from in-game HUD
                _key("Escape")
                time.sleep(1.0)
                driver.resign()
                time.sleep(2.5)

            elif state == "post_game":
                # Post-game screen: QUIT button at (50,20) is unreliable via
                # socket (confirmed in doc 01, section 10). Use ESC-spam.
                driver.ensure_main_menu(retries=8)
                time.sleep(1.0)

            elif state == "loading":
                # Loading splash lasts 5-10 s. Wait for it to clear, then
                # we'll be in-game → resign on next iteration.
                time.sleep(12.0)

            elif state in ("tech_tree", "diplomacy", "home_city"):
                # All are one or two ESC presses away from in-game HUD,
                # then another from main menu. Spam covers both.
                driver.ensure_main_menu(retries=6)
                time.sleep(1.0)

            elif state in ("skirmish_setup", "civ_picker"):
                # CRITICAL: the skirmish lobby and its civ-picker modals do NOT
                # respond to the Escape key (verified live 2026-06-10 — ESC was
                # silently swallowed). They must be dismissed by *clicking*:
                #   1. CANCEL button (closes a "SELECT CIVILIZATION" / "SELECT
                #      HOME CITY" modal if one is open) at ~(690, 965).
                #   2. "<- Back" button (top-left, leaves the lobby to the main
                #      menu) at lobby_coords back_button = (50, 25).
                # After the Back click the lobby fades out over ~1.5 s; the
                # verifying detect must wait for that fade or it reads a stale
                # mid-transition frame as skirmish_setup (false negative).
                from tools.aoe3_automation import lobby_driver as _L
                try:
                    back_xy = _L.load_coords()["lobby"]["back_button"]
                except Exception:
                    back_xy = [50, 25]
                _L.click(690, 965)          # CANCEL picker modal (no-op if absent)
                time.sleep(1.0)
                _L.click(back_xy[0], back_xy[1])  # <- Back → main menu
                time.sleep(3.0)             # lobby fade-out + main-menu settle

            else:
                # unknown — blind ESC-spam
                driver.ensure_main_menu(retries=8)
                time.sleep(1.0)

        except Exception:
            # Never let a recovery error propagate — just loop
            pass

        time.sleep(1.0)

    # Final check
    return detect_screen_state() == "main_menu"
