#!/usr/bin/env python3
"""ANWBritish full capture via the FAST anwHubTest random-map path.

Combines two proven pieces (harness-only input, NO xdotool/cursor-grab):
  * drive_hubtest.py  — fast anwHubTest map selection (skips slow Skirmish
    civ-picker fumbling for the MAP; we still set P1=British).
  * british_full_capture.py — the canonical surface-capture sequence.

Pre-condition: game running, harness socket live at /tmp/AOE3DEHarness.sock.
If a leftover match is paused with the ESC menu open, we resign it first.

Captures into artifacts/validation/visual_art/ANWBritish/full/:
  01_lobby, 02_loading, 03_hud, 09_hero_selected, 07_scoreboard,
  06_diplomacy, 05_homecity_panel, 05_tech_tree, 08_esc_menu,
  08_ageup_age2..5, 09_endgame.

Honest crash reporting + ~15 min wall cap.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World")
sys.path.insert(0, str(REPO))
_hd = str(Path(__file__).resolve().parent)
while _hd in sys.path:
    sys.path.remove(_hd)

from tools.aoe3_harness.harness_client import HarnessClient  # noqa: E402
from tools.aoe3_harness.vk import (  # noqa: E402
    VK_ESCAPE, VK_RETURN, VK_TAB, VK_SPACE, VK_UP, VK_DOWN, VK_END, VK_H, VK_J,
    VK_A, VK_B, VK_C, VK_D, VK_E, VK_F, VK_G, VK_I, VK_K, VK_L, VK_M, VK_N,
    VK_O, VK_P, VK_Q, VK_R, VK_S, VK_T, VK_U, VK_V, VK_W, VK_X, VK_Y, VK_Z,
    VK_0, VK_1, VK_2, VK_3, VK_4, VK_5, VK_6, VK_7, VK_8, VK_9,
)

SOCK = "/tmp/AOE3DEHarness.sock"
OUT = REPO / "artifacts/validation/visual_art/ANWBritish/full"
OUT.mkdir(parents=True, exist_ok=True)
TMP = Path("/tmp/brit_hub_capture")
TMP.mkdir(exist_ok=True)
LOG_PATH = (
    Path.home() / ".local/share/Steam/steamapps/compatdata/933110"
    / "pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt"
)

# Fast-path map coords (from drive_hubtest.py)
SKIRMISH = (130, 482)
MAP_BTN = (1637, 425)
HUBTEST_TILE = (1059, 304)        # "Unknown" tile after End
# British P1 selection (from british_full_capture.py)
P1_CIV_FLAG = (630, 170)
PICKER_OK = (215, 962)
PLAY_BTN = (1648, 1048)
# In-game surfaces (british_full_capture.py constants)
GEARS_BTN = (1860, 30)
ESC_TECH_TREE = (1830, 140)
DIPLOMACY_BTN = (1691, 35)
SPEED_BAR_MAX = (1895, 1058)
AGE_UP_BTN = (1356, 1029)
POLITICIAN_1 = (435, 540)
ACCEPT_BTN = (760, 1010)
# ESC-menu resign (this build's right-aligned menu, color-scanned 2026-06-02)
ESC_RESIGN_HERE = (1720, 365)
RESIGN_YES = (760, 605)

_CHAR_TO_VK = {
    'a': VK_A, 'b': VK_B, 'c': VK_C, 'd': VK_D, 'e': VK_E, 'f': VK_F,
    'g': VK_G, 'h': VK_H, 'i': VK_I, 'j': VK_J, 'k': VK_K, 'l': VK_L,
    'm': VK_M, 'n': VK_N, 'o': VK_O, 'p': VK_P, 'q': VK_Q, 'r': VK_R,
    's': VK_S, 't': VK_T, 'u': VK_U, 'v': VK_V, 'w': VK_W, 'x': VK_X,
    'y': VK_Y, 'z': VK_Z, '0': VK_0, '1': VK_1, '2': VK_2, '3': VK_3,
    '4': VK_4, '5': VK_5, '6': VK_6, '7': VK_7, '8': VK_8, '9': VK_9,
    ' ': VK_SPACE, '\r': VK_RETURN, '\n': VK_RETURN,
}

_c: HarnessClient = None  # type: ignore
_START = time.monotonic()
WALL_CAP_S = 15 * 60


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] (+{int(time.monotonic()-_START)}s) {m}", flush=True)


def over_cap() -> bool:
    return (time.monotonic() - _START) > WALL_CAP_S


def connect() -> None:
    global _c
    _c = HarnessClient(SOCK, timeout=60.0)
    _c.connect(timeout=15.0)
    s = _c.state()
    log(f"connected pid={s.pid} ready={s.ready} {s.internal_w}x{s.internal_h}")


def alive() -> bool:
    try:
        _c.state()
        return True
    except Exception:
        return False


def snap(name: str, dest: Path | None = None) -> Path:
    p = (dest or OUT) / name
    try:
        r = _c.screenshot(str(p))
        log(f"  => {name} ({r.bytes_written:,}B)")
    except Exception as e:
        log(f"  SHOT FAIL {name}: {type(e).__name__}")
    return p


def click(x: int, y: int, wait: float = 0.4) -> None:
    _c.move(x, y); time.sleep(0.05); _c.click(x, y); time.sleep(wait)


def key(vk: int, wait: float = 0.2) -> None:
    _c.key(vk); time.sleep(wait)


def keys(vk: int, n: int, wait: float = 0.05) -> None:
    for _ in range(n):
        _c.key(vk); time.sleep(wait)


def type_text(t: str) -> None:
    for ch in t.lower():
        vk = _CHAR_TO_VK.get(ch)
        if vk is not None:
            _c.key(vk); time.sleep(0.04)


def cheat(phrase: str) -> None:
    key(VK_RETURN, 0.8); type_text(phrase); time.sleep(0.3); key(VK_RETURN, 1.5)


def last_mode() -> int | None:
    try:
        txt = LOG_PATH.read_text(errors="ignore")
    except OSError:
        return None
    lm = None
    for line in txt.splitlines():
        if "entering mode" in line:
            try:
                lm = int(line.split("entering mode ")[1].split(" ")[0])
            except (IndexError, ValueError):
                pass
    return lm


def wait_for_ingame(timeout: float = 240.0) -> bool:
    deadline = time.monotonic() + timeout
    try:
        start_off = LOG_PATH.stat().st_size
    except OSError:
        start_off = 0
    log(f"  waiting for mode 27 (timeout={timeout}s)")
    while time.monotonic() < deadline:
        if not alive():
            log("  CRASH during load wait")
            return False
        try:
            with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
                f.seek(start_off)
                c = f.read()
            if "entering mode 27" in c:
                log("  mode 27 — in game")
                return True
            if "D3D11 Error" in c or "forced to terminate" in c:
                log("  CRASH signal in log")
                return False
        except OSError:
            pass
        time.sleep(3.0)
    log("  TIMEOUT waiting for mode 27")
    return False


def resign_if_in_match() -> None:
    """If a leftover match is live (mode 27/34), resign to main menu."""
    lm = last_mode()
    log(f"  pre-flight last mode = {lm}")
    if lm in (27, 34):
        log("  leftover match detected — resigning to main menu")
        snap("_preflight_match.png", TMP)
        # ensure ESC menu open
        click(*GEARS_BTN, 1.2)
        snap("_preflight_escmenu.png", TMP)
        click(*ESC_RESIGN_HERE, 1.5)
        snap("_preflight_resign_confirm.png", TMP)
        click(*RESIGN_YES, 3.0)
        time.sleep(3.0)
        # postgame -> back to menu (top-left back + center continue)
        click(1145, 737, 2.5)   # view postgame / continue
        click(50, 20, 2.5)      # back to main menu
        time.sleep(4.0)
        log(f"  post-resign last mode = {last_mode()}")


def probe_age_up_ready() -> bool:
    from PIL import Image
    p = str(TMP / "ageup_probe.png")
    try:
        _c.screenshot(p)
        with Image.open(p) as im:
            crop = im.crop((1320, 1000, 1395, 1060)).convert("RGB")
            px = list(crop.getdata())
            gold = sum(1 for (r, g, b) in px if r >= 180 and g >= 140 and b <= 100)
            return gold / len(px) > 0.05
    except Exception:
        return False


def capture_age_up(age: int, name: str) -> bool:
    if over_cap():
        log(f"  WALL CAP hit before age {age}")
        return False
    log(f"--- Age {age}: {name} ---")
    cheat("this is too hard"); cheat("this is too hard"); time.sleep(1.0)
    for a in range(5):
        key(VK_H, 1.5)
        if probe_age_up_ready():
            break
        time.sleep(8.0)
    else:
        log(f"  age-up never active for age {age}")
        return False
    click(*AGE_UP_BTN, 2.0)
    snap(name)
    click(*POLITICIAN_1, 0.6)
    click(*ACCEPT_BTN, 2.0)
    time.sleep(25.0)
    return True


def drive_into_hubtest_british() -> bool:
    """Fast path: Skirmish -> P1=British -> anwHubTest map -> Play."""
    log("Step A: Skirmish")
    click(*SKIRMISH, 3.5)
    snap("_A_skirmish.png", TMP)
    if not alive():
        log("ABORT: crash after Skirmish")
        return False

    log("Step B: P1 = ANWBritish (picker idx 3)")
    click(*P1_CIV_FLAG, 2.5)
    snap("_B_picker.png", TMP)
    keys(VK_UP, 60, 0.03); time.sleep(0.5)
    keys(VK_DOWN, 3, 0.06); time.sleep(0.5)
    snap("_B_picker_at3.png", TMP)
    click(*PICKER_OK, 2.5)

    log("Step C: anwHubTest map (fast-path)")
    click(*MAP_BTN, 2.5)
    click(150, 304, 0.4)            # focus grid
    key(VK_END, 1.0)
    snap("_C_mapend.png", TMP)
    click(*HUBTEST_TILE, 0.25); click(*HUBTEST_TILE, 2.5)
    snap("01_lobby.png")           # canonical lobby capture
    if not alive():
        log("ABORT: crash after map select")
        return False

    log("Step D: Play")
    click(*PLAY_BTN, 3.0)
    snap("02_loading.png")
    return wait_for_ingame(timeout=240.0)


def summarize(note: str = "") -> int:
    log("=== CAPTURE SUMMARY ===")
    surfaces = [
        "01_lobby.png", "02_loading.png", "03_hud.png", "09_hero_selected.png",
        "07_scoreboard.png", "06_diplomacy.png", "05_homecity_panel.png",
        "05_tech_tree.png", "08_esc_menu.png", "08_ageup_age2.png",
        "08_ageup_age3.png", "08_ageup_age4.png", "08_ageup_age5.png",
        "09_endgame.png",
    ]
    ok = 0
    for s in surfaces:
        p = OUT / s
        if p.exists() and p.stat().st_size > 0:
            log(f"  OK   ({p.stat().st_size:>10,}B) {s}"); ok += 1
        else:
            log(f"  MISS                     {s}")
    log(f"Total: {ok}/{len(surfaces)} surfaces")
    if note:
        log(f"NOTE: {note}")
    return 0


def main() -> int:
    connect()
    resign_if_in_match()
    if over_cap():
        return summarize("wall cap during preflight")

    if not drive_into_hubtest_british():
        snap("_load_failure.png", TMP)
        return summarize("FAILED to reach in-game on anwHubTest (known engine "
                         "bug: anwHubTest may fail mode6->mode27 on session reuse)")

    log("In-game. Settle 10s."); time.sleep(10.0)
    if not alive():
        return summarize("crash right after load")
    snap("03_hud.png")
    click(*SPEED_BAR_MAX, 0.5)

    log("Hero/Explorer")
    key(VK_ESCAPE, 0.5)
    for ex, ey in [(920, 430), (880, 450), (960, 450), (840, 420)]:
        click(ex, ey, 0.8)
    snap("09_hero_selected.png")

    log("Scoreboard")
    key(VK_ESCAPE, 0.3); key(VK_TAB, 1.5); snap("07_scoreboard.png"); key(VK_TAB, 0.5)

    log("Diplomacy")
    click(*DIPLOMACY_BTN, 2.0); snap("06_diplomacy.png"); key(VK_ESCAPE, 0.8)

    log("Home City")
    key(VK_J, 2.5); snap("05_homecity_panel.png"); key(VK_ESCAPE, 0.8)

    log("ESC menu + Tech Tree")
    click(*GEARS_BTN, 1.5); snap("08_esc_menu.png")
    click(*ESC_TECH_TREE, 3.0); snap("05_tech_tree.png"); key(VK_ESCAPE, 1.0); time.sleep(0.5)

    log("Age-up II..V")
    cheat("this is too hard"); cheat("this is too hard"); time.sleep(1.0)
    for a in range(5):
        key(VK_H, 1.5)
        if probe_age_up_ready():
            break
        time.sleep(8.0)
    click(*AGE_UP_BTN, 2.0); snap("08_ageup_age2.png")
    click(*POLITICIAN_1, 0.6); click(*ACCEPT_BTN, 2.0); time.sleep(25.0)

    if alive() and not over_cap():
        capture_age_up(3, "08_ageup_age3.png")
    if alive() and not over_cap():
        capture_age_up(4, "08_ageup_age4.png")
    if alive() and not over_cap():
        capture_age_up(5, "08_ageup_age5.png")

    log("Resign / endgame")
    if alive():
        click(*GEARS_BTN, 1.5)
        click(*ESC_RESIGN_HERE, 1.5)
        click(*RESIGN_YES, 3.0); time.sleep(2.0)
        snap("09_endgame.png")
        click(1145, 737, 3.0)
        click(50, 20, 3.0)

    return summarize()


if __name__ == "__main__":
    raise SystemExit(main())
