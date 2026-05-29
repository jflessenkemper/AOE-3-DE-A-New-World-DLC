#!/usr/bin/env python3
"""Drive ONE 1v7 AI skirmish with all 6 wall-strategy test civs in
slots P2..P7 (P8 = random), then quit the game cleanly to flush every
``anw<civ>.personality`` file at once.

Key discovery (2026-05-12): The engine ONLY flushes personality
uservars to disk when the game *process* terminates cleanly via
the in-game Exit → Yes UI. Neither resign, View Postgame, nor
Quit-to-Main-Menu trigger a flush. So we must:

  1. Configure the lobby once with all six test civs in AI slots.
  2. Click Play; observe long enough for the auto-resign harness
     (``cLLTestModeAutoResignMs``) to fire each AI's
     ``gameOverHandler`` (and buffer its probe write).
  3. Resign as human.
  4. Click View Postgame → Quit (back to main menu) — this releases
     the in-match resources but keeps probes buffered.
  5. Click Exit → Yes (the in-game quit-to-desktop confirmation) —
     this triggers the engine's personality-serialiser, writing all
     buffered probes to ``Game/AI/<civ>.personality`` on disk.
  6. Wait for the game process to exit.
  7. Read each test civ's personality file via
     ``tools.playtest.probes_from_replay.parse_personality_file``.

Matrix (one civ per wall strategy, all in the same lobby):
    P2  ANWGermans       Frederick       FortressRing
    P3  ANWInca          Pachacuti       ChokepointSegments
    P4  ANWBritish       Wellington      CoastalBatteries
    P5  ANWUSA           Washington      FrontierPalisades
    P6  ANWRevFrance     Robespierre     UrbanBarricade
    P7  ANWLakota        CrazyHorse      MobileNoWalls
    P8  random           (untouched)     (control slot)

Outputs (``artifacts/validation/ai_playstyle/``):
    matrix_summary.json     — driver-side log of what happened
    <civ_id>/personality.xml — copy of flushed personality file
    playstyle_verdicts.md   — produced by validate_six_civ_playstyle.py

Run from repo root:
    python3 tools/aoe3_automation/run_six_civ_oneshot.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.aoe3_automation import lobby_driver as ld
from tools.aoe3_automation.in_game_driver import GameDriver

# ── Configuration ──────────────────────────────────────────────────────

# Slot order P2..P7 = 6 test civs.
# (civ_id_for_log, picker_token, leader, wall_strategy, personality_filename)
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
OUT_DIR = REPO_ROOT / "artifacts/validation/ai_playstyle"

# Observe ≥ auto-resign threshold + buffer. Auto-resign at xsGetTime>=180_000ms
# game-time. At 5× speed → ~36s wall. Add buffer for all 7 AIs to actually fire.
OBSERVE_SECONDS = 60

# In-game UI coords (1920×1080)
VIEW_POSTGAME_XY      = (1155, 735)   # "View Postgame" button on abandon screen
POSTGAME_QUIT_XY      = (50, 25)      # "Quit" top-left on postgame scoreboard
MAIN_MENU_EXIT_XY     = (115, 1002)   # "Exit" bottom-left of main menu
EXIT_CONFIRM_YES_XY   = (762, 595)    # "Yes" on Quit confirm dialog


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
    """Configure P2..P7 with the 6 test civs (OCR-verified). P1, P8 untouched
    (whatever the lobby was last set to, typically Random)."""
    info = {"per_slot": []}
    for slot_idx, (civ_id, token, leader, _strat, _pfile) in enumerate(MATRIX, start=1):
        # slot_idx 1..6 → P2..P7 (slot index 1==P2)
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


def navigate_postgame_to_main_menu() -> dict:
    """After resign → 'You Abandon Your Town': View Postgame → Quit → main menu."""
    info: dict = {}

    print("  [nav] click View Postgame", flush=True)
    ld.xdo(f"mousemove {VIEW_POSTGAME_XY[0]} {VIEW_POSTGAME_XY[1]}")
    time.sleep(0.5)
    ld.xdo("click 1")
    time.sleep(5)

    print("  [nav] click Quit (postgame scoreboard)", flush=True)
    ld.xdo(f"mousemove {POSTGAME_QUIT_XY[0]} {POSTGAME_QUIT_XY[1]}")
    time.sleep(0.5)
    ld.xdo("click 1")
    time.sleep(4)
    return info


def quit_game_cleanly() -> dict:
    """Click Exit on main menu → Yes on confirm dialog. This is the
    only sequence that triggers personality flush."""
    info: dict = {}
    print("  [exit] click Exit on main menu", flush=True)
    ld.xdo(f"mousemove {MAIN_MENU_EXIT_XY[0]} {MAIN_MENU_EXIT_XY[1]}")
    time.sleep(0.5)
    ld.xdo("click 1")
    time.sleep(2)

    print("  [exit] click Yes to confirm", flush=True)
    ld.xdo(f"mousemove {EXIT_CONFIRM_YES_XY[0]} {EXIT_CONFIRM_YES_XY[1]}")
    time.sleep(0.5)
    ld.xdo("click 1")

    # Wait for game process to exit.
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            res = subprocess.run(["pgrep", "-f", "AoE3DE_s.exe"],
                                 capture_output=True, text=True, timeout=2)
            if not res.stdout.strip():
                info["game_exited"] = True
                info["exit_after_s"] = round(time.time() - (deadline - 30), 1)
                print(f"  [exit] game process gone after {info['exit_after_s']}s",
                      flush=True)
                return info
        except Exception:
            pass
        time.sleep(1)
    info["game_exited"] = False
    info["exit_after_s"] = 30
    print("  [exit] WARN: game still running after 30s", flush=True)
    return info


def snapshot_personalities(pre_mtimes: dict[str, float]) -> dict:
    """After game exit: copy each test civ's personality file to artifacts."""
    out = {"per_civ": [], "all_touched_anw_files": []}
    # All anw* files touched since pre-snapshot
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

    # GameDriver for in_game / resign helpers.
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

    # Baseline mtimes for ALL anw* files before we start
    pre_mtimes = {}
    for p in AI_DIR.glob("anw*.personality"):
        pre_mtimes[p.name] = p.stat().st_mtime
    overall["pre_match_anw_file_count"] = len(pre_mtimes)

    # ── Step 1: enter skirmish lobby ────────────────────────────────────
    print("\n[1] Click Skirmish to enter lobby", flush=True)
    try:
        ld.click_skirmish(coords)
        time.sleep(5)
    except Exception as e:
        overall["error"] = f"click_skirmish: {e}"
        (OUT_DIR / "matrix_summary.json").write_text(json.dumps(overall, indent=2))
        return 2

    # ── Step 2: configure P2..P7 with 6 test civs ───────────────────────
    print("\n[2] Configure lobby: P2..P7 = 6 test civs", flush=True)
    overall["lobby_config"] = configure_lobby(coords, ref)

    # ── Step 3: click Play ──────────────────────────────────────────────
    print("\n[3] Click Play", flush=True)
    try:
        ld.click_play(coords)
    except Exception as e:
        overall["error"] = f"click_play: {e}"
        (OUT_DIR / "matrix_summary.json").write_text(json.dumps(overall, indent=2))
        return 2

    # ── Step 4: wait for in-game ────────────────────────────────────────
    print("\n[4] Wait for in-game (180s timeout)", flush=True)
    try:
        in_game = drv.wait_for_in_game(timeout=180, dismiss_errors=True)
        overall["wait_for_in_game"] = bool(in_game)
        if not in_game:
            overall["error"] = "wait_for_in_game timed out"
            (OUT_DIR / "matrix_summary.json").write_text(json.dumps(overall, indent=2))
            return 2
    except Exception as e:
        overall["error"] = f"wait_for_in_game: {e}"
        (OUT_DIR / "matrix_summary.json").write_text(json.dumps(overall, indent=2))
        return 2

    # ── Step 5: speed 5× ────────────────────────────────────────────────
    print("\n[5] set_speed(5)", flush=True)
    try:
        drv.set_speed(5)
    except Exception as e:
        overall["set_speed_error"] = str(e)

    # ── Step 6: observe (auto-resign triggers within window) ────────────
    print(f"\n[6] Observe {OBSERVE_SECONDS}s wall-time "
          f"(auto-resign at ~36s @ 5×)", flush=True)
    t0 = time.time()
    time.sleep(OBSERVE_SECONDS)
    overall["observe_seconds"] = round(time.time() - t0, 1)

    # ── Step 7: resign ──────────────────────────────────────────────────
    print("\n[7] Resign", flush=True)
    try:
        ok = drv.resign()
        overall["resign_returned_ok"] = bool(ok)
    except Exception as e:
        overall["resign_error"] = str(e)
        for _ in range(3):
            ld.xdo("key Escape"); time.sleep(1)

    # ── Step 8: navigate post-game ──────────────────────────────────────
    print("\n[8] Navigate postgame → main menu", flush=True)
    overall["postgame_nav"] = navigate_postgame_to_main_menu()

    # ── Step 9: quit game cleanly (TRIGGERS PERSONALITY FLUSH) ──────────
    print("\n[9] Quit game cleanly (triggers personality flush)", flush=True)
    overall["quit"] = quit_game_cleanly()

    # ── Step 10: extra settle time for disk write ───────────────────────
    print("\n[10] settle (5s for disk writes)", flush=True)
    time.sleep(5)

    # ── Step 11: snapshot personalities ─────────────────────────────────
    print("\n[11] Snapshot personality files", flush=True)
    overall["personalities"] = snapshot_personalities(pre_mtimes)

    print("\nTouched anw*.personality files:",
          overall["personalities"]["all_touched_anw_files"], flush=True)

    overall["end_ts"] = time.time()
    overall["total_elapsed_s"] = round(overall["end_ts"] - overall["start_ts"], 1)
    (OUT_DIR / "matrix_summary.json").write_text(json.dumps(overall, indent=2))
    print(f"\n[DONE] summary: {OUT_DIR / 'matrix_summary.json'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
