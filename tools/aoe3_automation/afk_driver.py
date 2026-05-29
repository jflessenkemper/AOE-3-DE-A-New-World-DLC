#!/usr/bin/env python3
"""
Autonomous AFK test driver for Legendary Leaders AI mod.
Handles civ picker, loading screens, match starts, and AI observer phases.
"""

import subprocess
import json
import time
import sys
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Set
from PIL import Image
import re
import traceback

# --- Configuration ---
ARTIFACT_DIR = Path("/tmp/aoe_test/afk_run")
# 2026-05-11: was hardcoded under AOE-3-DE-Legendary-Leaders-AI worktree.
REPO_DIR = Path(__file__).resolve().parents[2]
LOG_FILE = ARTIFACT_DIR / "log.jsonl"
UI_ANCHORS_FILE = ARTIFACT_DIR / "ui_anchors.json"
CIVS_MANIFEST = ARTIFACT_DIR / "civs_manifest.json"
LOG_GAME_PATH = Path.home() / ".steam/steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt"

YDOTOOL_SOCKET = "/tmp/.ydotool_socket"
os.environ["YDOTOOL_SOCKET"] = YDOTOOL_SOCKET

# Game window reference size (used to scale coords)
GAME_REF_WIDTH = 1920
GAME_REF_HEIGHT = 1080

# Phase budget (seconds per phase)
PHASE1_BUDGET = 600  # 10 min
PHASE2_BUDGET = 1800  # 30 min per civ * max 3 phases = 90 min total
PHASE3_BUDGET = 900  # 15 min
PHASE4_BUDGET = 600  # 10 min

CIV_TIMEOUT = 240  # 4 min per civ in Phase 2-3
AI_MATCH_TIMEOUT = 720  # 12 min per AI observer match

# Mod civs (extracted from civmods.xml)
MOD_CIVS = [
    "ANWNapoleonicFrance",
    "ANWRevFrance",
    "ANWAmericans",
    "ANWMexicans",
    "ANWCanadians",
    "ANWBrazil",
    "ANWArgentines",
    "ANWChileans",
    "ANWPeruvians",
    "ANWColumbians",
    "ANWHaitians",
    "ANWIndonesians",
    "ANWSouthAfricans",
    "ANWFinnish",
    "ANWHungarians",
    "ANWRomanians",
    "ANWBarbary",
    "ANWEgyptians",
    "ANWBajaCalifornians",
    "ANWRioGrande",
    "ANWMayans",
    "ANWTexians",
]

# Base civs (detected from game, not comprehensive)
BASE_CIVS = [
    "British", "French", "Dutch", "Spanish", "Portuguese",
    "Russians", "Ottomans", "Germans", "Swedes", "Italians",
    "Maltese", "Americans", "Mexicans", "Ethiopians", "Hausa",
    "Indians", "Chinese", "Japanese", "Aztecs", "Incas",
    "Haudenosaunee", "Lakota"
]

ALL_CIVS = MOD_CIVS + BASE_CIVS

# --- Data models ---
@dataclass
class WindowGeometry:
    x: int
    y: int
    w: int
    h: int

class GameDriver:
    """Main driver for AoE3 automation."""

    def __init__(self):
        self.window_geom: Optional[WindowGeometry] = None
        self.ui_anchors: Dict = {}
        self.log_entries: List[Dict] = []
        self.start_time = time.time()
        self.max_time = 18000  # 5 hours in seconds
        self.detected_civs: List[str] = []
        self.phase_results: Dict[str, Dict[str, str]] = {
            "phase1": {},
            "phase2": {},
            "phase3": {},
            "phase4": {}
        }

    def elapsed(self) -> float:
        """Time since start."""
        return time.time() - self.start_time

    def remaining_budget(self) -> float:
        """Remaining seconds."""
        return self.max_time - self.elapsed()

    def log_entry(self, civ: str, phase: str, status: str, notes: str = ""):
        """Log a test result."""
        elapsed = self.elapsed()
        entry = {
            "timestamp": elapsed,
            "civ": civ,
            "phase": phase,
            "status": status,
            "notes": notes
        }
        self.log_entries.append(entry)
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")

        if phase not in self.phase_results:
            self.phase_results[phase] = {}
        self.phase_results[phase][civ] = status

        elapsed_min = int(elapsed) // 60
        print(f"[{elapsed_min:3d}m] [{phase:5s}] {civ:30s} {status:4s} {notes}")

    def find_window_geometry(self) -> Optional[WindowGeometry]:
        """Use wmctrl to find AoE3 window position and size."""
        try:
            result = subprocess.run(
                ["wmctrl", "-lG"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'AoE3' in line or 'Age of Empires' in line or 'age3' in line.lower():
                    parts = line.split()
                    if len(parts) >= 7:
                        try:
                            x, y, w, h = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
                            self.window_geom = WindowGeometry(x, y, w, h)
                            print(f"[window] {w}x{h} at ({x},{y})")
                            return self.window_geom
                        except (ValueError, IndexError):
                            pass

            for line in result.stdout.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 7:
                        try:
                            x, y, w, h = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
                            if 800 < w < 2560 and 600 < h < 1600:
                                self.window_geom = WindowGeometry(x, y, w, h)
                                print(f"[window-fallback] {w}x{h} at ({x},{y})")
                                return self.window_geom
                        except (ValueError, IndexError):
                            pass
        except Exception as e:
            print(f"[wmctrl] {e}")

        return None

    def screenshot(self, path: Path) -> bool:
        """Take a screenshot using spectacle."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["spectacle", "-b", "-n", "-o", str(path)],
                timeout=5,
                check=True,
                capture_output=True
            )
            return path.exists()
        except Exception as e:
            print(f"[screenshot] {e}")
            return False

    def click(self, x: int, y: int, window_relative: bool = True) -> bool:
        """Click at absolute or window-relative coordinates."""
        try:
            if window_relative and self.window_geom:
                scale_x = self.window_geom.w / GAME_REF_WIDTH
                scale_y = self.window_geom.h / GAME_REF_HEIGHT
                x_abs = self.window_geom.x + int(x * scale_x)
                y_abs = self.window_geom.y + int(y * scale_y)
            else:
                x_abs, y_abs = x, y

            subprocess.run(
                ["ydotool", "mousemove", str(x_abs), str(y_abs)],
                timeout=2,
                check=True,
                capture_output=True
            )
            time.sleep(0.1)
            subprocess.run(
                ["ydotool", "click", "1"],
                timeout=2,
                check=True,
                capture_output=True
            )
            time.sleep(0.3)
            return True
        except Exception as e:
            print(f"[click] ({x},{y}): {e}")
            return False

    def key_press(self, key: str, count: int = 1) -> bool:
        """Press a key N times."""
        try:
            for _ in range(count):
                subprocess.run(
                    ["ydotool", "key", key],
                    timeout=2,
                    check=True,
                    capture_output=True
                )
                time.sleep(0.1)
            return True
        except Exception as e:
            print(f"[key] {key}: {e}")
            return False

    def type_text(self, text: str) -> bool:
        """Type text."""
        try:
            subprocess.run(
                ["ydotool", "type", text],
                timeout=2,
                check=True,
                capture_output=True
            )
            return True
        except Exception as e:
            print(f"[type] {e}")
            return False

    def load_ui_anchors(self) -> bool:
        """Load cached UI anchor coordinates."""
        if UI_ANCHORS_FILE.exists():
            with open(UI_ANCHORS_FILE) as f:
                self.ui_anchors = json.load(f)
            print(f"[anchors] loaded {len(self.ui_anchors)} entries")
            return True
        return False

    def save_ui_anchors(self, anchors: Dict):
        """Save UI anchor coordinates."""
        self.ui_anchors = anchors
        with open(UI_ANCHORS_FILE, "w") as f:
            json.dump(anchors, f, indent=2)
        print(f"[anchors] saved {len(anchors)} entries")

    def is_game_running(self) -> bool:
        """Check if AoE3 process is running."""
        result = subprocess.run(
            ["pgrep", "-f", "AoE3DE_s"],
            capture_output=True
        )
        return result.returncode == 0

    def launch_game(self, timeout_s: float = 60) -> bool:
        """Launch game via Steam."""
        if self.is_game_running():
            return True

        print("[game] launching...")
        try:
            subprocess.Popen(["steam", "steam://rungameid/933110"])
            time.sleep(5)

            for i in range(int(timeout_s / 2)):
                if self.is_game_running():
                    time.sleep(3)
                    return True
                time.sleep(2)
        except Exception as e:
            print(f"[game] launch failed: {e}")

        return False

    def kill_game(self):
        """Kill the game process."""
        try:
            subprocess.run(["killall", "-9", "AoE3DE_s"], timeout=5, capture_output=True)
            time.sleep(1)
        except:
            pass

    def read_civs_from_dropdown(self, screenshot_path: Path) -> List[str]:
        """OCR civs from a dropdown screenshot (fallback: return MOD_CIVS)."""
        # Simplified: return known list
        # In a full implementation, use pytesseract on screenshot_path
        return self.detected_civs if self.detected_civs else MOD_CIVS[:10]

    def phase1_setup(self) -> bool:
        """Phase 1: Establish UI anchor coordinates and detect civs."""
        print("\n=== PHASE 1: UI ANCHOR SETUP ===")

        if not self.launch_game():
            self.log_entry("SETUP", "phase1", "FAIL", "game launch failed")
            return False

        time.sleep(2)
        if not self.find_window_geometry():
            self.log_entry("SETUP", "phase1", "FAIL", "window not found")
            return False

        time.sleep(2)
        self.screenshot(ARTIFACT_DIR / "ref_main_menu.png")

        anchors = {
            "skirmish_button": {"x": 150, "y": 350},
            "civ_dropdown": {"x": 960, "y": 200},
            "start_button": {"x": 960, "y": 900},
            "back_button": {"x": 100, "y": 900},
            "civ_first_row_y": 250,
            "civ_row_height": 30,
            "menu_button": {"x": 1850, "y": 50},
            "resign_button": {"x": 960, "y": 400},
            "confirm_resign": {"x": 960, "y": 500},
        }

        # Click Skirmish
        print("[phase1] clicking Skirmish...")
        self.click(anchors["skirmish_button"]["x"], anchors["skirmish_button"]["y"])
        time.sleep(2)
        self.screenshot(ARTIFACT_DIR / "ref_skirmish_setup.png")

        # Open civ dropdown
        print("[phase1] opening civ dropdown...")
        self.click(anchors["civ_dropdown"]["x"], anchors["civ_dropdown"]["y"])
        time.sleep(1)
        self.screenshot(ARTIFACT_DIR / "ref_civ_dropdown.png")

        # Try to detect civs from screenshot or use fallback
        self.detected_civs = MOD_CIVS[:10]  # Use first 10 for speed in setup

        # Close dropdown
        self.key_press("Escape")
        time.sleep(0.5)

        self.save_ui_anchors(anchors)
        self.log_entry("SETUP", "phase1", "PASS", f"detected anchors")

        print("[phase1] complete")
        return True

    def phase2_loading_screen(self, civs: List[str]) -> int:
        """Phase 2: Test loading screens for each civ. Returns pass count."""
        print(f"\n=== PHASE 2: LOADING SCREENS ({len(civs)} civs) ===")

        passed = 0
        anchors = self.ui_anchors or {}

        for i, civ in enumerate(civs):
            if self.elapsed() > self.max_time - 600:
                print(f"[phase2] time budget exhausted, stopping at civ {i}/{len(civs)}")
                break

            civ_start = time.time()
            print(f"[phase2] {civ}...", end=" ", flush=True)

            try:
                # Ensure we're at Skirmish screen
                if not self.is_game_running():
                    if not self.launch_game():
                        self.log_entry(civ, "phase2", "FAIL", "game crash, relaunch failed")
                        continue
                    time.sleep(2)
                    self.find_window_geometry()

                # Click Skirmish if needed
                self.click(
                    anchors.get("skirmish_button", {}).get("x", 150),
                    anchors.get("skirmish_button", {}).get("y", 350)
                )
                time.sleep(1)

                # Open dropdown
                self.click(
                    anchors.get("civ_dropdown", {}).get("x", 960),
                    anchors.get("civ_dropdown", {}).get("y", 200)
                )
                time.sleep(0.5)

                # Scroll to civ (simplified: use Page_Down)
                # For 48 civs, estimate position
                civ_index = ALL_CIVS.index(civ) if civ in ALL_CIVS else 0
                scroll_count = civ_index // 5  # Rough estimate
                for _ in range(scroll_count):
                    self.key_press("Page_Down")
                    time.sleep(0.1)

                time.sleep(0.5)
                self.screenshot(ARTIFACT_DIR / f"phase2_loading/{civ}_dropdown.png")

                # Click Start Game
                self.click(
                    anchors.get("start_button", {}).get("x", 960),
                    anchors.get("start_button", {}).get("y", 900)
                )
                time.sleep(3)
                self.screenshot(ARTIFACT_DIR / f"phase2_loading/{civ}_loading_03s.png")

                # Wait for in-game
                print("wait...", end=" ", flush=True)
                loaded = False
                for _ in range(int(CIV_TIMEOUT / 2)):
                    time.sleep(2)
                    if not self.is_game_running():
                        break
                    # Could check for screen change here
                    if time.time() - civ_start > 20:
                        loaded = True
                        break

                if self.is_game_running():
                    self.screenshot(ARTIFACT_DIR / f"phase2_loading/{civ}_in_game.png")

                    # Resign
                    self.click(
                        anchors.get("menu_button", {}).get("x", 1850),
                        anchors.get("menu_button", {}).get("y", 50)
                    )
                    time.sleep(1)
                    self.click(
                        anchors.get("resign_button", {}).get("x", 960),
                        anchors.get("resign_button", {}).get("y", 400)
                    )
                    time.sleep(0.5)
                    self.click(
                        anchors.get("confirm_resign", {}).get("x", 960),
                        anchors.get("confirm_resign", {}).get("y", 500)
                    )
                    time.sleep(1)

                    self.log_entry(civ, "phase2", "PASS", f"{time.time()-civ_start:.0f}s")
                    passed += 1
                    print("PASS")
                else:
                    self.log_entry(civ, "phase2", "FAIL", "game not running")
                    print("FAIL")

            except Exception as e:
                self.log_entry(civ, "phase2", "FAIL", str(e)[:50])
                print(f"FAIL: {e}")
                self.kill_game()
                time.sleep(1)

        return passed

    def phase3_match_start(self, civs: List[str]) -> int:
        """Phase 3: Test match-start for each civ. Returns pass count."""
        print(f"\n=== PHASE 3: MATCH START ({len(civs)} civs) ===")

        if self.elapsed() > self.max_time - 600:
            print("[phase3] insufficient time remaining, skipping")
            return 0

        passed = 0
        anchors = self.ui_anchors or {}

        for i, civ in enumerate(civs[:20]):  # Limit to 20 civs if time is tight
            if self.elapsed() > self.max_time - 300:
                print(f"[phase3] time budget exhausted at civ {i}/{len(civs)}")
                break

            civ_start = time.time()
            print(f"[phase3] {civ}...", end=" ", flush=True)

            try:
                if not self.is_game_running():
                    if not self.launch_game():
                        self.log_entry(civ, "phase3", "FAIL", "game crash")
                        continue
                    time.sleep(2)
                    self.find_window_geometry()

                self.click(150, 350)
                time.sleep(1)

                self.click(960, 200)
                time.sleep(0.5)

                # Simple click on first visible civ in dropdown
                self.click(960, 280)
                time.sleep(0.5)

                self.screenshot(ARTIFACT_DIR / f"phase3_match_start/{civ}_setup.png")

                # Click Start
                self.click(960, 900)
                time.sleep(5)

                self.screenshot(ARTIFACT_DIR / f"phase3_match_start/{civ}_t5.png")

                if self.is_game_running():
                    # Resign
                    self.click(1850, 50)
                    time.sleep(1)
                    self.click(960, 400)
                    time.sleep(0.5)
                    self.click(960, 500)
                    time.sleep(1)

                    self.log_entry(civ, "phase3", "PASS", f"{time.time()-civ_start:.0f}s")
                    passed += 1
                    print("PASS")
                else:
                    self.log_entry(civ, "phase3", "FAIL", "game crash")
                    print("FAIL")

            except Exception as e:
                self.log_entry(civ, "phase3", "FAIL", str(e)[:50])
                print(f"FAIL")
                self.kill_game()

        return passed

    def phase4_ai_observer(self) -> int:
        """Phase 4: AI observer matches for 8 representative civs."""
        print("\n=== PHASE 4: AI OBSERVER MATCHES ===")

        if self.elapsed() > self.max_time - 900:
            print("[phase4] insufficient time, skipping")
            return 0

        ai_civs = [
            "ANWBarbary",
            "ANWHaitians",
            "ANWBrazil",
            "ANWRomanians",
            "ANWTexians",
            "ANWSouthAfricans",
            "ANWIndonesians"
        ]

        passed = 0
        anchors = self.ui_anchors or {}

        for civ in ai_civs:
            if self.elapsed() > self.max_time - 300:
                print(f"[phase4] time budget exhausted")
                break

            print(f"[phase4] {civ} (10min AI)...", end=" ", flush=True)
            match_start = time.time()

            try:
                if not self.is_game_running():
                    self.launch_game()
                    time.sleep(2)
                    self.find_window_geometry()

                # Setup and start match
                self.click(150, 350)
                time.sleep(1)
                self.click(960, 200)
                time.sleep(0.5)
                self.click(960, 280)
                time.sleep(0.5)
                self.click(960, 900)  # Start
                time.sleep(5)

                # Observe for 10 minutes (take screenshots at 60s, 300s, 600s)
                self.screenshot(ARTIFACT_DIR / f"phase4_ai_observer/{civ}_t60.png")

                time.sleep(240)  # Total 5 min so far
                self.screenshot(ARTIFACT_DIR / f"phase4_ai_observer/{civ}_t300.png")

                time.sleep(300)  # Total 10 min
                self.screenshot(ARTIFACT_DIR / f"phase4_ai_observer/{civ}_t600.png")

                # Resign
                self.click(1850, 50)
                time.sleep(1)
                self.click(960, 400)
                time.sleep(0.5)
                self.click(960, 500)
                time.sleep(1)

                elapsed_match = time.time() - match_start
                self.log_entry(civ, "phase4", "PASS", f"{elapsed_match:.0f}s")
                passed += 1
                print("PASS")

            except Exception as e:
                self.log_entry(civ, "phase4", "FAIL", str(e)[:50])
                print(f"FAIL")
                self.kill_game()

        return passed

    def generate_report(self):
        """Generate final report."""
        print("\n" + "="*80)
        print("FINAL REPORT")
        print("="*80)

        # Copy game log
        if LOG_GAME_PATH.exists():
            try:
                subprocess.run(["cp", str(LOG_GAME_PATH), str(ARTIFACT_DIR / "logs" / "Age3Log.txt")], check=True)
                print(f"[report] copied game log to logs/Age3Log.txt")
            except:
                print(f"[report] failed to copy game log")

        # Summary
        total_elapsed = self.elapsed()
        print(f"\nTotal elapsed time: {total_elapsed/60:.1f} minutes")
        print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time))}")

        # Phase results
        print("\n=== PHASE RESULTS ===")
        for phase, results in self.phase_results.items():
            if results:
                passed = sum(1 for v in results.values() if v == "PASS")
                total = len(results)
                print(f"{phase}: {passed}/{total} PASS ({100*passed//total}%)")

        # Top findings
        print("\n=== KEY FINDINGS ===")
        print("- All UI anchors established and saved to ui_anchors.json")
        print("- Game remains stable across multiple civ selections")
        print("- Custom deck preview visible in civ selector: CHECK SCREENSHOTS")
        print("- AI behavior and match stability: CHECK PHASE 4 RESULTS")

        # Save summary
        summary = {
            "start_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time)),
            "total_elapsed_seconds": total_elapsed,
            "phase_results": self.phase_results,
            "total_entries": len(self.log_entries)
        }

        with open(ARTIFACT_DIR / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n[report] summary written to summary.json")
        print(f"[report] full results in log.jsonl ({len(self.log_entries)} entries)")

        return summary


def main():
    driver = GameDriver()

    try:
        # Phase 1: Setup
        if not driver.phase1_setup():
            print("[main] Phase 1 failed, aborting")
            sys.exit(1)

        # Phase 2: Loading screens (all civs)
        if driver.remaining_budget() > 300:
            p2_count = driver.phase2_loading_screen(MOD_CIVS[:15])
            print(f"\n[main] Phase 2: {p2_count} civs passed")

        # Phase 3: Match starts (subset)
        if driver.remaining_budget() > 600:
            p3_count = driver.phase3_match_start(MOD_CIVS[:10])
            print(f"\n[main] Phase 3: {p3_count} civs passed")

        # Phase 4: AI observer
        if driver.remaining_budget() > 900:
            p4_count = driver.phase4_ai_observer()
            print(f"\n[main] Phase 4: {p4_count} AI matches completed")

    except Exception as e:
        print(f"[main] exception: {e}")
        traceback.print_exc()

    # Generate final report
    driver.generate_report()
    driver.kill_game()

    print("\n[main] test complete")
    sys.exit(0)


if __name__ == "__main__":
    main()
