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
from tools.aoe3_automation import in_game_driver as _igd
from tools.aoe3_automation.ally_all import ally_all

# ---------------------------------------------------------------------------
# Harness backend wiring.
# ---------------------------------------------------------------------------
# CRITICAL (2026-06-05): this runner historically never connected the
# AOE3DEHarness control socket, so EVERY click fell through to the flaky
# xdotool path. In this Proton/gamescope build, xdotool clicks frequently
# mis-target in-game panels (home-city button, player-summary rows, resign),
# leaving the runner stuck on an AI home-city screen — which then got
# re-snapped as scoreboard/esc/endgame. The harness routes clicks through
# the engine control socket and lands reliably (verified: menu + tech-tree
# clicks land first-try). Wire it into BOTH lobby_driver and in_game_driver.
_HARNESS_SOCKET = "/tmp/AOE3DEHarness.sock"


def _wire_harness() -> bool:
    """Connect the AOE3DEHarness socket and register it as the input backend.

    Returns True if the harness is connected+ready (clicks route through the
    socket); False if unavailable (callers continue on the xdotool fallback).
    """
    try:
        from tools.aoe3_harness.harness_client import HarnessClient
        client = HarnessClient(_HARNESS_SOCKET, timeout=5.0)
        client.connect(timeout=5.0)
        if client.state().ready == 1:
            ldr.set_harness_backend(client)
            _igd.set_harness_backend(client)
            log.info("harness_connected", socket=_HARNESS_SOCKET)
            return True
        log.warning("harness_not_ready", socket=_HARNESS_SOCKET)
    except Exception as exc:
        log.warning("harness_connect_failed", socket=_HARNESS_SOCKET, exc=str(exc))
    return False


def _return_to_game_world(max_tries: int = 4) -> bool:
    """Force the UI back to the plain in-game world (no panel, no ESC menu).

    The in-game capture flow opens several modal surfaces (Home City panel,
    Player Summary, ESC menu). If one is left open it blocks every later
    click and poisons subsequent captures. This routine normalises the state:

      * If the ESC menu is up (pixel probe), press Escape to dismiss it.
      * Otherwise press Escape once to close any open panel; if that *opened*
        the ESC menu (because nothing was open), press Escape again.

    Returns True once the game world is confirmed clean (no ESC menu pixel).
    """
    for _ in range(max_tries):
        if _igd._esc_menu_open():
            _igd._key("Escape")
            time.sleep(0.8)
            continue
        # No ESC menu visible — either game world, or a panel is open.
        _igd._key("Escape")
        time.sleep(0.8)
        if _igd._esc_menu_open():
            # Escape opened the menu => we were already at game world. Dismiss.
            _igd._key("Escape")
            time.sleep(0.8)
        return True
    return False

# ---------------------------------------------------------------------------
# Splash-detection guard (graceful-degradation import)
# ---------------------------------------------------------------------------
# If PIL / image_utils is unavailable the splash poll is silently skipped and
# the pipeline falls back to the plain HUD_SETTLE sleep — no crash.
try:
    from tools.aoe3_automation.image_utils import is_splash_frame as _is_splash_frame
    from tools.aoe3_automation.image_utils import is_asset_preloading_frame as _is_asset_preloading_frame
    _SPLASH_DETECTION_AVAILABLE = True
except Exception:
    _SPLASH_DETECTION_AVAILABLE = False
    _is_asset_preloading_frame = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Civs that cannot be selected from the lobby picker (Revolution-only)
SKIP_CIVS: set[str] = set()

# Smoke-test civ list (2 civs, chosen for being near top of picker)
SMOKE_CIVS: list[str] = ["ANWBritish", "ANWFrench"]

# Seconds to wait after click_play before capturing the loading screen frame.
# 2026-05-28 speed-up #2 trimmed this from 11 → 9, but that caused a race for
# ANWBritish (02_loading showed the lobby, not the loading banner, because the
# engine hadn't transitioned within 9s).  Restored to 11 to restore the safety
# margin.  The state-transition guard below provides an additional correctness
# check at minimal overhead.
LOADING_SCREEN_SLEEP = 11

# Minimum elapsed time (seconds) since click_play before we allow the
# 02_loading capture.  If is_in_game() is True before this many seconds pass,
# we have already missed the loading screen and will warn.
_LOADING_SCREEN_GUARD_S = 5

# Seconds to settle before HUD captures after wait_for_in_game.
# wait_for_in_game returns once the engine emits "entering mode 27 (SinglePlayer)"
# but the visual loading screen can persist for another ~20-25s while assets
# stream in.  Was 40s; observed on Alaska (forced) the lag is ~20s.
# 2026-05-28 speed-up #2: cut from 22 → 17 for the overnight all-civs sweep.
# 2026-05-30: HUD_SETTLE kept at 17 as a belt-and-suspenders floor.  The new
# splash-clear poll (see wait_for_splash_clear below) now handles correctness;
# 17s covers the case where splash detection is unavailable or the probe fails.
HUD_SETTLE = 17

# Reduced settle when wait_for_splash_clear positively confirmed the splash is
# gone via pixel probe.  The frame is already rendered; we only need a short
# gap for gamescope to flush the next vsync and _focus_window() to land.
# Old: always 17s → New: 3s when visually confirmed, 17s when blind.
# (2026-06-09 speed-up #3)
HUD_SETTLE_CONFIRMED = 3

# Splash-clear poll parameters.  After wait_for_in_game returns True the
# "Asset Preloading" splash can persist for 14-25 s.  We probe with a
# throwaway screenshot and loop until the frame is no longer a splash OR until
# SPLASH_CLEAR_TIMEOUT elapses (then proceed anyway — belt-and-suspenders).
# 2026-06-09 raised 35→75: the loading screen can APPEAR as late as ~25 s and
# then persist another ~30-40 s while assets stream, so 35 s could time out
# mid-load and fall through to a contaminated capture.
SPLASH_CLEAR_TIMEOUT = 75   # seconds before giving up and proceeding
SPLASH_POLL_INTERVAL = 2    # seconds between probe screenshots
# A single not-loading probe at t=0 is meaningless: the Asset-Preloading screen
# can take a few seconds to APPEAR, so an early "clear" reading just means it
# hasn't shown up yet (this is the 2026-06-09 regression — poll=0 said clear,
# settle 3 s, then the screen appeared and the capture landed on it).  We only
# trust a "clear" reading if EITHER we positively watched the loading screen
# clear (a seen→gone transition, stable for SPLASH_CLEAR_STREAK consecutive
# probes), OR we have polled past SPLASH_APPEAR_WINDOW_S with no loading screen
# ever seen (the load genuinely finished before we started polling).
SPLASH_APPEAR_WINDOW_S = 27   # max time the loading screen may take to appear
SPLASH_CLEAR_STREAK = 2       # consecutive not-loading probes to confirm a clear

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


def wait_for_splash_clear(log: Any, civ_token: str) -> bool:
    """Poll until the "Asset Preloading" splash is gone, then return.

    Takes throwaway probe screenshots to a temp path and calls is_splash_frame
    from image_utils.  Loops while splash is detected and elapsed < SPLASH_CLEAR_TIMEOUT.
    Logs each poll attempt.

    Degrades silently if PIL / image_utils is unavailable (_SPLASH_DETECTION_AVAILABLE
    is False) — control returns immediately and the caller's HUD_SETTLE covers it.

    Returns True ONLY when the splash was positively confirmed clear via the
    pixel probe (the ``if not still_splash: break`` path).  Returns False in
    every other exit: PIL/image_utils unavailable, probe exception, or timeout.
    The caller uses the return value to choose between HUD_SETTLE_CONFIRMED (fast
    path — visually verified) and HUD_SETTLE (full belt-and-suspenders floor).
    """
    import tempfile
    if not _SPLASH_DETECTION_AVAILABLE:
        log.info("splash_poll_skipped", civ=civ_token,
                 reason="image_utils_or_pil_unavailable")
        return False

    probe_path = Path(tempfile.gettempdir()) / ".aoe3_splash_probe.png"
    t_start = time.time()
    poll_idx = 0
    confirmed_clear = False
    seen_splash = False     # have we ever observed the loading screen?
    clear_streak = 0        # consecutive not-loading probes
    while True:
        elapsed = time.time() - t_start
        if elapsed >= SPLASH_CLEAR_TIMEOUT:
            log.warning("splash_poll_timeout", civ=civ_token,
                        elapsed_s=round(elapsed, 1),
                        timeout_s=SPLASH_CLEAR_TIMEOUT, seen_splash=seen_splash)
            break
        # Capture probe frame
        try:
            _gs_screenshot(probe_path)
        except Exception as exc:
            log.info("splash_poll_probe_failed", civ=civ_token, poll=poll_idx,
                     error=str(exc))
            break
        still_splash = _is_splash_frame(probe_path)
        if still_splash:
            seen_splash = True
            clear_streak = 0
        else:
            clear_streak += 1
        log.info("splash_poll", civ=civ_token, poll=poll_idx,
                 elapsed_s=round(elapsed, 1), still_splash=still_splash,
                 seen_splash=seen_splash, clear_streak=clear_streak)
        if not still_splash:
            # Trust a "clear" reading only if we positively watched the loading
            # screen clear (seen→gone, stable), OR the appearance window has
            # fully elapsed with no loading screen ever observed (already done).
            if seen_splash and clear_streak >= SPLASH_CLEAR_STREAK:
                confirmed_clear = True
                break
            if (not seen_splash) and elapsed >= SPLASH_APPEAR_WINDOW_S:
                confirmed_clear = True
                break
        poll_idx += 1
        time.sleep(SPLASH_POLL_INTERVAL)
    # Clean up probe
    try:
        probe_path.unlink(missing_ok=True)
    except Exception:
        pass
    return confirmed_clear


def _wait_assetpreload_clear(
    probe_path: Path,
    *,
    timeout_s: float = 30.0,
    poll_s: float = 2.0,
) -> bool:
    """Poll until the AoE3 "Asset Preloading (Beta)" splash is gone.

    AoE3's "Asset Preloading (Beta)" splash lingers after opening the Home City
    panel (and the AI Home City scene) — if we shoot immediately we save a dark
    loading screen, not the real scene. This helper polls until the splash clears
    before the caller takes the real screenshot — see validate_no_loading_screen_contamination.py.

    Takes a throwaway probe screenshot to *probe_path* (reuses _gs_screenshot,
    the same backend used by _safe_screenshot), calls is_asset_preloading_frame,
    and if True sleeps *poll_s* and retries until the frame is clean or
    *timeout_s* elapses.

    Returns True if the splash cleared (or was never detected).
    Returns False on timeout.
    Never raises — wraps everything in try/except so the caller always gets
    a bool and can still proceed to take the real shot.
    """
    if not _SPLASH_DETECTION_AVAILABLE or _is_asset_preloading_frame is None:
        # PIL / image_utils unavailable — degrade silently, let caller proceed.
        return True
    try:
        t_start = time.time()
        while True:
            elapsed = time.time() - t_start
            if elapsed >= timeout_s:
                return False
            try:
                _gs_screenshot(probe_path)
            except Exception:
                # Probe shot failed — stop polling, let real capture try anyway.
                return True
            try:
                still_loading = _is_asset_preloading_frame(probe_path)
            except Exception:
                # Detector error — degrade, let caller proceed.
                return True
            if not still_loading:
                return True
            time.sleep(poll_s)
    except Exception:
        return True
    finally:
        try:
            probe_path.unlink(missing_ok=True)
        except Exception:
            pass


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
                # 2026-06-09: re-wire the harness BEFORE the popup dismiss.
                # The relaunch killed the old AoE3 process, so the harness
                # socket wired for it is dead; without re-wiring here,
                # _dismiss_weekly_popup()'s clicks (harness MOVE/CLICK) hit a
                # broken pipe (Errno 32) every relaunch and silently degrade to
                # xdotool. The CALLER also re-wires post-relaunch (kept as
                # belt-and-suspenders and so validate_harness_rewire_after_relaunch
                # stays green); this in-function re-wire just makes the
                # immediately-following popup dismiss use a live socket.
                try:
                    _wire_harness()
                    log.info("harness_rewired_in_relaunch")
                except Exception as exc:
                    log.warning("harness_rewire_in_relaunch_failed", exc=str(exc))
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
    needs. Three-step defence:
      1. Press Escape — closes any focused modal that accepts Escape, including
         the weekly profile-picture-reward popup.  Harmless on the bare menu.
      2. Click the known Close button coord twice with a short gap — catches
         popups that don't respond to Escape (e.g. are focused on a button
         that traps the key).  If no popup is present, the coord lands on
         background art and the click is a no-op.
      3. Short settle to let the animation complete before the next click.

    If AoE3 is not alive, returns immediately.

    Total cost: ~2.5s per civ.
    """
    try:
        if not _is_aoe3_alive():
            return
        _focus_window()
        time.sleep(0.5)
        # Step 1: Escape — closes Escape-dismissible modals (including the
        # Weekly Profile Picture Reward popup and any stuck OK-dialog).
        _key("Escape")
        time.sleep(0.6)
        # Step 2: Three blind clicks at the Close button location.  Three
        # because the popup is sometimes mid-fade when click 1 fires and
        # the engine swallows click 2 on some frame-timing paths.
        _click(*_WEEKLY_POPUP_CLOSE, delay=0.4)
        time.sleep(0.5)
        _click(*_WEEKLY_POPUP_CLOSE, delay=0.4)
        time.sleep(0.5)
        _click(*_WEEKLY_POPUP_CLOSE, delay=0.3)
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
    buildings: bool = False,
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

    # ── 0c. Screen-state precondition ────────────────────────────────────────
    # Guard against the case where the game is sitting in a paused match (or
    # other non-menu state) when this civ's capture run begins.
    # wait_for_main_menu() above is unreliable mid-session (Age3Log already
    # contains the mode-1 marker from boot). This pixel+OCR check is the
    # authoritative gate.
    try:
        from tools.aoe3_automation.screen_state import ensure_at_main_menu
        if not ensure_at_main_menu(driver, max_attempts=3):
            _state = __import__(
                "tools.aoe3_automation.screen_state",
                fromlist=["detect_screen_state"],
            ).detect_screen_state()
            warnings.append(f"precondition:not_at_main_menu:state={_state}:aborting")
            log.warning(
                "precondition_failed_bad_screen_state",
                civ=civ_token,
                state=_state,
            )
            _write_manifest(
                civ_dir, civ_token=civ_token, host_perspective=True,
                host_civ_token=None, match_id=mid, captured_at=captured_at,
                captures=captures, status="bad_screen_state", warnings=warnings,
            )
            return {
                "civ_token": civ_token,
                "status": "bad_screen_state",
                "elapsed_s": round(time.time() - t0, 1),
            }
    except Exception as exc:
        warnings.append(f"precondition:screen_state_check:{exc!r}")

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

    # ── 2. Pick P1 civ via OCR-verified selection ────────────────────────────
    # 2026-06-09: prefer_ocr=True forces the OCR-walk path in
    # set_civ_by_token_verified, bypassing the stale picker_civ_order.json
    # cache. The cache was frozen before Californians/Canadians/CentralAmericans
    # were added, so every civ after those three has a wrong scroll_count/click_row
    # (e.g. ANWBritish scroll_count=24 now lands on NapoleonicFrance/French).
    # With prefer_ocr=True the function OCR-walks the picker, locates the row
    # whose text matches the expected civ token via _find_target_row_in_picker,
    # clicks it, and confirms — it never trusts stale coordinates.
    try:
        _focus_window()
        res = ldr.set_civ_by_token_verified(coords, civ_token, enriched_ref,
                                            prefer_ocr=True)
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

    # ── 5. Capture 02_loading ─────────────────────────────────────────────────
    # Wait LOADING_SCREEN_SLEEP seconds to be mid-loading-screen, then snap.
    # We must NOT call wait_for_in_game first because the loading screen will
    # be gone by the time that returns.  After the snap we continue into
    # wait_for_in_game as normal.
    #
    # State-transition guard (BUG 4 fix): poll in 1-second ticks while we wait.
    # If is_in_game() returns True before _LOADING_SCREEN_GUARD_S seconds have
    # elapsed, the engine transitioned faster than expected and we risk
    # capturing the lobby instead of the loading screen — record a warning.
    # If is_in_game() is already True at the moment we take the screenshot, we
    # have missed the loading screen entirely and record a different warning.
    _play_t0 = time.time()
    _snap_at = _play_t0 + LOADING_SCREEN_SLEEP
    _transitioned_early = False
    while time.time() < _snap_at:
        elapsed_since_play = time.time() - _play_t0
        if elapsed_since_play < _LOADING_SCREEN_GUARD_S:
            # Still inside the guard window — check for suspiciously fast
            # transition (means we may still be on the lobby).
            try:
                if driver.is_in_game():
                    _transitioned_early = True
                    warnings.append("02_loading:in_game_before_guard_expired"
                                    f"_elapsed={elapsed_since_play:.1f}s")
                    break
            except Exception:
                pass
        time.sleep(1.0)
    if _transitioned_early:
        warnings.append("02_loading:skipped_transitioned_too_fast")
        log.warning("loading_capture_skipped_too_fast", civ=civ_token,
                    elapsed_s=round(time.time() - _play_t0, 1))
    else:
        # Verify we haven't already passed the loading screen
        _already_in_game = False
        try:
            _already_in_game = driver.is_in_game()
        except Exception:
            pass
        if _already_in_game:
            warnings.append("02_loading:skipped_already_in_game_at_capture_time")
            log.warning("loading_capture_skipped_already_in_game", civ=civ_token)
        else:
            p = full_dir / "02_loading.png"
            ms = _utc_now_ms()
            if _safe_screenshot("02_loading", p, warnings):
                captures.append(_build_capture_entry(
                    "02_loading", "full/02_loading.png", ms,
                    LABEL_TO_CROPS["02_loading"]))
            else:
                warnings.append("02_loading:screenshot_failed")

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

    # ── 7. Splash-clear poll, then settle, then 03_hud ───────────────────────
    # Poll until the "Asset Preloading" splash visual has cleared (typically
    # 14-25 s after the mode-27 log marker).  Degrades gracefully if PIL is
    # unavailable.  HUD_SETTLE follows as a belt-and-suspenders floor.
    # 2026-06-09 speed-up #3: use HUD_SETTLE_CONFIRMED (3s) when the probe
    # positively confirmed the frame is clear; fall back to HUD_SETTLE (17s)
    # when blind (PIL unavailable, probe failed, or timeout).
    splash_confirmed = wait_for_splash_clear(log, civ_token)
    settle_s = HUD_SETTLE_CONFIRMED if splash_confirmed else HUD_SETTLE
    log.info("in_game", civ=civ_token, settling_s=settle_s,
             splash_confirmed=splash_confirmed)
    time.sleep(settle_s)
    _focus_window()
    p = full_dir / "03_hud.png"
    ms = _utc_now_ms()
    if _safe_screenshot("03_hud", p, warnings):
        captures.append(_build_capture_entry(
            "03_hud", "full/03_hud.png", ms, LABEL_TO_CROPS["03_hud"]))

    # ── 8. Home City panel (04) ───────────────────────────────────────────────
    # The 'H' hotkey opens the in-game Home City panel (verified 2026-06-01,
    # verified_coords_british.md line 152). The previous HOMECITY_BTN=(1850,80)
    # click targeted empty HUD space and never opened the panel — every prior
    # run captured the plain game world here.
    _hc_panel_opened = False
    try:
        _focus_window()
        _key("h")
        _hc_panel_opened = True
        time.sleep(2.2)
        # Guard: AoE3 "Asset Preloading (Beta)" splash lingers after opening Home
        # City — poll until it clears before shooting, else we save a loading
        # screen — see validate_no_loading_screen_contamination.py.
        _ap_probe = full_dir / "_preload_probe.png"
        if not _wait_assetpreload_clear(_ap_probe):
            warnings.append("homecity_panel_assetpreload_timeout")
        p = full_dir / "04_homecity_panel.png"
        ms = _utc_now_ms()
        if _safe_screenshot("04_homecity_panel", p, warnings):
            captures.append(_build_capture_entry(
                "04_homecity_panel", "full/04_homecity_panel.png", ms,
                LABEL_TO_CROPS["04_homecity_panel"]))

            # ── 8b. Post-launch civ assertion ────────────────────────────────
            # 2026-06-09: guard against stale-cache wrong-civ launches.
            # Invert HOME_CITY_TO_TOKEN to get the expected on-screen home-city
            # name for this civ token, then OCR the HC panel screenshot and
            # compare.  If the names don't match, log a clear warning and mark
            # the result as civ_mismatch so it is excluded from promotion.
            try:
                import re as _re
                # Build token→home-city mapping from the canonical reverse table.
                _token_to_hc: dict[str, list[str]] = {}
                for _hc_name, _tok in ldr.HOME_CITY_TO_TOKEN.items():
                    _token_to_hc.setdefault(_tok, []).append(_hc_name)
                _expected_hc_names = _token_to_hc.get(civ_token, [])

                # OCR the saved HC-panel screenshot for any home-city name.
                _ocr_text_raw = ""
                try:
                    import pytesseract
                    from PIL import Image as _PILImage
                    _hc_img = _PILImage.open(p)
                    _ocr_text_raw = pytesseract.image_to_string(_hc_img)
                except Exception as _ocr_exc:
                    log.warning("civ_assert_ocr_unavailable",
                                civ=civ_token, exc=str(_ocr_exc))
                    warnings.append(f"civ_assert:ocr_unavailable:{_ocr_exc!r}")

                if _ocr_text_raw:
                    _ocr_upper = _ocr_text_raw.upper()
                    # Check whether ANY known home-city name appears in the OCR.
                    _found_hc_names = [
                        n for n in ldr.HOME_CITY_TO_TOKEN
                        if n in _ocr_upper
                    ]
                    _expected_found = any(
                        n in _ocr_upper for n in _expected_hc_names
                    )
                    # Check whether a DIFFERENT civ's home-city name is visible.
                    _wrong_tokens = {
                        ldr.HOME_CITY_TO_TOKEN[n]
                        for n in _found_hc_names
                        if ldr.HOME_CITY_TO_TOKEN[n] != civ_token
                    }
                    if not _expected_found and _found_hc_names:
                        # A foreign home-city name is present → wrong civ launched.
                        log.warning(
                            "civ_mismatch_detected",
                            civ_expected=civ_token,
                            hc_expected=_expected_hc_names,
                            hc_found=_found_hc_names,
                            wrong_tokens=list(_wrong_tokens),
                        )
                        warnings.append(
                            f"civ_assert:MISMATCH expected={_expected_hc_names}"
                            f" found={_found_hc_names}"
                        )
                        # Mark result and write manifest, then skip remaining captures.
                        _write_manifest(
                            civ_dir, civ_token=civ_token, host_perspective=True,
                            host_civ_token=None, match_id=mid,
                            captured_at=captured_at, captures=captures,
                            status="civ_mismatch", warnings=warnings,
                        )
                        # Close HC panel before bailing out (best-effort).
                        try:
                            _key("h")
                            time.sleep(1.0)
                            _hc_panel_opened = False
                        except Exception:
                            pass
                        log.warning(
                            "civ_skipped_mismatch",
                            civ=civ_token,
                            elapsed_s=round(time.time() - t0, 1),
                        )
                        return {
                            "civ_token": civ_token,
                            "status": "civ_mismatch",
                            "elapsed_s": round(time.time() - t0, 1),
                        }
                    elif _expected_found:
                        log.info("civ_assert_ok", civ=civ_token,
                                 hc_found=_found_hc_names)
                    else:
                        # OCR ran but found no recognisable home-city name at all —
                        # HC panel may not have fully rendered; log but continue.
                        log.warning("civ_assert_ocr_no_match",
                                    civ=civ_token, ocr_snippet=_ocr_text_raw[:120])
                        warnings.append(
                            f"civ_assert:no_hc_name_in_ocr snippet={_ocr_text_raw[:80]!r}"
                        )
            except Exception as _assert_exc:
                # Non-fatal — assertion failure must never abort the run.
                log.warning("civ_assert_exception", civ=civ_token,
                            exc=str(_assert_exc))
                warnings.append(f"civ_assert:exception:{_assert_exc!r}")

        # Close the Home City scene by toggling 'h' again (verified live: 'h'
        # both opens AND closes the in-game Home City view, leaving the camera
        # untouched). CRITICAL: do NOT click (1870,865) to close — that point
        # is inside the minimap, so the click jumps the camera to an unexplored
        # (black) map corner and every later game-world capture renders pure
        # black. Escape is also wrong here (it opens the ESC menu over the
        # sticky HC scene instead of dismissing it).
        _key("h")
        _hc_panel_opened = False
        time.sleep(1.5)
    except Exception as exc:
        warnings.append(f"homecity_panel:{exc!r}")
        # Defensive close: ensure the HC panel is shut before the building tour
        # or any subsequent step, regardless of where the exception occurred.
        if _hc_panel_opened:
            try:
                _key("h")
                time.sleep(1.0)
                _hc_panel_opened = False
                log.info("hc_panel_closed_in_except", civ=civ_token)
            except Exception:
                pass
    # Belt-and-suspenders: if _hc_panel_opened is still True something went
    # wrong above — make one final best-effort close before continuing.
    if _hc_panel_opened:
        try:
            _key("h")
            time.sleep(1.0)
            log.warning("hc_panel_force_closed", civ=civ_token)
        except Exception:
            pass

    # ── 9. ESC menu → Tech Tree (05) ─────────────────────────────────────────
    # Open the ESC menu via the pixel-verified Escape opener (the gears-icon
    # click at (1860,30) proved unreliable — it frequently failed to open the
    # menu, leaving this step capturing the plain game world). Then click
    # Technology Tree, screenshot, and normalise back to the game world.
    try:
        _focus_window()
        # Open the ESC menu with a plain Escape (reliable from a clean game
        # world in this build). The old pixel-verified opener probed (1750,100)
        # which sits inside the always-on score panel, so it false-positived
        # and never actually opened the menu.
        _key("Escape")
        time.sleep(1.5)
        # Click Technology Tree button in the ESC menu panel (y=140 verified).
        _click(*TECH_TREE_BTN, delay=2.0)
        time.sleep(2.5)
        p = full_dir / "05_tech_tree.png"
        ms = _utc_now_ms()
        if _safe_screenshot("05_tech_tree", p, warnings):
            captures.append(_build_capture_entry(
                "05_tech_tree", "full/05_tech_tree.png", ms,
                LABEL_TO_CROPS["05_tech_tree"]))
        # Close: tech tree → ESC menu (Escape), ESC menu → game world (Escape).
        _key("Escape")
        time.sleep(1.0)
        _key("Escape")
        time.sleep(1.0)
    except Exception as exc:
        warnings.append(f"tech_tree:{exc!r}")
        try:
            _key("Escape")
            time.sleep(0.6)
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
    # Open via the pixel-verified Escape opener (the gears-icon click proved
    # unreliable — it was eaten by the still-open Player Summary panel and the
    # menu never appeared).
    try:
        _focus_window()
        # Plain Escape opens the ESC menu (no pixel probe — see step 9 note).
        _key("Escape")
        time.sleep(1.5)
        p = full_dir / "08_esc_menu.png"
        ms = _utc_now_ms()
        if _safe_screenshot("08_esc_menu", p, warnings):
            captures.append(_build_capture_entry(
                "08_esc_menu", "full/08_esc_menu.png", ms,
                LABEL_TO_CROPS["08_esc_menu"]))
        # Close the ESC menu (Escape) before the AI-homecity step so diplomacy
        # opens cleanly.
        _key("Escape")
        time.sleep(1.0)
    except Exception as exc:
        warnings.append(f"esc_menu:{exc!r}")
        try:
            _key("Escape")
            time.sleep(0.6)
        except Exception:
            pass

    # -- 12. Diplomacy (06/06b) + AI Home City (10) -- MUST RUN LAST ----------
    # CRITICAL state-machine note: the diplomacy PLAYER SUMMARY panel and the AI
    # home-city scene are BOTH "sticky" -- they do NOT close on Escape (Escape
    # merely opens the ESC menu *on top of* them). So every clean-world surface
    # (hud, scoreboard, esc-menu, home-city, tech-tree) is captured ABOVE, and
    # these two sticky panels are captured here at the very end. The only action
    # after them is resign, which works because the ESC menu's Resign button is
    # clickable over the sticky overlay.
    #
    # Flow: open diplomacy (1691,35) -> capture 06 -> best-effort ally P2 +
    # APPLY -> capture 06b -> click the demo player's NAME text at
    # (DIPLOMACY_FLAG_X, row_y), which opens that AI's Home City scene (verified
    # 2026-06-01: x=500 name text, NOT x=380 flag icon) -> capture 10. The panel
    # is already open from the 06 capture, so NO reopen is needed -- the prior
    # run's AI-HC miss was caused by reopening when the ESC menu (not diplomacy)
    # was on top.
    try:
        _focus_window()
        _click(*DIPLOMACY_BTN, delay=1.5)
        time.sleep(1.5)
        p_pre = full_dir / "06_diplomacy.png"
        ms_pre = _utc_now_ms()
        if _safe_screenshot("06_diplomacy", p_pre, warnings):
            captures.append(_build_capture_entry(
                "06_diplomacy", "full/06_diplomacy.png", ms_pre,
                LABEL_TO_CROPS["06_diplomacy"]))
        # Best-effort ally + APPLY (non-critical 06b surface). Wrapped so a miss
        # cannot abort the AI-home-city capture that follows.
        try:
            row_y = diplomacy_row_y(DIPLOMACY_DEMO_PLAYER_INDEX)
            _click(DIPLOMACY_ALLY_X, row_y, delay=0.4)
            time.sleep(0.4)
            _click(*DIPLOMACY_APPLY, delay=0.8)
            time.sleep(1.5)
            p_post = full_dir / "06b_diplomacy_after_ally.png"
            ms_post = _utc_now_ms()
            _safe_screenshot("06b_diplomacy_after_ally", p_post, warnings)
        except Exception as exc:
            warnings.append(f"diplomacy_ally_apply:{exc!r}")
        # Click the AI player's NAME text to open their Home City scene. The
        # diplomacy panel is still open from the 06 capture above, so this lands
        # on the live panel (no reopen needed).
        try:
            row_y = diplomacy_row_y(DIPLOMACY_DEMO_PLAYER_INDEX)
            _click(DIPLOMACY_FLAG_X, row_y, delay=1.0)
            time.sleep(2.5)  # HC scene takes a moment to render
            # Guard: AoE3 "Asset Preloading (Beta)" splash lingers after opening
            # the AI Home City scene — poll until it clears before shooting, else
            # we save a loading screen — see validate_no_loading_screen_contamination.py.
            _ap_probe_ai = full_dir / "_preload_probe_ai.png"
            if not _wait_assetpreload_clear(_ap_probe_ai):
                warnings.append("ai_homecity_assetpreload_timeout")
            p = full_dir / "10_ai_homecity.png"
            ms = _utc_now_ms()
            if _safe_screenshot("10_ai_homecity", p, warnings):
                captures.append(_build_capture_entry(
                    "10_ai_homecity", "full/10_ai_homecity.png", ms,
                    LABEL_TO_CROPS["10_ai_homecity"]))
        except Exception as exc:
            warnings.append(f"ai_homecity:{exc!r}")
    except Exception as exc:
        warnings.append(f"diplomacy:{exc!r}")

    # ── 12b. Building tour (optional, --buildings) ───────────────────────────
    # Runs AFTER all core in-game surfaces (HUD/HC/tech-tree/diplomacy/AI-HC)
    # and BEFORE resign so the game is still live with a settler on the map.
    # Failure is isolated: a building-tour exception is logged as a warning
    # and never aborts the civ or the sweep.
    if buildings:
        try:
            from tools.aoe3_automation.anw_building_tour import run_building_tour  # lazy import
            n_built = run_building_tour(civ_token, out_root)
            log.info("building_tour_done", civ=civ_token, n_buildings=n_built)
        except Exception as exc:
            log.warning("building_tour_failed", civ=civ_token, exc=str(exc))
            warnings.append(f"building_tour:{exc!r}")

    # ── 13. Resign → View Postgame → endgame (09) ────────────────────────────
    # Verified 2026-05-20: full resign flow is
    #   ESC menu → Resign(1830,365) → YES(760,605)
    #     → "You Abandon Your Town" → VIEW POSTGAME(1145,737)
    #     → postgame results screen with all 8 flags + scores
    # We open the ESC menu via Escape here (rather than the gears icon) because
    # this step may run with the AI home-city view still on screen; Escape
    # reliably surfaces the ESC menu (with a clickable Resign) on top of it.
    try:
        # Open the ESC menu via a plain Escape (works over the sticky AI HC
        # view — verified live this session). No pixel probe: it samples the
        # always-on score panel and false-positives.
        _key("Escape")
        time.sleep(1.5)
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
    p.add_argument("--buildings", action="store_true", default=False,
                   help="After each civ's core in-game captures, run the building tour "
                        "(anw_building_tour.run_building_tour) to screenshot every "
                        "constructable structure. Output lands in the same <civ>/full/ "
                        "dir as core surfaces. Failure is isolated per civ and never "
                        "aborts the sweep.")
    args = p.parse_args()

    out_root = Path(args.out)
    if not out_root.is_absolute():
        out_root = _REPO_ROOT / out_root
    out_root.mkdir(parents=True, exist_ok=True)

    _configure_logging(out_root)

    # Wire the harness BEFORE any clicks. Without this every click used the
    # flaky xdotool fallback (see _wire_harness docstring). Best-effort: if the
    # socket is down we log a warning and continue on xdotool.
    _wire_harness()

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
                # Re-wire the harness: the old socket belonged to the dead process;
                # without this every click hits a broken pipe (Errno 32).
                _wire_harness()
                log.info("harness_rewired_post_relaunch", civ=civ_token)
                try:
                    driver.ensure_main_menu(retries=8)
                except Exception:
                    pass
            # Loop-level screen-state gate: catches the case where relaunch
            # succeeded but the game booted into a non-menu state (e.g. resumed
            # a save, or the boot animation hasn't finished clearing to menu).
            try:
                from tools.aoe3_automation.screen_state import ensure_at_main_menu as _eamm
                if not _eamm(driver, max_attempts=3):
                    from tools.aoe3_automation.screen_state import detect_screen_state as _dss
                    _bad_state = _dss()
                    log.warning(
                        "loop_precondition_failed_bad_screen_state",
                        civ=civ_token,
                        state=_bad_state,
                    )
                    results.append({
                        "civ_token": civ_token,
                        "status": "bad_screen_state",
                        "elapsed_s": 0.0,
                    })
                    continue
            except Exception as _exc:
                log.warning("loop_screen_state_check_error", civ=civ_token, exc=str(_exc))
            try:
                r = _run_host_civ(
                    civ_token, out_root,
                    driver=driver, coords=coords,
                    enriched_ref=enriched_ref, resume=args.resume,
                    buildings=args.buildings,
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
                # Re-wire the harness: the old socket belonged to the dead process;
                # without this every click hits a broken pipe (Errno 32).
                _wire_harness()
                log.info("harness_rewired_post_relaunch", ally=ally_token)
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
