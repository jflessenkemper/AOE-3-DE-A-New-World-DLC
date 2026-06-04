#!/usr/bin/env python3
"""One-shot end-to-end timing test for the probe-capture pipeline.

Runs ONE 1v1 skirmish with the new flow:
  - live log mirror (crash-resilient)
  - log-marker-based in-game wait (no escape spam)
  - observe_until_coverage with early exit on meta.* probes
  - clean UI-driven resign (engine flushes XS log buffer)

Records every phase timing and writes a JSON report.

Usage:
    python3 -m tools.aoe3_automation.timing_probe_run [--output DIR]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from tools.aoe3_automation.in_game_driver import GameDriver
from tools.aoe3_automation.log_capture import (
    start_log_tail, stop_log_tail, probe_count_in_slice,
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="/tmp/aoe_test/timing_probe_run",
                   help="output directory for match.log and report.json")
    p.add_argument("--max-observe", type=int, default=180,
                   help="max observe seconds (default 180)")
    p.add_argument("--min-observe", type=int, default=45,
                   help="min observe seconds before early-exit (default 45)")
    args = p.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    timings: dict[str, float] = {}
    overall_start = time.time()

    drv = GameDriver(art_dir=out)

    # ── Phase A: launch (or detect already-running) ─────────────────────
    t = time.time()
    if not drv.is_running():
        print("[A] launching game …")
        ok = drv.open(timeout=180, post_wait=8)
        if not ok:
            print("FAIL: game did not launch in time")
            return 1
    else:
        print("[A] game already running")
    timings["launch_s"] = time.time() - t

    # ── Phase B: main menu ──────────────────────────────────────────────
    t = time.time()
    print("[B] waiting for main menu …")
    drv.wait_for_main_menu(timeout=60)
    timings["main_menu_wait_s"] = time.time() - t

    # ── Phase C: start skirmish ─────────────────────────────────────────
    print("[C] starting log mirror + skirmish (P1=Random idx0, P2=Random idx0)…")
    match_log = out / "match.log"
    log_mirror = start_log_tail(match_log)

    t = time.time()
    drv.start_skirmish(p1_civ_idx=0, p2_civ_idx=0)  # 1v1, both Random
    timings["setup_clicks_s"] = time.time() - t

    # ── Phase D: load to playable (poll for WorldAssetPreloadingTime) ──
    t = time.time()
    print("[D] waiting for WorldAssetPreloadingTime …")
    if not drv.wait_for_in_game(timeout=180, dismiss_errors=True,
                                log_mirror=log_mirror):
        print("FAIL: WorldAssetPreloadingTime never observed")
        content = stop_log_tail(log_mirror)
        (out / "match.log").write_text(content, encoding="utf-8", errors="replace")
        timings["load_s"] = time.time() - t
        timings["TOTAL_s"] = time.time() - overall_start
        (out / "report.json").write_text(json.dumps({
            "result": "load_timeout", "timings": timings,
            "probe_count": probe_count_in_slice(content),
        }, indent=2))
        return 1
    timings["load_s"] = time.time() - t

    # ── Phase E: speed up + observe with early exit ────────────────────
    print("[E] setting speed 5x")
    drv.set_speed(5)

    t = time.time()
    print(f"[E] observe_until_coverage min={args.min_observe}s max={args.max_observe}s")
    coverage = drv.observe_until_coverage(
        log_mirror,
        required_families=("meta",),
        min_probe_count=2,
        min_seconds=args.min_observe,
        max_seconds=args.max_observe,
    )
    timings["observe_s"] = time.time() - t

    # ── Phase F: resign (flushes the buffered probe lines) ─────────────
    t = time.time()
    print("[F] resigning …")
    resign_ok = drv.resign()
    timings["resign_s"] = time.time() - t

    # ── Phase G: stop mirror, count probes ─────────────────────────────
    t = time.time()
    log_content = stop_log_tail(log_mirror)
    timings["mirror_stop_s"] = time.time() - t
    probe_n = probe_count_in_slice(log_content)
    timings["TOTAL_s"] = time.time() - overall_start

    # Family breakdown
    families: dict[str, int] = {}
    for line in log_content.splitlines():
        idx = line.find("[ANWP v=2 ")
        if idx < 0:
            continue
        ti = line.find("tag=", idx)
        if ti < 0:
            continue
        te = line.find("]", ti)
        if te < 0:
            te = len(line)
        fam = line[ti + 4:te].split(".", 1)[0]
        if fam:
            families[fam] = families.get(fam, 0) + 1

    report = {
        "result": "ok" if resign_ok else "resign_unconfirmed",
        "timings_s": {k: round(v, 1) for k, v in timings.items()},
        "probe_count": probe_n,
        "families": families,
        "coverage_observe_result": coverage,
        "match_log_bytes": len(log_content),
    }
    (out / "report.json").write_text(json.dumps(report, indent=2))

    print("\n" + "=" * 60)
    print("TIMING REPORT")
    print("=" * 60)
    for k, v in timings.items():
        print(f"  {k:<22s}  {v:7.2f}s")
    print(f"\n  probe_count = {probe_n}")
    print(f"  families    = {families}")
    print(f"  coverage    = {coverage}")
    print(f"\n  match.log:   {match_log}")
    print(f"  report.json: {out / 'report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
