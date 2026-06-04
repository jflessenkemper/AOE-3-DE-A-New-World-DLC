"""Tail the live Age3Log.txt while a match is running and produce a structured
digest so we can review AI behaviour after the fact without sitting on a
``tail -f``.

Non-intrusive: pure file IO, no cursor / keyboard / window grabbing. Run with
``python3 tools/validation/live_log_watcher.py`` and play the match. Ctrl-C
when you're done; the digest at ``artifacts/validation/live_test/digest.md``
will summarise the session. Each line of the live log is bucketed into one
of five categories:

  * **probes** — every ``[ANWP v=2 …]`` line (one per civ-doctrine event)
  * **wall_closure** — ``wall.closure=`` ratio per ring (closes vs. spec)
  * **errors** — ``cmdsExecXS`` failures, ``failed to load``, asserts
  * **warnings** — engine warnings (xs runtime, file-load misses, etc.)
  * **chat_red** — in-game red error chat (sometimes the only signal of an
    XS rule that throws but doesn't kill the AI thread)

Writes a running digest every 5 seconds, plus a final summary on Ctrl-C.
"""
from __future__ import annotations

import os
import re
import signal
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

LIVE_LOG = Path(
    os.path.expanduser(
        "~/.local/share/Steam/steamapps/compatdata/933110/pfx/"
        "drive_c/users/steamuser/Games/Age of Empires 3 DE/Logs/Age3Log.txt"
    )
)
OUT_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "validation" / "live_test"
DIGEST = OUT_DIR / "digest.md"
RAW_PROBES = OUT_DIR / "probes.log"
RAW_ERRORS = OUT_DIR / "errors.log"

# Buckets
_PROBE_RE = re.compile(r"\[ANWP v=2[^\]]*\][^\n]*")
_WALL_RE = re.compile(r"wall\.closure[=:]\s*([0-9.]+)")
_ERR_RE = re.compile(
    r"(cmdsExecXS|failed to load|assertion|fatal|EXCEPTION|XS error|"
    r"runtime error|RULE FAILED)", re.IGNORECASE)
_WARN_RE = re.compile(r"(warning|WARN |MISS )", re.IGNORECASE)


def _format_digest(state: dict, started_at: float, log_size: int) -> str:
    elapsed = int(time.time() - started_at)
    out: list[str] = []
    out.append(f"# Live log digest — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    out.append("")
    out.append(f"- Source: `{LIVE_LOG}`")
    out.append(f"- Watching for: `{elapsed}s` so far")
    out.append(f"- Log file size: `{log_size}` bytes")
    out.append("")
    out.append("## Counts")
    out.append("")
    out.append(f"- `[ANWP v=2]` probes: **{state['probes']}**")
    out.append(f"- `wall.closure` samples: **{len(state['wall_ratios'])}**")
    out.append(f"- Errors: **{state['errors']}**")
    out.append(f"- Warnings: **{state['warnings']}**")
    out.append("")
    if state['wall_ratios']:
        ratios = state['wall_ratios']
        out.append("## Wall closure ratios (target ≥ 0.60 by Age 3)")
        out.append("")
        out.append(f"- min: `{min(ratios):.2f}`")
        out.append(f"- max: `{max(ratios):.2f}`")
        out.append(f"- mean: `{sum(ratios)/len(ratios):.2f}`")
        if any(r < 0.6 for r in ratios):
            below = sum(1 for r in ratios if r < 0.6)
            out.append(f"- **{below}/{len(ratios)} samples below 0.60** — half-wall risk")
        out.append("")
    if state['probe_civs']:
        out.append("## Civs that fired probes")
        out.append("")
        for civ, n in state['probe_civs'].most_common():
            out.append(f"- `{civ}`: {n}")
        out.append("")
    if state['recent_errors']:
        out.append("## Recent errors (last 20)")
        out.append("")
        for line in state['recent_errors'][-20:]:
            out.append(f"- `{line.strip()[:200]}`")
        out.append("")
    if state['recent_warnings']:
        out.append("## Recent warnings (last 10)")
        out.append("")
        for line in state['recent_warnings'][-10:]:
            out.append(f"- `{line.strip()[:200]}`")
        out.append("")
    return "\n".join(out)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not LIVE_LOG.exists():
        print(f"WARN: live log not yet present at {LIVE_LOG}", flush=True)
        print("  Waiting for the game to start it…", flush=True)

    state = {
        "probes": 0,
        "errors": 0,
        "warnings": 0,
        "wall_ratios": [],
        "probe_civs": Counter(),
        "recent_errors": [],
        "recent_warnings": [],
    }
    started_at = time.time()
    last_digest = 0.0

    # Open in tail mode: seek to end on first open so we only capture
    # *this* session's events. (If the user wants the full file replayed,
    # they can ``rm Age3Log.txt`` between sessions; AoE3 DE truncates on
    # game launch anyway.)
    pos = LIVE_LOG.stat().st_size if LIVE_LOG.exists() else 0
    print(f"Tailing {LIVE_LOG} from byte {pos}…", flush=True)
    print(f"Digest will be written every 5s to {DIGEST}", flush=True)
    print("Ctrl-C to stop and write final summary.", flush=True)

    raw_p = RAW_PROBES.open("w")
    raw_e = RAW_ERRORS.open("w")

    def _flush_and_exit(*_a):
        digest = _format_digest(state, started_at,
                                LIVE_LOG.stat().st_size if LIVE_LOG.exists() else 0)
        DIGEST.write_text(digest)
        raw_p.close()
        raw_e.close()
        print("\n=== Final digest ===")
        print(digest)
        sys.exit(0)

    signal.signal(signal.SIGINT, _flush_and_exit)
    signal.signal(signal.SIGTERM, _flush_and_exit)

    while True:
        try:
            if not LIVE_LOG.exists():
                time.sleep(2)
                continue
            cur_size = LIVE_LOG.stat().st_size
            if cur_size < pos:
                # log was truncated (new game launch) — restart from 0
                pos = 0
                state["probes"] = 0
                state["errors"] = 0
                state["warnings"] = 0
                state["wall_ratios"].clear()
                state["probe_civs"].clear()
                state["recent_errors"].clear()
                state["recent_warnings"].clear()
                started_at = time.time()
                print("Log truncated — new session detected, resetting counters.",
                      flush=True)
            if cur_size > pos:
                with LIVE_LOG.open("rb") as f:
                    f.seek(pos)
                    chunk = f.read(cur_size - pos).decode("utf-8", "replace")
                    pos = cur_size
                for line in chunk.splitlines():
                    if "[ANWP v=2" in line:
                        state["probes"] += 1
                        raw_p.write(line + "\n")
                        raw_p.flush()
                        m = re.search(r"civ=(\w+)", line)
                        if m:
                            state["probe_civs"][m.group(1)] += 1
                    m = _WALL_RE.search(line)
                    if m:
                        try:
                            state["wall_ratios"].append(float(m.group(1)))
                        except ValueError:
                            pass
                    if _ERR_RE.search(line):
                        state["errors"] += 1
                        state["recent_errors"].append(line)
                        raw_e.write(line + "\n")
                        raw_e.flush()
                    elif _WARN_RE.search(line):
                        state["warnings"] += 1
                        state["recent_warnings"].append(line)
            # periodic digest write
            if time.time() - last_digest > 5.0:
                DIGEST.write_text(_format_digest(state, started_at, pos))
                last_digest = time.time()
            time.sleep(1)
        except Exception as exc:
            print(f"watcher error: {exc}", flush=True)
            time.sleep(2)


if __name__ == "__main__":
    sys.exit(main())
