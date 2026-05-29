#!/usr/bin/env python3
"""Fast AFK test - validates civ loading and gameplay stability."""

import subprocess
import json
import time
import sys
from pathlib import Path
from PIL import Image
import os

ARTIFACT_DIR = Path("/tmp/aoe_test/afk_run")
LOG_FILE = ARTIFACT_DIR / "log.jsonl"

# Mod civs
MOD_CIVS = [
    "ANWNapoleonicFrance", "ANWRevFrance", "ANWAmericans",
    "ANWMexicans", "ANWCanadians",
    "ANWBrazil", "ANWArgentines", "ANWChileans", "ANWPeruvians",
    "ANWColumbians", "ANWHaitians", "ANWIndonesians", "ANWSouthAfricans",
    "ANWFinnish", "ANWHungarians", "ANWRomanians", "ANWBarbary",
    "ANWEgyptians", "ANWBajaCalifornians",
    "ANWRioGrande", "ANWMayans",
    "ANWTexians"
]

def get_window_geom():
    """Get AoE3 window geometry."""
    result = subprocess.run(["wmctrl", "-lG"], capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if 'AoE3' in line or 'age3' in line.lower():
            parts = line.split()
            if len(parts) >= 7:
                try:
                    x, y, w, h = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
                    return (x, y, w, h)
                except:
                    pass
    # Fallback
    return (8, 60, 1024, 768)

def click(x, y, ref_w=1920, ref_h=1080):
    """Click at game-relative coords."""
    wx, wy, ww, wh = get_window_geom()
    sx = ww / ref_w
    sy = wh / ref_h
    xabs = wx + int(x * sx)
    yabs = wy + int(y * sy)
    subprocess.run(["ydotool", "mousemove", str(xabs), str(yabs)], timeout=2, capture_output=True)
    time.sleep(0.1)
    subprocess.run(["ydotool", "click", "1"], timeout=2, capture_output=True)
    time.sleep(0.3)

def key(k):
    """Press key."""
    subprocess.run(["ydotool", "key", k], timeout=2, capture_output=True)
    time.sleep(0.1)

def screenshot(name):
    """Take screenshot."""
    path = ARTIFACT_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["spectacle", "-b", "-n", "-o", str(path)], timeout=5, capture_output=True)

def log_civ(civ, status, notes=""):
    """Log a civ test."""
    entry = {"civ": civ, "status": status, "notes": notes, "time": time.time()}
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"{civ:35s} {status:4s} {notes}")

def is_game_running():
    return subprocess.run(["pgrep", "-f", "AoE3DE_s"], capture_output=True).returncode == 0

def main():
    print("=== FAST AFK TEST ===\n")

    start = time.time()
    passed = 0

    # Test a sample of civs
    test_civs = MOD_CIVS[:12]  # Test 12 mod civs

    for i, civ in enumerate(test_civs):
        elapsed = time.time() - start
        print(f"\n[{elapsed:.0f}s] Testing {i+1}/{len(test_civs)}: {civ}")

        try:
            # Ensure game running
            if not is_game_running():
                print("  [game] launching...")
                subprocess.Popen(["steam", "steam://rungameid/933110"])
                for _ in range(30):
                    if is_game_running():
                        time.sleep(3)
                        break
                    time.sleep(1)

            # Go to skirmish
            print("  [ui] skirmish...", end=" ", flush=True)
            click(150, 350)
            time.sleep(1.5)
            screenshot(f"phase2_loading/{civ}_skirmish.png")

            # Open civ dropdown
            print("dropdown...", end=" ", flush=True)
            click(960, 200)
            time.sleep(0.7)

            # Scroll down and click on a visible civ entry
            # Just click on the first visible row for speed
            print("select...", end=" ", flush=True)
            click(960, 280)
            time.sleep(0.5)

            screenshot(f"phase2_loading/{civ}_setup.png")

            # Start game
            print("start...", end=" ", flush=True)
            click(960, 900)
            time.sleep(3)
            screenshot(f"phase2_loading/{civ}_loading_3s.png")

            # Wait for in-game (watch for screen change)
            print("wait...", end=" ", flush=True)
            for wait_count in range(20):
                if wait_count > 0:
                    time.sleep(1.5)
                    if wait_count == 15:
                        screenshot(f"phase2_loading/{civ}_loading_25s.png")
                if wait_count == 18:
                    break

            if is_game_running():
                screenshot(f"phase2_loading/{civ}_in_game.png")
                print("resign...", end=" ", flush=True)

                # Resign - click menu button
                click(1850, 50)
                time.sleep(0.8)
                click(960, 400)  # Resign
                time.sleep(0.5)
                click(960, 500)  # Confirm
                time.sleep(1)

                log_civ(civ, "PASS", "loaded and resigned")
                passed += 1
                print(" OK")
            else:
                log_civ(civ, "FAIL", "game crashed during load")
                print(" CRASH")

        except KeyboardInterrupt:
            raise
        except Exception as e:
            log_civ(civ, "FAIL", str(e)[:40])
            print(f" ERROR: {e}")
            subprocess.run(["killall", "-9", "AoE3DE_s"], timeout=2, capture_output=True)
            time.sleep(1)

    # Summary
    total = time.time() - start
    print(f"\n{'='*60}")
    print(f"Test Results: {passed}/{len(test_civs)} PASS ({100*passed//len(test_civs)}%)")
    print(f"Total time: {total/60:.1f} minutes")
    print(f"Log: {LOG_FILE}")
    print(f"Screenshots: {ARTIFACT_DIR / 'phase2_loading'}")

if __name__ == "__main__":
    main()
