"""anw_navigator.py — Single source of truth for AoE3 DE game navigation.

This module consolidates all verified 1920×1080 UI coordinates and provides a
``Navigator`` class that wraps ``HarnessClient`` with reliable, calibrated
primitives for driving Age of Empires 3 DE (build 100.15.99076.0 P2, ANW mod).

Key design rules baked in here:
  - **Double-click rule**: large scene-transition buttons (Play, Quit, Skirmish,
    map OK, dialog Accept) require two clicks with ~0.6 s between them;
    ``click_transition()`` encodes this everywhere it is needed.
  - **Camera-relative caveat**: in-game spatial clicks (TC, command card) are only
    valid when the camera is positioned at the game-start default (TC at ~905,475).
    Any method that performs such clicks documents this assumption in its docstring.
  - **Relaunch reset**: when ESC / menu state becomes wedged, the reliable recovery
    is ``relaunch()``, which kills stale processes and boots back to MAIN_MENU via
    ``tools.aoe3_harness._fix_harness_launch``.
  - All coordinates come from live harness-driven verification sessions and are
    tagged ``# verified 2026-06-04`` or ``# verified 2026-06-03``.

Imports work regardless of cwd thanks to the sys.path insert below.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

# Ensure the repo root is on sys.path so harness_client can be imported from
# any working directory.
sys.path.insert(0, "/var/home/jflessenkemper/AOE-3-DE-A-New-World")

from PIL import Image  # noqa: E402  (after sys.path insert)

from tools.aoe3_harness.harness_client import HarnessClient, HarnessState  # noqa: E402
from tools.aoe3_harness.british_recapture_2026 import apply_cheat_harness  # noqa: E402

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

SOCK: str = "/tmp/AOE3DEHarness.sock"
REPO: Path = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World")

# ---------------------------------------------------------------------------
# Main-menu coordinates  (x≈150, verified 2026-06-04)
# ---------------------------------------------------------------------------
MM_CONTINUE          = (150, 262)   # verified 2026-06-04
MM_LOAD              = (150, 320)   # verified 2026-06-04
MM_STORY_MODE        = (150, 378)   # verified 2026-06-04
MM_HISTORICAL        = (150, 435)   # verified 2026-06-04
MM_SKIRMISH          = (150, 490)   # verified 2026-06-04
MM_MULTIPLAYER       = (150, 550)   # verified 2026-06-04
MM_HOME_CITY         = (150, 608)   # verified 2026-06-04
MM_ART_OF_WAR        = (150, 662)   # verified 2026-06-04
MM_OPTIONS           = (150, 720)   # verified 2026-06-04
MM_TOOLS             = (150, 778)   # verified 2026-06-04
MM_NEWS              = (150, 835)   # verified 2026-06-04
MM_EXIT              = (150, 998)   # verified 2026-06-04

# Weekly popup dismiss button  (verified 2026-06-04)
POPUP_CLOSE          = (720, 762)   # verified 2026-06-04

# ---------------------------------------------------------------------------
# Options screen  (verified 2026-06-04)
# ---------------------------------------------------------------------------
OPT_TAB_GRAPHICS     = (112, 346)   # verified 2026-06-04
OPT_TAB_GAME         = (112, 400)   # verified 2026-06-04
OPT_TAB_UI           = (112, 454)   # verified 2026-06-04
OPT_TAB_SOUND        = (112, 509)   # verified 2026-06-04
OPT_TAB_ACCESS       = (112, 563)   # verified 2026-06-04
OPT_TAB_HOTKEYS      = (112, 617)   # verified 2026-06-04
OPT_BACK             = (180, 992)   # bottom-left Back (Options/Tools/Compendium)  verified 2026-06-04

# ---------------------------------------------------------------------------
# Back buttons (top-left)  (verified 2026-06-04)
# ---------------------------------------------------------------------------
BACK_TOP_LEFT        = (30, 13)     # Home City / Campaigns / Multiplayer back  verified 2026-06-04

# ---------------------------------------------------------------------------
# Skirmish lobby  (verified 2026-06-03)
# ---------------------------------------------------------------------------
LOBBY_PLAY           = (1640, 1018)  # verified 2026-06-03
LOBBY_MAP_BOX        = (1637, 430)   # verified 2026-06-03
LOBBY_DIFF_DROPDOWN  = (1780, 711)   # verified 2026-06-03
# Difficulty option y-coords (x≈1660)  verified 2026-06-03
LOBBY_DIFF_X         = 1660
LOBBY_DIFF_EASY      = (LOBBY_DIFF_X, 757)   # verified 2026-06-03
LOBBY_DIFF_STANDARD  = (LOBBY_DIFF_X, 775)   # verified 2026-06-03
LOBBY_DIFF_MODERATE  = (LOBBY_DIFF_X, 794)   # verified 2026-06-03
LOBBY_DIFF_HARD      = (LOBBY_DIFF_X, 814)   # verified 2026-06-03
LOBBY_DIFF_HARDEST   = (LOBBY_DIFF_X, 834)   # verified 2026-06-03
LOBBY_DIFF_EXTREME   = (LOBBY_DIFF_X, 854)   # verified 2026-06-03

_DIFFICULTY_MAP = {
    "easy":     LOBBY_DIFF_EASY,
    "standard": LOBBY_DIFF_STANDARD,
    "moderate": LOBBY_DIFF_MODERATE,
    "hard":     LOBBY_DIFF_HARD,
    "hardest":  LOBBY_DIFF_HARDEST,
    "extreme":  LOBBY_DIFF_EXTREME,
}

# ---------------------------------------------------------------------------
# Map picker  (verified 2026-06-03)
# ---------------------------------------------------------------------------
MAP_PICKER_GRID_FOCUS  = (150, 304)   # click to focus grid  verified 2026-06-03
MAP_PICKER_UNKNOWN_TILE = (905, 315)   # "Unknown" custom-RandMap tile after End  verified 2026-06-03
MAP_PICKER_OK          = (1530, 1010)  # verified 2026-06-03

# ---------------------------------------------------------------------------
# Tools submenu  (verified 2026-06-04)
# ---------------------------------------------------------------------------
TOOLS_SCENARIO_EDITOR = (190, 400)   # verified 2026-06-04
TOOLS_COMPENDIUM      = (190, 509)   # verified 2026-06-04

# ---------------------------------------------------------------------------
# In-game HUD  (verified 2026-06-03)
# ---------------------------------------------------------------------------
HUD_SPEED_MAX        = (1895, 1058)  # rightmost speed tick  verified 2026-06-03
HUD_PLAYER_SUMMARY_BTN = (1691, 35)  # top-right HUD → Player Summary/Tribute  verified 2026-06-04
HUD_MINIMAP          = (1829, 951)   # minimap jump target  verified 2026-06-03
HUD_GEAR             = (1872, 30)    # top-right gear icon  verified 2026-06-03

# ---------------------------------------------------------------------------
# Town Center + command card  (camera at game-start default)  (verified 2026-06-03)
# ---------------------------------------------------------------------------
TC_COORD             = (905, 475)    # TC ground footprint  verified 2026-06-03
CMD_AGE_UP           = (45, 898)     # Advance-to-next-Age Roman-numeral slot  verified 2026-06-03
CMD_TRAIN_SETTLER    = (33, 840)     # top-left command slot  verified 2026-06-03

# ---------------------------------------------------------------------------
# Politician dialog  (verified 2026-06-03)
# ---------------------------------------------------------------------------
POLITICIAN_ACCEPT    = (775, 1005)   # verified 2026-06-03
POLITICIAN_CANCEL    = (1130, 1005)  # verified 2026-06-03
POLITICIAN_PORTRAIT_1 = (435, 540)   # first (leftmost) portrait  verified 2026-06-03
# Pixels checked for dialog-open heuristic  (verified 2026-06-03)
DIALOG_PROBE_POINTS  = [(1500, 300), (1500, 260), (1450, 340)]

# ---------------------------------------------------------------------------
# Pause / quit  (verified 2026-06-03)
# ---------------------------------------------------------------------------
PAUSE_RESIGN         = (1790, 365)   # verified 2026-06-03
PAUSE_QUIT           = (1790, 408)   # verified 2026-06-03
QUIT_YES             = (720, 600)    # "Are you sure?" confirm  verified 2026-06-03
RESIGN_YES           = (720, 602)    # Resign confirm  verified 2026-06-03

# Defeat overlay
DEFEAT_VIEW_MAP      = (262, 235)    # verified 2026-06-03
DEFEAT_QUIT_BTN      = (1840, 92)    # right-side menu after View Map  verified 2026-06-03

# ---------------------------------------------------------------------------
# VK codes
# ---------------------------------------------------------------------------
VK_ESC   = 0x1B
VK_ENTER = 0x0D
VK_END   = 0x23
VK_HOME  = 0x24
VK_LEFT  = 0x25
VK_UP    = 0x26
VK_RIGHT = 0x27
VK_DOWN  = 0x28
VK_F3    = 0x72
VK_F4    = 0x73
VK_F6    = 0x75
VK_H     = 0x48

# ---------------------------------------------------------------------------
# Screen identifier literals
# ---------------------------------------------------------------------------
SCREEN_MAIN_MENU        = "MAIN_MENU"
SCREEN_SKIRMISH_LOBBY   = "SKIRMISH_LOBBY"
SCREEN_MAP_PICKER       = "MAP_PICKER"
SCREEN_OPTIONS          = "OPTIONS"
SCREEN_IN_GAME          = "IN_GAME"
SCREEN_POLITICIAN       = "POLITICIAN_DIALOG"
SCREEN_PAUSE_MENU       = "PAUSE_MENU"
SCREEN_POSTGAME         = "POSTGAME"
SCREEN_EDITOR           = "EDITOR"
SCREEN_BLACK            = "BLACK"
SCREEN_UNKNOWN          = "UNKNOWN"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    """Timestamped console log line."""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Navigator
# ---------------------------------------------------------------------------

class Navigator:
    """Wraps HarnessClient with reliable, calibrated navigation primitives.

    All coordinates are 1920×1080 (the harness internal resolution).

    Args:
        sock:    Path to the AOE3DEHarness Unix socket.
        debug_dir: Directory for debug screenshots (default /tmp/anw_nav).
    """

    def __init__(
        self,
        sock: str = SOCK,
        debug_dir: str | Path = "/tmp/anw_nav",
    ) -> None:
        self._sock = sock
        self._debug_dir = Path(debug_dir)
        self._debug_dir.mkdir(parents=True, exist_ok=True)
        self._client: Optional[HarnessClient] = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self, timeout: float = 30.0) -> "Navigator":
        """Connect to the harness socket.

        Args:
            timeout: Seconds to wait for the socket to appear.

        Returns:
            self (for chaining).
        """
        log(f"connecting to harness at {self._sock}")
        self._client = HarnessClient(self._sock)
        self._client.connect(timeout=timeout)
        log("connected")
        return self

    def close(self) -> None:
        """Close the socket connection."""
        if self._client is not None:
            self._client.close()
            self._client = None

    @property
    def client(self) -> HarnessClient:
        """Return the underlying HarnessClient; raise if not connected."""
        if self._client is None:
            raise RuntimeError("Navigator not connected; call connect() first.")
        return self._client

    # ------------------------------------------------------------------
    # Reliability primitives
    # ------------------------------------------------------------------

    def shot(self, name: str) -> Path:
        """Capture a debug screenshot and return its path.

        Args:
            name: Filename stem (without extension); .png is appended.

        Returns:
            Path to the saved PNG.
        """
        path = self._debug_dir / f"{name}.png"
        self.client.screenshot(str(path))
        log(f"screenshot → {path}")
        return path

    def brightness(self, path: Path, points: List[Tuple[int, int]]) -> float:
        """Mean RGB value over a list of pixel coordinates.

        Args:
            path:   Path to a PNG screenshot.
            points: List of (x, y) pixel coordinates to sample.

        Returns:
            Mean of all sampled channel values (0–255).
        """
        with Image.open(path) as im:
            rgb = im.convert("RGB")
            total = 0.0
            for x, y in points:
                r, g, b = rgb.getpixel((x, y))
                total += (r + g + b) / 3.0
        return total / len(points) if points else 0.0

    def detect_screen(self) -> str:
        """Screenshot the current frame and classify it into a screen name.

        Classification uses simple pixel heuristics; returns UNKNOWN when no
        signature matches confidently enough.  Calibrate thresholds live after
        verifying with debug screenshots.

        Returns:
            One of the SCREEN_* module constants.
        """
        path = self.shot("detect_probe")
        with Image.open(path) as im:
            rgb = im.convert("RGB")

            def mean(pts: List[Tuple[int, int]]) -> float:
                vals = [(rgb.getpixel((x, y))[0]
                         + rgb.getpixel((x, y))[1]
                         + rgb.getpixel((x, y))[2]) / 3.0
                        for x, y in pts]
                return sum(vals) / len(vals) if vals else 0.0

            # EDITOR (checked FIRST): the top menu bar is a reddish/brown band
            # spanning the FULL width at y≈9 (top_bar > 60) while the lower
            # two-thirds is near-black (editor canvas only renders in the top
            # ~third via the harness).  Must precede the IN_GAME check because
            # the editor's full-width menu bar also lights the y≈15 row and its
            # green canvas would otherwise satisfy the portrait gate.  An
            # in-game HUD only lights the LEFT of the top row (x<500), so its
            # full-width top_bar mean stays < 60.
            top_bar_mean = mean([(x, 9) for x in range(0, 1920, 80)])
            lower_mean = mean([(x, y) for x in range(200, 1800, 200)
                               for y in range(400, 1000, 100)])
            if top_bar_mean > 60 and lower_mean < 25:
                return SCREEN_EDITOR

            # IN_GAME: the coloured resource-bar strip at the very top-left
            # (y≈15, x 10..500) reads bright (~150-170) whenever a match is
            # running — even if the map view itself is black fog after a
            # camera/minimap jump.  Precedes the BLACK check (which samples the
            # possibly-all-fog map area).
            hud_mean = mean([(x, 15) for x in range(10, 500, 30)])
            if hud_mean > 90:
                # Politician age-up dialog: right-side BG dimmed
                # (DIALOG_PROBE_POINTS < 100) AND the 5 portrait panels lit
                # (portrait_row > 25).  Both gates needed so black-fog maps and
                # bright-terrain games are not mistaken for a dialog.
                dialog_mean = mean(DIALOG_PROBE_POINTS)
                portrait_row = mean([(x, 135) for x in range(250, 1450, 150)])
                if dialog_mean < 100 and portrait_row > 25:
                    return SCREEN_POLITICIAN
                # Pause menu: right-side button band at x≈1790, y 275–420.
                pause_mean = mean([(1790, y) for y in range(275, 420, 15)])
                if pause_mean > 120:
                    return SCREEN_PAUSE_MENU
                return SCREEN_IN_GAME

            # BLACK: entire frame near-black AND no HUD strip (true loading).
            whole_mean = mean([(x, y) for x in range(100, 1900, 200)
                               for y in range(100, 1000, 200)])
            if whole_mean < 15:
                return SCREEN_BLACK

            # --- Menu-family screens (calibrated 2026-06-04 from live shots) ---
            # Key separating signals:
            #   right_half = mean RGB along y=540, x 960..1920 (harbour bright
            #                in main-menu/sub-screens; ~17 dark wood in lobby).
            #   center500  = pixel (960,500): ~64 on harbour menus, ~20 when an
            #                Options/centred panel covers the middle, ~19 lobby.
            #   opt_tabs   = left tab column x=112, y 346..617 (>60 in Options
            #                AND Home City; combined with center500<35 it is
            #                unique to Options).
            right_half = mean([(x, 540) for x in range(960, 1920, 120)])
            center500  = mean([(960, 500)])
            opt_tabs   = mean([(112, y) for y in range(346, 620, 25)])
            play_band  = mean([(x, 1018) for x in range(1590, 1700, 15)])

            # OPTIONS: tab column lit AND the centred panel darkens (960,500).
            if opt_tabs > 60 and center500 < 35:
                return SCREEN_OPTIONS

            # SKIRMISH_LOBBY / MAP_PICKER: dark wood background (no harbour).
            # Lobby centre is dark; the map picker centre (tile grid) is bright.
            if right_half < 40:
                if center500 > 55:
                    return SCREEN_MAP_PICKER
                return SCREEN_SKIRMISH_LOBBY

            # MAIN_MENU (or a harbour-background sub-screen — Home City, Tools,
            # News, Story Mode): bright harbour fills centre+right.  detect_
            # screen cannot always tell the root main menu from these overlays
            # (they share the backdrop); the navigation methods track which
            # sub-screen they opened by construction, and goto_main_menu()
            # unwinds via ESC which is harmless at the true root.
            if right_half > 100 and center500 > 45:
                return SCREEN_MAIN_MENU

            # POSTGAME: score table — bright top strip, dark body, no harbour.
            top_s = mean([(x, 50) for x in range(200, 1800, 100)])
            body  = mean([(x, 600) for x in range(200, 1800, 100)])
            if top_s > 50 and body < 60 and right_half < 80:
                return SCREEN_POSTGAME

        return SCREEN_UNKNOWN

    def click_transition(self, x: int, y: int, settle: float = 4.0) -> None:
        """Double-click a scene-transition button and wait for it to settle.

        Encodes the verified pattern: move → 0.5 s → click → 0.6 s → click
        → sleep(settle).  This reliably commits Play, Quit, Skirmish, map OK,
        and dialog Accept buttons that ignore a single click.

        Args:
            x, y:   Coordinate of the transition button.
            settle: Seconds to sleep after the second click (default 4.0).
        """
        log(f"click_transition ({x},{y}) settle={settle}s")
        c = self.client
        c.move(x, y)
        time.sleep(0.5)
        c.click(x, y)
        time.sleep(0.6)
        c.click(x, y)
        time.sleep(settle)

    def click_once(self, x: int, y: int) -> None:
        """Move to (x, y) and send a single click (for lightweight widgets).

        Use for dropdowns, list items, tab buttons, and command-card actions —
        anything that is not a full scene-transition.

        Args:
            x, y: Coordinate of the widget.
        """
        log(f"click_once ({x},{y})")
        c = self.client
        c.move(x, y)
        time.sleep(0.2)
        c.click(x, y)
        time.sleep(0.3)

    def click_until_screen(
        self,
        x: int,
        y: int,
        target: str,
        tries: int = 4,
        settle: float = 3.5,
    ) -> bool:
        """Click (x,y) and verify arrival at ``target``, re-clicking if needed.

        Robust replacement for a blind double-click on scene transitions: each
        attempt sends ONE click then waits + re-detects.  This self-corrects
        whether the widget needs one or two clicks (a 2nd attempt supplies the
        2nd click) without the hazard of a blind double-click landing its second
        press on the freshly-transitioned screen.  Stops as soon as ``target``
        is detected.

        Args:
            x, y:   Widget coordinate.
            target: Expected SCREEN_* after the transition.
            tries:  Max single-click attempts.
            settle: Seconds to wait after each click before re-detecting.

        Returns:
            True if ``target`` was reached, else False.
        """
        for attempt in range(1, tries + 1):
            self.client.move(x, y)
            time.sleep(0.3)
            self.client.click(x, y)
            time.sleep(settle)
            screen = self.detect_screen()
            if screen == target:
                log(f"  reached {target} (attempt {attempt})")
                return True
            log(f"  {target} not reached (got {screen}); retry {attempt}/{tries}")
        log(f"  WARN: never reached {target} after {tries} attempts")
        return False

    def dismiss_popups(self) -> None:
        """Dismiss the 'Free Weekly Profile Picture' popup if present.

        Sends a double-click to the popup's Close button (720, 762).
        Harmless when the popup is absent — the click lands on the harbour
        scene background.
        """
        log("dismiss_popups — clicking Close (720,762)")
        self.click_transition(*POPUP_CLOSE, settle=1.0)

    def wait_ready(self, timeout: float = 240.0) -> HarnessState:
        """Poll STATE until ready==1.

        Args:
            timeout: Seconds before raising (default 240).

        Returns:
            HarnessState at the moment ready==1 was observed.
        """
        log(f"wait_ready (timeout={timeout}s)")
        deadline = time.monotonic() + timeout
        while True:
            st = self.client.state()
            if st.ready == 1:
                log(f"  ready=1 (pid={st.pid})")
                return st
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"Harness ready=1 not observed within {timeout}s"
                )
            time.sleep(min(2.0, remaining))

    def wait_screen(self, target: str, timeout: float = 60.0) -> None:
        """Poll detect_screen until it returns *target*.

        Args:
            target:  Expected screen constant (e.g. SCREEN_MAIN_MENU).
            timeout: Seconds before raising (default 60).
        """
        log(f"wait_screen target={target} timeout={timeout}s")
        deadline = time.monotonic() + timeout
        while True:
            current = self.detect_screen()
            if current == target:
                log(f"  screen={current} ✓")
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"wait_screen: expected {target!r} but last saw {current!r} "
                    f"after {timeout}s"
                )
            log(f"  screen={current}, waiting…")
            time.sleep(min(3.0, remaining))

    # ------------------------------------------------------------------
    # Launch / recovery
    # ------------------------------------------------------------------

    def relaunch(self) -> None:
        """Kill any stale harness process and relaunch, waiting for ready=1.

        Shells out to ``python3 -m tools.aoe3_harness._fix_harness_launch``
        from the repo root.  That script:
          1. SIGKILLs any surviving AoE3DE_s.exe and removes the stale socket.
          2. Spawns AOE3DEHarness with the correct umu/Proton environment.
          3. Polls until the socket appears (≤200 s) then STATE ready=1 (≤240 s).
          4. Detaches, leaving the harness running.

        After relaunch, this method reconnects the HarnessClient and calls
        wait_ready().  The game boots to MAIN_MENU — use this as the reliable
        reset when ESC / menu state is wedged.
        """
        log("relaunch: invoking _fix_harness_launch …")
        self.close()
        subprocess.run(
            [sys.executable, "-m", "tools.aoe3_harness._fix_harness_launch"],
            cwd=str(REPO),
            check=True,
        )
        log("relaunch: subprocess finished, reconnecting …")
        self.connect(timeout=60.0)
        self.wait_ready(timeout=240.0)
        # ready=1 fires before the menu has rendered (frame is still black for
        # several seconds) and a "Free Weekly Profile Picture" popup may appear
        # — its 5 portrait tiles + dimmed BG otherwise mimic the politician
        # dialog signature.  Wait for a lit frame, then dismiss popups.
        self._settle_menu_render()
        log("relaunch: ready=1 + rendered, at MAIN_MENU")

    def _settle_menu_render(self, timeout: float = 60.0) -> None:
        """Wait for a menu frame to render (not BLACK), then dismiss popups.

        Used after relaunch/load transitions where ready=1 precedes the first
        drawn frame.  Polls overall brightness until lit, dismisses the weekly
        profile-picture popup, and settles.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            path = self.shot("settle_probe")
            with Image.open(path) as im:
                rgb = im.convert("RGB")
                pts = [(x, y) for x in range(100, 1900, 300)
                       for y in range(100, 1000, 150)]
                avg = sum(sum(rgb.getpixel(p)) / 3 for p in pts) / len(pts)
            if avg > 40:
                break
            time.sleep(3.0)
        time.sleep(1.0)
        self.dismiss_popups()
        time.sleep(1.0)

    # ------------------------------------------------------------------
    # Menu navigation
    # ------------------------------------------------------------------

    def goto_main_menu(self) -> None:
        """Ensure we are on the MAIN_MENU screen.

        Strategy:
          1. If already MAIN_MENU, return immediately.
          2. Try ESC to close any in-game or submenu overlay; check again.
          3. If still not MAIN_MENU after ESC attempts, call relaunch().
        """
        log("goto_main_menu")
        screen = self.detect_screen()
        if screen == SCREEN_MAIN_MENU:
            log("  already at MAIN_MENU")
            return

        # Try ESC / Back to unwind
        for attempt in range(3):
            log(f"  ESC attempt {attempt + 1}/3 (current={screen})")
            self.client.key(VK_ESC)
            time.sleep(1.5)
            screen = self.detect_screen()
            if screen == SCREEN_MAIN_MENU:
                log("  reached MAIN_MENU via ESC")
                return

        # Try clicking top-left Back (works for Home City, Multiplayer, etc.)
        self.click_once(*BACK_TOP_LEFT)
        time.sleep(2.0)
        screen = self.detect_screen()
        if screen == SCREEN_MAIN_MENU:
            log("  reached MAIN_MENU via top-left Back")
            return

        # Fall back to full relaunch
        log("  goto_main_menu: ESC/Back failed, relaunching …")
        self.relaunch()

    def open_skirmish(self) -> None:
        """Navigate from MAIN_MENU to the Skirmish lobby screen.

        Calls goto_main_menu() first, then double-clicks Skirmish (150,490).
        """
        log("open_skirmish")
        self.goto_main_menu()
        if not self.click_until_screen(*MM_SKIRMISH, SCREEN_SKIRMISH_LOBBY,
                                       tries=4, settle=3.5):
            raise RuntimeError("open_skirmish: could not reach SKIRMISH_LOBBY")
        log("  opened Skirmish lobby")

    def open_options(self, tab: str = "graphics") -> None:
        """Navigate from MAIN_MENU to the Options screen and select a tab.

        Args:
            tab: One of 'graphics', 'game', 'ui', 'sound', 'accessibility',
                 'hotkeys' (case-insensitive).
        """
        log(f"open_options tab={tab}")
        self.goto_main_menu()
        self.click_transition(*MM_OPTIONS, settle=2.0)

        tab_map = {
            "graphics":     OPT_TAB_GRAPHICS,
            "game":         OPT_TAB_GAME,
            "ui":           OPT_TAB_UI,
            "sound":        OPT_TAB_SOUND,
            "accessibility": OPT_TAB_ACCESS,
            "hotkeys":      OPT_TAB_HOTKEYS,
        }
        coord = tab_map.get(tab.lower(), OPT_TAB_GRAPHICS)
        self.click_once(*coord)
        time.sleep(1.0)
        log(f"  Options tab={tab} opened")

    def _back_options(self) -> None:
        """Click the bottom-left Back button (Options / Tools / Compendium)."""
        log("back via OPT_BACK (180,992)")
        self.click_once(*OPT_BACK)
        time.sleep(2.0)

    def _back_top_left(self) -> None:
        """Click the top-left ◄ BACK button (Home City / Campaigns / Multiplayer)."""
        log("back via BACK_TOP_LEFT (30,13)")
        self.click_once(*BACK_TOP_LEFT)
        time.sleep(2.0)

    def open_home_city(self) -> None:
        """Navigate from MAIN_MENU to the Home City screen (150, 608)."""
        log("open_home_city")
        self.goto_main_menu()
        self.click_transition(*MM_HOME_CITY, settle=2.0)

    def open_tools(self) -> None:
        """Navigate from MAIN_MENU to the Tools submenu (150, 778)."""
        log("open_tools")
        self.goto_main_menu()
        self.click_transition(*MM_TOOLS, settle=2.0)

    def open_scenario_editor(self) -> None:
        """Navigate from MAIN_MENU → Tools → Scenario Editor (190, 400)."""
        log("open_scenario_editor")
        self.open_tools()
        self.click_transition(*TOOLS_SCENARIO_EDITOR, settle=3.0)

    def open_compendium(self) -> None:
        """Navigate from MAIN_MENU → Tools → Compendium (190, 509)."""
        log("open_compendium")
        self.open_tools()
        self.click_transition(*TOOLS_COMPENDIUM, settle=2.0)

    def open_historical_battles(self) -> None:
        """Navigate from MAIN_MENU to Historical Battles (150, 435)."""
        log("open_historical_battles")
        self.goto_main_menu()
        self.click_transition(*MM_HISTORICAL, settle=2.0)

    def open_story_mode(self) -> None:
        """Navigate from MAIN_MENU to Story Mode (150, 378)."""
        log("open_story_mode")
        self.goto_main_menu()
        self.click_transition(*MM_STORY_MODE, settle=2.0)

    def open_multiplayer(self) -> None:
        """Navigate from MAIN_MENU to the Multiplayer hub (150, 550)."""
        log("open_multiplayer")
        self.goto_main_menu()
        self.click_transition(*MM_MULTIPLAYER, settle=2.0)

    def open_load(self) -> None:
        """Navigate from MAIN_MENU to the Load / Open File screen (150, 320)."""
        log("open_load")
        self.goto_main_menu()
        self.click_transition(*MM_LOAD, settle=2.0)

    def open_news(self) -> None:
        """Navigate from MAIN_MENU to the News/Community overlay (150, 835)."""
        log("open_news")
        self.goto_main_menu()
        self.click_transition(*MM_NEWS, settle=2.0)

    # ------------------------------------------------------------------
    # Skirmish lobby helpers
    # ------------------------------------------------------------------

    def lobby_set_difficulty(self, level: str) -> None:
        """Set the skirmish difficulty via the dropdown.

        Args:
            level: One of 'easy', 'standard', 'moderate', 'hard', 'hardest',
                   'extreme' (case-insensitive).
        """
        log(f"lobby_set_difficulty {level}")
        self.click_once(*LOBBY_DIFF_DROPDOWN)
        time.sleep(0.6)
        coord = _DIFFICULTY_MAP.get(level.lower(), LOBBY_DIFF_EASY)
        self.click_once(*coord)
        time.sleep(0.5)

    def lobby_open_map_picker(self) -> None:
        """Double-click the map-name box to open the Select Map picker (1637,430)."""
        log("lobby_open_map_picker")
        self.click_transition(*LOBBY_MAP_BOX, settle=2.0)

    def lobby_pick_unknown_map(self) -> None:
        """In the map picker, jump to End and click the 'Unknown' custom tile.

        Clicks OK (1530, 1010) to confirm.  The "Unknown" tile is the ANW custom
        RandMap; list order can shift between sessions — verify the right-hand
        info panel if the map matters.
        """
        log("lobby_pick_unknown_map")
        self.lobby_open_map_picker()
        # Focus the grid and jump to the end where custom maps live
        self.click_once(*MAP_PICKER_GRID_FOCUS)
        time.sleep(0.4)
        self.client.key(VK_END)
        time.sleep(1.0)
        self.shot("map_picker_end")
        # Click the Unknown tile
        self.click_once(*MAP_PICKER_UNKNOWN_TILE)
        time.sleep(0.5)
        # Confirm
        self.click_transition(*MAP_PICKER_OK, settle=2.0)

    def lobby_play(self, timeout: float = 150.0) -> None:
        """Click Play (1640, 1018) and wait for the IN_GAME screen.

        Args:
            timeout: Seconds to wait for IN_GAME HUD (default 150).
        """
        log("lobby_play")
        # Play needs the double-click rule; the match then loads for ~60-90s.
        # Re-click once if we're still in the lobby after a short grace period
        # (the first double-click occasionally only highlights), then wait.
        deadline = time.monotonic() + timeout
        clicked = 0
        while time.monotonic() < deadline:
            screen = self.detect_screen()
            if screen == SCREEN_IN_GAME:
                log("  IN_GAME")
                return
            if screen == SCREEN_SKIRMISH_LOBBY and clicked < 3:
                clicked += 1
                log(f"  clicking Play (attempt {clicked})")
                self.click_transition(*LOBBY_PLAY, settle=6.0)
            else:
                # BLACK / loading — just wait for the HUD to come up.
                time.sleep(5.0)
        raise TimeoutError(
            f"lobby_play: never reached IN_GAME within {timeout}s")

    def start_skirmish(self, difficulty: str = "Easy") -> None:
        """Full flow: MAIN_MENU → open_skirmish → set difficulty → lobby_play.

        Args:
            difficulty: Difficulty level string (default 'Easy').
        """
        log(f"start_skirmish difficulty={difficulty}")
        self.open_skirmish()
        self.lobby_set_difficulty(difficulty)
        self.lobby_play()

    # ------------------------------------------------------------------
    # In-game actions
    # ------------------------------------------------------------------

    def set_speed_max(self) -> None:
        """Click the rightmost game-speed tick to set speed to maximum (1895,1058)."""
        log("set_speed_max")
        self.click_once(*HUD_SPEED_MAX)

    def cheat(self, phrase: str) -> None:
        """Apply a cheat code via the in-game chat mechanism.

        Delegates to apply_cheat_harness (from british_recapture_2026).

        Args:
            phrase: The cheat phrase to type (e.g. 'medium rare please').
        """
        log(f"cheat: {phrase!r}")
        apply_cheat_harness(self.client, phrase)

    def cheat_resources(self, n: int = 6) -> None:
        """Apply resource cheats n times each to stockpile food and coin.

        Uses the two verified working cheats:
          - 'medium rare please'      → +10 000 food per use
          - 'give me liberty or give me coin' → +10 000 coin per use

        Args:
            n: Number of times to apply each cheat (default 6 → ~60k each).
        """
        log(f"cheat_resources n={n}")
        for _ in range(n):
            self.cheat("medium rare please")
        for _ in range(n):
            self.cheat("give me liberty or give me coin")

    def pan(self, direction: str, n: int = 6) -> None:
        """Pan the camera with arrow keys.

        Args:
            direction: One of 'left', 'up', 'right', 'down'.
            n:         Number of key taps (default 6).
        """
        vk_map = {
            "left":  VK_LEFT,
            "up":    VK_UP,
            "right": VK_RIGHT,
            "down":  VK_DOWN,
        }
        vk = vk_map.get(direction.lower())
        if vk is None:
            raise ValueError(f"Unknown direction: {direction!r}")
        log(f"pan {direction} x{n}")
        for _ in range(n):
            self.client.key(vk)
            time.sleep(0.1)

    def minimap_jump(self, x: int = 1829, y: int = 951) -> None:
        """Click the minimap to jump the camera to a world point.

        Args:
            x, y: Pixel coordinate on the minimap (default centre ≈1829,951).
        """
        log(f"minimap_jump ({x},{y})")
        self.click_once(x, y)

    def toggle_score(self) -> None:
        """Toggle the Score panel (F4 / 0x73)."""
        log("toggle_score F4")
        self.client.key(VK_F4)

    def toggle_objectives(self) -> None:
        """Toggle the Objectives dialog (F3 / 0x72)."""
        log("toggle_objectives F3")
        self.client.key(VK_F3)

    def toggle_player_summary(self) -> None:
        """Toggle the Player Summary dialog (F6 / 0x75)."""
        log("toggle_player_summary F6")
        self.client.key(VK_F6)

    def home_city_panel(self) -> None:
        """Open the Home City / deck / shipments overlay (H / 0x48)."""
        log("home_city_panel H")
        self.client.key(VK_H)

    def reveal_map(self) -> None:
        """Reveal the ENTIRE map via the 'X marks the spot' cheat.

        VERIFIED 2026-06-04: typing this cheat through chat removes the fog of
        war for the whole map, so every player's base is visible on the minimap
        and by panning.  This is the reliable "see all enemy bases" method —
        unlike unilateral allying, it needs no AI cooperation and works in FFA.
        (The minimap fills with terrain/resources/coloured player dots.)
        """
        log("reveal_map — 'X marks the spot'")
        self.cheat("X marks the spot")

    def player_summary(self) -> None:
        """Open the Player Summary / Tribute panel (HUD button ≈1691,35).

        VERIFIED 2026-06-04: lists all 8 players with team colours and tribute
        columns (Send / Clear / Close).  Use to read the full player roster or
        send resources.  NOTE: this is NOT a diplomacy/ally toggle — single-
        player FFA skirmish has no unilateral "ally AI" control, so to *see*
        enemy bases use reveal_map() instead.  Close with CLOSE (≈1410,815) or
        by re-clicking the HUD button.
        """
        log("player_summary — HUD button (1691,35)")
        self.click_once(*HUD_PLAYER_SUMMARY_BTN)

    def ally_all(self, opponents: int = 7) -> None:
        """Best-effort: open the player panel to attempt allying opponents.

        LIMITATION (2026-06-04): the stock Alt+D diplomacy hotkey did not open a
        diplomacy panel through the harness, and the HUD panel at (1691,35) is
        the Player Summary/Tribute panel (no ally toggle) — FFA skirmish does
        not expose unilateral allying.  For the practical goal of *seeing* every
        base, prefer reveal_map().  This method simply opens the player panel so
        a caller can inspect/tribute; it does not change diplomacy.
        """
        log(f"ally_all (best-effort; opponents={opponents}) — see reveal_map()")
        self.player_summary()

    def select_tc(self, tc: Tuple[int, int] = TC_COORD) -> None:
        """Click the Town Center ground footprint.

        CAMERA-RELATIVE: assumes the camera is at the game-start default
        position (TC ground footprint ≈905,475).  Move the camera first if
        the game has been running for a while.

        Args:
            tc: (x, y) override for the TC footprint.
        """
        log(f"select_tc at {tc}")
        self.click_once(*tc)
        time.sleep(0.5)

    def age_up(self, politician: int = 1) -> None:
        """Trigger an age-up from the TC command card.

        Flow: select_tc → click age-up button (45,898) → screenshot the
        politician dialog → click politician portrait → Accept (775,1005).

        CAMERA-RELATIVE: assumes camera is on the TC (fresh game start or
        after a minimap_jump to base).

        Args:
            politician: 1-based index of the politician portrait to select
                        (default 1 = leftmost / pre-selected).
        """
        log(f"age_up politician={politician}")
        self.select_tc()
        self.click_once(*CMD_AGE_UP)
        time.sleep(2.0)
        self.shot("age_up_dialog")
        # Click politician portrait (portraits row y≈540, first at x≈435)
        portrait_x = 435 + (politician - 1) * 130
        portrait_y = 540
        self.click_once(portrait_x, portrait_y)
        time.sleep(0.5)
        self.click_transition(*POLITICIAN_ACCEPT, settle=3.0)

    def train_settler(self) -> None:
        """Click the Train Settler command card slot (33, 840).

        CAMERA-RELATIVE: assumes camera is positioned on the TC.
        """
        log("train_settler")
        self.select_tc()
        self.click_once(*CMD_TRAIN_SETTLER)

    def apply_age_dialog_detect(self) -> bool:
        """Return True if the politician age-up dialog appears to be open.

        Heuristic: ≥2 of the three probe pixels near (1500,300) have mean
        RGB < 100, indicating the background has been dimmed by the dialog
        overlay.  Verified 2026-06-03.

        Returns:
            True if the dialog is likely open.
        """
        path = self.shot("dialog_probe")
        with Image.open(path) as im:
            rgb = im.convert("RGB")
            dark_count = 0
            for x, y in DIALOG_PROBE_POINTS:
                r, g, b = rgb.getpixel((x, y))
                if (r + g + b) / 3.0 < 100:
                    dark_count += 1
        result = dark_count >= 2
        log(f"apply_age_dialog_detect → {result} (dark_count={dark_count})")
        return result

    def pause_menu(self) -> None:
        """Press ESC to open the in-game pause menu.

        Note: ESC can be flaky right after a harness relaunch (see wiki).
        If the menu does not appear, press ESC twice.
        """
        log("pause_menu ESC")
        self.client.key(VK_ESC)
        time.sleep(1.5)

    def quit_to_main(self) -> None:
        """From in-game: open pause menu → Quit → confirm YES → wait for MAIN_MENU.

        ESC → Quit (1790,408) double-click → YES (720,600) double-click.
        """
        log("quit_to_main")
        self.pause_menu()
        self.client.key(VK_ESC)   # press twice in case focus was on chat
        time.sleep(0.5)
        self.click_transition(*PAUSE_QUIT, settle=2.0)
        self.click_transition(*QUIT_YES, settle=4.0)
        log("  waiting for MAIN_MENU …")
        self.wait_screen(SCREEN_MAIN_MENU, timeout=30.0)

    def resign(self) -> None:
        """From in-game: open pause menu → Resign → confirm YES.

        ESC → Resign (1790,365) double-click → YES (720,602) double-click.
        """
        log("resign")
        self.pause_menu()
        self.click_transition(*PAUSE_RESIGN, settle=2.0)
        self.click_transition(*RESIGN_YES, settle=4.0)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "anw_navigator — AoE3 DE game navigation CLI.\n"
            "Requires the AOE3DEHarness socket to be running at "
            f"{SOCK}."
        )
    )
    p.add_argument(
        "--sock", default=SOCK,
        help=f"Path to the harness socket (default: {SOCK})"
    )
    p.add_argument(
        "--debug-dir", default="/tmp/anw_nav",
        help="Directory for debug screenshots (default: /tmp/anw_nav)"
    )
    sub = p.add_subparsers(dest="command", required=True)

    # detect
    sub.add_parser("detect", help="Connect, print detect_screen() result.")

    # selftest
    sub.add_parser(
        "selftest",
        help="Connect, print state + detect_screen. Non-destructive."
    )

    # goto
    goto = sub.add_parser(
        "goto",
        help="Navigate to a screen: MAIN_MENU, SKIRMISH_LOBBY, OPTIONS, "
             "HOME_CITY, TOOLS, EDITOR."
    )
    goto.add_argument(
        "screen",
        choices=["MAIN_MENU", "SKIRMISH_LOBBY", "OPTIONS", "HOME_CITY",
                 "TOOLS", "EDITOR"],
    )

    # tour
    sub.add_parser(
        "tour",
        help="Visit Options tabs, Home City, Tools, back to main, "
             "screenshotting each for calibration."
    )

    return p


def main() -> int:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args()

    nav = Navigator(sock=args.sock, debug_dir=args.debug_dir)
    nav.connect(timeout=30.0)

    try:
        if args.command == "detect":
            screen = nav.detect_screen()
            print(screen)

        elif args.command == "selftest":
            st = nav.client.state()
            print(
                f"state: pid={st.pid} uptime_ms={st.uptime_ms} "
                f"ready={st.ready} {st.internal_w}x{st.internal_h}"
            )
            screen = nav.detect_screen()
            print(f"screen: {screen}")

        elif args.command == "goto":
            target = args.screen
            if target == "MAIN_MENU":
                nav.goto_main_menu()
            elif target == "SKIRMISH_LOBBY":
                nav.open_skirmish()
            elif target == "OPTIONS":
                nav.open_options()
            elif target == "HOME_CITY":
                nav.open_home_city()
            elif target == "TOOLS":
                nav.open_tools()
            elif target == "EDITOR":
                nav.open_scenario_editor()
            after = nav.detect_screen()
            print(f"screen after goto {target}: {after}")

        elif args.command == "tour":
            log("=== tour: starting from MAIN_MENU ===")
            nav.goto_main_menu()
            nav.shot("tour_00_main_menu")

            # Options — all tabs
            tabs = ["graphics", "game", "ui", "sound", "accessibility", "hotkeys"]
            for tab in tabs:
                nav.open_options(tab=tab)
                nav.shot(f"tour_opt_{tab}")
                log(f"  Options/{tab} → screen={nav.detect_screen()}")
                nav._back_options()
                nav.goto_main_menu()

            # Home City
            nav.open_home_city()
            nav.shot("tour_home_city")
            log(f"  Home City → screen={nav.detect_screen()}")
            nav._back_top_left()
            nav.goto_main_menu()
            nav.shot("tour_after_home_city_back")

            # Tools
            nav.open_tools()
            nav.shot("tour_tools")
            log(f"  Tools → screen={nav.detect_screen()}")
            nav._back_options()
            nav.goto_main_menu()
            nav.shot("tour_end_main_menu")
            log(f"  final screen={nav.detect_screen()}")
            log(f"=== tour complete — screenshots in {nav._debug_dir} ===")

    finally:
        nav.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
