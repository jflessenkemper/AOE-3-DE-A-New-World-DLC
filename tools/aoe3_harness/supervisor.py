"""Per-pass orchestration: truncate log, wait for match, archive results.

Absorbs the logic of tools/validation/hubtest_archive_log.sh.

State file: tools/aoe3_harness/state.json (schema defined at bottom of this file).

Key constants:
  AGE3_LOG_PATH = Path("~/.local/share/Steam/steamapps/compatdata/933110/pfx/
                        drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt")
  AI_OUTPUT_GLOB = "Age3DEAIOutputPlayer*.txt"   # same Logs/ directory
  ARTIFACT_ROOT = Path("artifacts/validation/ai_playstyle/")
  MATCH_DURATION_S = 1260   # 21 minutes; matches hubtest_archive_log.sh

STATE_SCHEMA = {
    "last_run_ts": "ISO8601 string",
    "passes_complete": [1, 2, ...],          # list of completed pass numbers
    "passes_archive": {
        "1": "artifacts/validation/ai_playstyle/hubtest_pass1_<ts>/",
        ...
    },
    "civ_coverage": {
        "ANWBritish": {"probes": 42, "status": "PASS"},
        ...
    },
}
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tools.aoe3_automation.log_capture import (
    AGE3_LOG_PATH,
    read_since,
    snapshot_offset,
)
from tools.aoe3_harness.launch import kill_stale, launch_game, wait_for_exit
from tools.aoe3_harness.paths import (
    AI_OUTPUT_DIR,
    AI_OUTPUT_GLOB,
    AI_OUTPUT_SEARCH_DIRS,
    ARTIFACT_ROOT,
    STATE_PATH,
)

PASS_CIVS: dict[int, list[str]] = {
    1: ["ANWCanadians", "ANWAztecs", "ANWBarbary", "ANWBrazil", "ANWGermans", "ANWArgentines", "ANWChileans"],
    2: ["ANWHaitians", "ANWBritish", "ANWHausa", "ANWItalians", "ANWColumbians", "ANWChinese", "ANWIndonesians"],
    3: ["ANWDutch", "ANWRomanians", "ANWMexicans", "ANWHaudenosaunee", "ANWEgyptians", "ANWMayans", "ANWPortuguese"],
    4: ["ANWRussians", "ANWRevFrance", "ANWHungarians", "ANWEthiopians", "ANWSouthAfricans", "ANWUSA", "ANWJapanese"],
    5: ["ANWFinnish", "ANWLakota", "ANWFrench", "ANWNapoleonicFrance", "ANWInca", "ANWSpanish", "ANWIndians"],
    6: ["ANWSwedes", "ANWMaltese", "ANWTexians", "ANWOttomans", "ANWPeruvians"],
}

MATCH_DURATION_S: int = 1260  # 21 minutes; matches hubtest_archive_log.sh
SCENARIO_FILE: str = "ANEWWORLD.age3Yscn"


def _find_ai_output_files() -> list[Path]:
    """Locate Age3DEAIOutputPlayer*.txt files by searching all known directories.

    Risk 1 mitigation: the actual output directory is unconfirmed.  We search
    Logs/, Startup/, and Game/AI/ paths under the Wine prefix to handle engine
    variations.

    Returns:
        List of matching Path objects (may be empty if none exist yet).
    """
    found: list[Path] = []
    for search_dir in AI_OUTPUT_SEARCH_DIRS:
        if search_dir.exists():
            found.extend(sorted(search_dir.glob(AI_OUTPUT_GLOB)))
    # Deduplicate while preserving order (shouldn't happen, but be safe)
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in found:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def _snapshot_ai_offsets(ai_files: list[Path]) -> dict[str, int]:
    """Snapshot byte offsets for all current per-AI output files.

    Args:
        ai_files: List of per-AI file paths to snapshot.

    Returns:
        Dict mapping file path (as string key) -> current byte size.
        Files that do not yet exist get offset 0.
    """
    offsets: dict[str, int] = {}
    for path in ai_files:
        try:
            offsets[str(path)] = path.stat().st_size
        except FileNotFoundError:
            offsets[str(path)] = 0
    return offsets


def _read_ai_since(path: Path, offset: int) -> str:
    """Read per-AI file content from offset to end-of-file.

    Args:
        path: Path to the Age3DEAIOutputPlayer<N>.txt file.
        offset: Byte offset captured before the match started.

    Returns:
        UTF-8 decoded string of new content; empty string if no new data.
    """
    if not path.exists():
        return ""
    size = path.stat().st_size
    if size <= offset:
        return ""
    with path.open("rb") as fh:
        fh.seek(offset)
        raw = fh.read()
    return raw.decode("utf-8", errors="replace")


def probe_summary(log_content: str) -> dict:
    """Return counts of key probe tag types in the log content.

    Args:
        log_content: Raw string content from Age3Log.txt match slice.

    Returns:
        Dict with counts for probe types found in the log.
    """
    return {
        "llp_v2_total": log_content.count("[LLP v=2 "),
        "milestone_first_wall": log_content.count("milestone.first_wall_segment"),
        "milestone_first_barracks": log_content.count("milestone.first_barracks"),
        "posture_snapshot": log_content.count("posture.snapshot"),
    }


def archive_pass(
    pass_number: int,
    log_content: str,
    ai_slices: dict[str, str],
    ts: str,
) -> Path:
    """Write the archived pass directory and return its path.

    Args:
        pass_number: Pass number (1–6).
        log_content: Delta content from Age3Log.txt for this match.
        ai_slices: Dict mapping filename -> content for per-AI file deltas.
        ts: Timestamp string for the archive directory name (ISO8601 compact).

    Returns:
        The archive directory Path (created if needed).
    """
    archive_dir = ARTIFACT_ROOT / f"hubtest_pass{pass_number}_{ts}"
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Write Age3Log.txt delta
    (archive_dir / "Age3Log.txt").write_text(log_content, encoding="utf-8")

    # Write per-AI deltas (using original filename)
    for source_path_str, content in ai_slices.items():
        source_name = Path(source_path_str).name
        (archive_dir / source_name).write_text(content, encoding="utf-8")

    print(f"[harness/supervisor] Archived pass {pass_number} -> {archive_dir}")
    return archive_dir


def update_state(pass_number: int, archive_dir: Path, civ_results: dict) -> None:
    """Read state.json, update pass completion and civ coverage, write back atomically.

    Args:
        pass_number: The completed pass number.
        archive_dir: Path to the archive directory for this pass.
        civ_results: Dict mapping civ token -> {"probes": N, "status": "PASS"|"FAIL"}.
    """
    state: dict = {
        "last_run_ts": None,
        "passes_complete": [],
        "passes_archive": {},
        "civ_coverage": {},
    }
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    state["last_run_ts"] = datetime.now(timezone.utc).isoformat()
    passes_complete: list[int] = state.get("passes_complete", [])
    if pass_number not in passes_complete:
        passes_complete.append(pass_number)
        passes_complete.sort()
    state["passes_complete"] = passes_complete

    passes_archive: dict = state.get("passes_archive", {})
    passes_archive[str(pass_number)] = str(archive_dir)
    state["passes_archive"] = passes_archive

    civ_coverage: dict = state.get("civ_coverage", {})
    civ_coverage.update(civ_results)
    state["civ_coverage"] = civ_coverage

    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)


def run_pass(
    pass_number: int,
    dry_run: bool = False,
    skip_launch: bool = False,
    force_kill: bool = False,
) -> Path:
    """Run one hub-test pass end-to-end.

    Steps:
      1. Validate pass_number is in PASS_CIVS.
      2. Kill stale AoE3 processes (unless skip_launch).
      3. Snapshot Age3Log.txt byte offset (Risk 3: append-only isolation).
      4. Also snapshot offsets for any existing Age3DEAIOutputPlayer*.txt files.
      5. Launch game via launch.launch_game(scenario=SCENARIO_FILE).
      6. Print the civ list for this pass (user sets up lobby manually).
      7. Sleep MATCH_DURATION_S.
      8. Archive Age3Log.txt delta to artifacts/validation/ai_playstyle/hubtest_passN_<ts>/.
      9. Also archive per-AI file deltas (byte-offset slices) to same dir.
      10. Emit probe-count summary.
      11. Update state.json.
      12. Return the archive directory Path.

    Args:
        pass_number: 1–6.
        dry_run: Print steps but do not execute game launch or log mutations.
        skip_launch: For re-archiving an already-running match (advanced use).
        force_kill: Escalate stale-process kill to SIGKILL after 5s.

    Returns:
        The archive directory Path.

    Raises:
        ValueError: if pass_number is not in PASS_CIVS.
    """
    if pass_number not in PASS_CIVS:
        raise ValueError(
            f"pass_number must be 1–6; got {pass_number}"
        )

    civs = PASS_CIVS[pass_number]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    print(f"\n{'='*70}")
    print(f"[harness/supervisor] Pass {pass_number} / 6 — {len(civs)} civs")
    print(f"[harness/supervisor] Civs: {', '.join(civs)}")
    print(f"{'='*70}\n")

    # Step 3: snapshot main log offset
    log_offset = 0 if dry_run else snapshot_offset()
    print(f"[harness/supervisor] Age3Log.txt snapshot offset: {log_offset} bytes")

    # Step 4: snapshot per-AI file offsets
    ai_files = [] if dry_run else _find_ai_output_files()
    ai_offsets = {} if dry_run else _snapshot_ai_offsets(ai_files)
    if ai_files:
        print(f"[harness/supervisor] Snapshotted {len(ai_files)} per-AI file(s):")
        for p in ai_files:
            print(f"  {p.name}: {ai_offsets.get(str(p), 0)} bytes")
    else:
        print("[harness/supervisor] No per-AI files yet (will capture any created during match)")

    # Step 5: launch game
    if skip_launch:
        print("[harness/supervisor] skip_launch=True: assuming game is already running")
    else:
        launch_game(
            scenario=SCENARIO_FILE,
            dry_run=dry_run,
            force_kill=force_kill,
        )

    # Step 6: print setup instructions
    print(f"\n[harness/supervisor] === LOBBY SETUP FOR PASS {pass_number} ===")
    print("[harness/supervisor] The game should now be loading.")
    print("[harness/supervisor] Navigate to: Single Player -> Skirmish -> Load Scenario -> ANEWWORLD")
    print("[harness/supervisor] Set up the following AI players in slots 1-7:")
    for i, civ in enumerate(civs, 1):
        print(f"    Slot {i}: {civ}")
    if len(civs) < 7:
        for i in range(len(civs) + 1, 8):
            print(f"    Slot {i}: any AI / leave empty")
    print("[harness/supervisor] Start the match. The harness will wait for match completion.\n")

    # Step 7: wait
    if dry_run:
        print(f"[harness/supervisor] dry-run: would wait {MATCH_DURATION_S}s for match")
    else:
        print(f"[harness/supervisor] Waiting {MATCH_DURATION_S}s ({MATCH_DURATION_S//60}m) for match...")
        time.sleep(MATCH_DURATION_S)

    # Step 8: archive Age3Log.txt delta
    log_content = "" if dry_run else read_since(log_offset)
    summary = probe_summary(log_content)
    print(f"[harness/supervisor] Age3Log.txt delta: {len(log_content)} bytes, "
          f"{summary['llp_v2_total']} [LLP v=2] probes")

    # Step 9: archive per-AI deltas
    ai_slices: dict[str, str] = {}
    if not dry_run:
        # Also look for any NEW per-AI files that appeared during the match
        current_ai_files = _find_ai_output_files()
        for path in current_ai_files:
            offset = ai_offsets.get(str(path), 0)
            content = _read_ai_since(path, offset)
            if content:
                ai_slices[str(path)] = content
                probe_ct = content.count("[LLP v=2 ")
                print(f"[harness/supervisor] {path.name}: {len(content)} bytes, "
                      f"{probe_ct} [LLP v=2] probes")

    # Step 10: emit full probe summary
    print(f"\n[harness/supervisor] Probe summary:")
    print(f"  [LLP v=2] total: {summary['llp_v2_total']}")
    print(f"  milestone.first_wall_segment: {summary['milestone_first_wall']}")
    print(f"  milestone.first_barracks: {summary['milestone_first_barracks']}")
    print(f"  posture.snapshot: {summary['posture_snapshot']}")

    # Derive per-civ coverage from probes
    civ_probe_counts: dict[str, int] = {}
    for civ in civs:
        pattern = re.compile(rf"\[LLP v=2[^\]]*\bciv={re.escape(civ)}\b")
        count = len(pattern.findall(log_content))
        civ_probe_counts[civ] = count

    # Archive
    archive_dir = archive_pass(pass_number, log_content, ai_slices, ts)

    # Civ results
    civ_results = {
        civ: {
            "probes": civ_probe_counts.get(civ, 0),
            "status": "PASS" if civ_probe_counts.get(civ, 0) > 0 else "UNKNOWN",
        }
        for civ in civs
    }

    # Step 11: update state
    if not dry_run:
        update_state(pass_number, archive_dir, civ_results)
        print(f"[harness/supervisor] state.json updated.")

    print(f"\n[harness/supervisor] Pass {pass_number} complete. Archive: {archive_dir}\n")
    return archive_dir
