#!/usr/bin/env python3
"""ANW Visual Capture Runner — per-civ unattended screenshot harvester.

Drives AoE3 DE through each ANW civ's lobby → match → post-game states and
captures 9 art surfaces per civ (host perspective) plus 1 diplomacy surface
per ally civ (ally perspective).

CLI:
    python3 -m tools.aoe3_automation.anw_visual_capture_runner \\
        [--mode host|ally|both]        \\
        [--civs ANWBritish,ANWFrench]  \\
        [--smoke]                       \\
        [--resume]                      \\
        [--host-civ ANWBritish]         \\
        [--max-civs N]

Pre-condition:
    AoE3 DE is already running and on the MAIN MENU.

Output layout: see tools/aoe3_automation/CAPTURE_MANIFEST_SCHEMA.md
"""
from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ---------------------------------------------------------------------------
# structlog setup — mirrors exhibition_runner_anw.py pattern
# ---------------------------------------------------------------------------
try:
    import structlog
    _structlog_available = True
except ImportError:
    _structlog_available = False

_JSONL_HANDLE: Optional[Any] = None


def _configure_logging(artifact_root: Path) -> None:
    global _JSONL_HANDLE
    artifact_root.mkdir(parents=True, exist_ok=True)
    if not _structlog_available:
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")
        return
    jsonl_path = artifact_root / "capture_runner.log.jsonl"
    _JSONL_HANDLE = jsonl_path.open("a", buffering=1, encoding="utf-8")
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=False),
            foreign_pre_chain=[timestamper, structlog.stdlib.add_log_level],
        )
    )
    jsonl_handler = logging.StreamHandler(stream=_JSONL_HANDLE)
    jsonl_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=[timestamper, structlog.stdlib.add_log_level],
        )
    )
    root_logger = logging.getLogger()
    root_logger.handlers = [console_handler, jsonl_handler]
    root_logger.setLevel(logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            timestamper,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


class _StdlibKwLogger:
    """Thin wrapper that lets stdlib loggers accept structlog-style kwargs.

    Renders the kwargs as ``key=value`` pairs appended to the event string.
    This is the fallback path when structlog is not installed.
    """

    def __init__(self, name: str):
        self._lg = logging.getLogger(name)

    @staticmethod
    def _fmt(event: str, kwargs: dict[str, Any]) -> str:
        if not kwargs:
            return event
        bits = " ".join(f"{k}={v}" for k, v in kwargs.items())
        return f"{event}  {bits}"

    def info(self, event: str, **kw: Any) -> None:
        self._lg.info(self._fmt(event, kw))

    def warning(self, event: str, **kw: Any) -> None:
        self._lg.warning(self._fmt(event, kw))

    def error(self, event: str, **kw: Any) -> None:
        self._lg.error(self._fmt(event, kw))

    def debug(self, event: str, **kw: Any) -> None:
        self._lg.debug(self._fmt(event, kw))

    def exception(self, event: str, **kw: Any) -> None:
        self._lg.exception(self._fmt(event, kw))


def _get_logger(name: str):
    if _structlog_available:
        import structlog as sl
        return sl.get_logger(name)
    return _StdlibKwLogger(name)


log = _get_logger(__name__)

# ---------------------------------------------------------------------------
# Game driver imports
# ---------------------------------------------------------------------------
from tools.aoe3_automation.anw_civ_picker_map import ANW_TO_PICKER_INDEX
from tools.aoe3_automation import lobby_driver as ldr
from tools.aoe3_automation.in_game_driver import (
    GameDriver,
    ESC_MENU_X,
    ESC_RESIGN,
    ESC_TECH_TREE,
    RESIGN_YES,
    POSTGAME_QUIT,
    VIEW_POSTGAME,
    GEARS_BTN,
    DIPLOMACY_BTN,
    DIPLOMACY_APPLY,
    DIPLOMACY_CLOSE,
    DIPLOMACY_FLAG_X,
    DIPLOMACY_ALLY_X,
    diplomacy_row_y,
    _click,
    _key,
    _focus_window,
)
from tools.aoe3_automation.lobby_driver import screenshot as _gs_screenshot
from tools.aoe3_automation.ally_all import ally_all

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Civs that cannot be selected from the lobby picker (Revolution-only)
SKIP_CIVS: set[str] = set()

# Smoke-test civ list (2 civs, chosen for being near top of picker)
SMOKE_CIVS: list[str] = ["ANWBritish", "ANWFrench"]

# Seconds to wait after click_play before capturing the loading screen frame
# 2026-05-28 speed-up #2: 11 → 9. Loading flag is fully rendered by 8s in all
# observed cases; the 11s value had 3s slack we don't need.
LOADING_SCREEN_SLEEP = 9

# Seconds to settle before HUD captures after wait_for_in_game.
# wait_for_in_game returns once the engine emits "entering mode 27 (SinglePlayer)"
# but the visual loading screen can persist for another ~20-25s while assets
# stream in.  Was 40s; observed on Alaska (forced) the lag is ~20s.
# 2026-05-28 speed-up #2: cut from 22 → 17 for the overnight all-civs sweep.
# 17s still clears the "Asset Preloading" splash on Alaska in all observed
# runs (typical preload window is 14-16s). If a civ shows up with a loading-
# screen caption still visible at 03_hud, bump back to 22.
HUD_SETTLE = 17

# In-game wait timeout
IN_GAME_TIMEOUT = 240

# Home City button coords (top-right of HUD; verified 2026-05-20 British session).
HOMECITY_BTN = (1850, 80)

# ESC menu Tech Tree click coords (verified 2026-05-20 at y=140, not 145).
TECH_TREE_BTN = ESC_TECH_TREE

# Default ally slot for diplomacy demo. P7 is the right-most opponent in most
# 8-player skirmish layouts; British session verified ally workflow at P7
# (row y=625) but the runner ranges with whichever opponent appears at P2 for
# the "ally + APPLY" demo. Use opponent slot 2 (P2) by default.
DIPLOMACY_DEMO_PLAYER_INDEX = 2

# Endgame screen settle time. Was 10s; postgame render is ~5s.
# 2026-05-28 speed-up #2: 6 → 4. Endgame fade-in completes in ~3s.
ENDGAME_SETTLE = 4

# Time to wait after returning to main menu between civs. Was 4s; 2s is fine.
# 2026-05-28 speed-up #2: 2 → 1. Main menu re-render is immediate.
INTER_CIV_DWELL = 1

# Schema version this runner writes
SCHEMA_VERSION = 1

# Canonical crop regions from CAPTURE_MANIFEST_SCHEMA.md
CROP_REGIONS: dict[str, tuple[int, int, int, int]] = {
    "lobby_portrait":            (620, 320, 1300, 920),
    "loading_flag":              (760, 380, 1160, 780),
    "home_city_button":          (1790, 50,  1910, 130),
    "hud_flag_corner":           (1660, 8,   1910, 60),
    "home_city_scene":           (0,   0,   1920, 1000),
    "tech_tree_overview":        (80,  100,  1840, 980),
    "diplomacy_panel":           (400, 140,  1520, 940),
    "scoreboard_player_row":     (200, 280,  1720, 360),
    "esc_menu_player_summary":   (550, 250,  1370, 830),
    "endgame_flag":              (200, 60,   1720, 540),
    "diplomacy_ally_portrait":   (400, 220,  1520, 320),
    # 2026-05-20: AI home-city scene is the same canvas as own HC. AI deck
    # name displays as "HIDDEN" (engine privacy feature for AI decks).
    "ai_home_city_scene":        (0,   0,   1920, 1000),
    "ai_deck_view":              (1400, 700, 1900, 1000),
}

# Mapping: label → list of crop names
LABEL_TO_CROPS: dict[str, list[str]] = {
    "01_lobby":           ["lobby_portrait"],
    "02_loading":         ["loading_flag"],
    "03_hud":             ["home_city_button", "hud_flag_corner"],
    "04_homecity_panel":  ["home_city_scene"],
    "05_tech_tree":       ["tech_tree_overview"],
    "06_diplomacy":       ["diplomacy_panel"],
    "07_scoreboard":      ["scoreboard_player_row"],
    "08_esc_menu":        ["esc_menu_player_summary"],
    "09_endgame":         ["endgame_flag"],
    # Optional surface — only produced when AI HC step succeeds.
    "10_ai_homecity":     ["ai_home_city_scene", "ai_deck_view"],
}

ALLY_LABEL_TO_CROPS: dict[str, list[str]] = {
    "06_diplomacy": ["diplomacy_ally_portrait"],
}

# ---------------------------------------------------------------------------
# Civ label lookup (strip leading "ANW" prefix as a readable label)
# ---------------------------------------------------------------------------

def _civ_label(token: str) -> str:
    """Return a human-readable label from the token. E.g. ANWBritish → British."""
    return token[3:] if token.startswith("ANW") else token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _match_id(civ_token: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    return f"{civ_token.lower()}_{ts}"


def _safe_screenshot(label: str, out_path: Path, warnings: list[str]) -> bool:
    """Wrap gamescopectl-based screenshot; record failures into warnings list.

    Mid-civ AoE3 death (observed for Germans/Aztecs/Argentines 2026-05-18):
    if the game has exited between captures, the gamescopectl screenshot
    will burn 5 retries (~3s) and xdotool spam will burn another ~100s.
    Short-circuit by checking AoE3 liveness before each attempt — saves
    ~110s per remaining surface in the fail case, and produces a
    diagnostic warning that downstream tooling can detect.
    """
    if not _is_aoe3_alive():
        warnings.append(f"screenshot:{label}:game_died_pre_capture")
        return False
    try:
        _gs_screenshot(out_path)
        ok = out_path.exists() and out_path.stat().st_size > 1000
    except Exception as exc:
        if not _is_aoe3_alive():
            warnings.append(f"screenshot:{label}:game_died_during_capture:{exc!r}")
            return False
        warnings.append(f"screenshot:{label}:exception:{exc!r}")
        return False
    if not ok:
        warnings.append(f"screenshot:{label}:no_png_produced")
    return ok


# Coords empirically located 2026-05-18 against the SELECT MAP picker at
# 1920x1080.  The "ANW HUB TEST" custom map fails to load on session re-use
# (engine bug), so we force every match onto Alaska, a stable vanilla
# competitive map.  These coords are picker-popup-relative, so they only
# work after clicking the lobby "Select Map" button.
_MAP_BTN = (1645, 425)              # Lobby "Select Map" button
# 2026-05-28: Re-calibrated against the live picker. Previous coords
# (1408, 832) hit the Filter checkbox column on the right (no-op), and
# (1616, 991) landed BETWEEN OK and Cancel — closer to Cancel — so the
# picker silently closed without saving. Empirically verified by
# clicking + screenshotting picker_diag/02..07. Acropolis tile center
# is ~(965, 837); Alaska tile center is ~(1195, 837); OK button center
# is ~(1530, 1010); Cancel is ~(1740, 1010).
_ALASKA_TILE = (1195, 837)          # Alaska tile (row 3 col 5) in picker
_PICKER_OK = (1530, 1010)           # OK button in picker
_PICKER_CANCEL = (1740, 1010)       # Cancel button (fallback)

# ---------------------------------------------------------------------------
# Diverse opponents lineup
# ---------------------------------------------------------------------------
# 2026-05-28: Britain run at 15:13 reached IN_GAME but the engine crashed on
# entering mode 27 (SinglePlayer). MAP CODE in Age3Log.txt showed
# "AlaskaLarge/8/8169/1/0/141/1/-1/2/-1/3/-1/4/-1/5/-1/6/-1/7/-1" — every
# opponent slot resolved as -1 (Random), forcing the engine to dice-roll 7
# ANW civs simultaneously at match start.  Empirically that random-resolve
# step is fragile on ANW civs (probably hits a missing leader-dispatch path
# under load) and is the leading hypothesis for the mode-27 silent crash.
#
# Pinning opponents to specific ANW civs also fixes the secondary user
# complaint that the loading screen showed "all British flags" — diverse
# pins produce diverse flags.
#
# Chosen 7 to span Europe/Africa/Asia diversity within the ANW roster and
# avoid stacking duplicates of any one engine archetype.
_DIVERSE_OPPONENTS: list[str] = [
    "ANWFrench",      # P2 slot
    "ANWDutch",       # P3
    "ANWGermans",     # P4
    "ANWPortuguese",  # P5
    "ANWSpanish",     # P6
    "ANWRussians",    # P7
    "ANWOttomans",    # P8
]
# Module-level flag: lobby opponent slots stay set across iterations within
# the same AoE3 session, so we only configure them once per session and
# skip re-setting on subsequent civs (saves ~90s × N civs).  Reset to False
# by _relaunch_aoe3 because a relaunch loses lobby state.
_LOBBY_OPPONENTS_SET: bool = False


def _setup_diverse_opponents(coords: dict, enriched_ref: dict,
                              warnings: list[str]) -> bool:
    """Pin P2..P8 to specific ANW civs to avoid Random=-1 mode-27 crash.

    Idempotent at the module level via the _LOBBY_OPPONENTS_SET flag.
    Returns True on full success, False if any slot failed (caller can
    decide whether to continue with mixed Random + Pinned).

    Best-effort: an individual slot failure is logged to warnings but does
    NOT abort the run — the loading-screen / crash issue improves
    monotonically with each pinned slot, so partial success is still net
    positive.
    """
    global _LOBBY_OPPONENTS_SET
    if _LOBBY_OPPONENTS_SET:
        return True

    # Import lazily so this module loads on hosts without a calibrated
    # lobby (e.g. CI static checks).
    try:
        import tools.aoe3_automation.lobby_driver as ldr_mod
    except ImportError as exc:
        warnings.append(f"setup_diverse_opponents:import:{exc!r}")
        return False

    all_ok = True
    for slot_idx, civ in enumerate(_DIVERSE_OPPONENTS, start=1):
        try:
            res = ldr_mod.set_opponent_civ_by_token_verified(
                coords, slot_idx, civ, enriched_ref, prefer_ocr=False,
            )
            if not res.get("ok"):
                all_ok = False
                warnings.append(
                    f"setup_diverse_opponents:slot{slot_idx}:{civ}:"
                    f"{res.get('error', 'unknown')}"
                )
        except Exception as exc:
            all_ok = False
            warnings.append(
                f"setup_diverse_opponents:slot{slot_idx}:{civ}:{exc!r}"
            )
    if all_ok:
        _LOBBY_OPPONENTS_SET = True
    return all_ok


def _force_map_alaska(warnings: list[str]) -> None:
    """Open lobby map picker, select Alaska, confirm.

    Called from each per-civ flow right before click_play(), so we don't
    re-load the broken custom map every iteration.  Idempotent: if Alaska
    is already selected, this still clicks Alaska + OK with no net effect.
    """
    _focus_window()
    time.sleep(0.2)
    _click(*_MAP_BTN, delay=1.0)
    time.sleep(1.0)
    _click(*_ALASKA_TILE, delay=0.6)
    time.sleep(0.5)
    _click(*_PICKER_OK, delay=1.0)
    time.sleep(1.2)


def _is_aoe3_alive() -> bool:
    """Return True iff an AoE3DE_s.exe process is running.

    AoE3 has been observed dying silently mid-iteration (2026-05-18:
    twice during 7-civ smoke, possibly GPU contention with parallel CoH2
    session). Without this check the runner spends ~5min/civ retrying
    screenshots against a dead window.

    2026-05-28: previous version excluded only ``reaper`` from the comm
    filter, but ``pgrep -f`` also matches any shell/python process whose
    ARGV contains 'AoE3DE_s.exe' — including the runner's own diagnostic
    bash invocations. That false-positive let the runner believe AoE3
    was alive after a mid-game crash and skip the relaunch path entirely,
    losing 6 in-game captures per crashed civ. Tightened the comm filter
    to a known-game allowlist instead of a known-stale denylist.
    """
    # Allowlisted /proc/<pid>/comm values that genuinely indicate an
    # AoE3 process. Comm is truncated to 15 chars by the kernel, so we
    # match against the prefixes the actual game reports.
    #
    # 2026-05-28: Empirically verified via /proc/<pid>/comm of a live
    # AoE3 DE process on Bazzite + Proton Experimental: comm reports
    # 'Age3DE' (proton/wine64-preloader sets the process name to a
    # truncated 'Age3DE' string, NOT 'AoE3DE_s.exe' as the argv shows).
    # An earlier allowlist of ('AoE3DE', 'AoE3') would never match the
    # real game, defeating the entire purpose of the alive check.
    # Include 'Age3DE' (real comm) as well as the argv-style prefixes
    # as belt-and-suspenders against future Proton/Wine versions that
    # might report comm differently.
    AOE3_COMM_PREFIXES = ("Age3DE", "AoE3DE", "AoE3")
    try:
        out = subprocess.run(
            ["pgrep", "-f", "AoE3DE_s.exe"],
            capture_output=True, text=True, timeout=5,
        )
        pids = [ln for ln in out.stdout.strip().splitlines() if ln]
        if not pids:
            return False
        for pid in pids:
            try:
                comm = Path(f"/proc/{pid}/comm").read_text().strip()
                if any(comm.startswith(p) for p in AOE3_COMM_PREFIXES):
                    return True
            except FileNotFoundError:
                continue
        return False
    except Exception:
        return False


def _relaunch_aoe3(timeout_s: int = 240) -> bool:
    """Kill any stale AoE3 reapers and re-launch the game via Steam.

    Blocks until the AoE3 process is alive AND the lobby_driver can take
    a 1920x1080 screenshot. Returns True on success.
    """
    log.warning("aoe3_relaunch_start")
    # 2026-05-28: relaunch loses the lobby's opponent-civ slots — they reset
    # to Random.  Clear the module-level flag so the next _run_host_civ
    # re-pins P2..P8 via _setup_diverse_opponents().
    global _LOBBY_OPPONENTS_SET
    _LOBBY_OPPONENTS_SET = False
    # CRITICAL: invalidate gamescope_detect cache. The cached (DISPLAY, GS)
    # tuple from the prior boot may now point at a dead Xwayland / socket.
    # Without this, every xdotool call post-relaunch fails with "Failed
    # creating new xdo instance" because XOpenDisplay on a torn-down :N
    # returns NULL.
    try:
        from tools.aoe3_automation import gamescope_detect
        gamescope_detect.invalidate_cache()
    except Exception as exc:
        log.warning("aoe3_relaunch_invalidate_cache_fail", exc=str(exc))
    # Best-effort cleanup of gamescopereaper zombies left over from a crash.
    try:
        subprocess.run(["pkill", "-9", "-f", "gamescopereaper.*AoE3DE"],
                       timeout=5, capture_output=True)
    except Exception:
        pass
    # Trigger Steam launch.
    try:
        subprocess.Popen(["steam", "steam://run/933110"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as exc:
        log.error("aoe3_relaunch_steam_fail", exc=str(exc))
        return False
    # Wait for the process to come up.
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if _is_aoe3_alive():
            break
        time.sleep(3.0)
    else:
        log.error("aoe3_relaunch_proc_timeout")
        return False
    # Wait for the window to be screenshot-capable (main menu).
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            test_path = Path("/tmp/_anw_relaunch_test.png")
            test_path.unlink(missing_ok=True)
            _gs_screenshot(test_path)
            if test_path.exists() and test_path.stat().st_size > 10_000:
                test_path.unlink(missing_ok=True)
                log.info("aoe3_relaunch_ready",
                         elapsed_s=round(time.time() - t0, 1))
                # 2026-05-28: dismiss the recurring "Choose One Free Weekly
                # Profile Picture Reward" modal that blocked the entire
                # overnight run (0/40 civs progressed past it). The popup
                # appears every week on first launch. Click "Close" (left
                # button) blindly — if it isn't there, the click lands on
                # the main-menu Quit/Exit area which we immediately leave
                # via subsequent navigation, so it's harmless.
                _dismiss_weekly_popup()
                return True
        except Exception:
            pass
        time.sleep(3.0)
    log.error("aoe3_relaunch_screenshot_timeout")
    return False


# Weekly popup button coords on 1920x1080. Verified 2026-05-28 from
# ANWArgentines/full/01_lobby.png pixel grid: the Close button body
# spans y=755-790 with brown background rgb≈(82,34,17). The first
# patch picked y=750 which lands on a 1-pixel black border *above*
# the button — heuristic always returned rgb=(0,0,0) and dismissal
# never fired. Body center is (730, 770).
_WEEKLY_POPUP_CLOSE = (730, 770)


def _dismiss_weekly_popup() -> None:
    """Wait for the main menu to render, then blind-click the weekly
    profile-picture-reward popup's Close button.

    History: runs 1-3 of the 40-civ overnight capture (~12 hours total)
    all failed at 0/40 because the weekly "Choose One Free Weekly
    Profile Picture Reward!" modal blocked the entire main menu. Pixel-
    probe detection heuristics returned `rgb=(0, 0, 0)` because the
    probe screenshot fired during the brief window between gamescope
    reporting ready and the actual menu/popup rendering. Stop fighting
    the probe — wait long enough for the menu to render, then click
    the known Close coords unconditionally. If the popup isn't present
    that week, (730, 770) is background art in the main menu so the
    click is harmless.

    Called from _relaunch_aoe3() post-readiness; fires once per
    relaunch (and once per civ when --force-relaunch-between-civs is set).
    """
    # 2026-05-28: probe screenshots fire too early to see the popup.
    # Wait for the menu to actually render before the dismissal click.
    # The relaunch path already waits for screenshot file size > 10KB,
    # but that fires on the first gamescope frame (often pure black or
    # a loading splash). Empirically the popup appears ~8-12s after
    # gamescope is ready. We sleep 10s, then click twice with a small
    # gap; the second click is a no-op if the popup already dismissed.
    try:
        time.sleep(10.0)
        _focus_window()
        time.sleep(0.6)
        _click(*_WEEKLY_POPUP_CLOSE, delay=0.5)
        time.sleep(1.2)
        # Second click: defensive — popup is sometimes still in fade-out
        # animation on the first click, in which case the engine swallows
        # the first. (730, 770) on the menu (no popup) is dead background.
        _click(*_WEEKLY_POPUP_CLOSE, delay=0.5)
        time.sleep(1.0)
        log.info("popup_dismiss_blind_click_done")
    except Exception as exc:
        log.warning("popup_dismiss_exception", exc=str(exc))


def _dismiss_weekly_popup_quick() -> None:
    """Fast per-civ popup dismiss for use when the main menu is already
    settled (wait_for_main_menu just returned successfully).

    Skips the 10s fresh-launch settle that the original _dismiss_weekly_popup
    needs. If the popup is present we click Close twice with a short gap;
    if not, the clicks land on background art (no-op).

    Total cost: ~2s per civ. Without this, the British capture's 01_lobby
    showed the popup blocking the main menu — proves the runner-startup
    dismiss alone is insufficient (popup can re-arm or be missed entirely
    if AoE3 was already running before the runner started).
    """
    try:
        if not _is_aoe3_alive():
            return
        _focus_window()
        time.sleep(0.3)
        _click(*_WEEKLY_POPUP_CLOSE, delay=0.4)
        time.sleep(0.8)
        _click(*_WEEKLY_POPUP_CLOSE, delay=0.4)
        time.sleep(0.4)
        log.info("popup_dismiss_quick_done")
    except Exception as exc:
        log.warning("popup_dismiss_quick_exception", exc=str(exc))


def _build_capture_entry(
    label: str,
    full_path_rel: str,
    captured_ms: int,
    crop_names: list[str],
    *,
    ally: bool = False,
) -> dict:
    """Build one entry for manifest.captures[] with crop metadata."""
    crops = []
    for name in crop_names:
        region = list(CROP_REGIONS[name])
        crops.append({
            "name": name,
            "crop_region": region,
            "crop_path": f"crops/{name}.png",
            "thumb_path": f"thumbs/{name}.webp",
        })
    return {
        "label": label,
        "full_path": full_path_rel,
        "captured_ms": captured_ms,
        "ocr_text": None,
        "crops": crops,
    }


def _write_manifest(
    civ_dir: Path,
    *,
    civ_token: str,
    host_perspective: bool,
    host_civ_token: Optional[str],
    match_id: str,
    captured_at: str,
    captures: list[dict],
    status: str,
    warnings: list[str],
) -> None:
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "civ_token": civ_token,
        "civ_label": _civ_label(civ_token),
        "captured_at": captured_at,
        "host_perspective": host_perspective,
        "host_civ_token": host_civ_token,
        "match_id": match_id,
        "captures": captures,
        "status": status,
        "warnings": warnings,
    }
    (civ_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))


def _is_complete(civ_dir: Path) -> bool:
    """Return True if manifest says status=complete and all crop/thumb files exist."""
    mf = civ_dir / "manifest.json"
    if not mf.exists():
        return False
    try:
        data = json.loads(mf.read_text())
    except Exception:
        return False
    if data.get("status") != "complete":
        return False
    for cap in data.get("captures", []):
        for crop in cap.get("crops", []):
            if not (civ_dir / crop["crop_path"]).exists():
                return False
            if not (civ_dir / crop["thumb_path"]).exists():
                return False
    return True


def _resolve_civs(arg: Optional[str], *, smoke: bool, max_civs: Optional[int]) -> list[str]:
    if smoke:
        civs = SMOKE_CIVS
    elif arg:
        civs = [c.strip() for c in arg.split(",") if c.strip()]
    else:
        civs = sorted(ANW_TO_PICKER_INDEX.keys())
    civs = [c for c in civs if c not in SKIP_CIVS]
    for c in civs:
        if c not in ANW_TO_PICKER_INDEX:
            raise SystemExit(f"unknown civ token: {c!r} (not in ANW_TO_PICKER_INDEX)")
    if max_civs is not None:
        civs = civs[:max_civs]
    return civs


# ---------------------------------------------------------------------------
# Host-perspective capture (one civ, full 9-surface run)
# ---------------------------------------------------------------------------

def _run_host_civ(
    civ_token: str,
    out_root: Path,
    *,
    driver: GameDriver,
    coords: dict,
    enriched_ref: dict,
    resume: bool,
) -> dict:
    """Capture all 9 host-perspective surfaces for one civ.

    Returns a summary dict with civ_token, status, elapsed_s.
    """
    civ_dir = out_root / civ_token
    full_dir = civ_dir / "full"
    full_dir.mkdir(parents=True, exist_ok=True)

    if resume and _is_complete(civ_dir):
        log.info("civ_skip_complete", civ=civ_token)
        return {"civ_token": civ_token, "status": "skipped_complete", "elapsed_s": 0.0}

    t0 = time.time()
    captured_at = _utc_now_iso()
    mid = _match_id(civ_token)
    warnings: list[str] = []
    captures: list[dict] = []

    log.info("civ_start", civ=civ_token, mode="host")

    # ── 0. Ensure main menu ──────────────────────────────────────────────────
    try:
        driver.wait_for_main_menu(timeout=60)
    except Exception as exc:
        warnings.append(f"wait_for_main_menu:pre:{exc!r}")

    # ── 0b. Per-civ popup dismiss (defence-in-depth) ─────────────────────────
    # 2026-05-28: The runner-startup dismiss (line ~1189) and the per-relaunch
    # dismiss (in _relaunch_aoe3) cover most cases, but the British visual
    # confirmation showed 01_lobby and 02_loading captured WITH the weekly
    # popup still on screen. Safest fix: dismiss again on every civ entry,
    # before click_skirmish is attempted. The menu is already settled here
    # (wait_for_main_menu just succeeded), so settle_pre can be short. If
    # the popup isn't present, (730, 770) lands on main-menu background art
    # and the click is a harmless no-op.
    try:
        _dismiss_weekly_popup_quick()
    except Exception as exc:
        warnings.append(f"per_civ_popup_dismiss:{exc!r}")

    # ── 1. Click Skirmish ────────────────────────────────────────────────────
    try:
        ldr.click_skirmish(coords)
        time.sleep(2.0)
    except Exception as exc:
        warnings.append(f"click_skirmish:{exc!r}")
        _write_manifest(civ_dir, civ_token=civ_token, host_perspective=True,
                        host_civ_token=None, match_id=mid, captured_at=captured_at,
                        captures=captures, status="failed", warnings=warnings)
        log.warning("civ_failed", civ=civ_token, reason="click_skirmish",
                    elapsed_s=round(time.time() - t0, 1))
        return {"civ_token": civ_token, "status": "failed", "elapsed_s": round(time.time() - t0, 1)}

    # ── 2. Pick P1 civ via cache-driven fast path ────────────────────────────
    # 2026-05-18: prefer_ocr=False uses picker_civ_order.json (fresh as of
    # 2026-05-17) scroll_count + click_row, no OCR. The OCR fallback is
    # broken in this build (PATH_B_NOTES.md: picker auto-recentres on
    # currently-selected civ, "reset to Random" pre-step not implemented).
    # The lobby/loading/HUD captures themselves serve as visual verification.
    try:
        _focus_window()
        res = ldr.set_civ_by_token_verified(coords, civ_token, enriched_ref,
                                            prefer_ocr=False)
        if not res.get("ok"):
            raise RuntimeError(f"set_civ_verified not ok: {res.get('history', [])!r}")
        time.sleep(0.6)
    except Exception as exc:
        warnings.append(f"select_civ:{exc!r}")
        try:
            driver.ensure_main_menu(retries=4)
        except Exception:
            pass
        _write_manifest(civ_dir, civ_token=civ_token, host_perspective=True,
                        host_civ_token=None, match_id=mid, captured_at=captured_at,
                        captures=captures, status="failed", warnings=warnings)
        log.warning("civ_failed", civ=civ_token, reason="select_civ",
                    elapsed_s=round(time.time() - t0, 1))
        return {"civ_token": civ_token, "status": "failed", "elapsed_s": round(time.time() - t0, 1)}

    # ── 2b. Pin P2..P8 to diverse ANW civs (once per session) ────────────────
    # 2026-05-28: Mitigates mode-27 engine crash + the user's
    # "loading screen shows all British flags" complaint.  Gated by the
    # module-level _LOBBY_OPPONENTS_SET flag so we only pay the ~90s OCR-
    # verified picker cost on the first civ of each session.  Best-effort:
    # a partial-pin (some Random remaining) is still progress, so we log
    # to warnings but don't abort.
    try:
        _setup_diverse_opponents(coords, enriched_ref, warnings)
    except Exception as exc:
        warnings.append(f"setup_diverse_opponents:outer:{exc!r}")

    # ── 3. Capture 01_lobby ───────────────────────────────────────────────────
    time.sleep(1.5)
    p = full_dir / "01_lobby.png"
    ms = _utc_now_ms()
    if _safe_screenshot("01_lobby", p, warnings):
        captures.append(_build_capture_entry(
            "01_lobby", "full/01_lobby.png", ms, LABEL_TO_CROPS["01_lobby"]))

    # ── 3b. Force map to a stable vanilla (Alaska) ────────────────────────────
    # 2026-05-18: anwHubTest custom map currently fails to load on session
    # re-use (engine bug: mode 6 -> mode 0 with no mode-27 entry on the 3rd+
    # attempt within a single game session). Visual sweep is unblocked by
    # running on a stable competitive vanilla map. Doctrine matrix uses
    # anwHubTest separately, after this sweep completes.
    try:
        _force_map_alaska(warnings)
    except Exception as exc:
        warnings.append(f"force_map_alaska:{exc!r}")

    # ── 4. Click PLAY ─────────────────────────────────────────────────────────
    try:
        ldr.click_play(coords)
        time.sleep(2.0)
    except Exception as exc:
        warnings.append(f"click_play:{exc!r}")
        _write_manifest(civ_dir, civ_token=civ_token, host_perspective=True,
                        host_civ_token=None, match_id=mid, captured_at=captured_at,
                        captures=captures, status="failed", warnings=warnings)
        log.warning("civ_failed", civ=civ_token, reason="click_play",
                    elapsed_s=round(time.time() - t0, 1))
        return {"civ_token": civ_token, "status": "failed", "elapsed_s": round(time.time() - t0, 1)}

    # ── 5. Capture 02_loading (12-15s after click_play) ───────────────────────
    # Sleep ~13s to be mid-loading-screen, then snap. We must NOT wait for
    # in-game first because the loading screen will be gone. After the snap
    # we continue into wait_for_in_game as normal.
    time.sleep(LOADING_SCREEN_SLEEP)
    p = full_dir / "02_loading.png"
    ms = _utc_now_ms()
    if _safe_screenshot("02_loading", p, warnings):
        captures.append(_build_capture_entry(
            "02_loading", "full/02_loading.png", ms, LABEL_TO_CROPS["02_loading"]))
    else:
        warnings.append("02_loading:loading_screen_too_short_or_already_past")

    # ── 6. Wait for in-game ───────────────────────────────────────────────────
    try:
        in_game = driver.wait_for_in_game(timeout=IN_GAME_TIMEOUT, dismiss_errors=True)
    except Exception as exc:
        warnings.append(f"wait_for_in_game:{exc!r}")
        in_game = False
    if not in_game:
        warnings.append("wait_for_in_game:timeout_or_failure")
        try:
            driver.ensure_main_menu(retries=8)
        except Exception:
            pass
        _write_manifest(civ_dir, civ_token=civ_token, host_perspective=True,
                        host_civ_token=None, match_id=mid, captured_at=captured_at,
                        captures=captures, status="failed", warnings=warnings)
        log.warning("civ_failed", civ=civ_token, reason="wait_for_in_game",
                    elapsed_s=round(time.time() - t0, 1))
        return {"civ_token": civ_token, "status": "failed", "elapsed_s": round(time.time() - t0, 1)}

    # ── 7. Settle, then 03_hud ────────────────────────────────────────────────
    log.info("in_game", civ=civ_token, settling_s=HUD_SETTLE)
    time.sleep(HUD_SETTLE)
    _focus_window()
    p = full_dir / "03_hud.png"
    ms = _utc_now_ms()
    if _safe_screenshot("03_hud", p, warnings):
        captures.append(_build_capture_entry(
            "03_hud", "full/03_hud.png", ms, LABEL_TO_CROPS["03_hud"]))

    # ── 8. Home City panel (04) ───────────────────────────────────────────────
    try:
        _focus_window()
        _click(*HOMECITY_BTN, delay=1.5)
        time.sleep(1.5)
        p = full_dir / "04_homecity_panel.png"
        ms = _utc_now_ms()
        if _safe_screenshot("04_homecity_panel", p, warnings):
            captures.append(_build_capture_entry(
                "04_homecity_panel", "full/04_homecity_panel.png", ms,
                LABEL_TO_CROPS["04_homecity_panel"]))
        _key("Escape")
        time.sleep(0.8)
    except Exception as exc:
        warnings.append(f"homecity_panel:{exc!r}")

    # ── 9. ESC menu → Tech Tree (05) ─────────────────────────────────────────
    # Open ESC menu via the gears icon (more reliable than Escape key in this
    # build), click Technology Tree, screenshot, then close.
    try:
        _focus_window()
        _click(*GEARS_BTN, delay=1.2)
        time.sleep(1.2)
        # Click Technology Tree button in the ESC menu panel (y=140 verified).
        _click(*TECH_TREE_BTN, delay=2.0)
        time.sleep(2.0)
        p = full_dir / "05_tech_tree.png"
        ms = _utc_now_ms()
        if _safe_screenshot("05_tech_tree", p, warnings):
            captures.append(_build_capture_entry(
                "05_tech_tree", "full/05_tech_tree.png", ms,
                LABEL_TO_CROPS["05_tech_tree"]))
        # Close tech tree (Escape returns to ESC menu, second Escape closes it)
        _key("Escape")
        time.sleep(0.6)
        _key("Escape")
        time.sleep(0.6)
    except Exception as exc:
        warnings.append(f"tech_tree:{exc!r}")
        # Make sure we're not stuck in ESC menu
        try:
            _key("Escape")
            time.sleep(0.5)
        except Exception:
            pass

    # ── 10. Diplomacy panel (06) — open via in-HUD inkwell, ally P2, APPLY ──
    # Verified 2026-05-20: F4 hotkey does NOT open diplomacy in this build.
    # Use the inkwell+red-quill icon at (1691, 35). Then click the ALLY radio
    # for the demo player row, then APPLY at (510, 815).
    try:
        _focus_window()
        _click(*DIPLOMACY_BTN, delay=1.5)
        time.sleep(1.5)
        # Snapshot the open diplomacy panel before allying — captures the
        # full PLAYER SUMMARY layout for verification.
        p_pre = full_dir / "06_diplomacy.png"
        ms_pre = _utc_now_ms()
        if _safe_screenshot("06_diplomacy", p_pre, warnings):
            captures.append(_build_capture_entry(
                "06_diplomacy", "full/06_diplomacy.png", ms_pre,
                LABEL_TO_CROPS["06_diplomacy"]))
        # Click ALLY radio for P2 (or DIPLOMACY_DEMO_PLAYER_INDEX), then APPLY.
        # In-game notification "X has changed their diplomatic stance" confirms.
        try:
            row_y = diplomacy_row_y(DIPLOMACY_DEMO_PLAYER_INDEX)
            _click(DIPLOMACY_ALLY_X, row_y, delay=0.4)
            time.sleep(0.4)
            _click(*DIPLOMACY_APPLY, delay=0.8)
            time.sleep(1.5)
            # Capture post-APPLY state showing ally relationship for completeness
            p_post = full_dir / "06b_diplomacy_after_ally.png"
            ms_post = _utc_now_ms()
            _safe_screenshot("06b_diplomacy_after_ally", p_post, warnings)
        except Exception as exc:
            warnings.append(f"diplomacy_ally_apply:{exc!r}")
        # Close diplomacy panel via the CLOSE button (more reliable than Esc).
        _click(*DIPLOMACY_CLOSE, delay=0.6)
        time.sleep(0.8)
    except Exception as exc:
        warnings.append(f"diplomacy:{exc!r}")
        # Best-effort recovery: Esc out of any open modal.
        try:
            _key("Escape")
            time.sleep(0.5)
        except Exception:
            pass

    # ── 10b. AI Home City visual confirmation (optional surface 10) ──────────
    # User-requested feature 2026-05-20: "click on the diplomacy ai flag to
    # break up their homecity, and ensure that their new world deck appears
    # there for visual confirmation too".
    #
    # Flow:
    #   1. Reopen diplomacy panel (inkwell icon at 1691,35).
    #   2. Click the demo player's flag at (380, row_y) — opens that AI's
    #      Home City scene with the AI's deck visible. Deck name displays
    #      as "HIDDEN" (engine privacy feature for AI decks, NOT a bug —
    #      see verified_coords_british.md).
    #   3. Snapshot. Then close HC (Escape) to return to the game world.
    #
    # If this step fails (e.g. AI eliminated mid-match), the main 06_diplomacy
    # capture is sufficient for v1.0; this is a "nice to have" extra surface.
    try:
        _focus_window()
        _click(*DIPLOMACY_BTN, delay=1.2)
        time.sleep(1.2)
        row_y = diplomacy_row_y(DIPLOMACY_DEMO_PLAYER_INDEX)
        _click(DIPLOMACY_FLAG_X, row_y, delay=1.0)
        time.sleep(2.5)  # HC scene takes a moment to render
        p = full_dir / "10_ai_homecity.png"
        ms = _utc_now_ms()
        if _safe_screenshot("10_ai_homecity", p, warnings):
            captures.append(_build_capture_entry(
                "10_ai_homecity", "full/10_ai_homecity.png", ms,
                LABEL_TO_CROPS["10_ai_homecity"]))
        # Close AI HC view (Escape) back to game world.
        _key("Escape")
        time.sleep(0.8)
    except Exception as exc:
        warnings.append(f"ai_homecity:{exc!r}")
        # Best-effort: Esc out of any modal that may have opened.
        try:
            _key("Escape")
            time.sleep(0.5)
        except Exception:
            pass

    # ── 11. Scoreboard (07) — always-visible top-right score panel, no Tab ──
    # Verified 2026-05-20: Tab does NOT toggle a fullscreen scoreboard in this
    # build. The top-right score panel is permanently visible. Just snap the
    # current HUD frame; the scoreboard_player_row crop region is already
    # tuned to capture the always-visible panel.
    try:
        _focus_window()
        p = full_dir / "07_scoreboard.png"
        ms = _utc_now_ms()
        if _safe_screenshot("07_scoreboard", p, warnings):
            captures.append(_build_capture_entry(
                "07_scoreboard", "full/07_scoreboard.png", ms,
                LABEL_TO_CROPS["07_scoreboard"]))
    except Exception as exc:
        warnings.append(f"scoreboard:{exc!r}")

    # ── 12. ESC menu (08) ────────────────────────────────────────────────────
    # Open via gears icon at (1860, 30) instead of Escape key.
    try:
        _focus_window()
        _click(*GEARS_BTN, delay=1.2)
        time.sleep(1.2)
        p = full_dir / "08_esc_menu.png"
        ms = _utc_now_ms()
        if _safe_screenshot("08_esc_menu", p, warnings):
            captures.append(_build_capture_entry(
                "08_esc_menu", "full/08_esc_menu.png", ms,
                LABEL_TO_CROPS["08_esc_menu"]))
    except Exception as exc:
        warnings.append(f"esc_menu:{exc!r}")

    # ── 13. Resign → View Postgame → endgame (09) ────────────────────────────
    # Verified 2026-05-20: full resign flow is
    #   gears(1860,30) → Resign(1830,365) → YES(760,605)
    #     → "You Abandon Your Town" → VIEW POSTGAME(1145,737)
    #     → postgame results screen with all 8 flags + scores
    try:
        # ESC menu should already be open from step 12.
        # Click Resign.
        _click(*ESC_RESIGN, delay=0.5)
        time.sleep(0.8)
        _click(*RESIGN_YES, delay=0.6)
        # Wait for the "You Abandon Your Town" dialog to appear.
        time.sleep(4.0)
        # Click VIEW_POSTGAME to reach the final endgame summary.
        _click(*VIEW_POSTGAME, delay=2.0)
        time.sleep(ENDGAME_SETTLE)
        p = full_dir / "09_endgame.png"
        ms = _utc_now_ms()
        if _safe_screenshot("09_endgame", p, warnings):
            captures.append(_build_capture_entry(
                "09_endgame", "full/09_endgame.png", ms,
                LABEL_TO_CROPS["09_endgame"]))
    except Exception as exc:
        warnings.append(f"resign_endgame:{exc!r}")

    # ── 14. Return to main menu ──────────────────────────────────────────────
    try:
        _click(*POSTGAME_QUIT, delay=1.0)
        time.sleep(3.0)
        driver.ensure_main_menu(retries=5)
    except Exception as exc:
        warnings.append(f"return_main_menu:{exc!r}")

    time.sleep(INTER_CIV_DWELL)

    # Determine final status
    captured_labels = {cap["label"] for cap in captures}
    required = {"01_lobby", "03_hud", "04_homecity_panel",
                "06_diplomacy", "07_scoreboard", "08_esc_menu", "09_endgame"}
    missing_required = required - captured_labels
    if missing_required:
        status = "partial"
        warnings.append(f"missing_required_labels:{sorted(missing_required)!r}")
    else:
        status = "complete"

    _write_manifest(civ_dir, civ_token=civ_token, host_perspective=True,
                    host_civ_token=None, match_id=mid, captured_at=captured_at,
                    captures=captures, status=status, warnings=warnings)

    elapsed = round(time.time() - t0, 1)
    log.info("civ_done", civ=civ_token, status=status, elapsed_s=elapsed,
             n_captures=len(captures), n_warnings=len(warnings))
    return {"civ_token": civ_token, "status": status, "elapsed_s": elapsed}


# ---------------------------------------------------------------------------
# Ally-perspective capture (one ally civ, diplomacy surface only)
# ---------------------------------------------------------------------------

def _run_ally_civ(
    ally_token: str,
    host_token: str,
    out_root: Path,
    *,
    driver: GameDriver,
    coords: dict,
    enriched_ref: dict,
    resume: bool,
) -> dict:
    """Capture the diplomacy panel from the host's perspective with ally_token as P2.

    Output lands at out_root/allies/<ally_token>/.
    """
    ally_dir = out_root / "allies" / ally_token
    full_dir = ally_dir / "full"
    full_dir.mkdir(parents=True, exist_ok=True)

    if resume and _is_complete(ally_dir):
        log.info("ally_skip_complete", ally=ally_token)
        return {"civ_token": ally_token, "status": "skipped_complete", "elapsed_s": 0.0}

    t0 = time.time()
    captured_at = _utc_now_iso()
    mid = _match_id(f"ally_{ally_token}")
    warnings: list[str] = []
    captures: list[dict] = []

    log.info("civ_start", civ=ally_token, mode="ally", host=host_token)

    # Ensure main menu
    try:
        driver.wait_for_main_menu(timeout=60)
    except Exception as exc:
        warnings.append(f"wait_for_main_menu:pre:{exc!r}")

    # Click Skirmish
    try:
        ldr.click_skirmish(coords)
        time.sleep(2.0)
    except Exception as exc:
        warnings.append(f"click_skirmish:{exc!r}")
        _write_manifest(ally_dir, civ_token=ally_token, host_perspective=False,
                        host_civ_token=host_token, match_id=mid, captured_at=captured_at,
                        captures=captures, status="failed", warnings=warnings)
        log.warning("ally_failed", ally=ally_token, reason="click_skirmish")
        return {"civ_token": ally_token, "status": "failed", "elapsed_s": round(time.time() - t0, 1)}

    # Pick host civ at P1 (cache-driven fast path; OCR fallback broken in this build)
    try:
        _focus_window()
        res = ldr.set_civ_by_token_verified(coords, host_token, enriched_ref,
                                            prefer_ocr=False)
        if not res.get("ok"):
            raise RuntimeError(f"host P1 not ok: {res!r}")
        time.sleep(0.6)
    except Exception as exc:
        warnings.append(f"select_host_civ:{exc!r}")
        try:
            driver.ensure_main_menu(retries=4)
        except Exception:
            pass
        _write_manifest(ally_dir, civ_token=ally_token, host_perspective=False,
                        host_civ_token=host_token, match_id=mid, captured_at=captured_at,
                        captures=captures, status="failed", warnings=warnings)
        log.warning("ally_failed", ally=ally_token, reason="select_host_civ")
        return {"civ_token": ally_token, "status": "failed", "elapsed_s": round(time.time() - t0, 1)}

    # Pick ally civ at P2 (slot=1 means P2 in opponent_civ_pickers indexing;
    # cache-driven fast path; OCR fallback broken in this build)
    try:
        res2 = ldr.set_opponent_civ_by_token_verified(
            coords, 1, ally_token, enriched_ref, prefer_ocr=False)
        if not res2.get("ok"):
            raise RuntimeError(f"ally P2 not ok: {res2!r}")
        time.sleep(0.6)
    except Exception as exc:
        warnings.append(f"select_ally_civ:{exc!r}")
        try:
            driver.ensure_main_menu(retries=4)
        except Exception:
            pass
        _write_manifest(ally_dir, civ_token=ally_token, host_perspective=False,
                        host_civ_token=host_token, match_id=mid, captured_at=captured_at,
                        captures=captures, status="failed", warnings=warnings)
        log.warning("ally_failed", ally=ally_token, reason="select_ally_civ")
        return {"civ_token": ally_token, "status": "failed", "elapsed_s": round(time.time() - t0, 1)}

    # Click PLAY
    try:
        ldr.click_play(coords)
        time.sleep(2.0)
    except Exception as exc:
        warnings.append(f"click_play:{exc!r}")
        _write_manifest(ally_dir, civ_token=ally_token, host_perspective=False,
                        host_civ_token=host_token, match_id=mid, captured_at=captured_at,
                        captures=captures, status="failed", warnings=warnings)
        log.warning("ally_failed", ally=ally_token, reason="click_play")
        return {"civ_token": ally_token, "status": "failed", "elapsed_s": round(time.time() - t0, 1)}

    # Wait for in-game
    try:
        in_game = driver.wait_for_in_game(timeout=IN_GAME_TIMEOUT, dismiss_errors=True)
    except Exception as exc:
        warnings.append(f"wait_for_in_game:{exc!r}")
        in_game = False
    if not in_game:
        warnings.append("wait_for_in_game:timeout")
        try:
            driver.ensure_main_menu(retries=8)
        except Exception:
            pass
        _write_manifest(ally_dir, civ_token=ally_token, host_perspective=False,
                        host_civ_token=host_token, match_id=mid, captured_at=captured_at,
                        captures=captures, status="failed", warnings=warnings)
        log.warning("ally_failed", ally=ally_token, reason="wait_for_in_game")
        return {"civ_token": ally_token, "status": "failed", "elapsed_s": round(time.time() - t0, 1)}

    # Settle, set ally stance, open diplomacy via in-HUD button.
    time.sleep(HUD_SETTLE)
    try:
        _focus_window()
        # Open diplomacy panel via inkwell icon (F4 doesn't work in this build).
        _click(*DIPLOMACY_BTN, delay=1.5)
        time.sleep(1.5)
        # Set the demo P2 (opponent slot 1) to ALLY via the radio column,
        # then APPLY. This shows the ally panel state instead of Tab-based
        # diplomacy hacks that no longer work.
        try:
            row_y = diplomacy_row_y(DIPLOMACY_DEMO_PLAYER_INDEX)
            _click(DIPLOMACY_ALLY_X, row_y, delay=0.4)
            time.sleep(0.4)
            _click(*DIPLOMACY_APPLY, delay=0.8)
            time.sleep(1.2)
        except Exception as exc:
            warnings.append(f"ally_radio_apply:{exc!r}")
        # Reopen if APPLY auto-closed the panel; otherwise it stays open.
        # We then capture the diplomacy state for ally crop.
        p = full_dir / "06_diplomacy.png"
        ms = _utc_now_ms()
        if _safe_screenshot("06_diplomacy", p, warnings):
            captures.append(_build_capture_entry(
                "06_diplomacy", "full/06_diplomacy.png", ms,
                ALLY_LABEL_TO_CROPS["06_diplomacy"],
                ally=True))
        # Close panel cleanly via CLOSE button.
        _click(*DIPLOMACY_CLOSE, delay=0.6)
        time.sleep(0.8)
    except Exception as exc:
        warnings.append(f"diplomacy:{exc!r}")

    # Resign and return to main menu via the verified gears → Resign flow.
    try:
        _focus_window()
        _click(*GEARS_BTN, delay=1.2)
        time.sleep(1.2)
        _click(*ESC_RESIGN, delay=0.5)
        time.sleep(0.8)
        _click(*RESIGN_YES, delay=0.6)
        time.sleep(4.0)
        # Skip past abandon screen via VIEW_POSTGAME for consistency, then quit
        _click(*VIEW_POSTGAME, delay=1.5)
        time.sleep(3.0)
        _click(*POSTGAME_QUIT, delay=1.0)
        time.sleep(3.0)
        driver.ensure_main_menu(retries=5)
    except Exception as exc:
        warnings.append(f"resign:{exc!r}")

    time.sleep(INTER_CIV_DWELL)

    status = "complete" if any(c["label"] == "06_diplomacy" for c in captures) else "failed"
    _write_manifest(ally_dir, civ_token=ally_token, host_perspective=False,
                    host_civ_token=host_token, match_id=mid, captured_at=captured_at,
                    captures=captures, status=status, warnings=warnings)

    elapsed = round(time.time() - t0, 1)
    log.info("civ_done", civ=ally_token, mode="ally", status=status,
             elapsed_s=elapsed, n_captures=len(captures), n_warnings=len(warnings))
    return {"civ_token": ally_token, "status": status, "elapsed_s": elapsed}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(
        description="ANW visual capture runner — unattended per-civ screenshot harvester."
    )
    p.add_argument("--mode", choices=["host", "ally", "both"], default="both",
                   help="host=host-perspective only; ally=ally-perspective only; both=all (default)")
    p.add_argument("--civs", default=None,
                   help="Comma-separated ANW civ tokens. Default: all minus skip set.")
    p.add_argument("--smoke", action="store_true",
                   help=f"Quick smoke test: only {SMOKE_CIVS} (2 civs).")
    p.add_argument("--resume", action="store_true",
                   help="Skip civs whose manifest.json reports status=complete.")
    p.add_argument("--host-civ", default="ANWBritish",
                   help="Anchor host civ for ally-perspective pass (default: ANWBritish).")
    p.add_argument("--max-civs", type=int, default=None,
                   help="Cap the civ list at N entries.")
    p.add_argument("--out", default="artifacts/validation/visual_art",
                   help="Output root (relative to repo root).")
    p.add_argument("--force-relaunch-between-civs", action="store_true",
                   help="Kill AoE3 + relaunch after every civ. Pattern: 2026-05-18 "
                        "observed AoE3 silently crashes on 2nd-iter mode 27 entry, "
                        "so a fresh game per civ gives 100%% success at ~10s/civ "
                        "extra cost.")
    args = p.parse_args()

    out_root = Path(args.out)
    if not out_root.is_absolute():
        out_root = _REPO_ROOT / out_root
    out_root.mkdir(parents=True, exist_ok=True)

    _configure_logging(out_root)

    civs = _resolve_civs(args.civs, smoke=args.smoke, max_civs=args.max_civs)
    log.info("runner_start", mode=args.mode, n_civs=len(civs),
             smoke=args.smoke, resume=args.resume, host_civ=args.host_civ)

    # Load shared resources
    enriched_ref_path = _REPO_ROOT / "enriched_reference.json"
    if not enriched_ref_path.exists():
        print(f"ERROR: enriched_reference.json not found at {enriched_ref_path}",
              file=sys.stderr)
        return 1
    enriched_ref = json.loads(enriched_ref_path.read_text(encoding="utf-8"))
    coords = ldr.load_coords()
    driver = GameDriver(art_dir=str(out_root / "_driver_scratch"))

    results: list[dict] = []

    # Defensive: if AoE3 is already running when the runner starts, the
    # per-civ loop will not call _relaunch_aoe3() for civ #0 and the
    # weekly Free-Profile-Picture popup (if present) blocks every civ.
    # Dismiss it once at startup. If AoE3 isn't running, this is a no-op
    # because xdotool's --window targeting fails harmlessly.
    if _is_aoe3_alive():
        log.info("startup_popup_dismiss_attempt")
        try:
            _dismiss_weekly_popup()
        except Exception as exc:
            log.warning("startup_popup_dismiss_exception", exc=str(exc))

    # ── Host pass ────────────────────────────────────────────────────────────
    if args.mode in ("host", "both"):
        for idx, civ_token in enumerate(civs):
            # If user requested forced relaunch between civs (default off),
            # kill AoE3 BEFORE this iteration if it's not the first one.
            # This guarantees every civ runs on a fresh "1st-iter" engine
            # state, sidestepping the silent 2nd-iter mode 27 crash.
            if args.force_relaunch_between_civs and idx > 0:
                log.info("force_relaunch_pre_civ", civ=civ_token)
                try:
                    subprocess.run(
                        ["pkill", "-9", "-f", "AoE3DE_s.exe"],
                        timeout=5, capture_output=True,
                    )
                except Exception:
                    pass
                time.sleep(3.0)
            # AoE3 has been observed dying silently mid-iteration. Verify
            # the game is alive before each civ; relaunch if not.
            if not _is_aoe3_alive():
                log.warning("aoe3_dead_pre_civ", civ=civ_token)
                if not _relaunch_aoe3():
                    log.error("aoe3_relaunch_failed_aborting_civ", civ=civ_token)
                    results.append({"civ_token": civ_token, "status": "failed",
                                    "elapsed_s": 0.0})
                    continue
                try:
                    driver.ensure_main_menu(retries=8)
                except Exception:
                    pass
            try:
                r = _run_host_civ(
                    civ_token, out_root,
                    driver=driver, coords=coords,
                    enriched_ref=enriched_ref, resume=args.resume,
                )
            except Exception as exc:
                tb = traceback.format_exc()
                log.error("civ_unhandled", civ=civ_token, exc=str(exc), tb=tb)
                r = {"civ_token": civ_token, "status": "failed", "elapsed_s": 0.0}
                try:
                    driver.ensure_main_menu(retries=5)
                except Exception:
                    pass
            results.append(r)

    # ── Ally pass ────────────────────────────────────────────────────────────
    if args.mode in ("ally", "both"):
        host_civ = args.host_civ
        if host_civ not in ANW_TO_PICKER_INDEX:
            print(f"ERROR: --host-civ {host_civ!r} is not a valid ANW token.",
                  file=sys.stderr)
            return 1
        # Ally pass runs over the same civ list (each becomes the P2 ally)
        for ally_token in civs:
            if ally_token == host_civ:
                continue  # skip ally=host (trivial, also causes picker conflict)
            if not _is_aoe3_alive():
                log.warning("aoe3_dead_pre_ally", ally=ally_token)
                if not _relaunch_aoe3():
                    log.error("aoe3_relaunch_failed_aborting_ally", ally=ally_token)
                    results.append({"civ_token": ally_token, "status": "failed",
                                    "elapsed_s": 0.0})
                    continue
                try:
                    driver.ensure_main_menu(retries=8)
                except Exception:
                    pass
            try:
                r = _run_ally_civ(
                    ally_token, host_civ, out_root,
                    driver=driver, coords=coords,
                    enriched_ref=enriched_ref, resume=args.resume,
                )
            except Exception as exc:
                tb = traceback.format_exc()
                log.error("ally_unhandled", ally=ally_token, exc=str(exc), tb=tb)
                r = {"civ_token": ally_token, "status": "failed", "elapsed_s": 0.0}
                try:
                    driver.ensure_main_menu(retries=5)
                except Exception:
                    pass
            results.append(r)

    # ── Summary ──────────────────────────────────────────────────────────────
    n_complete = sum(1 for r in results if r["status"] == "complete")
    n_failed   = sum(1 for r in results if r["status"] == "failed")
    n_partial  = sum(1 for r in results if r["status"] == "partial")
    n_skipped  = sum(1 for r in results if "skipped" in r["status"])
    total_s    = sum(r["elapsed_s"] for r in results)

    print(
        f"[capture] done: complete={n_complete} partial={n_partial} "
        f"failed={n_failed} skipped={n_skipped} total_civs={len(results)} "
        f"elapsed={total_s:.0f}s  out={out_root}"
    )

    if _JSONL_HANDLE:
        _JSONL_HANDLE.close()

    return 0 if n_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
