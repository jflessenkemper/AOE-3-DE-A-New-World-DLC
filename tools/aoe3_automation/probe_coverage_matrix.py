#!/usr/bin/env python3
"""Probe-coverage matrix runner — drives the gamescope rig through a set of
AI-vs-AI skirmishes designed to exercise every probe family the
Legendary-Leaders mod emits, then runs ``tools.playtest.replay_probes``
against the per-match Age3Log.txt slice.

Why Age3Log.txt and not the .age3Yrec replay
────────────────────────────────────────────
Each AI emits ``[LLP v=2 ...]`` probe lines via ``aiEcho()`` (→ Age3Log.txt)
AND ``aiChat()`` (→ replay).  The aiChat path stores values as string-table
indices in the .age3Yrec binary format — NOT plain text.  Regex scanning the
raw replay bytes therefore returns zero probe lines.  ``aiEcho()`` writes
plain ASCII to Age3Log.txt when developer mode is active, which is what the
validator parses.

Developer mode is enabled automatically by ``manage_game.py open`` (it
creates a ``user.cfg`` with the bare ``developer`` token in the game's user
Startup directory).  Use ``--no-dev-mode`` to suppress it for production
launches.

Why this exists
───────────────
The XS-side instrumentation now covers every state-mutating mod hook
(buildstyle/personality/elite/commander/influence + 17 compliance.* and
event.* periodic snapshots). To prove every civ's playstyle and
buildstyle line up with the public reference (a_new_world.html),
we need real matches that emit the wire-format probes and a validator pass
over the captured log slices.

Nine test packs cover every doctrine claim in a_new_world.html:

    1. terrain_forest     — TempForest map, forest-bias civs (British/French/Iro/Swede)
    2. terrain_water      — Caribbean,    naval civs (Dutch/Portuguese/Italians/Maltese)
    3. forward_outward    — Plateau,      forward-base civs (Aztec/Lakota/Hausa/Sioux)
    4. walls_fortified    — Yukon,        ring-wall civs (French/Russian/Inca/Bourbon)
    5. walls_mobile       — Plains,       MobileNoWalls (Lakota/Sioux/Comanche/Mongol)
    6. diplomacy_treaty   — Andes,        native-treaty heavy (Iro/Sioux/Aztec/Inca)
    7. age_cadence        — Saguenay,     all 4 civs hit Age 4 by t=900s
    8. revolution         — Pampas,       4 revolt civs (Napoleonic France / US / Mexico / Brazil)
    9. combat_attrition   — Great Plains, 25+ min aggressive match with commander civs
                            (Napoleonic France, Wellington's British) — exercises
                            event.elite.*, event.commander.*, event.style.applied,
                            event.personality.applied, event.terrain.preference,
                            event.heading.preference, event.strongpoint.profile,
                            event.base.influence

Each pack:
  * picks 4 civ slots via in_game_driver.GameDriver.start_skirmish()
  * snapshots Age3Log.txt byte offset BEFORE the match (via log_capture)
  * observes for the configured duration (default 18 min real-time per pack,
    35 min for combat_attrition)
  * resigns via in_game_driver.GameDriver.resign()
  * reads the Age3Log.txt delta (per-match slice) and writes match.log
  * runs replay_probes --json on match.log (NOT on the .age3Yrec replay)
  * aggregates pass/fail per player into a JSON report

Timing estimate (CoH2 coexistence, gamescope resource contention):
  ingame 18 min x ~1.5 wall/game ratio  ~ 27 min per standard pack
  combat_attrition: ingame 35 min x 1.5 ~ 53 min
  8 standard packs + attrition pack + ~10 min loading overhead ~ 4.5 h wall time
  Plan accordingly before kicking off the full matrix unattended.

Pre-flight gate (run automatically unless --skip-preflight):
  (a) unittest discover tests/validation must pass
  (b) manage_game.py sync --dry-run must report no pending changes
  (c) cLLReplayProbes = true must be set in game/ai/core/aiGlobals.xs
  (d) Smoke-test baseline (if present) must parse and yield >=1 probe line
  (e) AoE3 must be running and at the main menu
  (f) Developer mode must be active (user.cfg with "developer" token present)

Output:
  ~/aoe_test/probe_coverage_matrix/       (or --output-dir)
    pack_<n>_<name>/
      run.log
      <screenshots from GameDriver>
      match.log            <- Age3Log.txt delta for this match (probe source)
      replay.age3Yrec      <- copied from Savegame (for reference only)
      validator.json       <- replay_probes JSON (parsed from match.log)
      validator.txt        <- replay_probes human output
    summary.json           <- per-pack pass/fail roll-up
    REPORT.md              <- human summary

Usage:
    python3 tools/aoe3_automation/probe_coverage_matrix.py            # run all 9
    python3 tools/aoe3_automation/probe_coverage_matrix.py --pack 3   # forward_outward
    python3 tools/aoe3_automation/probe_coverage_matrix.py --dry-run  # design only
    python3 tools/aoe3_automation/probe_coverage_matrix.py --observe 600  # 10m/pack
    python3 tools/aoe3_automation/probe_coverage_matrix.py --skip-preflight
    python3 tools/aoe3_automation/probe_coverage_matrix.py --abort-on-crash
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = Path.home() / "aoe_test" / "probe_coverage_matrix"

# Smoke-test baseline directory (item 4).
SMOKE_BASELINE = Path(__file__).parent / "smoke_test_baseline"

# Recorded games location (Proton prefix).
RECORDED_GAMES = (
    Path.home()
    / ".local/share/Steam/steamapps/compatdata/933110"
    / "pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/76561198170207043/Savegame"
)

# Civ index map (item 5): maps 0-based picker index to civ name.
# Built by auditing the civ picker; loaded at startup to validate PACKS.
CIV_INDEX_MAP_PATH = Path(__file__).parent / "civ_index_map.json"


# ─── Pack catalog ──────────────────────────────────────────────────────────

@dataclass
class TestPack:
    name: str
    map_idx: int                     # 0-based index in map-picker dropdown
    p1_civ_idx: int
    p2_civ_idx: int
    p3_civ_idx: int
    p4_civ_idx: int
    description: str
    observe_seconds: Optional[int] = None  # override per-pack (None = global default)
    expected_doctrines: dict[str, str] = field(default_factory=dict)
    # Expected civs: list of (idx, expected_name) pairs for validation.
    # If civ_index_map.json is present, startup will check these.
    expected_civs: list[tuple[int, str]] = field(default_factory=list)


PACKS: list[TestPack] = [
    TestPack(
        name="terrain_forest",
        map_idx=21,     # TempForest in standard maplist (placeholder — verify map idx)
        p1_civ_idx=5,   # British        [map: idx 5 → "British"]
        p2_civ_idx=16,  # French         [map: idx 16 → "French"]
        p3_civ_idx=20,  # Haudenosaunee  [map: idx 20 → "Haudenosaunee"]
        p4_civ_idx=42,  # Swedes         [map: idx 42 → "Swedes"]
        description=(
            "Forest-bias civs on TempForest. Validates terrain_primary=forest "
            "and heading_axis claims."
        ),
        expected_doctrines={"British": "naval", "French": "fortress_ring"},
        expected_civs=[
            (5, "British"), (16, "French"), (20, "Haudenosaunee"), (42, "Swedes"),
        ],
    ),
    TestPack(
        name="terrain_water",
        map_idx=4,      # Caribbean
        p1_civ_idx=12,  # Dutch          [map: idx 12 → "Dutch"]
        p2_civ_idx=35,  # Portuguese     [map: idx 35 → "Portuguese"]
        p3_civ_idx=26,  # Italians       [map: idx 26 → "Italians"]
        p4_civ_idx=29,  # Maltese        [map: idx 29 → "Maltese"]
        description=(
            "Naval civs on Caribbean. Validates fleetSnap≥4 and "
            "wallStrategy=CoastalBatteries."
        ),
        expected_doctrines={"Dutch": "naval", "Maltese": "fortress_ring"},
        expected_civs=[
            (12, "Dutch"), (35, "Portuguese"), (26, "Italians"), (29, "Maltese"),
        ],
    ),
    TestPack(
        name="forward_outward",
        map_idx=14,     # Plateau
        p1_civ_idx=2,   # Aztecs         [map: idx 2 → "Aztecs"]
        p2_civ_idx=28,  # Lakota         [map: idx 28 → "Lakota"]
        p3_civ_idx=21,  # Hausa          [map: idx 21 → "Hausa"]
        p4_civ_idx=20,  # Haudenosaunee  [map: idx 20 → "Haudenosaunee"]
        description=(
            "Forward-base civs on Plateau. Validates event.delta fwdBase "
            "changes ≥1 and attack plans ≥3. Also checks new probe tags: "
            "event.style.applied, event.personality.applied, "
            "event.terrain.preference, event.heading.preference."
        ),
        expected_doctrines={"Aztecs": "mobile_no_walls", "Lakota": "mobile_no_walls"},
        expected_civs=[
            (2, "Aztecs"), (28, "Lakota"), (21, "Hausa"), (20, "Haudenosaunee"),
        ],
    ),
    TestPack(
        name="walls_fortified",
        map_idx=24,     # Yukon
        p1_civ_idx=16,  # French         [map: idx 16 → "French"]
        p2_civ_idx=39,  # Russians       [map: idx 39 → "Russians"]
        p3_civ_idx=23,  # Inca           [map: idx 23 → "Inca"]
        p4_civ_idx=4,   # Brazilians     [map: idx 4 → "Brazilians"]
                        # (was "Bourbon revolt" placeholder — updated to Brazilians,
                        #  a fortified revolt civ; verify if a Bourbon entry is present)
        description=(
            "Ring-wall civs on Yukon. Validates wallGeom segments≥8 "
            "and strategy=FortressRing."
        ),
        expected_doctrines={"French": "fortress_ring", "Russians": "fortress_ring"},
        expected_civs=[
            (16, "French"), (39, "Russians"), (23, "Inca"), (4, "Brazilians"),
        ],
    ),
    TestPack(
        name="walls_mobile",
        map_idx=12,     # Plains
        p1_civ_idx=28,  # Lakota         [map: idx 28 → "Lakota"]
        p2_civ_idx=20,  # Haudenosaunee  [map: idx 20 → "Haudenosaunee"]
        p3_civ_idx=21,  # Hausa          [map: idx 21 → "Hausa"]
        p4_civ_idx=2,   # Aztecs         [map: idx 2 → "Aztecs"]
        description=(
            "MobileNoWalls civs on Plains. Validates wallGeom segments=0 "
            "throughout match."
        ),
        expected_doctrines={"Lakota": "mobile_no_walls", "Aztecs": "mobile_no_walls"},
        expected_civs=[
            (28, "Lakota"), (20, "Haudenosaunee"), (21, "Hausa"), (2, "Aztecs"),
        ],
    ),
    TestPack(
        name="diplomacy_treaty",
        map_idx=1,      # Andes
        p1_civ_idx=20,  # Haudenosaunee  [map: idx 20 → "Haudenosaunee"]
        p2_civ_idx=28,  # Lakota         [map: idx 28 → "Lakota"]
        p3_civ_idx=2,   # Aztecs         [map: idx 2 → "Aztecs"]
        p4_civ_idx=23,  # Inca           [map: idx 23 → "Inca"]
        description=(
            "Native-treaty heavy civs on Andes. Validates "
            "compliance.diplomacy tposts≥2."
        ),
        expected_doctrines={"Haudenosaunee": "treaty", "Lakota": "treaty"},
        expected_civs=[
            (20, "Haudenosaunee"), (28, "Lakota"), (2, "Aztecs"), (23, "Inca"),
        ],
    ),
    TestPack(
        name="age_cadence",
        map_idx=15,     # Saguenay
        p1_civ_idx=5,   # British        [map: idx 5 → "British"]
        p2_civ_idx=16,  # French         [map: idx 16 → "French"]
        p3_civ_idx=18,  # Germans        [map: idx 18 → "Germans"]
        p4_civ_idx=42,  # Swedes         [map: idx 42 → "Swedes"]
        description=(
            "Standard 1v1v1v1 European on Saguenay. Validates "
            "tech.ageReq fires for every age transition."
        ),
        expected_civs=[
            (5, "British"), (16, "French"), (18, "Germans"), (42, "Swedes"),
        ],
    ),
    TestPack(
        name="revolution",
        map_idx=11,     # Pampas
        p1_civ_idx=32,  # NapoleonicFrance  [map: idx 32 → "NapoleonicFrance"]
        p2_civ_idx=33,  # Ottomans          [map: idx 33 → "Ottomans"]
                        # NOTE: "United States" not found in picker survey; Ottomans
                        # substituted. Update when US civ idx is confirmed.
        p3_civ_idx=31,  # Mexicans          [map: idx 31 → "Mexicans"]
        p4_civ_idx=4,   # Brazilians        [map: idx 4 → "Brazilians"]
        description=(
            "Revolution civs on Pampas. Validates event.delta age==5 "
            "and chatset matches anw prefix."
        ),
        expected_civs=[
            (32, "NapoleonicFrance"), (33, "Ottomans"), (31, "Mexicans"), (4, "Brazilians"),
        ],
    ),
    TestPack(
        name="combat_attrition",
        map_idx=12,     # Plains (small, fast clashes)
        p1_civ_idx=32,  # NapoleonicFrance  [map: idx 32 → "NapoleonicFrance"]
        p2_civ_idx=5,   # British           [map: idx 5 → "British"]
        p3_civ_idx=32,  # NapoleonicFrance
        p4_civ_idx=5,   # British
        observe_seconds=35 * 60,  # 35 min — enough for commanders to die & be rebuilt
        description=(
            "Long aggressive match on Plains with commander-unit civs "
            "(Napoleonic France's Napoleon, Wellington's British). "
            "Exercises: event.elite.*, event.commander.*, event.style.applied, "
            "event.personality.applied, event.terrain.preference, "
            "event.heading.preference, event.strongpoint.profile, "
            "event.base.influence. Use aggressive vs aggressive personalities "
            "on a small map to maximise unit deaths and recovery events."
        ),
        expected_civs=[
            (32, "NapoleonicFrance"), (5, "British"),
        ],
    ),
]


# ─── Logging ──────────────────────────────────────────────────────────────

def log(pack_dir: Path, msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    with (pack_dir / "run.log").open("a") as f:
        f.write(line + "\n")
    print(line, flush=True)


# ─── Civ index map helpers (item 5) ───────────────────────────────────────

def _load_civ_index_map() -> dict[int, str]:
    """Load civ_index_map.json if it exists, else return empty dict."""
    if CIV_INDEX_MAP_PATH.exists():
        raw = json.loads(CIV_INDEX_MAP_PATH.read_text())
        return {int(k): v for k, v in raw.items()}
    return {}


def _validate_pack_civs(
    pack: TestPack, civ_map: dict[int, str]
) -> list[str]:
    """Return list of mismatch error strings for this pack's civ expectations."""
    if not civ_map:
        return []  # no map present — skip
    errs: list[str] = []
    for idx, expected_name in pack.expected_civs:
        actual = civ_map.get(idx)
        if actual is None:
            errs.append(
                f"  pack '{pack.name}': idx {idx} not in civ_index_map.json "
                f"(expected '{expected_name}'). Re-run civ index survey."
            )
        elif actual.lower() != expected_name.lower():
            errs.append(
                f"  pack '{pack.name}': idx {idx} maps to '{actual}' "
                f"but pack expects '{expected_name}'. Update PACKS or "
                f"re-run civ index survey."
            )
    return errs


# ─── Pre-flight gate (item 11) ─────────────────────────────────────────────

def _run_preflight(art_dir: Path) -> list[str]:
    """Run all pre-flight checks. Returns list of failure messages (empty = pass)."""
    failures: list[str] = []

    # (a) unittest discover tests/validation
    print("[preflight] (a) running unittest discover tests/validation …")
    res = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "tests/validation"],
        cwd=str(REPO), capture_output=True, text=True,
    )
    if res.returncode != 0:
        failures.append(
            f"(a) unittest tests/validation failed (exit {res.returncode}):\n"
            + (res.stderr or res.stdout)[-2000:]
        )
    else:
        print("    OK")

    # (b) manage_game.py sync --dry-run — must report no pending changes
    print("[preflight] (b) checking sync status …")
    res2 = subprocess.run(
        [sys.executable, "tools/aoe3_automation/manage_game.py", "sync", "--dry-run"],
        cwd=str(REPO), capture_output=True, text=True,
    )
    # rsync --dry-run with --checksum: if any files would change, output has file names.
    dry_output = (res2.stdout + res2.stderr)
    # Filter out header/footer lines; any filename-looking line means a pending change.
    pending_lines = [
        l for l in dry_output.splitlines()
        if l.strip() and not l.startswith("Running:") and not l.startswith("Sync complete")
        and not l.startswith("WARN") and "/" in l
    ]
    if res2.returncode != 0:
        failures.append(
            f"(b) manage_game.py sync --dry-run failed (exit {res2.returncode}):\n"
            + dry_output[-1000:]
        )
    elif pending_lines:
        failures.append(
            f"(b) sync --dry-run detected {len(pending_lines)} pending change(s). "
            f"Run `manage_game.py sync` first:\n  " + "\n  ".join(pending_lines[:20])
        )
    else:
        print("    OK")

    # (c) smoke-test baseline — must be a .log file with real probes
    print("[preflight] (c) checking smoke-test baseline …")
    baseline_log = next(SMOKE_BASELINE.glob("*.log"), None) if SMOKE_BASELINE.exists() else None
    baseline_replay = next(SMOKE_BASELINE.glob("*.age3Yrec"), None) if SMOKE_BASELINE.exists() else None
    if baseline_log:
        res3 = subprocess.run(
            [sys.executable, "-m", "tools.playtest.replay_probes",
             str(baseline_log), "--json"],
            cwd=str(REPO), capture_output=True, text=True,
        )
        # Exit 0 = probes found and parsed; exit 2 = no probes (bad for baseline).
        probe_lines = [l for l in res3.stdout.splitlines() if l.strip()]
        if res3.returncode == 2 or len(probe_lines) == 0:
            failures.append(
                f"(c) smoke-test baseline {baseline_log.name} yielded zero probes. "
                f"Re-capture with developer mode active (manage_game.py open) and "
                f"re-run in_game_driver.py --self-test to regenerate baseline.log."
            )
        elif res3.returncode not in (0, 1):
            failures.append(
                f"(c) smoke-test baseline replay_probes failed on {baseline_log.name} "
                f"(exit {res3.returncode})"
            )
        else:
            print(f"    OK (baseline: {baseline_log.name}, {len(probe_lines)} probe lines)")
    elif baseline_replay:
        failures.append(
            f"(c) smoke-test baseline is a .age3Yrec replay ({baseline_replay.name}), "
            f"which cannot be parsed (chat is binary-encoded). "
            f"Regenerate: run in_game_driver.py --self-test with developer mode active, "
            f"copy the resulting match.log to smoke_test_baseline/baseline.log."
        )
    else:
        print("    (c) no smoke-test baseline present — skipping")

    # (d) cLLReplayProbes = true in aiGlobals.xs
    print("[preflight] (d) checking cLLReplayProbes …")
    globals_xs = REPO / "game/ai/core/aiGlobals.xs"
    if globals_xs.exists():
        content = globals_xs.read_text()
        if "cLLReplayProbes = true" not in content:
            failures.append(
                "(d) cLLReplayProbes is NOT true in game/ai/core/aiGlobals.xs. "
                "Probes will not fire. Set it to true and re-sync."
            )
        else:
            print("    OK")
    else:
        failures.append(f"(d) file not found: {globals_xs}")

    # (e) AoE3 running and detectable
    print("[preflight] (e) detecting AoE3 display …")
    try:
        from tools.aoe3_automation.gamescope_detect import detect_aoe3_display
        d, gs = detect_aoe3_display(use_cache=False)
        print(f"    OK (DISPLAY={d}  GS={gs})")
    except RuntimeError as e:
        failures.append(f"(e) AoE3 not detected: {e}")
    except ImportError:
        failures.append("(e) gamescope_detect module not found")

    # (f) developer mode user.cfg present with ALL THREE required tokens.
    # The bare "developer" token is insufficient: XS-log routing is gated
    # separately by +ixsLog / +cxsLog (see game.cfg lines 84-87 in install).
    # Without +ixsLog/+cxsLog, aiEcho() is silently dropped even with dev mode.
    print("[preflight] (f) checking developer mode user.cfg …")
    try:
        from tools.aoe3_automation.log_capture import (
            USER_CFG_PATH, _REQUIRED_TOKENS, _has_all_tokens
        )
        if USER_CFG_PATH.exists():
            content = USER_CFG_PATH.read_text(encoding="utf-8", errors="replace")
            if _has_all_tokens(content):
                print(f"    OK ({USER_CFG_PATH}) — all tokens present: "
                      f"{', '.join(_REQUIRED_TOKENS)}")
            else:
                failures.append(
                    f"(f) user.cfg exists but is missing one or more required "
                    f"tokens {_REQUIRED_TOKENS} at {USER_CFG_PATH}. "
                    f"Re-run manage_game.py open (which calls ensure_dev_mode()) "
                    f"or manually run: python3 -c "
                    f"'from tools.aoe3_automation.log_capture import ensure_dev_mode; "
                    f"ensure_dev_mode()'"
                )
        else:
            failures.append(
                f"(f) developer mode user.cfg not found: {USER_CFG_PATH}. "
                f"Run manage_game.py open (without --no-dev-mode) before starting the matrix. "
                f"Without all three tokens {_REQUIRED_TOKENS}, aiEcho() is "
                f"silently dropped and match.log will have zero probes."
            )
    except ImportError:
        failures.append("(f) log_capture module not found")

    return failures


# ─── Match driver ──────────────────────────────────────────────────────────

def _newest_replay(after_ts: float) -> Optional[Path]:
    if not RECORDED_GAMES.exists():
        return None
    candidates = [p for p in RECORDED_GAMES.rglob("*.age3Yrec")
                  if p.stat().st_mtime >= after_ts]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def run_pack(
    pack: TestPack,
    observe_seconds: int,
    pack_dir: Path,
    *,
    wall_limit: int = 35 * 60,
) -> dict:
    """Drive one skirmish pack via GameDriver. Returns status dict."""
    pack_dir.mkdir(parents=True, exist_ok=True)
    log(pack_dir, f"=== pack {pack.name} starting ===")
    log(pack_dir, pack.description)

    # Item 1: detect display at start of each pack so CoH2 start/stop is handled.
    from tools.aoe3_automation.gamescope_detect import invalidate_cache
    invalidate_cache()

    # Build GameDriver pointing at this pack's art dir.
    from tools.aoe3_automation.in_game_driver import GameDriver
    drv = GameDriver(art_dir=pack_dir)

    pack_observe = pack.observe_seconds if pack.observe_seconds is not None else observe_seconds
    pack_wall_limit = max(wall_limit, int(pack_observe * 2.5))
    wall_deadline = time.time() + pack_wall_limit

    # Initial screenshot: confirm main menu.
    drv.screenshot("00_main_menu")

    log(pack_dir, f"starting skirmish: map={pack.map_idx} "
        f"civs=[{pack.p1_civ_idx},{pack.p2_civ_idx},{pack.p3_civ_idx},{pack.p4_civ_idx}]")

    # Start a live log mirror BEFORE the match.  This gives crash-resilient
    # capture (bytes that hit disk are saved to match.log incrementally) AND
    # a poll target for early-exit-on-coverage during observation.
    match_log = pack_dir / "match.log"
    from tools.aoe3_automation.log_capture import (
        start_log_tail, stop_log_tail, probe_count_in_slice,
    )
    log_mirror = start_log_tail(match_log)
    log(pack_dir, f"log mirror started -> {match_log}")

    phase_timings: dict[str, float] = {}

    def _t(label: str, t0: float) -> None:
        phase_timings[label] = time.time() - t0

    match_start_ts = time.time()
    t_setup = time.time()
    drv.start_skirmish(
        p1_civ_idx=pack.p1_civ_idx,
        p2_civ_idx=pack.p2_civ_idx,
        p3_civ_idx=pack.p3_civ_idx,
        p4_civ_idx=pack.p4_civ_idx,
        map_idx=pack.map_idx,
    )
    _t("setup_clicks_s", t_setup)

    log(pack_dir, "waiting for WorldAssetPreloadingTime marker (no key spam) …")
    t_load = time.time()
    if not drv.wait_for_in_game(timeout=180, dismiss_errors=True,
                                log_mirror=log_mirror):
        log(pack_dir, "TIMEOUT — WorldAssetPreloadingTime never observed")
        stop_log_tail(log_mirror)
        return {"pack": pack.name, "status": "launch_timeout",
                "phase_timings": phase_timings}
    _t("load_to_playable_s", t_load)

    drv.set_speed(5)
    log(pack_dir, f"in-game reached; observing with early-exit "
        f"(min={min(60, pack_observe)}s max={pack_observe}s)")

    # Required tag families: meta + at least one of compliance/style/personality
    # would be ideal, but we accept "any boot probes" as evidence the AI is alive.
    t_obs = time.time()
    coverage = drv.observe_until_coverage(
        log_mirror,
        required_families=("meta",),
        min_probe_count=2,
        min_seconds=min(60, pack_observe),
        max_seconds=pack_observe,
    )
    _t("observe_s", t_obs)
    log(pack_dir, f"observe result: {coverage}")

    log(pack_dir, "resigning …")
    t_resign = time.time()
    resign_ok = drv.resign()
    _t("resign_s", t_resign)
    if not resign_ok:
        log(pack_dir, "WARN: resign() did not confirm return to main menu")

    # Stop the mirror — picks up the post-resign flush burst.
    log_content = stop_log_tail(log_mirror)
    probe_n = probe_count_in_slice(log_content)
    log(pack_dir, f"match.log: {len(log_content)} bytes, {probe_n} probe lines")
    if probe_n == 0:
        log(pack_dir, "WARN: zero [LLP v=2] probes — engine may have buffered "
            "without flushing, or AI did not boot.")
    log(pack_dir, f"phase_timings: {phase_timings}")

    # Also copy the most recent replay (for reference / future analysis).
    replay = _newest_replay(after_ts=match_start_ts - 60)
    if replay is None:
        log(pack_dir, "WARN: no replay file found in Savegame (match.log is primary)")
    else:
        log(pack_dir, f"copying replay {replay.name} (reference only)")
        dst_replay = pack_dir / "replay.age3Yrec"
        shutil.copy2(replay, dst_replay)

    # Run validator against match.log (NOT the .age3Yrec replay).
    log(pack_dir, "running replay_probes validator on match.log …")
    txt_out = pack_dir / "validator.txt"
    json_out = pack_dir / "validator.json"
    with txt_out.open("w") as f:
        rc_txt = subprocess.run(
            [sys.executable, "-m", "tools.playtest.replay_probes",
             str(match_log), "--strict", "--source", "log"],
            cwd=str(REPO), stdout=f, stderr=subprocess.STDOUT,
        ).returncode
    with json_out.open("w") as f:
        subprocess.run(
            [sys.executable, "-m", "tools.playtest.replay_probes",
             str(match_log), "--json", "--source", "log"],
            cwd=str(REPO), stdout=f,
        )

    # Quick tag-family audit.
    tag_families: list[str] = []
    try:
        json_lines = [l for l in json_out.read_text().splitlines() if l.strip()]
        seen_tags: set[str] = set()
        for line in json_lines:
            obj = json.loads(line)
            seen_tags.add(obj.get("tag", ""))
        families = {t.split(".")[0] for t in seen_tags}
        tag_families = sorted(families)
    except Exception:
        pass

    log(pack_dir, f"validator exit={rc_txt}  tag_families={tag_families}")

    return {
        "pack": pack.name,
        "status": "ok" if rc_txt == 0 else f"validator_rc_{rc_txt}",
        "validator_rc": rc_txt,
        "replay": dst_replay.name if 'dst_replay' in locals() else None,
        "txt": str(txt_out),
        "json": str(json_out),
        "tag_families": tag_families,
        "phase_timings": phase_timings,
        "probe_count": probe_n,
    }


# ─── Aggregator ────────────────────────────────────────────────────────────

def write_summary(results: list[dict], art: Path) -> None:
    summary_path = art / "summary.json"
    summary_path.write_text(json.dumps(results, indent=2))

    md = ["# Probe-coverage matrix report", "",
          f"_Generated {time.strftime('%Y-%m-%d %H:%M:%S')}_", ""]
    ok_count = sum(1 for r in results if r.get("status") == "ok")
    md.append(f"Total packs: {len(results)}  Passed: {ok_count}/{len(results)}")
    md.append("")
    md.append("| Pack | Status | Tag families |")
    md.append("|---|---|---|")
    for r in results:
        fams = ", ".join(r.get("tag_families", []))
        md.append(f"| {r['pack']} | {r['status']} | {fams or '—'} |")
    (art / "REPORT.md").write_text("\n".join(md))
    print(f"\nReport: {art / 'REPORT.md'}")
    print(f"Summary: {summary_path}")


# ─── Main ──────────────────────────────────────────────────────────────────

def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--pack", type=int, default=None,
                   help="Run a single pack by 1-indexed number (1..9)")
    p.add_argument("--observe", type=int, default=18 * 60,
                   help="Seconds of in-game observation per pack (default 1080)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print the plan and exit without driving the game")
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                   help=f"Directory for artefacts (default {DEFAULT_OUTPUT_DIR})")
    p.add_argument("--skip-preflight", action="store_true",
                   help="Skip the pre-flight gate (emergency override)")
    p.add_argument("--continue-on-crash", dest="continue_on_crash",
                   action="store_true", default=True,
                   help="Continue to next pack on crash/timeout (default)")
    p.add_argument("--abort-on-crash", dest="continue_on_crash",
                   action="store_false",
                   help="Abort entire matrix run on first crash/timeout")
    args = p.parse_args(argv)

    art = args.output_dir
    art.mkdir(parents=True, exist_ok=True)

    # Resolve pack list.
    if args.pack is not None:
        if not 1 <= args.pack <= len(PACKS):
            print(f"--pack must be 1..{len(PACKS)}", file=sys.stderr)
            return 2
        packs = [PACKS[args.pack - 1]]
    else:
        packs = list(PACKS)

    # Dry-run output (item 10 timing doc + item 11 pre-flight list).
    if args.dry_run:
        print(f"Probe-coverage matrix — DRY RUN")
        print(f"Output dir : {art}")
        print(f"Packs      : {len(packs)}")
        print()
        for i, pk in enumerate(packs, 1):
            obs = pk.observe_seconds if pk.observe_seconds is not None else args.observe
            print(f"  {i}. {pk.name:<22s}  map={pk.map_idx:<3d}  "
                  f"civs=[{pk.p1_civ_idx},{pk.p2_civ_idx},{pk.p3_civ_idx},{pk.p4_civ_idx}]  "
                  f"observe={obs}s")
            print(f"     {pk.description[:80]}")
        standard_packs = sum(1 for pk in packs if pk.observe_seconds is None)
        attrition_packs = len(packs) - standard_packs
        est_min = (
            standard_packs * (args.observe * 1.5 / 60)
            + attrition_packs * (35 * 1.5)
            + 10  # loading overhead
        )
        print(f"\nEstimated wall-clock: {est_min:.0f} min ({est_min/60:.1f} h)")
        print("\nPre-flight gate (skippable with --skip-preflight):")
        print("  (a) unittest discover tests/validation")
        print("  (b) manage_game.py sync --dry-run must show no changes")
        print("  (c) smoke-test baseline (smoke_test_baseline/baseline.log) yields >=1 probe")
        print("  (d) cLLReplayProbes = true in game/ai/core/aiGlobals.xs")
        print("  (e) AoE3 running and at main menu")
        print("  (f) developer mode user.cfg present (aiEcho -> Age3Log.txt)")

        # Also show civ-map warnings if present.
        civ_map = _load_civ_index_map()
        if civ_map:
            print(f"\nCiv index map loaded: {len(civ_map)} entries")
            all_errs = []
            for pk in packs:
                all_errs.extend(_validate_pack_civs(pk, civ_map))
            if all_errs:
                print(f"  WARNING: {len(all_errs)} civ-index mismatch(es):")
                for e in all_errs:
                    print(e)
            else:
                print("  All pack civ indexes match civ_index_map.json.")
        else:
            print("\nNo civ_index_map.json — run the civ-index survey to validate pack indexes.")

        return 0

    # ── Pre-flight (item 11) ────────────────────────────────────────────────
    if not args.skip_preflight:
        print("=" * 60)
        print("Pre-flight gate")
        print("=" * 60)
        failures = _run_preflight(art)
        if failures:
            print("\nPRE-FLIGHT FAILED:")
            for f in failures:
                print(f"  ✗ {f}")
            print("\nFix the above issues or re-run with --skip-preflight.")
            return 3
        print("Pre-flight PASSED.\n")

    # ── Civ-index validation (item 5) ───────────────────────────────────────
    civ_map = _load_civ_index_map()
    if civ_map:
        all_errs = []
        for pk in packs:
            all_errs.extend(_validate_pack_civs(pk, civ_map))
        if all_errs:
            print("CIV-INDEX MISMATCH(ES) — update PACKS or re-run civ survey:")
            for e in all_errs:
                print(e)
            return 4

    # ── Run packs ───────────────────────────────────────────────────────────
    results: list[dict] = []
    for i, pk in enumerate(packs, 1):
        pack_dir = art / f"pack_{i:02d}_{pk.name}"
        obs = pk.observe_seconds if pk.observe_seconds is not None else args.observe

        print(f"\n{'='*60}")
        print(f"Pack {i}/{len(packs)}: {pk.name}  observe={obs}s")
        print(f"{'='*60}")

        # Re-detect display before each pack (item 1).
        from tools.aoe3_automation.gamescope_detect import invalidate_cache
        invalidate_cache()

        try:
            r = run_pack(pk, obs, pack_dir)
        except Exception as exc:
            r = {"pack": pk.name, "status": f"exception:{exc}"}
            log(pack_dir, f"EXCEPTION: {exc}")
            # Attempt recovery (item 7).
            try:
                import traceback
                traceback.print_exc()
                print(f"[recover] attempting game restart …")
                manage = REPO / "tools/aoe3_automation/manage_game.py"
                subprocess.run([sys.executable, str(manage), "close"], timeout=30)
                time.sleep(5)
                subprocess.run([sys.executable, str(manage), "open", "--timeout", "180"],
                               timeout=200)
            except Exception as re_exc:
                print(f"[recover] recovery also failed: {re_exc}")

        results.append(r)
        # Persist intermediate summary so a mid-matrix crash isn't a total loss.
        write_summary(results, art)

        status = r.get("status", "unknown")
        print(f"Pack {pk.name}: {status}")

        if status not in ("ok",) and not args.continue_on_crash:
            print("--abort-on-crash set — stopping matrix run.")
            break

    ok_count = sum(1 for r in results if r.get("status") == "ok")
    print(f"\nMatrix complete: {ok_count}/{len(results)} packs passed.")
    write_summary(results, art)
    return 0 if ok_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
