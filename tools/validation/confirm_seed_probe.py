#!/usr/bin/env python3
"""confirm_seed_probe.py — live confirmation that the farm seed hook fires.

Arms gANWFarmSeed via the deployed anwFarmSeed.xs, starts ONE Skirmish match,
waits for AI preInit, and greps the per-player UTF-16 logs for the
`match.seed seed=<N>` probe. Resigns + resets seed to 0 on exit.

Reuses the calibrated helpers in smart_walls_sweep.py. Safe: never drives :0.
"""
from __future__ import annotations
import glob, os, re, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
import tools.validation.smart_walls_sweep as sw  # calibrated launch/lobby helpers
from tools.aoe3_automation.game_safety import GameSession  # memory/runtime guard

SEED = 777
SEED_FILE = Path(os.path.expanduser(
    "~/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/"
    "Games/Age of Empires 3 DE/76561198170207043/mods/local/A New World/"
    "game/ai/core/anwFarmSeed.xs"))
LOGDIR = Path(os.path.expanduser(
    "~/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/"
    "Games/Age of Empires 3 DE/Logs"))
_SEED_RE = re.compile(r"(extern int gANWFarmSeed = )(-?\d+)(\s*;)")


def set_seed(n: int) -> None:
    txt = SEED_FILE.read_text(encoding="utf-8")
    new, c = _SEED_RE.subn(rf"\g<1>{n}\g<3>", txt)
    assert c == 1, f"seed line not found ({c})"
    SEED_FILE.write_text(new, encoding="utf-8")
    print(f"[seed] gANWFarmSeed = {n}")


def grep_match_seed() -> list[str]:
    hits = []
    for f in glob.glob(str(LOGDIR / "Age3DEAIOutputPlayer*.txt")):
        raw = open(f, "rb").read()
        enc = "utf-16-le" if raw[:4].count(0) >= 1 else "utf-8"
        for line in raw.decode(enc, "replace").splitlines():
            if "tag=match.seed" in line:
                hits.append(os.path.basename(f) + ": " + line.strip()[:140])
    return hits


def main() -> int:
    set_seed(SEED)
    # Memory/runtime guard: a detached watchdog kills the AoE3 stack if memory
    # gets tight, a 240s cap is hit, or this process dies — so this can never
    # thrash the desktop again. kill_on_exit=False: we reuse a running game.
    guard = GameSession(max_runtime_s=240, kill_on_exit=False, hb_stale_s=240,
                        mem_floor_mb=3000, swap_cap_mb=2500)
    guard.__enter__()
    try:
        disp = sw.detect_aoe3_display_safe()
        if not disp or disp == ":0":
            print(f"[abort] no safe AoE3 display (got {disp})"); return 2
        sw.setup_envs(disp, sw.detect_gamescope_socket(disp))
        coords = __import__("json").loads(
            (REPO / "tools/aoe3_automation/lobby_coords.json").read_text())
        if sw.lobby is not None:
            try: sw.lobby.dismiss_weekly_popup()
            except Exception: pass
        pre = sw.log_byte_offset()
        print("[lobby] Skirmish -> pick Germans vs Napoleon -> Play")
        sw.click_raw(*sw.SKIRMISH_BTN, settle=4.5)
        sw.pick_civ_for_slot(coords, "ANWGermans", slot=0)
        sw.pick_civ_for_slot(coords, "ANWNapoleonicFrance", slot=1)
        sw.select_map(coords, "Alaska")
        play = coords["lobby"]["play_button"]
        sw.click_raw(*play, settle=0.5); time.sleep(0.5); sw.click_raw(*play, settle=2.0)
        print("[wait] for mode-27 (in-game) ...")
        if not sw.wait_for_mode_in_log(pre, "entering mode 27 (SinglePlayer)", timeout=160):
            print("[fail] never reached in-game"); return 3
        print("[wait] 35s for preInit/match.seed probe ...")
        time.sleep(35)
        hits = grep_match_seed()
        if hits:
            print(f"\n*** SEED HOOK CONFIRMED — match.seed probe fired ({len(hits)}) ***")
            for h in hits[:6]: print("  " + h)
            ok = any(f"seed={SEED}" in h for h in hits)
            print(f"value match seed={SEED}: {'YES' if ok else 'NO'}")
            return 0 if ok else 4
        print("[fail] no match.seed probe found in per-player logs"); return 5
    finally:
        try: sw.resign_match()
        except Exception: pass
        set_seed(0)
        guard.__exit__(None, None, None)   # drop heartbeat; watchdog winds down


if __name__ == "__main__":
    sys.exit(main())
