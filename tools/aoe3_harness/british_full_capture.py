#!/usr/bin/env python3
"""
ANWBritish full capture script — harness-only input (no xdotool/cursor-grab).

Captures:
  01_lobby.png               — skirmish setup with British selected
  02_loading.png             — loading screen
  03_hud.png                 — in-game HUD
  09_hero_selected.png       — explorer/hero unit selected in HUD
  07_scoreboard.png          — scoreboard (Tab hold)
  06_diplomacy.png           — diplomacy panel
  05_homecity_panel.png      — home city panel
  05_tech_tree.png           — tech tree (ESC menu → Technology Tree)
  08_esc_menu.png            — ESC menu
  08_ageup_age2.png          — Age II politician dialog (re-fresh)
  08_ageup_age3.png          — Age III politician dialog
  08_ageup_age4.png          — Age IV politician dialog
  08_ageup_age5.png          — Age V politician dialog

Run from repo root:
  python3 tools/aoe3_harness/british_full_capture.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
# Remove the harness dir from sys.path to avoid shadowing stdlib modules
# (tools/aoe3_harness/bisect.py shadows stdlib bisect which PIL needs)
_harness_dir = str(Path(__file__).resolve().parent)
while _harness_dir in sys.path:
    sys.path.remove(_harness_dir)

from tools.aoe3_harness.harness_client import HarnessClient, HarnessConnectionError
from tools.aoe3_harness.vk import (
    VK_ESCAPE, VK_RETURN, VK_TAB, VK_SPACE,
    VK_UP, VK_DOWN, VK_HOME, VK_END,
    VK_A, VK_B, VK_C, VK_D, VK_E, VK_F, VK_G, VK_H, VK_I, VK_J,
    VK_K, VK_L, VK_M, VK_N, VK_O, VK_P, VK_Q, VK_R, VK_S, VK_T,
    VK_U, VK_V, VK_W, VK_X, VK_Y, VK_Z,
    VK_0, VK_1, VK_2, VK_3, VK_4, VK_5, VK_6, VK_7, VK_8, VK_9,
    VK_SHIFT,
)

SOCK = "/tmp/AOE3DEHarness.sock"
OUT = REPO / "artifacts" / "validation" / "visual_art" / "ANWBritish" / "full"
OUT.mkdir(parents=True, exist_ok=True)
TMP = Path("/tmp/brit_capture")
TMP.mkdir(exist_ok=True)

# Verified coords (lobby_coords.json + in_game_driver.py calibrated values)
SKIRMISH_BTN      = (130, 482)   # main_menu.skirmish_button
P1_CIV_FLAG       = (630, 170)   # lobby.p1_civ_picker
PICKER_OK         = (215, 962)   # civ_picker.ok_button
PLAY_BTN          = (1645, 1019) # lobby.play_button
GEARS_BTN         = (1860, 30)   # ESC menu gear icon
ESC_RESIGN        = (1830, 365)  # ESC menu → Resign
RESIGN_YES        = (760, 605)   # Resign confirm → Yes
VIEW_POSTGAME     = (1145, 737)  # abandon screen → View Postgame
POSTGAME_QUIT     = (50, 20)     # postgame → back to main menu
DIPLOMACY_BTN     = (1691, 35)   # diplomacy inkwell icon
ESC_TECH_TREE     = (1830, 140)  # ESC menu → Technology Tree
SPEED_BAR_MAX     = (1895, 1058) # speed tick 5
AGE_UP_BTN        = (1356, 1029) # TC age-up action button
POLITICIAN_1      = (435, 540)   # leftmost politician portrait
ACCEPT_BTN        = (760, 1010)  # Accept button in age-up dialog

# VK map for cheat typing
_CHAR_TO_VK = {
    'a': VK_A, 'b': VK_B, 'c': VK_C, 'd': VK_D, 'e': VK_E, 'f': VK_F,
    'g': VK_G, 'h': VK_H, 'i': VK_I, 'j': VK_J, 'k': VK_K, 'l': VK_L,
    'm': VK_M, 'n': VK_N, 'o': VK_O, 'p': VK_P, 'q': VK_Q, 'r': VK_R,
    's': VK_S, 't': VK_T, 'u': VK_U, 'v': VK_V, 'w': VK_W, 'x': VK_X,
    'y': VK_Y, 'z': VK_Z,
    '0': VK_0, '1': VK_1, '2': VK_2, '3': VK_3, '4': VK_4,
    '5': VK_5, '6': VK_6, '7': VK_7, '8': VK_8, '9': VK_9,
    ' ': VK_SPACE,
    '\r': VK_RETURN, '\n': VK_RETURN,
    '&': None,  # will be skipped
}

_c: HarnessClient = None  # type: ignore


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def connect() -> None:
    global _c
    _c = HarnessClient(SOCK, timeout=15.0)
    _c.connect(timeout=10.0)
    s = _c.state()
    log(f"Connected: pid={s.pid} ready={s.ready} {s.internal_w}x{s.internal_h}")


def alive() -> bool:
    try:
        _c.state()
        return True
    except Exception:
        return False


def snap(name: str, *, dest: Path | None = None) -> Path:
    p = (dest or OUT) / name
    r = _c.screenshot(str(p))
    try:
        rel = p.relative_to(REPO)
    except ValueError:
        rel = p
    log(f"  => {rel} ({r.bytes_written:,}B)")
    return p


def tmp_snap(name: str) -> Path:
    return snap(name, dest=TMP)


def click(x: int, y: int, wait: float = 0.3) -> None:
    _c.move(x, y)
    time.sleep(0.05)
    _c.click(x, y)
    time.sleep(wait)


def key(vk: int, wait: float = 0.15) -> None:
    _c.key(vk)
    time.sleep(wait)


def keys(vk: int, n: int, wait: float = 0.05) -> None:
    for _ in range(n):
        _c.key(vk)
        time.sleep(wait)


def type_text(text: str) -> None:
    """Type a string via individual VK key presses (lowercase only)."""
    for ch in text.lower():
        vk = _CHAR_TO_VK.get(ch)
        if vk is None:
            log(f"  WARN: no VK for char {ch!r}, skipping")
            continue
        _c.key(vk)
        time.sleep(0.04)


def apply_cheat(phrase: str) -> None:
    """Open chat, type cheat phrase, close chat."""
    log(f"  cheat: {phrase!r}")
    key(VK_RETURN, wait=0.8)
    type_text(phrase)
    time.sleep(0.3)
    key(VK_RETURN, wait=1.5)


def wait_for_ingame(timeout: float = 300.0) -> bool:
    """Watch Age3Log.txt for 'entering mode 27' marker."""
    log_path = (
        Path.home()
        / ".local/share/Steam/steamapps/compatdata/933110"
        / "pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt"
    )
    deadline = time.monotonic() + timeout
    log(f"  Watching log for 'entering mode 27' (timeout={timeout}s)...")
    try:
        start_offset = log_path.stat().st_size
    except OSError:
        start_offset = 0

    last_snap_t = time.monotonic()
    snap_idx = 0
    while time.monotonic() < deadline:
        if not alive():
            log("  CRASH detected in wait_for_ingame")
            return False
        if time.monotonic() - last_snap_t > 20.0:
            try:
                snap_idx += 1
                _c.screenshot(str(TMP / f"load_poll_{snap_idx:02d}.png"))
                elapsed = int(time.monotonic() - (deadline - timeout))
                log(f"  load poll #{snap_idx} at {elapsed}s elapsed")
            except Exception:
                pass
            last_snap_t = time.monotonic()
        try:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                f.seek(start_offset)
                content = f.read()
            if "entering mode 27 (SinglePlayer)" in content:
                log("  mode 27 detected — in-game!")
                return True
            if "D3D11 Error" in content or "is forced to terminate" in content:
                log("  CRASH signal in log")
                return False
        except OSError:
            pass
        time.sleep(3.0)
    log(f"  TIMEOUT: never saw mode 27 after {timeout}s")
    return False


def probe_age_up_ready() -> bool:
    """Quick pixel probe to see if age-up button is gold/active."""
    from PIL import Image
    probe = str(TMP / "ageup_probe.png")
    try:
        _c.screenshot(probe)
        with Image.open(probe) as im:
            # AGE_UP region at (1320, 1000, 1395, 1060)
            crop = im.crop((1320, 1000, 1395, 1060)).convert("RGB")
            px = list(crop.getdata())
            golden = sum(1 for (r, g, b) in px if r >= 180 and g >= 140 and b <= 100)
            ratio = golden / len(px)
            log(f"  age-up gold ratio: {ratio:.2%}")
            return ratio > 0.05
    except Exception as e:
        log(f"  probe error: {e}")
        return False


def capture_age_up(target_age: int, out_name: str) -> bool:
    """Trigger age-up dialog, capture it, advance to next age."""
    log(f"--- Age {target_age}: {out_name} ---")
    # Apply resources
    apply_cheat("this is too hard")
    apply_cheat("this is too hard")
    time.sleep(1.0)

    # Select TC (H key)
    for attempt in range(5):
        key(VK_H, wait=1.5)
        tmp_snap(f"ageup{target_age}_tc_select_a{attempt}.png")
        if probe_age_up_ready():
            break
        log(f"  age-up not ready yet (attempt {attempt+1}), waiting 8s...")
        time.sleep(8.0)
    else:
        log(f"  WARN: age-up never active for age {target_age}")
        return False

    # Click age-up
    click(AGE_UP_BTN[0], AGE_UP_BTN[1], wait=2.0)
    tmp_snap(f"ageup{target_age}_dialog_raw.png")
    time.sleep(0.5)

    # Save to OUT
    snap(out_name)

    # Accept: click left politician then Accept
    click(POLITICIAN_1[0], POLITICIAN_1[1], wait=0.6)
    click(ACCEPT_BTN[0], ACCEPT_BTN[1], wait=2.0)
    log(f"  Accepted age {target_age}, waiting for transition...")
    time.sleep(25.0)  # at speed 5, transition takes ~20-25s

    return True


# ─── Main flow ───────────────────────────────────────────────────────────────

def main() -> int:
    connect()

    # ── 1. Navigate to Skirmish ───────────────────────────────────────────────
    log("Step 1: Main menu → Skirmish")
    tmp_snap("pre_skirmish.png")
    click(*SKIRMISH_BTN, wait=3.5)
    if not alive():
        log("ABORT: crash after Skirmish click")
        return 1
    tmp_snap("after_skirmish_click.png")

    # ── 2. Select P1 civ: ANWBritish ─────────────────────────────────────────
    log("Step 2: Select ANWBritish (arrow-key idx=3 — British Empire (London))")
    click(*P1_CIV_FLAG, wait=2.5)
    tmp_snap("picker_opened.png")
    # Scroll to top
    keys(VK_UP, 60, wait=0.03)
    time.sleep(0.5)
    tmp_snap("picker_at_top.png")
    # Navigate down 3 to British Empire (London)
    # Verified from picker screenshot: idx 0=Random, 1=Argentines, 2=Bourbon France, 3=British Empire
    keys(VK_DOWN, 3, wait=0.06)
    time.sleep(0.5)
    tmp_snap("picker_at_3.png")
    # Confirm
    click(*PICKER_OK, wait=2.5)
    log("  ANWBritish selected (expected)")

    # Capture lobby
    snap("01_lobby.png")
    log("01_lobby.png captured")

    if not alive():
        log("ABORT: crash after civ selection")
        return 1

    # ── 3. Click Play ─────────────────────────────────────────────────────────
    log("Step 3: Click Play")
    click(*PLAY_BTN, wait=3.0)
    snap("02_loading.png")
    log("02_loading.png captured")

    # ── 4. Wait for in-game ───────────────────────────────────────────────────
    log("Step 4: Waiting for in-game...")
    if not wait_for_ingame(timeout=300.0):
        log("ABORT: never reached in-game")
        _c.screenshot(str(TMP / "load_failure.png"))
        return 1

    log("  In-game! Settling 10s...")
    time.sleep(10.0)
    if not alive():
        log("ABORT: crash after loading")
        return 1
    snap("03_hud.png")
    log("03_hud.png captured")

    # ── 5. Set speed to max ────────────────────────────────────────────────────
    log("Step 5: Set max speed")
    click(*SPEED_BAR_MAX, wait=0.5)

    # ── 6. Hero/Explorer screenshot ───────────────────────────────────────────
    log("Step 6: Hero/Explorer screenshot")
    # Deselect anything first
    key(VK_ESCAPE, wait=0.5)
    # Try to select the Explorer by clicking near TC. At game start the explorer
    # is typically a few tiles from the TC centre. TC defaults to ~(920, 380) in
    # the default AoE3 starting camera. Explorer is often 1-2 tiles south/east.
    # We try multiple positions and keep the last one.
    for ex, ey in [(920, 430), (880, 450), (960, 450), (840, 420)]:
        click(ex, ey, wait=0.8)
        tmp_snap(f"hero_click_{ex}_{ey}.png")
    # The last click's selection panel should be visible. Take the hero shot.
    snap("09_hero_selected.png")
    log("09_hero_selected.png captured")

    # ── 7. Scoreboard ─────────────────────────────────────────────────────────
    log("Step 7: Scoreboard")
    key(VK_ESCAPE, wait=0.3)
    key(VK_TAB, wait=1.5)
    snap("07_scoreboard.png")
    log("07_scoreboard.png captured")
    key(VK_TAB, wait=0.5)

    # ── 8. Diplomacy ──────────────────────────────────────────────────────────
    log("Step 8: Diplomacy panel")
    click(*DIPLOMACY_BTN, wait=2.0)
    snap("06_diplomacy.png")
    log("06_diplomacy.png captured")
    key(VK_ESCAPE, wait=0.8)

    # ── 9. Home City ──────────────────────────────────────────────────────────
    log("Step 9: Home City panel")
    key(VK_J, wait=2.5)
    snap("05_homecity_panel.png")
    log("05_homecity_panel.png captured")
    key(VK_ESCAPE, wait=0.8)

    # ── 10. ESC menu ──────────────────────────────────────────────────────────
    log("Step 10: ESC menu")
    click(*GEARS_BTN, wait=1.5)
    snap("08_esc_menu.png")
    log("08_esc_menu.png captured")

    # Tech Tree from ESC menu
    click(*ESC_TECH_TREE, wait=3.0)
    snap("05_tech_tree.png")
    log("05_tech_tree.png captured")
    key(VK_ESCAPE, wait=1.0)  # close tech tree
    time.sleep(0.5)

    # ── 11. Age-up dialogs II → V ─────────────────────────────────────────────
    log("Step 11: Age-up dialogs")
    # Age II (capture, then advance)
    log("  --- Age II ---")
    apply_cheat("this is too hard")
    apply_cheat("this is too hard")
    time.sleep(1.0)
    for attempt in range(5):
        key(VK_H, wait=1.5)
        if probe_age_up_ready():
            break
        log(f"  age2 not ready (attempt {attempt+1}), waiting 8s...")
        time.sleep(8.0)
    click(*AGE_UP_BTN, wait=2.0)
    tmp_snap("ageup2_dialog_raw.png")
    snap("08_ageup_age2.png")
    log("08_ageup_age2.png captured")
    click(*POLITICIAN_1, wait=0.6)
    click(*ACCEPT_BTN, wait=2.0)
    log("  Age II accepted, waiting 25s...")
    time.sleep(25.0)

    if not alive():
        log("CRASH after Age II — saving summary and stopping")
        return _summarize(["08_ageup_age3.png", "08_ageup_age4.png", "08_ageup_age5.png"])

    # Age III
    ok3 = capture_age_up(3, "08_ageup_age3.png")
    if not alive():
        log("CRASH after Age III capture")
        return _summarize(["08_ageup_age4.png", "08_ageup_age5.png"])

    # Age IV
    ok4 = capture_age_up(4, "08_ageup_age4.png")
    if not alive():
        log("CRASH after Age IV capture")
        return _summarize(["08_ageup_age5.png"])

    # Age V
    ok5 = capture_age_up(5, "08_ageup_age5.png")

    # ── 12. Resign ────────────────────────────────────────────────────────────
    log("Step 12: Resign")
    if alive():
        click(*GEARS_BTN, wait=1.5)
        click(*ESC_RESIGN, wait=1.5)
        click(*RESIGN_YES, wait=3.0)
        time.sleep(2.0)
        snap("09_endgame.png")
        log("09_endgame.png captured")
        time.sleep(1.0)
        click(*VIEW_POSTGAME, wait=3.0)
        time.sleep(2.0)
        click(*POSTGAME_QUIT, wait=3.0)
        log("  Resigned to main menu")

    return _summarize([])


def _summarize(failed_surfaces: list[str]) -> int:
    log("\n=== CAPTURE SUMMARY ===")
    all_surfaces = [
        "01_lobby.png", "02_loading.png", "03_hud.png", "09_hero_selected.png",
        "07_scoreboard.png", "06_diplomacy.png", "05_homecity_panel.png",
        "05_tech_tree.png", "08_esc_menu.png", "08_ageup_age2.png",
        "08_ageup_age3.png", "08_ageup_age4.png", "08_ageup_age5.png",
        "09_endgame.png",
    ]
    ok = 0
    for s in all_surfaces:
        p = OUT / s
        if p.exists():
            log(f"  OK  ({p.stat().st_size:>10,}B) {s}")
            ok += 1
        else:
            log(f"  MISS                    {s}")
    log(f"\nTotal: {ok}/{len(all_surfaces)} surfaces captured")
    if failed_surfaces:
        log(f"Expected failures: {failed_surfaces}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
