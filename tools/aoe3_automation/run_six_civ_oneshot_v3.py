#!/usr/bin/env python3
"""6-civ matrix orchestrator v3 — catches startup error dialogs.

v2 (``run_six_civ_oneshot_v2.py``) reached ``ModeTrack -- entering mode 27``
cleanly but then the Age3Log went silent for 170+ seconds before our
quit was issued.  Diagnosis: between ``mode 27`` and actual gameplay,
``WorldAssetPreloadingTime`` fires, then a startup error / warning dialog
typically pops up that pauses the engine until the user clicks OK.
``wait_for_in_game(dismiss_errors=True)`` was insufficient because it
only fires a single late Return — by the time the dialog appears, the
function has already returned True on the earlier mode-27 marker.

This v3 fixes the gap:

  - After ``wait_for_in_game`` returns True, we BLOCK on the Age3Log for
    ``WorldAssetPreloadingTime`` (strongest signal that load has actually
    completed and the engine is now ready to draw the match HUD).
  - Then we **aggressively dismiss any blocking dialog**:
       * Take a screenshot.
       * Press Return (3x, 1s apart) — handles ``OK`` button on the
         "mod content missing" / "XS warning" / generic modal popups.
       * Click center-screen at common modal-OK coordinates.
       * Re-screenshot.
       * Repeat for up to 30 seconds, or until the AI auto-resign harness
         fires (which we detect by polling personality file mtimes).
  - During observe we keep taking screenshots every 20s into
    ``artifacts/validation/ai_playstyle/_obs/<ts>.png`` so we can audit
    what was on screen at every point.
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
OBS_DIR = OUT_DIR / "_obs"

# Wall-clock observe after dialogs are dismissed. At 5x speed, harness fires
# at 60000ms game-time = ~12s wall.  Triple that for safety.
OBSERVE_SECONDS = 60

ESC_MENU_X     = 1750
ESC_QUIT_Y     = 403
CONFIRM_YES_XY = (762, 595)

# Common AoE3 modal OK button positions (1920x1080).  Two typical layouts:
#   (a) single button centered: (960, 595)
#   (b) two-button (Yes/No): (762, 595) Yes, (1162, 595) No
MODAL_OK_POSITIONS = [
    (960, 595),   # centered OK
    (762, 595),   # left-of-center Yes / OK
    (1162, 595),  # right-of-center No (some dialogs default OK is right)
    (960, 540),   # higher centered
    (960, 650),   # lower centered
]


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
                    "attempts": res.get("attempts")}
            info["per_slot"].append(slim)
            print(f"    → ok={slim['ok']} ocr={slim['ocr_text']!r}", flush=True)
        except Exception as e:
            info["per_slot"].append({"slot": slot_idx + 1, "civ_id": civ_id,
                                     "token": token, "ok": False, "error": str(e)})
            print(f"    → ERROR {e}", flush=True)
    return info


def _click(x: int, y: int, label: str, settle: float = 1.0):
    print(f"  [click] {label} ({x},{y})", flush=True)
    ld.xdo(f"mousemove {x} {y}")
    time.sleep(0.3)
    ld.xdo("click 1")
    time.sleep(settle)


def _read_log() -> str:
    try:
        return LOG_PATH.read_text(errors="ignore")
    except Exception:
        return ""


def _grab(path: Path, label: str = "") -> bool:
    try:
        ld.screenshot(path)
        print(f"  [shot] {label or path.name} → {path}", flush=True)
        return True
    except Exception as e:
        print(f"  [shot] FAIL {label}: {e}", flush=True)
        return False


def _wait_for_world_preload(timeout_s: int = 180) -> bool:
    """Wait for 'WorldAssetPreloadingTime' in Age3Log — load actually complete."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if "WorldAssetPreloadingTime" in _read_log():
            return True
        time.sleep(2)
    return False


def _ai_files_changed(pre_mtimes: dict[str, float]) -> list[str]:
    """Return list of personality files whose mtime advanced past pre."""
    out = []
    for p in AI_DIR.glob("anw*.personality"):
        mt = p.stat().st_mtime
        if p.name not in pre_mtimes or mt > pre_mtimes[p.name] + 0.5:
            out.append(p.name)
    return out


def dismiss_startup_errors(pre_mtimes: dict[str, float],
                           shot_dir: Path,
                           total_seconds: int = 45) -> dict:
    """Aggressively dismiss any modal dialogs blocking match start.

    Strategy: every 3s, take a screenshot + press Return + click each common
    OK position + click center-screen. Stop early if personality files
    start updating (means AI has actually started ticking).
    """
    info = {"attempts": [], "files_changed_during_dismissal": []}
    shot_dir.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + total_seconds
    iteration = 0
    while time.time() < deadline:
        iteration += 1
        t = round(time.time() - (deadline - total_seconds), 1)
        # Screenshot first to see what's on screen
        shot = shot_dir / f"dismiss_t{int(t):03d}_iter{iteration}.png"
        _grab(shot, f"dismiss iter {iteration} t={t}s")
        # Send Return — most modal-OKs respond to it
        ld.xdo("key Return")
        time.sleep(0.3)
        # Click each common modal-OK position
        for (x, y) in MODAL_OK_POSITIONS:
            ld.xdo(f"mousemove {x} {y}")
            time.sleep(0.1)
            ld.xdo("click 1")
            time.sleep(0.1)
        # Send a second Return for good measure
        ld.xdo("key Return")
        time.sleep(0.2)
        info["attempts"].append({"iter": iteration, "t": t,
                                 "shot": shot.name})
        # Check if AI files have started updating — that's our success signal
        changed = _ai_files_changed(pre_mtimes)
        if changed:
            info["files_changed_during_dismissal"] = changed
            print(f"  [dismiss] AI files updated mid-dismissal: {changed} — stopping", flush=True)
            break
        time.sleep(2.5)
    return info


def quit_match_to_main_menu() -> dict:
    info: dict = {}
    pre = _read_log()
    info["pre_quit_log_chars"] = len(pre)
    ld.xdo("key Escape"); time.sleep(1.2)
    _click(ESC_MENU_X, ESC_QUIT_Y, "ESC menu → QUIT", settle=1.5)
    _click(*CONFIRM_YES_XY, "Quit confirm YES (1)", settle=0.6)
    _click(*CONFIRM_YES_XY, "Quit confirm YES (2)", settle=2.0)
    deadline = time.time() + 30
    saw_exit = False
    while time.time() < deadline:
        post = _read_log()[info["pre_quit_log_chars"]:]
        if "leaving mode 27" in post:
            saw_exit = True
            info["mode_27_exit_after_s"] = round(time.time() - (deadline - 30), 1)
            break
        time.sleep(1)
    info["mode_27_exit"] = saw_exit
    if not saw_exit:
        # Retry once
        print("  [log] WARN: no 'leaving mode 27' in 30s — retry", flush=True)
        ld.xdo("key Escape"); time.sleep(1.0)
        _click(ESC_MENU_X, ESC_QUIT_Y, "ESC menu → QUIT (retry)", settle=1.5)
        _click(*CONFIRM_YES_XY, "Quit confirm YES (retry)", settle=2.5)
        d2 = time.time() + 20
        while time.time() < d2:
            post = _read_log()[info["pre_quit_log_chars"]:]
            if "leaving mode 27" in post:
                saw_exit = True
                break
            time.sleep(1)
        info["mode_27_exit"] = saw_exit
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
            # Snapshot the file alongside the matrix output
            civ_out = OUT_DIR / civ_id
            civ_out.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, civ_out / "personality.xml")
            meta["snapshot"] = str(civ_out / "personality.xml")
        out["per_civ"].append(meta)
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OBS_DIR.mkdir(parents=True, exist_ok=True)
    coords = ld.load_coords()
    ref = load_ref()
    art_dir = OUT_DIR / "_driver_art"
    art_dir.mkdir(parents=True, exist_ok=True)
    drv = GameDriver(art_dir=art_dir)

    if not drv.is_running():
        print("FAIL: game not running. Run 'python3 tools/aoe3_automation/manage_game.py open' first.", flush=True)
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
    print(f"\n[0] Pre-match AI file count: {len(pre_mtimes)}", flush=True)

    print("\n[1] Click Skirmish", flush=True)
    ld.click_skirmish(coords); time.sleep(5)

    print("\n[2] Configure P2..P7", flush=True)
    overall["lobby_config"] = configure_lobby(coords, ref)

    print("\n[3] Click Play", flush=True)
    ld.click_play(coords)

    print("\n[4] wait_for_in_game (180s)", flush=True)
    in_game = drv.wait_for_in_game(timeout=180, dismiss_errors=True)
    overall["wait_for_in_game"] = bool(in_game)
    if not in_game:
        overall["error"] = "wait_for_in_game timeout"
        (OUT_DIR / "matrix_summary.json").write_text(json.dumps(overall, indent=2))
        return 2

    print("\n[5] Wait for WorldAssetPreloadingTime", flush=True)
    preload_done = _wait_for_world_preload(timeout_s=180)
    overall["world_preload_seen"] = preload_done
    if not preload_done:
        print("  [warn] no WorldAssetPreloadingTime in 180s — proceeding anyway", flush=True)

    print("\n[5.5] Pre-dismiss screenshot", flush=True)
    _grab(OBS_DIR / "00_pre_dismiss.png", "pre-dismiss")

    print("\n[6] Dismiss startup error dialogs (up to 45s)", flush=True)
    overall["dismiss"] = dismiss_startup_errors(pre_mtimes, OBS_DIR, total_seconds=45)

    # By now harness should have fired (60000ms game-time = ~12s wall at 5x).
    print("\n[7] Check personality flushes mid-game", flush=True)
    mid_changed = _ai_files_changed(pre_mtimes)
    overall["files_changed_mid_game"] = mid_changed
    print(f"  → mid-game changed: {mid_changed}", flush=True)

    print("\n[8] Try set_speed(5)", flush=True)
    try: drv.set_speed(5)
    except Exception as e: overall["set_speed_error"] = str(e)

    print(f"\n[9] Observe {OBSERVE_SECONDS}s with periodic screenshots", flush=True)
    t0 = time.time()
    next_shot = 0
    while time.time() - t0 < OBSERVE_SECONDS:
        if time.time() - t0 >= next_shot:
            _grab(OBS_DIR / f"obs_t{int(time.time()-t0):03d}.png",
                  f"observe t={int(time.time()-t0)}s")
            next_shot += 20
        # Mid-observe Return spam to dismiss any late-popping dialogs
        if int(time.time() - t0) in (3, 8, 15):
            ld.xdo("key Return"); time.sleep(0.3)
        time.sleep(1.0)
    overall["observe_seconds"] = round(time.time() - t0, 1)

    print("\n[10] Check personality flushes post-observe", flush=True)
    post_obs_changed = _ai_files_changed(pre_mtimes)
    overall["files_changed_post_observe"] = post_obs_changed
    print(f"  → post-observe changed: {post_obs_changed}", flush=True)

    print("\n[11] Quit match → main menu", flush=True)
    overall["quit"] = quit_match_to_main_menu()

    print("\n[12] Settle 5s, snapshot personalities", flush=True)
    time.sleep(5)
    overall["personalities"] = snapshot_personalities(pre_mtimes)
    print(f"\nTouched anw*.personality files: "
          f"{overall['personalities']['all_touched_anw_files']}", flush=True)

    overall["end_ts"] = time.time()
    overall["total_elapsed_s"] = round(overall["end_ts"] - overall["start_ts"], 1)
    (OUT_DIR / "matrix_summary.json").write_text(json.dumps(overall, indent=2))
    print(f"\n[DONE] summary: {OUT_DIR / 'matrix_summary.json'}", flush=True)
    return 0 if overall["personalities"]["all_touched_anw_files"] else 1


if __name__ == "__main__":
    sys.exit(main())
