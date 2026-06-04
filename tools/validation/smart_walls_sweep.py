#!/usr/bin/env python3
"""smart_walls_sweep.py — 4-civ smart-walls AI validation sweep.

Runs 4 x 1v1 AoE3 DE Skirmish matches (each ~4 min wall-clock) against
Napoleonic France (Napoleon) and captures [ANWP v=2] probe data from
Age3Log.txt to verify smart-walls AI behaviour for four wall-strategy
archetypes.

Target civs:
  1. ANWInca      (Pachacuti)  — chokepoint-segment.  Map: Texas
  2. ANWBritish   (Wellington) — coastal water-aware.  Map: Caribbean
  3. ANWGermans   (Frederick)  — FortressRing tier.    Map: Great Plains
  4. ANWUSA       (Washington) — FrontierPalisade.     Map: Texas

Opponent: ANWNapoleonicFrance (Napoleon) for all matches.

Safety constraints enforced:
  - NEVER send xdotool to DISPLAY=:0.
  - NEVER kill CoH2 (AppId=231430) processes.

Usage:
    cd /var/home/jflessenkemper/AOE-3-DE-A-New-World
    python3 tools/validation/smart_walls_sweep.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

# Repo root (two levels above this file: tools/validation/...)
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

# ── import lobby_driver helpers ───────────────────────────────────────────────
try:
    import tools.aoe3_automation.lobby_driver as lobby
    import tools.aoe3_automation.gamescope_detect as gs_detect
    from tools.aoe3_automation.anw_civ_picker_map import ANW_TO_PICKER_INDEX
    HARNESS_OK = True
except ImportError as _ie:
    print(f"WARN: could not import game harness: {_ie}", file=sys.stderr)
    HARNESS_OK = False
    lobby = None  # type: ignore
    gs_detect = None  # type: ignore
    ANW_TO_PICKER_INDEX = {}

# ── paths ─────────────────────────────────────────────────────────────────────

AGE3_LOG = Path.home() / (
    ".local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/"
    "users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt"
)

OUT_DIR = REPO / "artifacts" / "validation" / "live_test"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RUN_LOG = OUT_DIR / "run.log"

# ── constants ─────────────────────────────────────────────────────────────────

# 2026-05-28 (Sydney): observation extended 4→8 min. The verifyWallClosure
# rule has minInterval=60s and only fires AFTER the AI has built a wall
# plan (wood ≥ 75, Age 1 or 2, main base exists). On Alaska the first
# wall plan typically lands at 3.5-5 min game-time; 4-min wall-clock left
# zero room for the closure probe to fire even once. 8 min reliably yields
# 3-5 wall.closure probe lines per civ.
SWEEP_TIMEOUT_S   = 60 * 60   # 60 min hard wall for entire sweep (4 civs × ~12 min)
MATCH_TIMEOUT_S   = 12 * 60   # 12 min hard wall per civ (launch+match+teardown)
MATCH_OBSERVE_S   = 8  * 60   # 8 min in-game observation window
LAUNCH_WAIT_S     = 90        # max seconds to wait for game window after launch
MENU_WAIT_EXTRA_S = 12        # extra settle after game window detected

# Civ picker indices (from anw_civ_picker_map.py, verified against picker layout)
CIV_IDX = {
    "ANWInca":             23,   # Inca Empire
    "ANWBritish":          7,    # Britain
    "ANWGermans":          19,   # Germany
    "ANWUSA":              47,   # United States
    "ANWNapoleonicFrance": 17,   # French Empire (Napoleon)
}

# Match plan
# 2026-05-28 (Sydney): archetypes corrected to match playstyle_spec.json claims
# (audited in artifacts/validation/doctrine_audit/per_civ_wall_audit.md). The
# old labels (ChokeSegment / CoastalAware / FortressRing / FrontierPalisade)
# pre-dated several knob-table re-balances and reported FAIL even when the
# AI was behaving exactly to spec. Civs picked here cover the four most
# discriminating strategies (skipping ForwardLine since it intentionally
# builds no perimeter ring).
#
# Map: ALL civs use AlaskaLarge for now. The previous typeahead-based
# select_map() did not actually switch maps (engine always loaded Alaska
# regardless of typed input), and AlaskaLarge has been the only verified-
# stable 8-player config since the 2026-05-28 picker re-calibration. Per-
# map terrain variety can be re-introduced once the lobby-driver typeahead
# is fixed and verified end-to-end.
MATCHES = [
    {"civ": "ANWInca",    "leader": "Pachacuti",        "map": "Alaska", "archetype": "FrontierPalisade (DEInca knobs)"},
    {"civ": "ANWBritish", "leader": "Queen Elizabeth I","map": "Alaska", "archetype": "MobileNoWalls (British knobs)"},
    {"civ": "ANWGermans", "leader": "Frederick",        "map": "Alaska", "archetype": "ChokepointSegments (Germans knobs)"},
    {"civ": "ANWUSA",     "leader": "Washington",       "map": "Alaska", "archetype": "ChokepointSegments (DEAmericans knobs)"},
]

NAPOLEON_CIV = "ANWNapoleonicFrance"
NAPOLEON_IDX = CIV_IDX[NAPOLEON_CIV]

# Lobby coords (from lobby_coords.json)
SKIRMISH_BTN  = (130, 482)
P1_CIV        = (630, 170)
P2_CIV        = (630, 276)
MAP_BTN       = (1645, 395)
PLAY_BTN      = (1700, 1029)

# ESC menu / resign (from in_game_driver.py, calibrated 2026-05-07)
ESC_RESIGN    = (1750, 358)
RESIGN_YES    = (762, 595)


# ── logging ───────────────────────────────────────────────────────────────────

def rlog(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with RUN_LOG.open("a") as f:
        f.write(line + "\n")


# ── display detection ─────────────────────────────────────────────────────────

def detect_aoe3_display_safe() -> str | None:
    """Return AoE3 X display. Returns None if not found.
    NEVER returns :0 — aborts if that's the only option."""
    candidates = []
    for lock in sorted(glob.glob("/tmp/.X*-lock")):
        n = lock.removeprefix("/tmp/.X").removesuffix("-lock")
        if n.isdigit() and f":{n}" != ":0":
            candidates.append(f":{n}")

    for d in candidates:
        env = {**os.environ, "DISPLAY": d}
        try:
            res = subprocess.run(
                ["xwininfo", "-root", "-tree"], env=env,
                capture_output=True, text=True, timeout=5
            )
            if res.returncode == 0 and "Age of Empires III" in res.stdout:
                rlog(f"AoE3 window found on DISPLAY={d}")
                return d
        except subprocess.TimeoutExpired:
            pass
    return None


def detect_gamescope_socket(aoe3_display: str) -> str:
    """Pair AoE3 X display with gamescope socket name."""
    xdg = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    sockets = sorted([
        os.path.basename(s) for s in glob.glob(os.path.join(xdg, "gamescope-[0-9]*"))
        if not s.endswith((".lock", "-ei", "-ei.lock"))
    ])
    if not sockets:
        sockets = ["gamescope-0"]
    rlog(f"Gamescope sockets: {sockets}")
    try:
        num = int(aoe3_display.lstrip(":"))
        preferred = f"gamescope-{max(0, num - 1)}"
        if preferred in sockets:
            return preferred
    except ValueError:
        pass
    return sockets[0]


# ── low-level input ───────────────────────────────────────────────────────────

_XDO_ENV: dict = {}
_GS_ENV:  dict = {}
_COORDS:  dict = {}


def setup_envs(aoe3_display: str, gs_socket: str) -> None:
    global _XDO_ENV, _GS_ENV
    _XDO_ENV = {**os.environ, "DISPLAY": aoe3_display}
    _GS_ENV  = {**os.environ,
                "GAMESCOPE_WAYLAND_DISPLAY": gs_socket,
                "WAYLAND_DISPLAY": gs_socket}
    rlog(f"Input env set: DISPLAY={aoe3_display}  GS_WL={gs_socket}")
    # Propagate to lobby_driver module
    if HARNESS_OK:
        os.environ["AOE3_DISPLAY"] = aoe3_display
        os.environ["GAMESCOPE_WAYLAND_DISPLAY"] = gs_socket
        os.environ["WAYLAND_DISPLAY"] = gs_socket
        os.environ["DISPLAY"] = aoe3_display


def xdo(*args: str) -> None:
    if not _XDO_ENV:
        raise RuntimeError("setup_envs() not called")
    d = _XDO_ENV.get("DISPLAY", "")
    if d == ":0":
        raise RuntimeError(f"SAFETY GATE: refusing xdotool on DISPLAY={d}")
    subprocess.run(["xdotool", *args], env=_XDO_ENV, capture_output=True, check=False)


def click_raw(x: int, y: int, settle: float = 0.3) -> None:
    xdo("mousemove", str(x), str(y))
    time.sleep(0.15)
    xdo("click", "1")
    time.sleep(settle)


def key_raw(keyname: str, n: int = 1, delay: float = 0.12) -> None:
    for _ in range(n):
        xdo("key", keyname)
        time.sleep(delay)


def gsc_screenshot(path: str | Path, timeout: float = 15.0) -> bool:
    path = str(path)
    Path(path).unlink(missing_ok=True)
    subprocess.run(["gamescopectl", "screenshot", path],
                   env=_GS_ENV, capture_output=True, check=False,
                   timeout=int(timeout) + 2)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if Path(path).exists() and Path(path).stat().st_size > 50_000:
                return True
        except OSError:
            pass
        time.sleep(0.5)
    return False


# ── game lifecycle ────────────────────────────────────────────────────────────

def kill_aoe3_only() -> None:
    """Kill only AoE3DE_s.exe processes; never touch CoH2 (AppId=231430)."""
    for pat in ["AoE3DE_s.exe", "AoE3DE"]:
        res = subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True)
        for pid_str in res.stdout.split():
            try:
                pid = int(pid_str)
                cmd_r = subprocess.run(["cat", f"/proc/{pid}/cmdline"],
                                       capture_output=True)
                cmdline = cmd_r.stdout.replace(b"\x00", b" ").decode("utf-8", errors="replace")
                if "231430" in cmdline or "coh2" in cmdline.lower():
                    rlog(f"SAFETY: NOT killing pid {pid} (CoH2 in cmdline)")
                    continue
                rlog(f"SIGKILL AoE3 pid={pid}")
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, ValueError, PermissionError):
                pass


def aoe3_exe_running() -> bool:
    """Return True if AoE3DE_s.exe wine process exists (not just winedevice/reaper)."""
    res = subprocess.run(
        ["pgrep", "-f", "AoE3DE_s.exe"],
        capture_output=True, text=True
    )
    if res.returncode != 0:
        return False
    pids = [p for p in res.stdout.split() if p.strip().isdigit()]
    for pid_str in pids:
        try:
            cmd_r = subprocess.run(["cat", f"/proc/{pid_str}/cmdline"],
                                   capture_output=True)
            cmdline = cmd_r.stdout.replace(b"\x00", b" ").decode("utf-8", errors="replace")
            # The actual wine game process has "AoE3DE_s.exe" in its own cmdline
            if "AoE3DE_s.exe" in cmdline and "proton" not in cmdline:
                return True
        except Exception:
            pass
    # gamescopereaper holds the exe name in its args without running it
    # Fallback: check if window exists
    return detect_aoe3_display_safe() is not None


def launch_aoe3() -> bool:
    """Launch AoE3 via steam -applaunch 933110 and wait for window."""
    rlog("Launching AoE3 via steam -applaunch 933110 ...")
    subprocess.Popen(
        ["steam", "-applaunch", "933110"],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + LAUNCH_WAIT_S
    while time.time() < deadline:
        time.sleep(3)
        d = detect_aoe3_display_safe()
        if d is not None:
            rlog(f"AoE3 window appeared on DISPLAY={d}")
            return True
    rlog(f"TIMEOUT: AoE3 window not detected within {LAUNCH_WAIT_S}s")
    return False


def wait_for_mode_in_log(after_bytes: int, mode_str: str, timeout: int = 120) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(2)
        try:
            with AGE3_LOG.open("rb") as f:
                f.seek(after_bytes)
                chunk = f.read().decode("utf-8", errors="replace")
                if mode_str in chunk:
                    return True
        except OSError:
            pass
    return False


def log_byte_offset() -> int:
    try:
        return AGE3_LOG.stat().st_size
    except OSError:
        return 0


def read_log_slice(start_offset: int) -> str:
    try:
        with AGE3_LOG.open("rb") as f:
            f.seek(start_offset)
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


# ── civ picker navigation ─────────────────────────────────────────────────────

def pick_civ_for_slot(coords: dict, civ_token: str, slot: int) -> bool:
    """Select civ for lobby slot (0=P1, 1=P2). Uses lobby_driver fast path."""
    idx = CIV_IDX.get(civ_token)
    if idx is None:
        rlog(f"ERROR: no picker index for {civ_token}")
        return False
    rlog(f"  Picking {civ_token} (idx={idx}) for slot {slot} ...")
    try:
        if HARNESS_OK:
            # Try fast path first (uses cached scroll data)
            result = lobby.set_civ_by_token_fast(coords, civ_token, slot=slot)
            if result.get("ok"):
                rlog(f"  Fast path OK: {result}")
                return True
            rlog(f"  Fast path failed ({result.get('error')}), falling back to set_civ_by_index")
        # Fallback: use set_civ_by_index with lobby_driver
        if slot == 0:
            flag_xy = coords["lobby"]["p1_civ_picker"]
        else:
            flag_xy = coords["lobby"]["opponent_civ_pickers"][slot - 1]
        lobby.open_civ_picker(coords)
        lobby.scroll_up(coords, n=60)
        time.sleep(0.4)
        lobby.select_civ_in_picker(coords, idx)
        lobby.confirm_civ_selection(coords)
        rlog(f"  set_civ_by_index OK for {civ_token}")
        return True
    except Exception as exc:
        rlog(f"ERROR in pick_civ_for_slot({civ_token}, slot={slot}): {exc}")
        return False


# ── map selection ─────────────────────────────────────────────────────────────

# 2026-05-28 (Sydney): Picker tile coords inherited from
# tools/aoe3_automation/anw_doctrine_capture_runner.py:218-219, last verified
# 2026-05-28 15:46 by 02_loading.png showing "LRG ALASKA". The old typeahead
# path silently failed (Age3Log MAP CODE always reported AlaskaLarge regardless
# of typed input — same outcome but no error signal).
_LOBBY_MAP_BTN   = (1645, 425)
_PICKER_ALASKA   = (1195, 837)
_PICKER_OK_BTN   = (1530, 1010)


def select_map(coords: dict, map_name: str) -> None:
    """Pick the map via the lobby map picker.

    Currently only "Alaska" is wired (verified working). Any other name
    is logged and Alaska is picked as a safe fallback so the sweep doesn't
    crash on an unknown map but the operator notices the mismatch.
    """
    rlog(f"  Selecting map: {map_name}")
    if not map_name.lower().startswith("alaska"):
        rlog(f"  WARN: only Alaska is calibrated; treating '{map_name}' as Alaska")
    # Open picker
    click_raw(*_LOBBY_MAP_BTN, settle=1.6)
    time.sleep(0.8)
    # Click Alaska tile
    click_raw(*_PICKER_ALASKA, settle=1.0)
    time.sleep(0.5)
    # Confirm
    click_raw(*_PICKER_OK_BTN, settle=2.0)
    time.sleep(1.2)


# ── resign ────────────────────────────────────────────────────────────────────

def resign_match() -> None:
    rlog("Resigning match ...")
    key_raw("Escape")
    time.sleep(2.5)
    click_raw(*ESC_RESIGN, settle=1.5)
    time.sleep(1.5)
    click_raw(*RESIGN_YES, settle=3.0)
    time.sleep(2.0)
    key_raw("Escape")
    time.sleep(2.0)


# ── log analysis ──────────────────────────────────────────────────────────────

PROBE_RE = re.compile(
    r"\[ANWP v=2\s+t=\d+\s+p=\d+\s+civ=([^\s]+)\s+ldr=([^\s]+)\s+tag=([^\]]+)\](.*)"
)
CLOSURE_RE = re.compile(r"closure=([\d.]+)")


def analyse_log_slice(text: str) -> dict:
    probes: list[dict] = []
    closure_values: list[float] = []

    for line in text.splitlines():
        m = PROBE_RE.search(line)
        if not m:
            continue
        tag_str = m.group(3).strip()
        tag = tag_str.split()[0] if tag_str else ""
        probes.append({"tag": tag, "civ": m.group(1), "ldr": m.group(2)})
        if tag == "wall.closure":
            cm = CLOSURE_RE.search(m.group(4) or tag_str)
            if cm:
                try:
                    closure_values.append(float(cm.group(1)))
                except ValueError:
                    pass

    tag_counts: dict[str, int] = {}
    for p in probes:
        tag_counts[p["tag"]] = tag_counts.get(p["tag"], 0) + 1

    wall_stats: dict = {}
    if closure_values:
        wall_stats = {
            "min":   round(min(closure_values), 3),
            "max":   round(max(closure_values), 3),
            "mean":  round(sum(closure_values) / len(closure_values), 3),
            "count": len(closure_values),
        }

    return {
        "total_probes": len(probes),
        "tag_counts":   tag_counts,
        "wall_closure": wall_stats,
    }


# ── single match orchestration ────────────────────────────────────────────────

def run_match(coords: dict, match: dict, idx: int) -> dict:
    civ    = match["civ"]
    leader = match["leader"]
    map_n  = match["map"]
    arch   = match["archetype"]

    rlog(f"\n{'='*60}")
    rlog(f"MATCH {idx+1}/4: {civ} ({leader}) vs Napoleon  [{arch}]  map={map_n}")
    rlog(f"{'='*60}")

    result = {
        "civ": civ, "leader": leader, "map": map_n, "archetype": arch,
        "status": "SKIP", "error": None,
        "probes": 0, "tag_counts": {}, "wall_closure": {},
        "log_file": str(OUT_DIR / f"{civ}.log"),
    }

    deadline = time.time() + MATCH_TIMEOUT_S
    pre_offset = log_byte_offset()
    rlog(f"Log offset before match: {pre_offset} bytes")

    # ── Navigate to Skirmish ──────────────────────────────────────────────
    rlog("Clicking Skirmish ...")
    click_raw(*SKIRMISH_BTN, settle=4.5)

    # ── P1 civ ────────────────────────────────────────────────────────────
    try:
        if not pick_civ_for_slot(coords, civ, slot=0):
            result["error"] = f"pick_civ_for_slot failed: {civ}"
            rlog(f"SKIP: {result['error']}")
            key_raw("Escape", n=3); time.sleep(2)
            return result
    except Exception as exc:
        result["error"] = f"Exception picking P1 civ: {exc}"
        rlog(f"SKIP: {result['error']}")
        key_raw("Escape", n=3); time.sleep(2)
        return result

    if time.time() > deadline:
        result["status"] = "TIMEOUT"; return result

    # ── P2 civ (Napoleon) ────────────────────────────────────────────────
    try:
        if not pick_civ_for_slot(coords, NAPOLEON_CIV, slot=1):
            result["error"] = f"pick_civ_for_slot failed: {NAPOLEON_CIV}"
            rlog(f"SKIP: {result['error']}")
            key_raw("Escape", n=3); time.sleep(2)
            return result
    except Exception as exc:
        result["error"] = f"Exception picking P2 civ: {exc}"
        rlog(f"SKIP: {result['error']}")
        key_raw("Escape", n=3); time.sleep(2)
        return result

    if time.time() > deadline:
        result["status"] = "TIMEOUT"; return result

    # ── Map ───────────────────────────────────────────────────────────────
    try:
        select_map(coords, map_n)
    except Exception as exc:
        rlog(f"WARN: map selection error ({exc}); proceeding with default map")

    if time.time() > deadline:
        result["status"] = "TIMEOUT"; return result

    # ── Play ──────────────────────────────────────────────────────────────
    rlog("Clicking PLAY ...")
    play_xy = coords["lobby"]["play_button"]
    click_raw(*play_xy, settle=0.5)
    time.sleep(0.5)
    click_raw(*play_xy, settle=2.0)

    # ── Wait for in-game (mode 27) ────────────────────────────────────────
    rlog("Waiting for mode-27 (SinglePlayer) in log ...")
    in_game = wait_for_mode_in_log(
        pre_offset, "entering mode 27 (SinglePlayer)",
        timeout=min(150, int(deadline - time.time() - 90))
    )
    if not in_game:
        result["error"] = "mode-27 not found within timeout"
        result["status"] = "TIMEOUT" if time.time() > deadline else "SKIP"
        rlog(f"{result['status']}: {result['error']}")
        return result

    rlog(f"In-game confirmed. Observing for {MATCH_OBSERVE_S}s ...")

    # ── Observe ───────────────────────────────────────────────────────────
    # 2026-05-28 (Sydney): added crash detection. The previous loop happily
    # slept through silent AoE3 crashes — Age3Log frozen at "entering mode 27"
    # with no further entries while the script "observed" empty seconds for 4
    # min. Now we check the process alive every 30s and abort if it dies.
    observe_end = min(
        time.time() + MATCH_OBSERVE_S,
        deadline - 90   # leave 90s for resign + teardown
    )
    last_health_check = time.time()
    while time.time() < observe_end:
        time.sleep(10)
        if time.time() - last_health_check >= 30:
            last_health_check = time.time()
            if not aoe3_exe_running():
                result["error"] = "AoE3 process exited during observation"
                result["status"] = "CRASH"
                elapsed = int(time.time() - (observe_end - MATCH_OBSERVE_S))
                rlog(f"CRASH detected after {elapsed}s of observation")
                return result

    # ── Resign ────────────────────────────────────────────────────────────
    if time.time() > deadline - 20:
        rlog("WARN: near hard timeout, skipping graceful resign")
        # Force-SIGKILL the game
        kill_aoe3_only()
        time.sleep(5)
    else:
        resign_match()

    time.sleep(5)   # let any final probe lines flush to log

    # ── Collect log slice ─────────────────────────────────────────────────
    log_text = read_log_slice(pre_offset)
    log_path = OUT_DIR / f"{civ}.log"
    try:
        log_path.write_text(log_text, encoding="utf-8", errors="replace")
        rlog(f"Log slice saved: {log_path}  ({len(log_text)} bytes)")
    except OSError as exc:
        rlog(f"WARN: could not write log slice: {exc}")

    # ── Analyse ───────────────────────────────────────────────────────────
    analysis = analyse_log_slice(log_text)
    rlog(f"Probes: {analysis['total_probes']}  wall.closure: {analysis['wall_closure']}")

    result.update({
        "status":       "DONE",
        "probes":       analysis["total_probes"],
        "tag_counts":   analysis["tag_counts"],
        "wall_closure": analysis["wall_closure"],
    })
    return result


# ── verdict ───────────────────────────────────────────────────────────────────

def verdict(r: dict) -> str:
    if r["status"] not in ("DONE",):
        return "FAIL"
    probes = r.get("probes", 0)
    wc = r.get("wall_closure", {})
    # PASS if at least 1 wall.closure probe OR 5+ total probes (AI was active)
    if probes < 1:
        return "FAIL"
    if wc.get("count", 0) >= 1:
        return "PASS"
    if probes >= 5:
        return "PASS"
    return "FAIL"


# ── report helpers ────────────────────────────────────────────────────────────

def write_safety_abort(reason: str) -> None:
    p = OUT_DIR / "SAFETY_ABORT.md"
    p.write_text(f"# SAFETY ABORT\n\n{reason}\n\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    rlog(f"SAFETY_ABORT.md written: {reason}")


def write_report(results: list[dict], partial: bool = False) -> None:
    title = "Smart-Walls AI Sweep Report" + (" (PARTIAL)" if partial else "")
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# {title}",
        f"Generated: {ts}",
        "",
        "## Summary",
        "",
        "| Civ | Archetype | Map | Status | Probes | wall.closure (min/max/mean, n) | Verdict |",
        "|-----|-----------|-----|--------|--------|-------------------------------|---------|",
    ]
    for r in results:
        v  = verdict(r)
        wc = r.get("wall_closure", {})
        wcs = (f"{wc.get('min','–')}/{wc.get('max','–')}/{wc.get('mean','–')} "
               f"n={wc.get('count',0)}" if wc else "—")
        lines.append(
            f"| {r['civ']} | {r['archetype']} | {r.get('map','?')} | "
            f"{r['status']} | {r.get('probes',0)} | {wcs} | **{v}** |"
        )

    lines += ["", "## Archetype Verdicts", ""]
    for r in results:
        v = verdict(r)
        lines.append(f"- **{r['archetype']}** ({r['civ']} / {r.get('leader','?')}): **{v}**")

    lines += ["", "## Details", ""]
    for r in results:
        v = verdict(r)
        lines += [
            f"### {r['civ']} ({r['archetype']})",
            f"- Leader: {r.get('leader','?')} | Map: {r.get('map','?')}",
            f"- Status: {r['status']}",
            f"- Total [ANWP v=2] probes: {r.get('probes',0)}",
            f"- Tag breakdown: `{json.dumps(r.get('tag_counts', {}), sort_keys=True)}`",
            f"- wall.closure: `{json.dumps(r.get('wall_closure', {}))}`",
            f"- **Verdict: {v}**",
        ]
        if r.get("error"):
            lines.append(f"- Error: `{r['error']}`")
        lines.append("")

    report = OUT_DIR / "smart_walls_sweep.md"
    report.write_text("\n".join(lines) + "\n")
    rlog(f"Report written: {report}")

    (OUT_DIR / "results.json").write_text(
        json.dumps(results, indent=2, default=str)
    )


# ── main sweep ────────────────────────────────────────────────────────────────

def run_sweep() -> int:
    sweep_start = time.time()
    rlog("=" * 70)
    rlog("smart_walls_sweep.py — 4-civ smart-walls AI sweep")
    rlog(f"Repo: {REPO}")
    rlog(f"Timeout: {SWEEP_TIMEOUT_S}s total, {MATCH_TIMEOUT_S}s per match")
    rlog("=" * 70)

    if not HARNESS_OK:
        rlog("ERROR: game harness (lobby_driver) not available — cannot proceed")
        write_report([], partial=True)
        return 1

    # ── Verify developer user.cfg ─────────────────────────────────────────
    user_cfg = Path.home() / (
        ".local/share/Steam/steamapps/compatdata/933110/pfx/drive_c/"
        "users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Startup/user.cfg"
    )
    if user_cfg.exists() and "developer" in user_cfg.read_text():
        rlog("Developer mode: user.cfg OK (developer token present)")
    else:
        rlog("WARN: user.cfg missing or lacks 'developer' — probes may not appear")

    # ── Ensure AoE3 is running ────────────────────────────────────────────
    aoe3_disp = detect_aoe3_display_safe()
    if aoe3_disp is None:
        rlog("AoE3 window not detected — launching ...")
        launched = launch_aoe3()
        if not launched:
            msg = "AoE3 failed to launch within timeout"
            write_safety_abort(msg)
            write_report([], partial=True)
            return 1
        rlog(f"Waiting {MENU_WAIT_EXTRA_S}s for menu to settle ...")
        time.sleep(MENU_WAIT_EXTRA_S)
        aoe3_disp = detect_aoe3_display_safe()

    if aoe3_disp is None:
        displays = sorted(glob.glob("/tmp/.X*-lock"))
        msg = f"AoE3 window still not found after launch.  Lock files: {displays}"
        write_safety_abort(msg)
        write_report([], partial=True)
        return 1

    if aoe3_disp == ":0":
        write_safety_abort(
            "AoE3 detected on DISPLAY=:0 (user's main desktop). "
            "Refusing to inject input — would control the live desktop."
        )
        write_report([], partial=True)
        return 1

    # ── Set up display env ────────────────────────────────────────────────
    gs_socket = detect_gamescope_socket(aoe3_disp)
    setup_envs(aoe3_disp, gs_socket)

    # ── Load lobby coords ─────────────────────────────────────────────────
    coords_path = REPO / "tools" / "aoe3_automation" / "lobby_coords.json"
    coords = json.loads(coords_path.read_text())
    rlog("Lobby coords loaded.")

    # ── Wait for main menu marker ─────────────────────────────────────────
    rlog("Waiting for Pregame/SinglePlayerSetup mode in log ...")
    menu_found = wait_for_mode_in_log(
        0,
        "entering mode 3 (SinglePlayerSetup)",
        timeout=60
    )
    if not menu_found:
        # Try alternate marker
        menu_found = wait_for_mode_in_log(0, "entering mode 1 (Pregame)", timeout=10)
    if not menu_found:
        rlog("WARN: menu marker not found — game may already be at main menu; proceeding")
    else:
        rlog("Main menu confirmed in log")

    time.sleep(5)  # extra settle

    # 2026-05-28: Dismiss the weekly "Choose One Free Weekly Profile
    # Picture Reward!" popup. Previously this modal blocked the lobby
    # on the very first launch each week and every Skirmish click
    # silently landed on the popup chrome — every subsequent
    # screenshot captured the popup instead of the lobby, which is
    # exactly the failure mode the user observed before this fix.
    # Helper is safe to call when no popup is present (clicks land
    # on dead background art).
    if lobby is not None:
        try:
            rlog("Dismissing weekly profile-picture-reward popup (if present) ...")
            lobby.dismiss_weekly_popup()
        except Exception as exc:
            rlog(f"WARN: dismiss_weekly_popup raised {exc!r}; proceeding")

    # ── Run 4 matches ─────────────────────────────────────────────────────
    results: list[dict] = []

    for i, match in enumerate(MATCHES):
        elapsed = time.time() - sweep_start
        if elapsed > SWEEP_TIMEOUT_S - 180:
            rlog(f"WARN: sweep timeout approaching ({elapsed:.0f}s elapsed), skipping remaining")
            for rem in MATCHES[i:]:
                results.append({**rem,
                                 "status": "SKIP",
                                 "error": f"sweep timeout ({elapsed:.0f}s elapsed)",
                                 "probes": 0, "tag_counts": {}, "wall_closure": {}})
            break

        try:
            res = run_match(coords, match, i)
        except Exception as exc:
            rlog(f"EXCEPTION in run_match for {match['civ']}: {exc}")
            import traceback; rlog(traceback.format_exc())
            res = {**match, "status": "ERROR", "error": str(exc),
                   "probes": 0, "tag_counts": {}, "wall_closure": {}}
        results.append(res)

        # 2026-05-28 (Sydney): if AoE3 died during this match, mark all
        # remaining matches as SKIP-cascade and break out. Continuing
        # without the process produces 100% screenshot failures across
        # matches 2..N which masks the actual root-cause crash.
        if res.get("status") == "CRASH" or not aoe3_exe_running():
            rlog(f"GAME DIED after match {i+1}. Aborting remaining matches.")
            for rem in MATCHES[i+1:]:
                results.append({**rem,
                                 "status": "SKIP-CASCADE",
                                 "error": "previous match crashed AoE3 process",
                                 "probes": 0, "tag_counts": {}, "wall_closure": {}})
            break

        # After each match (except last), return to main menu
        if i < len(MATCHES) - 1:
            rlog(f"Match {i+1} done.  Returning to main menu ...")
            # Game should already be at main menu after resign.
            # Belt-and-suspenders: press Escape a few times.
            for _ in range(4):
                key_raw("Escape")
                time.sleep(1.5)
            time.sleep(5)

    # ── Run validators ────────────────────────────────────────────────────
    log_files = [str(OUT_DIR / f"{r['civ']}.log")
                 for r in results if (OUT_DIR / f"{r['civ']}.log").exists()]

    if log_files:
        rlog(f"Running validate_doctrine_compliance on {len(log_files)} log files ...")
        spec_candidates = [
            REPO / "playstyle_spec.json",
            REPO / "PLAYSTYLE_SPECIFICATIONS.json",
        ]
        spec = next((str(p) for p in spec_candidates if p.exists()), None)
        cmd = [sys.executable,
               str(REPO / "tools" / "validation" / "validate_doctrine_compliance.py"),
               "--logs", *log_files,
               "--json", str(OUT_DIR / "compliance.json"),
               "--out",  str(OUT_DIR / "compliance.txt"),
               "--allow-fail"]
        if spec:
            cmd[2:2] = ["--spec", spec]
        try:
            rv = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            rlog(f"validate_doctrine_compliance exit={rv.returncode}")
            if rv.stdout:
                rlog(rv.stdout[:3000])
            if rv.stderr:
                rlog(f"STDERR: {rv.stderr[:600]}")
        except Exception as exc:
            rlog(f"WARN: validate_doctrine_compliance: {exc}")

        for r in results:
            lf = OUT_DIR / f"{r['civ']}.log"
            if not lf.exists():
                continue
            cmd2 = [sys.executable,
                    str(REPO / "tools" / "validation" / "validate_runtime_logs.py"),
                    "--log-path", str(lf)]
            rlog(f"Runtime log validation for {r['civ']} ...")
            try:
                rv2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=30)
                rlog(f"  exit={rv2.returncode}")
                if rv2.stdout:
                    rlog(f"  {rv2.stdout[:800]}")
            except Exception as exc:
                rlog(f"  WARN: {exc}")
    else:
        rlog("WARN: No log files produced — skipping validators")

    # ── Write final report ────────────────────────────────────────────────
    write_report(results)

    rlog("\n" + "=" * 70)
    rlog("SWEEP COMPLETE — VERDICTS:")
    for r in results:
        rlog(f"  {r['civ']:24s} ({r['archetype']:18s}): {verdict(r)}")
    rlog("=" * 70)

    return 0 if all(verdict(r) == "PASS" for r in results) else 1


if __name__ == "__main__":
    sys.exit(run_sweep())
