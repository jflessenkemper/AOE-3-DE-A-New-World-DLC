#!/usr/bin/env python3
"""Run picker_pixel for every ANW civ and write a pass/fail summary.

This is the overnight smoke-test driver. It calls
``scripted_scenarios.scenario_picker_pixel`` in-process for each civ token
(no subprocess overhead), captures per-civ timing + the OCR
``actual_token``, and writes a JSON summary to
``artifacts/picker_matrix_smoke/summary.json``.

Why in-process instead of shelling out per civ:
  Each subprocess re-imports the harness (~1s), reloads coords, re-detects
  the gamescope display, and discards the picker_civ_order cache between
  runs. In-process, we pay those costs once and amortize across 46 picks.

Why ``prefer_ocr=True`` for every pick:
  The cache path doesn't post-verify. Running 46 picks with the cache on
  would silently land on the wrong civ for any cache entry that drifted
  between calibration and now. The OCR path is ~3× slower (~15s vs ~5s
  per pick) but always reads back the highlighted row and matches against
  enriched_reference.json. For overnight smoke, correctness > speed.

Usage::

    python3 tools/aoe3_automation/picker_matrix_smoke.py
    python3 tools/aoe3_automation/picker_matrix_smoke.py --civs ANWBritish,ANWFrench

Pre-condition: AoE3 must be on the Skirmish lobby (run navigate flow first
or use run_scenario_e2e.py without --skip-navigate at least once).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.aoe3_automation.anw_civ_picker_map import ANW_TO_PICKER_INDEX
from tools.aoe3_automation import scripted_scenarios

# Civ tokens that exist in enriched_reference / picker_map but are NOT
# directly selectable from the Skirmish lobby — they are Revolution-only
# civs that require playing as a parent civ and triggering a Revolution
# card mid-game. Calibrated 2026-05-11 by exhaustive picker OCR scan
# (see artifacts/lobby_driver/find_target/) which confirmed no row
# matches these tokens at any scroll position.
PICKER_SKIP = {
}


def run_one(civ: str, out_dir: Path) -> dict:
    """Run picker_pixel for a single civ; return result row."""
    civ_dir = out_dir / f"picker_pixel__{civ}"
    t0 = time.monotonic()
    try:
        manifest = scripted_scenarios.scenario_picker_pixel(civ, civ_dir)
        return {
            "civ": civ,
            "ok": True,
            "elapsed_s": round(time.monotonic() - t0, 1),
            "selection_method": manifest.get("selection_method"),
            "selection_attempts": manifest.get("selection_attempts"),
            "actual_token": manifest.get("actual_token"),
            "drift": (manifest.get("actual_token") != civ),
            "state_path": manifest.get("state_path"),
        }
    except SystemExit as e:
        return {
            "civ": civ,
            "ok": False,
            "elapsed_s": round(time.monotonic() - t0, 1),
            "error": str(e),
        }
    except Exception as e:
        return {
            "civ": civ,
            "ok": False,
            "elapsed_s": round(time.monotonic() - t0, 1),
            "error": f"{type(e).__name__}: {e}",
        }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--civs", default=None,
                    help="Comma-separated subset (default: all 46 ANW civs)")
    ap.add_argument("--out", type=Path,
                    default=REPO_ROOT / "artifacts" / "picker_matrix_smoke",
                    help="Output directory for per-civ crops + summary.json")
    ap.add_argument("--continue-on-error", action="store_true", default=True,
                    help="Continue to next civ on failure (default: True)")
    args = ap.parse_args(argv)

    if args.civs:
        civs = [c.strip() for c in args.civs.split(",") if c.strip()]
        unknown = [c for c in civs if c not in ANW_TO_PICKER_INDEX]
        if unknown:
            print(f"ERROR: unknown civ tokens: {unknown}", file=sys.stderr)
            return 2
    else:
        civs = sorted(ANW_TO_PICKER_INDEX.keys())

    skipped = [c for c in civs if c in PICKER_SKIP]
    civs = [c for c in civs if c not in PICKER_SKIP]
    if skipped:
        print(f"[matrix] skipping {len(skipped)} revolution-only civ(s): "
              f"{skipped}")

    args.out.mkdir(parents=True, exist_ok=True)
    print(f"[matrix] {len(civs)} civs -> {args.out}")
    print(f"[matrix] {time.strftime('%H:%M:%S')} starting")

    results: list[dict] = []
    t_start = time.monotonic()
    for i, civ in enumerate(civs, 1):
        elapsed_total = time.monotonic() - t_start
        print(f"\n[matrix {i}/{len(civs)} +{elapsed_total:.0f}s] {civ}",
              flush=True)
        row = run_one(civ, args.out)
        results.append(row)
        # Stream a progress line to stdout so a tail -f can monitor.
        status = "OK" if row["ok"] and not row.get("drift") else (
            "DRIFT" if row.get("drift") else "FAIL"
        )
        actual = row.get("actual_token", "?")
        print(f"  -> [{status}] elapsed={row['elapsed_s']}s actual={actual} "
              f"method={row.get('selection_method', 'n/a')} "
              f"attempts={row.get('selection_attempts', 'n/a')}",
              flush=True)
        if not row["ok"]:
            print(f"  -> error: {row.get('error', '')[:200]}", flush=True)
            if not args.continue_on_error:
                break
        # Write summary after every pick so an interrupt mid-run still
        # leaves a usable artifact.
        summary = {
            "completed": i,
            "total": len(civs),
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results,
        }
        (args.out / "summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )

    # Final tally
    total_elapsed = time.monotonic() - t_start
    ok = sum(1 for r in results if r["ok"] and not r.get("drift"))
    drift = sum(1 for r in results if r.get("drift"))
    fail = sum(1 for r in results if not r["ok"])
    print(f"\n[matrix] done in {total_elapsed:.0f}s "
          f"({total_elapsed/60:.1f} min)")
    print(f"[matrix] PASS: {ok}/{len(results)}   "
          f"DRIFT: {drift}   FAIL: {fail}")
    if drift or fail:
        print("[matrix] failures:")
        for r in results:
            if not r["ok"] or r.get("drift"):
                print(f"  - {r['civ']}: ok={r['ok']} "
                      f"actual={r.get('actual_token')} "
                      f"err={r.get('error', '-')[:100]}")
    return 0 if (ok == len(results)) else 1


if __name__ == "__main__":
    sys.exit(main())
