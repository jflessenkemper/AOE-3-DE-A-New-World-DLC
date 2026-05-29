#!/usr/bin/env python3
"""Drive six 1v7 AI skirmishes — one per wall strategy — and capture the
``anw<civ>.personality`` snapshot for each test civ.

Critical insight from prior runs: probes in retail FINAL_RELEASE builds
do NOT land in Age3Log.txt. ``aiEcho()`` is stripped at retail. The probe
channel is the personality uservar file at
``Game/AI/<leader>.personality`` (UTF-16 XML), written via
``llWritePersonalityProbe()`` and flushed when the AI reaches end-state
(post-game flow).

Implication: the test civ must be in an *AI slot* (P2..P8), not the human
slot (P1). The human player slot does not run AI scripts and emits no
probes. The previous version of this script placed the test civ at P1
and got 0 probes for every match.

Flow per civ:
    1. (Already at main menu) → click Skirmish.
    2. lobby_driver.set_opponent_civ_by_token_verified(P2, test_token, ref)
       — OCR-verified picker selection on slot P2.
    3. (Other 6 AI slots P3..P8 retain whatever was previously set —
        lobby state persists across matches in the same session.)
    4. lobby_driver.click_play() — starts loading.
    5. GameDriver.wait_for_in_game() — waits for WorldAssetPreloadingTime.
    6. GameDriver.set_speed(5) — max game speed.
    7. Sleep observe_seconds wall-time (≈ 15 game-min at 5× speed).
    8. GameDriver.resign() — opens ESC menu, clicks RESIGN, YES.
    9. Navigate the abandon-town screen (FFA path) → View Postgame →
       Quit. The View Postgame click triggers the personality uservar
       flush for every still-running AI.
   10. Snapshot ``anw<civ>.personality`` to
       ``artifacts/validation/ai_playstyle/<civ_id>/personality.xml``.

Civ matrix (six representative civs; some share UrbanBarricade because the
in-game doctrines re-aligned to HTML reference after the matrix was first
drafted — Germans, USA and Revolutionary France all use Republican Levee):
    homecitygerman                    Frederick     UrbanBarricade
    homecitydeinca                    Pachacuti     FortressRing
    homecitybritish                   Wellington    CoastalBatteries
    homecityusa                       Washington    UrbanBarricade
    anwhomecityrevolutionaryfrance Robespierre  UrbanBarricade
    homecityxpsioux                   CrazyHorse    MobileNoWalls

Run from repo root:
    python3 tools/aoe3_automation/run_six_civ_matrix.py
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

# (civ_id_for_log, picker_token, leader, wall_strategy, personality_filename)
MATRIX = [
    ("homecitygerman",     "ANWGermans",            "Frederick the Great",   "UrbanBarricade",     "anwgermans.personality"),
    ("homecitydeinca",     "ANWInca",               "Pachacuti",             "FortressRing",       "anwinca.personality"),
    ("homecitybritish",    "ANWBritish",            "Duke of Wellington",    "CoastalBatteries",   "anwbritish.personality"),
    ("homecityusa",        "ANWUSA",                "George Washington",     "UrbanBarricade",     "anwusa.personality"),
    ("anwhomecityrevolutionaryfrance", "ANWRevFrance", "Robespierre",    "UrbanBarricade",     "anwrevfrance.personality"),
    ("homecityxpsioux",    "ANWLakota",             "Crazy Horse",           "MobileNoWalls",      "anwlakota.personality"),
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
OBSERVE_SECONDS = 50  # wall-clock; at speed 5 ≈ 250 game-sec.
#                       AI auto-resigns at cLLTestModeAutoResignMs=180000ms
#                       game-time (≈ 36s wall @5×), flushing personality.
#                       Extra 14s wall buffer lets the engine settle the
#                       disk write before our snapshot.

# P2 slot index (used by set_opponent_civ_by_token_verified)
TEST_CIV_SLOT = 1  # slot 1 == P2 (slots 1..7 map to P2..P8)

# Post-game navigation coords (1920×1080)
VIEW_POSTGAME_XY = (1105, 752)  # "View Postgame" button on abandon screen
POSTGAME_QUIT_XY = (112, 38)    # Quit button on postgame scoreboard


# ── Helpers ────────────────────────────────────────────────────────────

def load_ref() -> dict:
    """Load OCR reference for set_opponent_civ_by_token_verified."""
    candidates = [
        REPO_ROOT / "tools/aoe3_automation/enriched_reference.json",
        REPO_ROOT / "tools/aoe3_automation/civ_reference.json",
    ]
    for p in candidates:
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                pass
    return {}


def navigate_postgame_to_main_menu(drv: GameDriver) -> dict:
    """After drv.resign(), the FFA path lands on the "You Abandon Your Town"
    overlay (3-AI-still-alive case keeps the match running). We need to
    click View Postgame (triggers AI personality flush) → Quit (returns
    to main menu).

    On 1v1 maps the flow is direct-to-main-menu so this is a no-op fallback.
    Returns a debug dict.
    """
    info = {"view_postgame_clicked": False, "quit_clicked": False,
            "back_at_main_menu": False}

    # Heuristic: if drv.ensure_main_menu already verified main menu,
    # there's nothing to navigate. Otherwise screenshot + click.
    try:
        if drv.ensure_main_menu(retries=1):
            info["back_at_main_menu"] = True
            return info
    except Exception:
        pass

    # Click View Postgame (best-effort, blind)
    ld.xdo(f"mousemove {VIEW_POSTGAME_XY[0]} {VIEW_POSTGAME_XY[1]}")
    time.sleep(0.4)
    ld.xdo("click 1")
    info["view_postgame_clicked"] = True
    time.sleep(3.0)  # let scoreboard render

    # Click Quit (top-left of scoreboard)
    ld.xdo(f"mousemove {POSTGAME_QUIT_XY[0]} {POSTGAME_QUIT_XY[1]}")
    time.sleep(0.4)
    ld.xdo("click 1")
    info["quit_clicked"] = True
    time.sleep(3.0)

    try:
        info["back_at_main_menu"] = bool(drv.ensure_main_menu(retries=3))
    except Exception:
        info["back_at_main_menu"] = False
    return info


def snapshot_personality(personality_fname: str, civ_id: str,
                         out_dir: Path) -> dict:
    """Copy the AI's .personality file to out_dir. Returns metadata dict."""
    src = AI_DIR / personality_fname
    meta = {"src": str(src), "exists": src.exists()}
    if not src.exists():
        return meta

    try:
        st = src.stat()
        meta["size_bytes"] = st.st_size
        meta["mtime_iso"] = time.strftime(
            "%Y-%m-%dT%H:%M:%S", time.localtime(st.st_mtime)
        )
        dst = out_dir / "personality.xml"
        shutil.copy2(src, dst)
        meta["dst"] = str(dst)
        # Count probe-bearing uservars (rough heuristic: every llProbe writes
        # a "<UserVar name=ll_*>" entry). Read as UTF-16 with BOM.
        try:
            raw = src.read_bytes()
            # Personality files are UTF-16 LE with BOM.
            text = raw.decode("utf-16", errors="ignore")
            meta["uservar_count"] = text.count("<UserVar ")
            meta["ll_uservar_count"] = text.count('name="ll_')
            # Quick wall-strategy probe detection
            for tag in ("wall.closure", "wall.plan", "doctrine.selected",
                        "compose.ratio", "ageup.target", "ageup.fired"):
                meta[f"has_{tag.replace('.', '_')}"] = (
                    f'"{tag}"' in text or f"={tag}" in text
                )
        except Exception as e:
            meta["uservar_count_error"] = str(e)
    except Exception as e:
        meta["copy_error"] = str(e)
    return meta


def run_one(civ_id: str, token: str, leader: str, strategy: str,
            personality_fname: str, coords: dict, ref: dict,
            drv: GameDriver, is_first: bool) -> dict:
    """Drive one match end-to-end. Returns a per-civ summary dict."""
    out_dir = OUT_DIR / civ_id
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "civ_id": civ_id, "token": token, "leader": leader,
        "wall_strategy": strategy, "personality_fname": personality_fname,
        "start_ts": time.time(),
    }
    print(f"\n{'=' * 60}", flush=True)
    print(f"[MATRIX] {civ_id}  →  {token}  ({leader} / {strategy})", flush=True)
    print(f"{'=' * 60}", flush=True)

    # Step 1: enter skirmish from main menu
    print(f"[1] click Skirmish", flush=True)
    try:
        ld.click_skirmish(coords)
        time.sleep(4)
    except Exception as e:
        summary["error"] = f"click_skirmish: {e}"
        return summary

    # Step 2: set P2 to test civ (OCR-verified)
    print(f"[2] set P2 = {token} (OCR verified)", flush=True)
    try:
        res = ld.set_opponent_civ_by_token_verified(
            coords, TEST_CIV_SLOT, token, ref, max_attempts=6,
        )
        summary["civ_selection"] = {k: v for k, v in res.items()
                                    if k != "history"}
        if not res.get("ok"):
            summary["error"] = f"civ select failed: {res.get('ocr_text', '?')}"
            ld.xdo("key Escape"); time.sleep(1)
            ld.xdo("key Escape"); time.sleep(1)
            return summary
    except Exception as e:
        summary["error"] = f"set_opponent_civ_by_token_verified: {e}"
        return summary

    # Step 3: record AI dir baseline (mtimes) + click play
    pre_mtimes = {}
    try:
        for p in AI_DIR.glob("anw*.personality"):
            pre_mtimes[p.name] = p.stat().st_mtime
    except Exception:
        pass
    summary["pre_match_personality_count"] = len(pre_mtimes)

    print(f"[3] click Play", flush=True)
    try:
        ld.click_play(coords)
    except Exception as e:
        summary["error"] = f"click_play: {e}"
        return summary

    # Step 4: wait for in-game
    print(f"[4] wait_for_in_game (180s timeout)", flush=True)
    try:
        in_game = drv.wait_for_in_game(timeout=180, dismiss_errors=True)
        summary["wait_for_in_game"] = bool(in_game)
        if not in_game:
            summary["error"] = "wait_for_in_game timed out"
            ld.xdo("key Escape"); time.sleep(1)
            ld.xdo("key Escape"); time.sleep(1)
            return summary
    except Exception as e:
        summary["error"] = f"wait_for_in_game: {e}"
        return summary

    # Step 5: max speed
    print(f"[5] set_speed(5)", flush=True)
    try:
        drv.set_speed(5)
    except Exception as e:
        summary["set_speed_error"] = str(e)

    # Step 6: observe
    print(f"[6] observe {OBSERVE_SECONDS}s wall-time", flush=True)
    t0 = time.time()
    time.sleep(OBSERVE_SECONDS)
    summary["observe_seconds"] = round(time.time() - t0, 1)

    # Step 7: resign (ESC → RESIGN → YES)
    print(f"[7] resign", flush=True)
    try:
        ok = drv.resign()
        summary["resign_returned_ok"] = bool(ok)
    except Exception as e:
        summary["resign_error"] = str(e)
        for _ in range(3):
            ld.xdo("key Escape"); time.sleep(1)

    # Step 8: navigate post-game (FFA path: abandon screen → View Postgame
    # → Quit). On 1v1 maps this is a no-op (already at main menu).
    print(f"[8] navigate_postgame_to_main_menu", flush=True)
    pg_info = navigate_postgame_to_main_menu(drv)
    summary["postgame_nav"] = pg_info

    # Give the engine a moment to flush .personality writes
    time.sleep(3.0)

    # Step 9: snapshot personality file + diff against pre-match state
    print(f"[9] snapshot {personality_fname}", flush=True)
    pmeta = snapshot_personality(personality_fname, civ_id, out_dir)
    summary["personality"] = pmeta

    # Diff: which AI files were touched during this match?
    post_mtimes = {}
    try:
        for p in AI_DIR.glob("anw*.personality"):
            post_mtimes[p.name] = p.stat().st_mtime
    except Exception:
        pass
    touched = []
    for name, mt in post_mtimes.items():
        if name not in pre_mtimes or mt > pre_mtimes[name]:
            touched.append(name)
    summary["touched_personality_files"] = sorted(touched)
    summary["post_match_personality_count"] = len(post_mtimes)
    print(f"    → {len(touched)} personality files touched: "
          f"{', '.join(sorted(touched))}", flush=True)

    summary["end_ts"] = time.time()
    summary["elapsed_s"] = round(summary["end_ts"] - summary["start_ts"], 1)
    return summary


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    coords = ld.load_coords()
    ref = load_ref()
    art_dir = OUT_DIR / "_driver_art"
    art_dir.mkdir(parents=True, exist_ok=True)
    drv = GameDriver(art_dir=art_dir)

    if not drv.is_running():
        print("FAIL: game not running. Start the game manually first.",
              flush=True)
        return 2

    # Sanity check: confirm we're at the main menu before kickoff. If not,
    # try a soft return (resign no-ops at main menu, but abandon-screen
    # navigation should land us safely).
    if not drv.ensure_main_menu(retries=2):
        print("WARN: not at main menu — attempting recovery navigation",
              flush=True)
        navigate_postgame_to_main_menu(drv)

    overall = {"start_ts": time.time(), "results": []}
    for idx, (civ_id, token, leader, strategy, pfname) in enumerate(MATRIX):
        try:
            res = run_one(civ_id, token, leader, strategy, pfname,
                          coords, ref, drv, is_first=(idx == 0))
        except KeyboardInterrupt:
            print("[MATRIX] KeyboardInterrupt — aborting", flush=True)
            break
        except Exception as e:
            res = {"civ_id": civ_id, "token": token,
                   "error": f"top-level: {e}"}
        overall["results"].append(res)
        (OUT_DIR / "matrix_summary.json").write_text(
            json.dumps(overall, indent=2)
        )

    overall["end_ts"] = time.time()
    overall["total_elapsed_s"] = round(
        overall["end_ts"] - overall["start_ts"], 1
    )
    (OUT_DIR / "matrix_summary.json").write_text(
        json.dumps(overall, indent=2)
    )
    print("\n[MATRIX] done. summary:",
          str(OUT_DIR / "matrix_summary.json"), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
