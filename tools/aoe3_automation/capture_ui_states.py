#!/usr/bin/env python3
"""One-shot script: capture reference screenshots for each UI state and
validate against detect_screen_state().

Run from repo root:
    python3 tools/aoe3_automation/capture_ui_states.py

Outputs:
    artifacts/validation/ui_states/<state>.png
    artifacts/validation/ui_states/_classifier_report.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Repo root on path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.aoe3_harness.harness_client import HarnessClient
from tools.aoe3_harness.vk import (
    VK_ESCAPE, VK_TAB, VK_F6, VK_F7,
)
from tools.aoe3_automation.in_game_driver import (
    GameDriver, set_harness_backend, _key, _click,
    GEARS_BTN, ESC_MENU_X, ESC_TECH_TREE, ESC_RESIGN, RESIGN_YES,
    VIEW_MAP, VIEW_POSTGAME, DIPLOMACY_BTN,
    HUD_PROBE_XY, HUD_THRESHOLD,
)
from tools.aoe3_automation.lobby_driver import (
    set_harness_backend as ldr_set_harness_backend,
    screenshot as ldr_screenshot,
)
from tools.aoe3_automation.screen_state import (
    detect_screen_state,
    ESC_MENU_PROBE_XY,
    ESC_MENU_PROBE_THRESHOLD,
)

SOCKET = "/tmp/AOE3DEHarness.sock"
OUT_DIR = REPO_ROOT / "artifacts" / "validation" / "ui_states"
OUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT: list[dict] = []
CLIENT: HarnessClient | None = None


def hkey(vk: int, delay: float = 0.5) -> None:
    """Send a key via harness VK code (not xdotool). Never raises."""
    if CLIENT is not None:
        try:
            CLIENT.key(vk)
        except Exception as e:
            print(f"  [hkey] harness key 0x{vk:02x} failed: {e}")
    time.sleep(delay)


def snap(label: str) -> Path:
    """Take a screenshot via harness and save to OUT_DIR/<label>.png."""
    p = OUT_DIR / f"{label}.png"
    ldr_screenshot(p)
    return p


def probe_pixels(p: Path) -> tuple[int, int]:
    """Return (hud_sum, esc_sum) pixel sums from a screenshot."""
    try:
        from PIL import Image
        img = Image.open(p)
        hud_px = img.getpixel(HUD_PROBE_XY)
        esc_px = img.getpixel(ESC_MENU_PROBE_XY)
        img.close()
        return sum(hud_px[:3]), sum(esc_px[:3])
    except Exception:
        return 0, 0


def record(state_label: str, png_path: Path | None, expected: str, note: str = "") -> str:
    """Classify png_path, record result, return classifier result."""
    if png_path is None or not png_path.exists():
        REPORT.append({
            "captured": False,
            "png": None,
            "classifier_returned": "N/A",
            "expected": expected,
            "match": False,
            "note": note or "screenshot failed",
        })
        print(f"  [{state_label}] SKIPPED (no PNG)")
        return "N/A"
    result = detect_screen_state(str(png_path))
    hud, esc = probe_pixels(png_path)
    matched = result == expected
    REPORT.append({
        "captured": True,
        "png": str(png_path),
        "classifier_returned": result,
        "expected": expected,
        "match": matched,
        "note": note,
        "pixel_debug": {"hud_sum": hud, "esc_sum": esc},
    })
    status = "OK" if matched else "MISMATCH"
    print(f"  [{state_label}] classifier={result!r} expected={expected!r} → {status}"
          f"  [hud={hud} esc={esc}]"
          + (f"  NOTE: {note}" if note else ""))
    return result


def wait_for_state(expected: str, max_wait: float = 5.0, label: str = "") -> bool:
    """Poll until detect_screen_state() == expected or timeout. Returns True on success."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        p = snap(f"_probe_{label or expected}")
        s = detect_screen_state(str(p))
        if s == expected:
            return True
        time.sleep(0.5)
    return False


def main() -> None:
    global CLIENT
    print("=== AoE3 UI State Capture + Classifier Validation ===")
    print(f"Socket: {SOCKET}")
    print(f"Output: {OUT_DIR}")
    print(f"ESC_MENU_PROBE_XY={ESC_MENU_PROBE_XY} threshold={ESC_MENU_PROBE_THRESHOLD}")

    # --- connect harness -------------------------------------------------------
    CLIENT = HarnessClient(SOCKET, timeout=15.0)
    try:
        CLIENT.connect(timeout=10.0)
        print("[harness] connected OK")
    except Exception as exc:
        print(f"[harness] FAILED to connect: {exc}")
        CLIENT = None

    if CLIENT is not None:
        set_harness_backend(CLIENT)
        ldr_set_harness_backend(CLIENT)

    driver = GameDriver(art_dir="/tmp/aoe3_capture_run")

    # =========================================================================
    # STEP 1: Game is PAUSED. Capture pause_menu.
    # =========================================================================
    print("\n[1] Capturing pause_menu (game starts paused)...")
    time.sleep(1.0)
    png = snap("pause_menu")
    record("pause_menu", png, "pause_menu")

    # =========================================================================
    # STEP 2: Close pause menu (click GEARS_BTN as toggle)
    # Per doc: GEARS_BTN at (1860, 30) opens/closes the ESC menu.
    # ESC key is unreliable in this build; use click.
    # =========================================================================
    print("\n[2] Dismissing pause menu via GEARS_BTN click...")
    _click(*GEARS_BTN)
    time.sleep(2.0)

    # Verify state changed
    probe_p = snap("_probe_after_gears")
    state_probe = detect_screen_state(str(probe_p))
    print(f"   After GEARS_BTN: state={state_probe!r}")

    if state_probe == "pause_menu":
        # GEARS_BTN didn't toggle, try ESC via harness VK
        print("   Still pause_menu, trying ESC via harness VK...")
        hkey(VK_ESCAPE, delay=2.0)
        probe_p = snap("_probe_esc")
        state_probe = detect_screen_state(str(probe_p))
        print(f"   After harness ESC: state={state_probe!r}")

    if state_probe == "pause_menu":
        # Game may be F7-paused AND menu is open. Try F7 to toggle F7-pause.
        print("   Still pause_menu, sending F7 (toggle game pause)...")
        hkey(VK_F7, delay=2.0)
        probe_p = snap("_probe_f7")
        state_probe = detect_screen_state(str(probe_p))
        print(f"   After F7: state={state_probe!r}")

    png = snap("in_game")
    record("in_game", png, "in_game")

    # =========================================================================
    # STEP 3: Open pause (GEARS_BTN) → Technology Tree
    # =========================================================================
    print("\n[3] Opening pause menu (GEARS_BTN) → tech_tree...")
    _click(*GEARS_BTN)
    time.sleep(2.0)
    # Confirm pause menu is open
    probe_p = snap("_probe_esc_open")
    state_probe = detect_screen_state(str(probe_p))
    print(f"   After GEARS_BTN for ESC menu: state={state_probe!r}")

    # Click TECHNOLOGY TREE button: (ESC_MENU_X, 140)
    print(f"   Clicking Technology Tree at ({ESC_MENU_X}, 140)...")
    _click(ESC_MENU_X, 140)
    time.sleep(3.0)
    png = snap("tech_tree")
    record("tech_tree", png, "tech_tree")

    # Close tech tree - click somewhere outside or back button
    # Tech tree has a close/back button. Per doc, ESC works.
    print("   Closing tech tree (harness ESC)...")
    hkey(VK_ESCAPE, delay=2.0)
    # May land back in pause menu; ESC again to exit
    probe_p = snap("_probe_after_tt_close")
    state_probe = detect_screen_state(str(probe_p))
    print(f"   After closing tech tree: state={state_probe!r}")
    if state_probe == "pause_menu":
        hkey(VK_ESCAPE, delay=2.0)
        probe_p = snap("_probe_after_esc2")
        state_probe = detect_screen_state(str(probe_p))
        print(f"   After 2nd ESC: state={state_probe!r}")

    # =========================================================================
    # STEP 4: Press Tab → scoreboard overlay (expected: in_game)
    # =========================================================================
    print("\n[4] Scoreboard (Tab key via harness)...")
    hkey(VK_TAB, delay=1.5)
    png = snap("scoreboard")
    record("scoreboard", png, "in_game",
           note="scoreboard is overlay; classifier returning 'in_game' is correct")
    # Release Tab (toggle off)
    hkey(VK_TAB, delay=1.0)

    # =========================================================================
    # STEP 5: Press F6 → diplomacy / player summary
    # =========================================================================
    print("\n[5] Diplomacy (F6 via harness)...")
    hkey(VK_F6, delay=2.0)
    png = snap("diplomacy")
    record("diplomacy", png, "diplomacy")
    # Close via harness ESC
    hkey(VK_ESCAPE, delay=1.5)

    # =========================================================================
    # STEP 6: Resign the match
    # =========================================================================
    print("\n[6] Resigning match...")
    # Open the gear/ESC menu
    _click(*GEARS_BTN)
    time.sleep(2.0)
    probe_p = snap("_probe_pre_resign")
    state_probe = detect_screen_state(str(probe_p))
    print(f"   Pre-resign state: {state_probe!r}")

    # Click RESIGN button at (ESC_MENU_X, 365)
    _click(*ESC_RESIGN)
    time.sleep(1.5)
    # Confirm YES at (760, 605)
    _click(*RESIGN_YES)
    time.sleep(1.0)
    # Click YES again (game may show a second dialog)
    _click(*RESIGN_YES)
    time.sleep(3.5)

    # Capture defeat/abandon screen
    print("   Capturing post_game (defeat/abandon screen)...")
    png = snap("post_game")
    record("post_game", png, "post_game")

    # =========================================================================
    # STEP 6b: Navigate out of post-game to main menu
    # =========================================================================
    print("   Navigating to main menu from post-game...")
    # "YOU ABANDON YOUR TOWN" screen: click VIEW MAP (810, 737)
    _click(*VIEW_MAP)
    time.sleep(2.5)
    # From right-side post-defeat menu: QUIT at (1840, 92) → main menu
    _click(1840, 92)
    time.sleep(4.0)

    # =========================================================================
    # STEP 7: Verify we're at main menu
    # =========================================================================
    print("\n[7] Capturing main_menu...")
    time.sleep(1.5)
    png = snap("main_menu")
    record("main_menu", png, "main_menu")

    # =========================================================================
    # STEP 8: Navigate to Skirmish setup
    # =========================================================================
    print("\n[8] Navigating to skirmish_setup (double-click Skirmish)...")
    # Skirmish button: x=80, y=490
    _click(80, 490)
    time.sleep(0.3)
    _click(80, 490)
    time.sleep(3.5)
    png = snap("skirmish_setup")
    record("skirmish_setup", png, "skirmish_setup")

    # =========================================================================
    # STEP 9: Open civ picker
    # =========================================================================
    print("\n[9] Opening civ_picker (click P1 civ flag)...")
    # P1 civ flag at (585, 176)
    _click(585, 176)
    time.sleep(2.5)
    png = snap("civ_picker")
    record("civ_picker", png, "skirmish_setup",
           note="civ_picker overlays lobby; classifier may return 'skirmish_setup'")
    # Cancel picker (ESC via harness)
    print("   Cancelling civ picker (harness ESC)...")
    hkey(VK_ESCAPE, delay=1.5)

    # =========================================================================
    # STEP 10: States not captured this run
    # =========================================================================
    print("\n[10] States NOT captured this run:")
    for label in ("home_city", "age_up_dialog", "loading"):
        REPORT.append({
            "captured": False,
            "png": None,
            "classifier_returned": "N/A",
            "expected": label,
            "match": False,
            "note": "not captured this run — requires additional game state setup",
        })
        print(f"   [{label}] — not captured this run")

    # =========================================================================
    # Return to main menu (leave game clean)
    # =========================================================================
    print("\n[cleanup] Returning to main menu (ESC to exit lobby)...")
    hkey(VK_ESCAPE, delay=2.0)
    final_png = snap("_final_state_check")
    final_state = detect_screen_state(str(final_png))
    hud_f, esc_f = probe_pixels(final_png)
    print(f"[cleanup] Final state: {final_state!r} [hud={hud_f} esc={esc_f}]")

    # =========================================================================
    # Write report
    # =========================================================================
    report_path = OUT_DIR / "_classifier_report.json"
    full_report = {
        "final_game_state": final_state,
        "at_main_menu": final_state == "main_menu",
        "esc_threshold_used": ESC_MENU_PROBE_THRESHOLD,
        "states": REPORT,
    }
    report_path.write_text(json.dumps(full_report, indent=2))
    print(f"\n[report] Written to {report_path}")

    # Summary
    print("\n=== SUMMARY ===")
    mismatches = []
    for r in REPORT:
        if r["captured"] and not r["match"]:
            mismatches.append(r)
    if mismatches:
        print(f"MISMATCHES ({len(mismatches)}):")
        for m in mismatches:
            png_name = Path(m['png']).name if m.get('png') else 'N/A'
            print(f"  {png_name}: expected={m['expected']!r} got={m['classifier_returned']!r}  {m.get('note','')}")
    else:
        print("No mismatches among captured states.")
    print(f"Game left at: {final_state!r}")

    if CLIENT is not None:
        CLIENT.close()


if __name__ == "__main__":
    main()
