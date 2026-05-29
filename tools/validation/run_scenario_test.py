#!/usr/bin/env python3
"""Orchestrate a single end-to-end AI test session using the ANEWWORLD scenario.

Why this exists
---------------
AoE3 DE's 46 ANW AIs write posture snapshots into
``Game/AI/<leader>.personality`` files via ``aiPersonalitySetPlayerUserVar()``.
The validator ``tools/validation/validate_personality_vs_spec.py`` reads those
files and produces PASS/FAIL per civ.  But running a full session by hand is
tedious: you have to stage the scenario file, launch Steam, watch for new
writes, then invoke the validator.  This script automates all of that —
*except* the menu navigation (Steam has no public CLI to auto-load a custom
scenario, and cursor-automation tools are off-limits per project policy).

Typical usage
-------------
::

    # From repo root:
    python3 tools/validation/run_scenario_test.py
    # Follow on-screen instructions (click Custom Maps → ANEWWORLD).

    # Skip launching the game (already running):
    python3 tools/validation/run_scenario_test.py --no-launch

    # Quick smoke-test (no game, --timeout 0 exits immediately after baseline):
    python3 tools/validation/run_scenario_test.py --no-launch --timeout 0

    # Per-match civ rebinding — re-emit ANEWWORLD.age3Yscn with a fresh
    # 8-civ slate before staging. Bypasses the lobby-picker entirely;
    # whichever 8 civs are in the slate are pre-bound to slots 1..8.
    #
    # Pick 8 civs at random from the 40-civ ANW roster:
    python3 tools/validation/run_scenario_test.py --randomize --seed 42
    #
    # Pin P1 (human) and randomize the 7 AI opponents:
    python3 tools/validation/run_scenario_test.py --p1-civ ANWBritish
    #
    # Explicit slate (must be exactly 8 comma-separated tokens, P1..P8):
    python3 tools/validation/run_scenario_test.py --civs \\
        ANWBritish,ANWFrench,ANWGermans,ANWSpanish,ANWDutch,ANWPortuguese,ANWOttomans,ANWRussians

Exit codes
----------
0  At least one fresh probe captured AND validator returned 0 (all PASS).
1  Fresh probes captured but validator returned non-zero (at least one FAIL).
2  Timeout reached with no fresh probes at all (pipeline broken / no match).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Repo / path constants
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.playtest.probes_from_replay import (  # noqa: E402
    PERSONALITY_DIR,
    PersonalityProbe,
    WALL_STRATEGY_NAMES,
    scan_personality_dir,
)

# Source scenario (relative to repo root).
SCENARIO_SRC = REPO_ROOT / "Scenario" / "ANEWWORLD.age3Yscn"

# Primary in-game Scenario destination (the engine reads from here).
SCENARIO_DST_GAME = (
    Path.home()
    / ".local/share/Steam/steamapps/compatdata/933110"
    / "pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE"
    / "76561198170207043/Scenario/ANEWWORLD.age3Yscn"
)

# Steam Cloud staging destination (makes the map appear in the lobby).
SCENARIO_DST_CLOUD = (
    Path.home()
    / ".local/share/Steam/userdata/209941315/933110/remote"
    / "scenario@ANEWWORLD.age3Yscn"
)

# Validator script.
VALIDATOR = REPO_ROOT / "tools/validation/validate_personality_vs_spec.py"

# Validator output JSON.
VALIDATOR_JSON = REPO_ROOT / "artifacts/validation/personality_compliance.json"

# Steam app ID for AoE3 DE.
AOEIII_STEAM_ID = "933110"

# How often to poll the personality dir (seconds).
POLL_INTERVAL = 5

# After the FIRST fresh write appears, exit early if no new writes for this
# many seconds (heuristic: the match has ended).
QUIET_AFTER_FIRST_WRITE_SECS = 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    """Return hex SHA-256 of a file (for idempotent copy check)."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _format_elapsed(seconds: float) -> str:
    """Format seconds as [H:MM:SS]."""
    s = int(seconds)
    h, remainder = divmod(s, 3600)
    m, sec = divmod(remainder, 60)
    if h:
        return f"[{h}:{m:02d}:{sec:02d}]"
    return f"[{m}:{sec:02d}]"


def _probe_summary(p: PersonalityProbe) -> str:
    """One-line summary of a PersonalityProbe for live output."""
    ws_name = WALL_STRATEGY_NAMES.get(p.wall_strategy, f"ws_{p.wall_strategy}")
    return (
        f"{p.leader_key}: match_ms={p.match_ms}"
        f" ws={ws_name}({p.wall_strategy})"
        f" bs={p.build_style_name}({p.style})"
        f" age={p.age} score={p.score}"
    )


# ---------------------------------------------------------------------------
# Baseline snapshot
# ---------------------------------------------------------------------------

def build_baseline(personality_dir: Path) -> dict[str, tuple[float, int]]:
    """Return {stem: (mtime, match_ms)} for every probe file currently on disk.

    Files without probe data are still recorded with match_ms=0 so we can
    detect *any* write to them.
    """
    baseline: dict[str, tuple[float, int]] = {}
    if not personality_dir.exists():
        return baseline

    for path in sorted(personality_dir.glob("*.personality")):
        mtime = path.stat().st_mtime
        # Try to decode probe data; fall back to match_ms=0 if absent.
        match_ms = 0
        try:
            from tools.playtest.probes_from_replay import parse_personality_file
            p = parse_personality_file(path)
            if p is not None:
                match_ms = p.match_ms
        except Exception:
            pass
        baseline[path.stem] = (mtime, match_ms)
    return baseline


def print_baseline_summary(baseline: dict[str, tuple[float, int]],
                           all_probes: list[PersonalityProbe]) -> None:
    """Print a one-line summary of the current baseline state."""
    probe_map = {p.leader_key: p for p in all_probes}
    prior_data = sum(1 for stem in baseline if probe_map.get(stem) is not None)
    no_data = sum(1 for stem in baseline if probe_map.get(stem) is None)
    # We don't have FAIL info here without running the validator — keep it
    # simple; just count what has probe data vs not.
    total = len(baseline)
    print(f"Baseline: {prior_data} civs with prior data, "
          f"{no_data} NO_DATA across {total} files — "
          "will report only fresh activity")


# ---------------------------------------------------------------------------
# Per-match civ rebinding
#
# The runbook's design: instead of pre-baking N coverage carriers, re-emit
# ANEWWORLD.age3Yscn per match by patching its P5 sub-records with a fresh
# 8-civ slate (P1=human + 7 AI). This lets a single carrier serve any civ
# matrix and bypasses the fragile lobby-picker step.
# ---------------------------------------------------------------------------

def _load_full_roster() -> list:
    """Return the canonical 40-civ roster (flat list, ANW-prefixed tokens)."""
    from tools.validation.scenario_emitter import PLAYBOOK_MATRIX
    seen = set()
    roster = []
    for slate_key in ("A", "B", "C", "D", "E"):
        for civ in PLAYBOOK_MATRIX[slate_key]:
            if civ not in seen:
                seen.add(civ)
                roster.append(civ)
    return roster


def choose_civs(civs_arg: Optional[str],
                p1_civ: Optional[str],
                randomize: bool,
                seed: Optional[int]) -> list:
    """Resolve the 8-civ slate for P1..P8.

    Priority: explicit --civs > --p1-civ + --randomize fill > --randomize.
    """
    if civs_arg:
        slate = [c.strip() for c in civs_arg.split(",") if c.strip()]
        if len(slate) != 8:
            raise ValueError(
                f"--civs expects 8 comma-separated tokens, got {len(slate)}"
            )
        return slate

    if randomize or p1_civ:
        rng = random.Random(seed) if seed is not None else random.Random()
        roster = _load_full_roster()
        if p1_civ:
            if p1_civ not in roster:
                raise ValueError(
                    f"--p1-civ {p1_civ!r} not in 40-civ roster: {roster}"
                )
            pool = [c for c in roster if c != p1_civ]
            rng.shuffle(pool)
            return [p1_civ] + pool[:7]
        shuffled = roster[:]
        rng.shuffle(shuffled)
        return shuffled[:8]

    return []


def rebind_scenario(src: Path, slate: list) -> Path:
    """Re-emit ANEWWORLD.age3Yscn with the given 8-civ slate.

    Returns the temp file path. Caller is responsible for cleanup if desired
    (the OS temp dir is fine for fire-and-forget testing).
    """
    from tools.validation.scenario_emitter import (
        load_scenario, set_player_bindings, pack_scenario, verify_trailer,
    )
    assert len(slate) == 8, f"slate must be 8 civs, got {len(slate)}"

    raw, body = load_scenario(src)
    ai_loaders = [""] + ["aiLoaderStandard"] * 7   # P1 = human
    new_body = set_player_bindings(body, slate, ai_loaders=ai_loaders)
    new_raw = pack_scenario(new_body, recompute_trailer=True)

    tmp = Path(tempfile.gettempdir()) / "_anw_rebound_ANEWWORLD.age3Yscn"
    tmp.write_bytes(new_raw)
    if not verify_trailer(tmp):
        raise RuntimeError(f"trailer verification failed on {tmp}")
    print(f"Rebound scenario: {len(new_raw)}B  P1={slate[0]}  "
          f"AI=[{', '.join(slate[1:])}]")
    return tmp


# ---------------------------------------------------------------------------
# Scenario staging
# ---------------------------------------------------------------------------

def stage_scenario(src: Path, dst: Path, label: str) -> None:
    """Copy src → dst if not byte-identical.  dst parent created if needed."""
    if not src.exists():
        print(f"ERROR: scenario source not found: {src}", file=sys.stderr)
        sys.exit(1)

    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists() and _sha256(src) == _sha256(dst):
        print(f"Scenario already up-to-date at {dst} (skipped).")
        return

    import shutil
    shutil.copy2(src, dst)
    size = dst.stat().st_size
    print(f"Scenario staged [{label}]: {size}B at {dst}")


# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------

def launch_game() -> None:
    """Fire the Steam URL to bring up AoE3 DE."""
    url = f"steam://run/{AOEIII_STEAM_ID}"
    try:
        subprocess.run(["xdg-open", url], check=True, timeout=5)
    except Exception as exc:
        print(f"WARNING: xdg-open failed ({exc}). Start the game manually.",
              file=sys.stderr)

    print()
    print("=" * 70)
    print("Game launching. In the in-game lobby:")
    print("  Single Player → Skirmish → Custom Maps → ANEWWORLD → Start")
    print()
    print("Watching for personality writes... (Ctrl-C to abort and report)")
    print("=" * 70)
    print()


# ---------------------------------------------------------------------------
# Polling
# ---------------------------------------------------------------------------

def detect_fresh(
    personality_dir: Path,
    baseline: dict[str, tuple[float, int]],
    already_reported: set[str],
) -> list[tuple[str, PersonalityProbe]]:
    """Return (stem, probe) tuples for files that are newer than baseline
    and haven't been reported yet.
    """
    fresh: list[tuple[str, PersonalityProbe]] = []
    if not personality_dir.exists():
        return fresh

    from tools.playtest.probes_from_replay import parse_personality_file

    for path in sorted(personality_dir.glob("*.personality")):
        stem = path.stem
        if stem in already_reported:
            continue
        try:
            current_mtime = path.stat().st_mtime
        except OSError:
            continue

        baseline_mtime, baseline_match_ms = baseline.get(stem, (-1.0, -1))
        if current_mtime <= baseline_mtime:
            continue  # no newer write

        # File is newer — try to decode.
        p = parse_personality_file(path)
        if p is None:
            continue  # file written but no probe data yet (partial write?)
        if p.match_ms == baseline_match_ms:
            continue  # mtime bumped but probe data unchanged

        fresh.append((stem, p))
    return fresh


def poll_loop(
    personality_dir: Path,
    baseline: dict[str, tuple[float, int]],
    timeout_secs: float,
    t_start: float,
) -> tuple[dict[str, PersonalityProbe], bool]:
    """Poll until timeout or quiet-after-first-write heuristic triggers.

    Returns ({stem: probe}, timed_out).
    """
    reported: dict[str, PersonalityProbe] = {}
    already_reported: set[str] = set()
    first_write_time: Optional[float] = None
    last_write_time: Optional[float] = None

    while True:
        now = time.monotonic()
        elapsed = now - t_start

        # --- timeout check ---
        if timeout_secs == 0:
            # Zero means "don't poll at all".
            break
        if elapsed >= timeout_secs:
            print(f"\nTimeout reached ({timeout_secs:.0f}s). Generating report...")
            return reported, len(reported) == 0

        # --- quiet-after-first-write check ---
        if first_write_time is not None and last_write_time is not None:
            quiet_for = now - last_write_time
            if quiet_for >= QUIET_AFTER_FIRST_WRITE_SECS:
                print(f"\nNo new writes for {QUIET_AFTER_FIRST_WRITE_SECS}s after "
                      f"first activity — assuming match ended.")
                break

        fresh = detect_fresh(personality_dir, baseline, already_reported)
        for stem, probe in fresh:
            elapsed_tag = _format_elapsed(now - t_start)
            print(f"{elapsed_tag} +{_probe_summary(probe)}")
            reported[stem] = probe
            already_reported.add(stem)
            if first_write_time is None:
                first_write_time = now
            last_write_time = now

        time.sleep(POLL_INTERVAL)

    return reported, len(reported) == 0


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def run_validator() -> int:
    """Invoke validate_personality_vs_spec.py and return its exit code."""
    result = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        check=False,
    )
    return result.returncode


def load_validator_json() -> Optional[dict]:
    """Load the refreshed personality_compliance.json if it exists."""
    if not VALIDATOR_JSON.exists():
        return None
    try:
        return json.loads(VALIDATOR_JSON.read_text())
    except Exception:
        return None


def print_session_delta(
    fresh_probes: dict[str, PersonalityProbe],
    validator_data: Optional[dict],
) -> None:
    """Print the session delta table — only civs with fresh probes."""
    if not fresh_probes:
        print("No fresh probes captured this session.")
        return

    print()
    print("Session delta (civs with fresh activity this session):")
    print(f"  {'Stem':<30s} {'match_ms':>10s}  {'Status'}")
    print("  " + "-" * 60)

    # Build a quick lookup from the validator JSON rows if available.
    status_by_stem: dict[str, str] = {}
    if validator_data and "rows" in validator_data:
        for row in validator_data["rows"]:
            pstem = row.get("personality_stem", "")
            status = row.get("preinit_status") or row.get("status", "?")
            status_by_stem[pstem] = status

    for stem in sorted(fresh_probes):
        probe = fresh_probes[stem]
        status = status_by_stem.get(stem, "?")
        print(f"  {stem:<30s} {probe.match_ms:>10d}  {status}")

    print()


def print_final_report_path(validator_data: Optional[dict]) -> None:
    md_path = REPO_ROOT / "artifacts/validation/personality_compliance.md"
    if md_path.exists():
        print(f"Full report: {md_path}")
    else:
        print("Full report: (not generated — validator did not run successfully)")


# ---------------------------------------------------------------------------
# Signal handler
# ---------------------------------------------------------------------------

# We store fresh_probes in a module-level container so the SIGINT handler can
# reach it without closures over mutable references.
_sigint_fresh_probes: dict[str, PersonalityProbe] = {}
_sigint_triggered = False


def _sigint_handler(signum: int, frame) -> None:  # type: ignore[type-arg]
    global _sigint_triggered
    if _sigint_triggered:
        # Second Ctrl-C — hard exit.
        sys.exit(2)
    _sigint_triggered = True
    print("\n\nInterrupted. Running partial report...")
    validator_rc = run_validator()
    validator_data = load_validator_json()
    print_session_delta(_sigint_fresh_probes, validator_data)
    print_final_report_path(validator_data)
    if _sigint_fresh_probes:
        sys.exit(0 if validator_rc == 0 else 1)
    else:
        sys.exit(2)


# ---------------------------------------------------------------------------
# CLI / main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Orchestrate a single end-to-end AI test session using the "
            "ANEWWORLD scenario.  Stages the scenario file, optionally "
            "launches AoE3 DE, polls for personality writes, then invokes "
            "the validator and prints a session delta report."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--no-baseline",
        action="store_true",
        help="Skip the baseline snapshot step (treat all current files as new).",
    )
    ap.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        metavar="MINUTES",
        help="Polling timeout in minutes (default: 15).  Use 0 to skip polling.",
    )
    ap.add_argument(
        "--no-launch",
        action="store_true",
        help="Do not launch Steam; user starts the game manually.",
    )
    ap.add_argument(
        "--personality-dir",
        type=Path,
        default=PERSONALITY_DIR,
        metavar="DIR",
        help=f"Override personality directory (default: {PERSONALITY_DIR}).",
    )
    ap.add_argument(
        "--civs",
        type=str,
        metavar="P1,P2,...,P8",
        help="Comma-separated 8 civ tokens to bind to P1..P8 before staging. "
             "P1 is the human slot, P2..P8 are AI. Example: "
             "ANWBritish,ANWFrench,ANWGermans,ANWSpanish,ANWDutch,"
             "ANWPortuguese,ANWOttomans,ANWRussians",
    )
    ap.add_argument(
        "--randomize",
        action="store_true",
        help="Randomly select 8 civs from the 40-civ ANW roster for "
             "P1..P8 (P1 = human). Use --seed for reproducibility.",
    )
    ap.add_argument(
        "--p1-civ",
        type=str,
        metavar="ANWxxx",
        help="Pin the P1 (human) slot to this civ token; P2..P8 are then "
             "filled by random selection from the remaining roster. "
             "Implies --randomize.",
    )
    ap.add_argument(
        "--seed",
        type=int,
        metavar="N",
        help="RNG seed for --randomize / --p1-civ slate selection.",
    )
    args = ap.parse_args()

    timeout_secs = args.timeout * 60.0

    # Install SIGINT handler so Ctrl-C produces a partial report.
    signal.signal(signal.SIGINT, _sigint_handler)

    # ------------------------------------------------------------------
    # 1. Baseline snapshot
    # ------------------------------------------------------------------
    if not args.no_baseline:
        print("Building baseline snapshot...")
        baseline = build_baseline(args.personality_dir)
        all_probes = scan_personality_dir(args.personality_dir)
        print_baseline_summary(baseline, all_probes)
    else:
        print("Baseline snapshot skipped (--no-baseline).")
        baseline = {}

    # ------------------------------------------------------------------
    # 2. Stage scenario (idempotent)
    # ------------------------------------------------------------------
    slate = choose_civs(args.civs, args.p1_civ, args.randomize, args.seed)
    src = SCENARIO_SRC
    if slate:
        src = rebind_scenario(SCENARIO_SRC, slate)
    stage_scenario(src, SCENARIO_DST_GAME, "game")
    stage_scenario(src, SCENARIO_DST_CLOUD, "cloud")

    # ------------------------------------------------------------------
    # 3. Launch (optional)
    # ------------------------------------------------------------------
    if not args.no_launch:
        launch_game()
    else:
        if timeout_secs > 0:
            print("--no-launch: skipping Steam launch. "
                  "Start the game manually, then wait for personality writes.")
            print()

    # ------------------------------------------------------------------
    # 4. Poll for fresh data
    # ------------------------------------------------------------------
    if timeout_secs == 0:
        print("--timeout 0: skipping poll loop.")
        fresh_probes: dict[str, PersonalityProbe] = {}
        timed_out = True  # no probes means we go to exit code 2 unless...
    else:
        print(f"Polling every {POLL_INTERVAL}s "
              f"(timeout {args.timeout:.1f}min, "
              f"early-exit after {QUIET_AFTER_FIRST_WRITE_SECS}s quiet)...")
        t_start = time.monotonic()
        fresh_probes, timed_out = poll_loop(
            args.personality_dir, baseline, timeout_secs, t_start
        )

    # Share with signal handler.
    _sigint_fresh_probes.update(fresh_probes)

    # ------------------------------------------------------------------
    # 5. Report
    # ------------------------------------------------------------------
    print()
    print("Running validator...")
    validator_rc = run_validator()

    validator_data = load_validator_json()
    print_session_delta(fresh_probes, validator_data)
    print_final_report_path(validator_data)

    # Exit codes:
    #   0 = fresh probes captured AND validator passed
    #   1 = fresh probes captured BUT validator found failures
    #   2 = no fresh probes (pipeline broken / timed out without any writes)
    if not fresh_probes:
        if timeout_secs == 0:
            # --timeout 0 is a dry-run smoke-test; report validator status.
            print("(timeout=0: no polling performed)")
            return 0 if validator_rc == 0 else 1
        print("No fresh probes captured — pipeline broken or no match ran.",
              file=sys.stderr)
        return 2

    return 0 if validator_rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
