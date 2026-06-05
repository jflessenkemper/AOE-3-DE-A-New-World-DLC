#!/usr/bin/env python3
"""sim_farm.driver — autonomous doctrine sweep. Runs with ZERO Opus tokens.

  python3 -m tools.sim_farm.driver --civs ANWGermans ANWInca --seeds 12345 \
      --observe-min 10 --opponent ANWNapoleonicFrance

For each (civ, seed): seed the RNG (anwFarmSeed), run one 1v1 Skirmish under
the GameSession safety guard, observe a bounded window, resign, harvest the
match's per-player probes, and grade per-age + walling doctrine. Writes a
JSON + Markdown report. Safe: never drives DISPLAY=:0; tears the game down
on exit; the watchdog kills it if memory gets tight.

SPEED: short observe window (default 10 game-min ≈ ~5-6 wall-min at Fast) +
game speed Fast. FIDELITY is unaffected — it's the real engine.
"""
from __future__ import annotations
import argparse, json, os, re, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
import tools.validation.smart_walls_sweep as sw          # calibrated lobby/lifecycle
import tools.validation.validate_per_age_v2 as v2         # grading + probe parse
from tools.aoe3_automation.game_safety import GameSession, kill_game_stack, aoe3_running
try:
    import tools.aoe3_automation.lobby_driver as lobby
except Exception:
    lobby = None

# Picker token (ANW*, used by the lobby) -> engine token (kbGetCivName, used by
# probes + spec). Revolution civs are identity; base/DE/XP civs map explicitly.
_PICKER_TO_ENGINE_BASE = {
    "ANWBritish": "British", "ANWFrench": "French", "ANWGermans": "Germans",
    "ANWSpanish": "Spanish", "ANWRussians": "Russians", "ANWOttomans": "Ottomans",
    "ANWDutch": "Dutch", "ANWPortuguese": "Portuguese", "ANWChinese": "Chinese",
    "ANWJapanese": "Japanese", "ANWIndians": "Indians", "ANWInca": "DEInca",
    "ANWMaltese": "DEMaltese", "ANWEthiopians": "DEEthiopians", "ANWHausa": "DEHausa",
    "ANWItalians": "DEItalians", "ANWMexicans": "DEMexicans", "ANWUSA": "DEAmericans",
    "ANWSwedes": "DESwedish", "ANWAztecs": "XPAztec", "ANWHaudenosaunee": "XPIroquois",
    "ANWLakota": "XPSioux",
}


def picker_to_engine(picker: str, engine_tokens: set) -> str:
    if picker in engine_tokens:          # revolution civ — identity
        return picker
    return _PICKER_TO_ENGINE_BASE.get(picker, picker)


SEED_FILE = Path(os.path.expanduser(
    "~/.local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/users/steamuser/"
    "Games/Age of Empires 3 DE/76561198170207043/mods/local/A New World/"
    "game/ai/core/anwFarmSeed.xs"))
LOGDIR = v2.DEFAULT_LOGDIR
OUT = REPO / "artifacts" / "sim_farm"
_SEED_RE = re.compile(r"(extern int gANWFarmSeed = )(-?\d+)(\s*;)")


def set_seed(n: int) -> None:
    txt = SEED_FILE.read_text(encoding="utf-8")
    new, c = _SEED_RE.subn(rf"\g<1>{n}\g<3>", txt)
    if c == 1:
        SEED_FILE.write_text(new, encoding="utf-8")


def log_offsets() -> dict:
    out = {}
    import glob
    for f in glob.glob(os.path.join(LOGDIR, "Age3DEAIOutputPlayer*.txt")):
        try:
            out[f] = os.path.getsize(f)
        except OSError:
            out[f] = 0
    return out


def harvest_delta(offsets: dict) -> dict:
    """Parse only probes appended since `offsets` -> {civ: {tag: [(t,kv)]}}."""
    import glob
    from collections import defaultdict
    out = defaultdict(lambda: defaultdict(list))
    for f in glob.glob(os.path.join(LOGDIR, "Age3DEAIOutputPlayer*.txt")):
        raw = open(f, "rb").read()[offsets.get(f, 0):]
        enc = "utf-16-le" if raw[:4].count(0) >= 1 else "utf-8"
        for ln in raw.decode(enc, "replace").splitlines():
            m = v2.PROBE.search(ln)
            if not m:
                continue
            out[m.group(3)][m.group(5).split()[0]].append(
                (int(m.group(1)), {k: float(x) for k, x in v2.KV.findall(m.group(6))}))
    return out


def run_match(test_civ: str, engine_civ: str, opponent: str, seed: int,
              observe_s: int, coords: dict, spec_civ: dict) -> dict:
    res = {"civ": test_civ, "engine_civ": engine_civ, "opponent": opponent,
           "seed": seed, "status": "SKIP", "grade": None, "error": None}
    set_seed(seed)
    offsets = log_offsets()
    # Farm owns the game lifecycle -> kill_on_exit=True; watchdog backstops memory.
    with GameSession(max_runtime_s=observe_s + 240, kill_on_exit=True,
                     hb_stale_s=max(180, observe_s // 2), mem_floor_mb=3000,
                     swap_cap_mb=2500) as guard:
        disp = sw.detect_aoe3_display_safe()
        if not disp:
            if not sw.launch_aoe3():
                res["error"] = "launch failed"; return res
            time.sleep(12); disp = sw.detect_aoe3_display_safe()
        if not disp or disp == ":0":
            res["error"] = f"unsafe display {disp}"; return res
        sw.setup_envs(disp, sw.detect_gamescope_socket(disp))
        if lobby:
            try: lobby.dismiss_weekly_popup()
            except Exception: pass
        pre = sw.log_byte_offset()
        sw.click_raw(*sw.SKIRMISH_BTN, settle=4.5)
        ok = sw.pick_civ_for_slot(coords, test_civ, slot=0) and \
            sw.pick_civ_for_slot(coords, opponent, slot=1)
        if not ok:
            res["error"] = "civ pick failed"; return res
        try: sw.select_map(coords, "Alaska")
        except Exception: pass
        play = coords["lobby"]["play_button"]
        sw.click_raw(*play, settle=0.5); time.sleep(0.5); sw.click_raw(*play, settle=2.0)
        if not sw.wait_for_mode_in_log(pre, "entering mode 27 (SinglePlayer)", timeout=170):
            res["error"] = "never reached in-game"; res["status"] = "TIMEOUT"; return res
        # observe bounded window with heartbeat + crash detection
        end = time.time() + observe_s
        while time.time() < end:
            time.sleep(10); guard.beat()
            if not aoe3_running():   # precise check (game_safety, not pgrep -f self-match)
                res["error"] = "crash during observe"; res["status"] = "CRASH"; return res
        try: sw.resign_match()
        except Exception: pass
        time.sleep(5)
    # grade (game torn down by GameSession exit) — probes keyed by ENGINE token
    tele = harvest_delta(offsets)
    tags = tele.get(engine_civ)
    if not tags:
        res["status"] = "NO_PROBES"; res["error"] = f"no probes for {engine_civ}"; return res
    res["grade"] = v2.validate_civ(spec_civ, tags)
    res["status"] = "DONE"
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description="ANW autonomous doctrine farm")
    ap.add_argument("--civs", nargs="+", required=True, help="engine civ tokens (e.g. ANWGermans)")
    ap.add_argument("--opponent", default="ANWNapoleonicFrance")
    ap.add_argument("--seeds", nargs="+", type=int, default=[12345])
    ap.add_argument("--observe-min", type=float, default=10.0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    spec = json.loads((REPO / "playstyle_spec.json").read_text())
    civs_spec = spec.get("civs", spec)
    # build engine->spec map via the readiness-site key map
    import importlib.util
    s = importlib.util.spec_from_file_location("brrs", REPO / "tools/validation/build_release_readiness_site.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    s2c = dict(getattr(m, "_SPEC_TO_CALIB_KEY", {}))
    calib_to_spec = {cv: sk for sk, cv in s2c.items()}
    engine_tokens = set(s2c.values())

    matrix = [(c, sd) for c in a.civs for sd in a.seeds]
    print(f"[farm] {len(matrix)} matches: civs={a.civs} seeds={a.seeds} "
          f"observe={a.observe_min}min opponent={a.opponent}")
    if a.dry_run:
        for c, sd in matrix:
            eng = picker_to_engine(c, engine_tokens)
            sk = calib_to_spec.get(eng)
            print(f"   {c:22s} -> engine={eng:18s} seed={sd:<8d} "
                  f"spec={'OK' if sk in civs_spec else 'MISSING'}")
        return 0

    if not sw.HARNESS_OK:
        print("[farm] ERROR: game harness not importable"); return 1
    coords = json.loads((REPO / "tools/aoe3_automation/lobby_coords.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    try:
        for c, sd in matrix:
            eng = picker_to_engine(c, engine_tokens)
            sk = calib_to_spec.get(eng)
            spec_civ = civs_spec.get(sk) if sk else None
            if not spec_civ:
                results.append({"civ": c, "seed": sd, "status": "NO_SPEC"}); continue
            print(f"\n[farm] === {c} (engine {eng}) seed={sd} ===")
            r = run_match(c, eng, a.opponent, sd, int(a.observe_min * 60), coords, spec_civ)
            print(f"[farm] {c}: {r['status']} grade="
                  f"{(r.get('grade') or {}).get('overall')}")
            results.append(r)
            if r["status"] in ("CRASH",):
                print("[farm] crash — cooling down 20s"); time.sleep(20)
    finally:
        set_seed(0)
        kill_game_stack("farm shutdown")
        (OUT / "results.json").write_text(json.dumps(results, indent=1, default=str))
        _write_md(results)
    npass = sum(1 for r in results if (r.get("grade") or {}).get("overall") == "PASS")
    print(f"\n[farm] done: {npass}/{len(results)} PASS. Report: {OUT/'report.md'}")
    return 0


def _write_md(results: list) -> None:
    lines = ["# ANW Doctrine Farm Report", "", time.strftime("%Y-%m-%d %H:%M"), "",
             "| Civ | Seed | Status | Int | Verdict | Checks |",
             "|-----|------|--------|-----|---------|--------|"]
    for r in results:
        g = r.get("grade") or {}
        checks = " ".join(f"{n}:{v}" for n, v, _ in g.get("checks", []))
        lines.append(f"| {r['civ']} | {r.get('seed','')} | {r['status']} | "
                     f"{g.get('intensity','')} | {g.get('overall','')} | {checks} |")
    (OUT / "report.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
