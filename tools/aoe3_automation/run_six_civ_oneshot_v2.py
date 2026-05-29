#!/usr/bin/env python3
"""6-civ matrix orchestrator v2.

v1 (``run_six_civ_oneshot.py``) failed twice in a row with **0 personality
file flushes** because the resign sequence (``drv.resign()`` then
View-Postgame → Quit) didn't reliably end the match — clicks landed on
in-game HUD elements (the top-left circle home-city button, etc.)
instead of the abandon screen, leaving the match in mode 27 forever.

This v2 takes a more direct path:

  - After observing N seconds, instead of resigning then navigating
    abandon screens, we open the ESC menu and click **QUIT** (which
    per the in_game_driver comments "goes DIRECTLY to main menu —
    no abandon screen / View Postgame" for skirmish games).
  - We then confirm YES on the resulting "Quit current game?" dialog.
  - We **poll Age3Log.txt** for ``ModeTrack -- leaving mode 27`` as
    positive confirmation that the engine processed the match-end
    (which is the trigger for personality file flush).
  - We do **not** try to navigate the abandon / scoreboard / "Exit
    to Desktop" flow. The engine flushes personality at mode-27 exit;
    desktop exit is irrelevant.
  - Observation window is bumped to **180s wall = 15 game-min at 5×**
    so AIs have plenty of time to populate probe state.

Outputs (same as v1):
    artifacts/validation/ai_playstyle/matrix_summary.json
    artifacts/validation/ai_playstyle/<civ_id>/personality.xml
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.aoe3_automation import lobby_driver as ld
from tools.aoe3_automation.in_game_driver import GameDriver

MATRIX = [
    ("homecitygerman",     "ANWGermans",   "Frederick the Great", "FortressRing",       "anwgermans.personality"),
    ("homecitydeinca",     "ANWInca",      "Pachacuti",           "ChokepointSegments", "anwinca.personality"),
    ("homecitybritish",    "ANWBritish",   "Duke of Wellington",  "CoastalBatteries",   "anwbritish.personality"),
    ("homecityusa",        "ANWUSA",       "George Washington",   "FrontierPalisades",  "anwusa.personality"),
    ("anwhomecityrevolutionaryfrance",
                           "ANWRevFrance", "Robespierre",         "UrbanBarricade",     "anwrevfrance.personality"),
    ("homecityxpsioux",    "ANWLakota",    "Crazy Horse",         "MobileNoWalls",      "anwlakota.personality"),
]

AI_DIR = Path.home() / (
    ".local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/"
    "steamuser/Games/Age of Empires 3 DE/76561198170207043/Game/AI"
)
LOG_PATH = Path.home() / (
    ".local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/"
    "steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt"
)
OUT_DIR = REPO_ROOT / "artifacts/validation/ai_playstyle"

# 180s wall = 15 game-min at 5× speed. AIs reach Age 2-3, build initial
# walls/military, have meaningful probe data. (v1 used 60s which was
# only ~5 game-min and probably too short to be interesting.)
OBSERVE_SECONDS = 180

# In-game ESC menu coords (calibrated 2026-05-07 in in_game_driver.py).
# 8 rows: PhotoMode/TechTree/Save/Load/Restart/Options/RESIGN/QUIT.
ESC_MENU_X     = 1750
ESC_RESIGN_Y   = 358
ESC_QUIT_Y     = 403

# Quit/resign confirm dialog (same coords for both confirms).
CONFIRM_YES_XY = (762, 595)
CONFIRM_NO_XY  = (1162, 595)

# Main-menu "Exit to Desktop" button + its confirm dialog.
MAIN_MENU_EXIT_XY   = (115, 1002)


def load_ref() -> dict:
    for p in [REPO_ROOT / "tools/aoe3_automation/enriched_reference.json",
              REPO_ROOT / "tools/aoe3_automation/civ_reference.json"]:
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                pass
    return {}


def configure_lobby(coords: dict, ref: dict) -> dict:
    info = {"per_slot": []}
    for slot_idx, (civ_id, token, leader, _strat, _pfile) in enumerate(MATRIX, start=1):
        print(f"  [slot P{slot_idx + 1}] {civ_id} ({token}, {leader})", flush=True)
        try:
            res = ld.set_opponent_civ_by_token_verified(
                coords, slot_idx, token, ref, max_attempts=6,
            )
            slim = {"slot": slot_idx + 1, "civ_id": civ_id, "token": token,
                    "ok": bool(res.get("ok")),
                    "ocr_text": res.get("ocr_text", "?"),
                    "match_score": res.get("match_score"),
                    "attempts": res.get("attempts")}
            info["per_slot"].append(slim)
            print(f"    → ok={slim['ok']} ocr={slim['ocr_text']!r}", flush=True)
        except Exception as e:
            info["per_slot"].append({"slot": slot_idx + 1, "civ_id": civ_id,
                                     "token": token, "ok": False,
                                     "error": str(e)})
            print(f"    → ERROR {e}", flush=True)
    return info


def _click(x: int, y: int, label: str, settle: float = 1.0):
    print(f"  [click] {label} ({x},{y})", flush=True)
    ld.xdo(f"mousemove {x} {y}")
    time.sleep(0.5)
    ld.xdo("click 1")
    time.sleep(settle)


def _read_log_lines() -> list[str]:
    try:
        return LOG_PATH.read_text(errors="ignore").splitlines()
    except Exception:
        return []


def _log_has(needle: str, since_line: int = 0) -> bool:
    lines = _read_log_lines()
    for ln in lines[since_line:]:
        if needle in ln:
            return True
    return False


def quit_match_to_main_menu() -> dict:
    """Open ESC menu, click QUIT, confirm YES. Poll Age3Log.txt for
    'leaving mode 27' as positive confirmation match ended."""
    info: dict = {}

    # Baseline: where is the log currently? We'll re-read it.
    pre_lines = _read_log_lines()
    info["log_lines_before_quit"] = len(pre_lines)

    # Step 1: Press Escape to open ESC menu.
    print("  [esc] press Escape (open ESC menu)", flush=True)
    ld.xdo("key Escape")
    time.sleep(1.2)

    # Step 2: Click QUIT in ESC menu (row 8 at y=403).
    _click(ESC_MENU_X, ESC_QUIT_Y, "ESC menu → QUIT", settle=1.5)

    # Step 3: Click YES on "Quit current game?" confirm dialog.
    # Click twice in case dialog fade-in delays the first click.
    _click(*CONFIRM_YES_XY, "Quit confirm YES (1)", settle=0.5)
    _click(*CONFIRM_YES_XY, "Quit confirm YES (2)", settle=2.0)

    # Step 4: Poll the log for "leaving mode 27" (max 30s).
    deadline = time.time() + 30
    saw_mode_27_exit = False
    while time.time() < deadline:
        if _log_has("ModeTrack -- leaving mode 27", since_line=info["log_lines_before_quit"]):
            saw_mode_27_exit = True
            info["mode_27_exit_after_s"] = round(time.time() - (deadline - 30), 1)
            print(f"  [log] saw 'leaving mode 27' after "
                  f"{info['mode_27_exit_after_s']}s — match ended cleanly",
                  flush=True)
            break
        time.sleep(1)
    info["mode_27_exit"] = saw_mode_27_exit

    if not saw_mode_27_exit:
        print("  [log] WARN: no 'leaving mode 27' in 30s — match may still be active",
              flush=True)
        # Last-ditch attempt: another Escape + click QUIT + YES, in case
        # first sequence didn't open the menu (clicks fell through).
        print("  [retry] second Escape + QUIT + YES attempt", flush=True)
        ld.xdo("key Escape"); time.sleep(1.0)
        _click(ESC_MENU_X, ESC_QUIT_Y, "ESC menu → QUIT (retry)", settle=1.5)
        _click(*CONFIRM_YES_XY, "Quit confirm YES (retry)", settle=2.5)
        # Re-poll for 20s.
        deadline2 = time.time() + 20
        while time.time() < deadline2:
            if _log_has("ModeTrack -- leaving mode 27", since_line=info["log_lines_before_quit"]):
                saw_mode_27_exit = True
                info["mode_27_exit_after_retry_s"] = round(time.time() - (deadline2 - 20), 1)
                print(f"  [log] saw 'leaving mode 27' after retry "
                      f"+{info['mode_27_exit_after_retry_s']}s", flush=True)
                break
            time.sleep(1)
        info["mode_27_exit"] = saw_mode_27_exit
    return info


def snapshot_personalities(pre_mtimes: dict[str, float]) -> dict:
    out = {"per_civ": [], "all_touched_anw_files": []}
    for p in sorted(AI_DIR.glob("anw*.personality")):
        mt = p.stat().st_mtime
        if p.name not in pre_mtimes or mt > pre_mtimes[p.name] + 0.5:
            out["all_touched_anw_files"].append(p.name)

    for civ_id, token, leader, strat, pfile in MATRIX:
        src = AI_DIR / pfile
        meta = {"civ_id": civ_id, "token": token, "strategy": strat,
                "personality_fname": pfile, "exists": src.exists()}
        if src.exists():
            mt = src.stat().st_mtime
            meta["size_bytes"] = src.stat().st_size
            meta["mtime_iso"] = time.strftime("%Y-%m-%dT%H:%M:%S",
                                              time.localtime(mt))
            meta["touched_this_run"] = (
                pfile not in pre_mtimes or mt > pre_mtimes[pfile] + 0.5
            )
            dst_dir = OUT_DIR / civ_id
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst_dir / "personality.xml")
            meta["dst"] = str(dst_dir / "personality.xml")
        out["per_civ"].append(meta)
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    coords = ld.load_coords()
    ref = load_ref()
    art_dir = OUT_DIR / "_driver_art"
    art_dir.mkdir(parents=True, exist_ok=True)
    drv = GameDriver(art_dir=art_dir)

    if not drv.is_running():
        print("FAIL: game not running. Run 'python3 tools/aoe3_automation/"
              "manage_game.py open' first.", flush=True)
        return 2

    if not drv.ensure_main_menu(retries=2):
        print("WARN: not at main menu — proceeding anyway", flush=True)

    overall: dict = {"start_ts": time.time(), "matrix": [
        {"civ_id": c, "token": t, "leader": ld_, "strategy": s,
         "personality_fname": p} for (c, t, ld_, s, p) in MATRIX
    ]}

    pre_mtimes = {}
    for p in AI_DIR.glob("anw*.personality"):
        pre_mtimes[p.name] = p.stat().st_mtime
    overall["pre_match_anw_file_count"] = len(pre_mtimes)

    print("\n[1] Click Skirmish", flush=True)
    ld.click_skirmish(coords)
    time.sleep(5)

    print("\n[2] Configure P2..P7", flush=True)
    overall["lobby_config"] = configure_lobby(coords, ref)

    print("\n[3] Click Play", flush=True)
    ld.click_play(coords)

    print("\n[4] Wait for in-game (180s timeout)", flush=True)
    in_game = drv.wait_for_in_game(timeout=180, dismiss_errors=True)
    overall["wait_for_in_game"] = bool(in_game)
    if not in_game:
        overall["error"] = "wait_for_in_game timeout"
        (OUT_DIR / "matrix_summary.json").write_text(json.dumps(overall, indent=2))
        return 2

    print("\n[5] set_speed(5)", flush=True)
    try:
        drv.set_speed(5)
    except Exception as e:
        overall["set_speed_error"] = str(e)

    print(f"\n[6] Observe {OBSERVE_SECONDS}s wall-time "
          f"(= {OBSERVE_SECONDS * 5 // 60} game-min at 5×)", flush=True)
    t0 = time.time()
    time.sleep(OBSERVE_SECONDS)
    overall["observe_seconds"] = round(time.time() - t0, 1)

    print("\n[7] Quit match → main menu (ESC → QUIT → YES, with log poll)",
          flush=True)
    overall["quit"] = quit_match_to_main_menu()

    print("\n[8] Settle 5s for engine to finalize disk write", flush=True)
    time.sleep(5)

    print("\n[9] Snapshot personality files", flush=True)
    overall["personalities"] = snapshot_personalities(pre_mtimes)

    print("\nTouched anw*.personality files:",
          overall["personalities"]["all_touched_anw_files"], flush=True)

    overall["end_ts"] = time.time()
    overall["total_elapsed_s"] = round(overall["end_ts"] - overall["start_ts"], 1)
    (OUT_DIR / "matrix_summary.json").write_text(json.dumps(overall, indent=2))
    print(f"\n[DONE] summary: {OUT_DIR / 'matrix_summary.json'}", flush=True)
    return 0 if overall["personalities"]["all_touched_anw_files"] else 1


if __name__ == "__main__":
    sys.exit(main())
