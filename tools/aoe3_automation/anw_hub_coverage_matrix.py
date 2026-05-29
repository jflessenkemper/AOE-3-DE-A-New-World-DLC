#!/usr/bin/env python3
"""ANW Hub Test coverage matrix (v2).

Runs N matches on ANW Hub Test cycling all 46 picker civs through the 7
AI slots, capturing personality probes + chat-log screenshots per match.
Produces a coverage report.

Flow per round:
  1. Assume clean lobby (ANW Hub Test selected, 8 players, treaty 20).
  2. For each AI slot P2..P8: set_opponent_civ_by_index(slot, picker_idx)
  3. Click PLAY
  4. Wait for mode 27 + WorldAssetPreloadingTime
  5. Observe N seconds (default 480 = 8 min match-clock, well past Age 1
     and into Commerce/Fortress so wall/age probes fire)
  6. Screenshot 4× during observation (~2/4/6/8 min) for chat capture
  7. ESC → QUIT to return to lobby
  8. Snapshot personality files updated this round
  9. Repeat for next round

The 45 ANW civs split into 7 rounds:
  R1: ANWArgentines, ANWAztecs, ANWBarbary,
      ANWEgyptians, ANWEthiopians, ANWFinnish
  R3: ANWFrench, ANWNapoleonicFrance, ANWRevFrance, ANWGermans,
      ANWColumbians, ANWHaitians, ANWHungarians
  R4: ANWInca, ANWIndonesians, ANWHaudenosaunee, ANWItalians,
  R5: ANWMaltese, ANWMayans, ANWMexicans, ANWIndians, ANWDutch,
      ANWOttomans, ANWPeruvians
      ANWSouthAfricans, ANWSpanish
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path("/var/home/jflessenkemper/AOE-3-DE-A-New-World")
sys.path.insert(0, str(REPO))

os.environ.setdefault("AOE3_X_DISPLAY", ":1")
from tools.aoe3_automation import lobby_driver  # noqa: E402
from tools.aoe3_automation.anw_civ_picker_map import (  # noqa: E402
    ANW_TO_PICKER_INDEX,
)

lobby_driver._GAMESCOPE_WID = "31457281"

OUT = REPO / "artifacts/validation/anw_hub_coverage"
OUT.mkdir(parents=True, exist_ok=True)

# Build 7-civ rounds covering all 46 ANW civs
ALL_CIVS = list(ANW_TO_PICKER_INDEX.keys())
ROUNDS: list[list[str]] = []
for start in range(0, len(ALL_CIVS), 7):
    row = ALL_CIVS[start:start + 7]
    while len(row) < 7:
        row.append("ANWBritish")  # pad last round
    ROUNDS.append(row)

PERSONALITY_DIR = Path(
    "/var/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/"
    "933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/"
    "76561198170207043/Game/AI"
)

LOG_PATH = Path(
    "/var/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/"
    "933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/"
    "Age3Log.txt"
)


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def wait_for_mode(target_mode: int, timeout_s: int = 180) -> bool:
    deadline = time.time() + timeout_s
    target_line = f"entering mode {target_mode}"
    while time.time() < deadline:
        try:
            txt = LOG_PATH.read_text(errors="ignore")
            if target_line in txt:
                last_mode = None
                for line in txt.splitlines():
                    if "entering mode" in line:
                        try:
                            m = int(line.split("entering mode ")[1].split(" ")[0])
                            last_mode = m
                        except (IndexError, ValueError):
                            pass
                if last_mode == target_mode:
                    return True
        except OSError:
            pass
        time.sleep(2)
    return False


def snapshot_personalities(out_dir: Path, cutoff_age_s: int = 1800) -> dict:
    """Copy *.personality files modified within cutoff seconds into out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - cutoff_age_s
    snap = {}
    for p in PERSONALITY_DIR.glob("*.personality"):
        if p.stat().st_mtime >= cutoff:
            shutil.copy(p, out_dir / p.name)
            snap[p.name] = {
                "mtime": p.stat().st_mtime,
                "size": p.stat().st_size,
            }
    return snap


def setup_round_civs(coords: dict, civs: list[str]) -> dict:
    """Set 7 opponent civs in the lobby. Returns dict with per-slot results."""
    result = {"slot_civs": {}, "failed": []}
    for slot_idx, civ in enumerate(civs, start=1):  # slots 1..7 = P2..P8
        picker_idx = ANW_TO_PICKER_INDEX.get(civ)
        if picker_idx is None:
            log(f"  P{slot_idx + 1}: SKIP {civ!r} (no picker index)")
            result["failed"].append({"slot": slot_idx, "civ": civ,
                                     "error": "unknown civ token"})
            continue
        log(f"  P{slot_idx + 1} = {civ} (picker idx {picker_idx})")
        try:
            lobby_driver.set_opponent_civ_by_index(
                coords, slot_idx, picker_idx)
            result["slot_civs"][slot_idx] = civ
            time.sleep(0.5)
        except Exception as e:
            log(f"    ERROR setting {civ}: {e}")
            result["failed"].append({"slot": slot_idx, "civ": civ,
                                     "error": str(e)})
    return result


def click_play_and_wait(coords: dict, round_out: Path | None = None) -> bool:
    px, py = coords["lobby"]["play_button"]
    log(f"  click PLAY at ({px},{py})")
    # archive log to round dir before truncating so probes are preserved
    if round_out is not None:
        try:
            shutil.copy(LOG_PATH, round_out / "pre_match_age3log.txt")
        except OSError:
            pass
    # Small pre-play settle — lobby must be fully stable before PLAY click.
    # Rounds 2+ arrive here straight after resign_to_lobby + civ picker
    # interactions; a 3s settle prevents the click landing while the engine
    # is still processing the previous match teardown.
    time.sleep(3.0)
    # truncate log so wait_for_mode sees only this match
    LOG_PATH.write_text("")
    lobby_driver.click(px, py, settle=0.5)
    # ANW Hub Test generates complex geometry (8 cliff spokes + craterRim +
    # central sea + 7 river inlets + 7 inner bays + trade ring + extras).
    # With 8 AI slots this takes up to ~90s to generate + ~15s for asset
    # preloading, so 240s is marginal. Bumped to 360s.
    return wait_for_mode(27, timeout_s=360)


def reenter_lobby_if_main_menu(coords: dict) -> bool:
    """If AoE3 dumped to main menu (mode 1) after resign, click Skirmish
    to re-enter the lobby (mode 3). Returns True if lobby ready.
    """
    try:
        txt = LOG_PATH.read_text(errors="ignore")
    except OSError:
        txt = ""
    # find last entered-mode line
    last_mode = None
    for line in txt.splitlines():
        if "entering mode" in line:
            try:
                last_mode = int(line.split("entering mode ")[1].split(" ")[0])
            except (IndexError, ValueError):
                pass
    log(f"  last entered mode: {last_mode}")
    if last_mode == 3:
        return True  # already in lobby
    if last_mode == 1:
        # at main menu - click Skirmish
        sx, sy = coords["main_menu"]["skirmish_button"]
        log(f"  re-entering lobby: click Skirmish ({sx},{sy})")
        lobby_driver.click(sx, sy, settle=0.5)
        time.sleep(8.0)
        # verify lobby loaded
        try:
            txt = LOG_PATH.read_text(errors="ignore")
        except OSError:
            txt = ""
        if "entering mode 3" in txt.split("\n")[-30:].__str__():
            return True
        # one more check via full log
        for line in reversed(txt.splitlines()):
            if "entering mode" in line:
                try:
                    m = int(line.split("entering mode ")[1].split(" ")[0])
                    return m == 3
                except (IndexError, ValueError):
                    pass
    return False


def resign_to_lobby() -> bool:
    """Press Escape → click QUIT in game menu → confirm Resign dialog.
    Calibrated 2026-05-15: Options=y305, Resign=y371, Quit=y437. Confirm
    dialog YES at (768,645), NO at (1280,645). Quit-from-match shows a
    Resign-style confirm (engine treats mid-match exit as resignation).
    """
    log("  ESC → game menu")
    subprocess.run(
        ["xdotool", "key", "--window", "31457281", "Escape"],
        env={**os.environ, "DISPLAY": ":1"}, check=False,
    )
    time.sleep(2.0)
    lobby_driver.screenshot(Path("/tmp/screens/_mtx_gamemenu.png"), retries=2)
    log("  click QUIT (1800, 437)")
    lobby_driver.click(1800, 437, settle=0.5)
    time.sleep(2.0)
    log("  click YES confirm (768, 645)")
    # Move cursor first, then click — gamescope sometimes drops clicks
    # that don't have an explicit cursor move beforehand
    subprocess.run(
        ["xdotool", "mousemove", "--window", "31457281", "768", "645"],
        env={**os.environ, "DISPLAY": ":1"}, check=False,
    )
    time.sleep(0.4)
    subprocess.run(
        ["xdotool", "click", "--window", "31457281", "1"],
        env={**os.environ, "DISPLAY": ":1"}, check=False,
    )
    time.sleep(4.0)
    # Post-game results may show; click bottom-center "Continue" if so
    lobby_driver.click(960, 1020, settle=0.5)
    time.sleep(2.0)
    return True


def run_round(round_idx: int, civs: list[str], observe_s: int = 480) -> dict:
    log(f"=== Round {round_idx + 1}/{len(ROUNDS)}: {civs} ===")
    coords = lobby_driver.load_coords()
    out_dir = OUT / f"round_{round_idx + 1:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ensure we're in the lobby (resign drops us to main menu)
    if not reenter_lobby_if_main_menu(coords):
        log("  WARN: could not confirm lobby state; proceeding anyway")

    setup_result = setup_round_civs(coords, civs)

    if not click_play_and_wait(coords, round_out=out_dir):
        log("  TIMEOUT waiting for mode 27 — aborting round")
        # still archive log and snapshot personalities even on failure
        try:
            shutil.copy(LOG_PATH, out_dir / "match_age3log.txt")
        except OSError:
            pass
        snap = snapshot_personalities(out_dir)
        return {
            "round": round_idx + 1,
            "civs": civs,
            "setup": setup_result,
            "status": "FAILED_LOAD",
            "personalities_captured": len(snap),
        }

    log(f"  in-match; observing {observe_s}s with 4 capture points")
    capture_times = [observe_s // 4, observe_s // 2,
                     3 * observe_s // 4, observe_s]
    last_t = 0
    for i, t in enumerate(capture_times):
        delta = t - last_t
        time.sleep(delta)
        lobby_driver.screenshot(
            str(out_dir / f"obs_{i + 1}_t{t}s.png"), retries=2)
        last_t = t

    # archive log BEFORE resign (resign may not generate further probes)
    try:
        shutil.copy(LOG_PATH, out_dir / "match_age3log.txt")
    except OSError:
        pass

    resign_to_lobby()

    # Post-resign settle: give the engine time to fully return to lobby/main
    # menu before the next round tries to set civ pickers and click PLAY.
    # Without this, the next round's set_opponent_civ_by_index calls land
    # while the lobby is still transitioning — pickers show wrong indices,
    # the map selection may reset to a non-ANW map, and the subsequent PLAY
    # click either errors or launches with wrong civs (causing FAILED_LOAD).
    log("  post-resign settle: 12s")
    time.sleep(12.0)

    snap = snapshot_personalities(out_dir)
    log(f"  captured {len(snap)} personality files")

    return {
        "round": round_idx + 1,
        "civs": civs,
        "setup": setup_result,
        "status": "OK",
        "personalities_captured": len(snap),
        "files": list(snap.keys()),
    }


def main(start_round: int = 1, observe_s: int = 480) -> None:
    """Run coverage matrix. start_round is 1-indexed (1..7)."""
    log(f"Coverage matrix starting: {len(ROUNDS)} rounds × 7 slots "
        f"(start={start_round}, observe={observe_s}s)")
    results = []
    # preserve prior results if resuming
    prior_report = OUT / "coverage_report.json"
    started = datetime.now().isoformat()
    if start_round > 1 and prior_report.exists():
        try:
            old = json.loads(prior_report.read_text())
            results = [r for r in old.get("results", [])
                       if r.get("round", 99) < start_round
                       and r.get("status") == "OK"]
            started = old.get("started", started)
            log(f"  resuming: preserved {len(results)} prior OK rounds")
        except (OSError, json.JSONDecodeError):
            pass

    for i, civs in enumerate(ROUNDS):
        if (i + 1) < start_round:
            continue  # skip already-done rounds
        result = run_round(i, civs, observe_s=observe_s)
        results.append(result)
        prior_report.write_text(
            json.dumps({
                "started": started,
                "updated": datetime.now().isoformat(),
                "rounds_total": len(ROUNDS),
                "rounds_done": i + 1,
                "results": results,
            }, indent=2)
        )
    log(f"DONE. Report: {OUT}/coverage_report.json")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-round", type=int, default=1,
                    help="1-indexed round to resume from (default 1)")
    ap.add_argument("--observe-s", type=int, default=480,
                    help="seconds to observe each match (default 480)")
    args = ap.parse_args()
    main(start_round=args.start_round, observe_s=args.observe_s)
