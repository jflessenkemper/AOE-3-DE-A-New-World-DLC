#!/usr/bin/env python3
"""compile_playtest_report.py — collapse every artifact a matrix run
produces into a SINGLE dense, scan-friendly text file.

After a matrix run, the relevant signal is scattered across:
  • artifacts/matrix_runner/matrix_report.{json,md}           (per-civ load OK?)
  • artifacts/matrix_runner/<idx>_<slug>/match.log            (raw engine log)
  • artifacts/matrix_runner/doctrine_compliance.{txt,json}    (per-claim)

Reading all of those individually burns tokens on prose, headers, and engine
noise. This tool produces ONE file that looks like:

    === RUN <ts> ===
    HEADER  matrix=<n civs, k pass>  doctrine=<n civs, k fail>  cards=<…>

    --- British Elizabeth (idx=05) ---
    matrix:    PASS  ai_loaded=110  probes_fired=1  match_ms=98000
    doctrine:  FAIL  3 PASS / 2 FAIL / 1 UNKNOWN
        ✗ first_dock_before_ms     expected≤360000  actual=540000
        ✗ wall_strategy            expected=0       actual=5
    cards:     2/3 in deck   shipped=[Greenwich Time, Scots Guards, Some Garbage]
    timeline:
        00:00  meta.boot          buildStyle=NavalMercantile
        02:30  milestone.first_barracks  age=2
        09:00  milestone.first_dock      age=2   ← TOO LATE
        15:00  posture.snapshot   ws=5  walls=0  ← WRONG STRATEGY

    --- Aztecs Montezuma (idx=08) ---
    ...

    === REGRESSIONS ===
    wall_strategy: 4 civs failing (British, Wellington, Henry, Maurice)
    first_dock_before_ms: 3 civs failing (...)

The body is dense (one civ ≈ 15 lines) so a 48-civ matrix lands at ~720
lines, comfortably scannable in a single tool call.

CLI:
    python3 tools/validation/compile_playtest_report.py
        [--matrix-dir tools/aoe3_automation/artifacts/matrix_runner]
        [--out artifacts/playtest_report.txt]
        [--top-failures 10]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Importable validator pieces — share parsers so the report is in lock-step
# with what the validator scores.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_doctrine_compliance as vdc  # noqa: E402

REPO_ROOT     = Path(__file__).resolve().parents[2]
MATRIX_DIR    = REPO_ROOT / "tools" / "aoe3_automation" / "artifacts" / "matrix_runner"
DEFAULT_OUT   = REPO_ROOT / "artifacts" / "playtest_report.txt"
DEFAULT_SPEC  = REPO_ROOT / "playstyle_spec.json"
DEFAULT_DECKS = REPO_ROOT / "tools" / "playtest" / "html_card_decks.json"

# Probe tags worth surfacing in the per-civ timeline. Anything else is
# noise for the scan-friendly report (the raw match.log is still on disk
# if you need it).
TIMELINE_TAGS = {
    "meta.boot",
    "milestone.first_dock",
    "milestone.first_barracks",
    "milestone.first_stable",
    "milestone.first_wall_segment",
    "milestone.first_fort",
    "milestone.first_trading_post",
    "milestone.first_artillery",
    "milestone.first_forward_base",
    "event.commander.ransom_initiated",
    "event.commander.rescue_squad",
    "tech.ship",
}
SNAPSHOT_TAGS = {"posture.snapshot", "comp.snapshot"}


# ─── helpers ───────────────────────────────────────────────────────────────

def _fmt_ms(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60:02d}:{s % 60:02d}"


def _slug_from_dir(p: Path) -> tuple[int, str]:
    m = re.match(r"(\d+)_(.+)", p.name)
    return (int(m.group(1)), m.group(2)) if m else (-1, p.name)


def _load_matrix_report(matrix_dir: Path) -> dict[str, Any]:
    f = matrix_dir / "matrix_report.json"
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ─── per-civ section ───────────────────────────────────────────────────────

def render_civ_section(spec_key: str, civ_idx: int, slug: str,
                       matrix_row: dict[str, Any] | None,
                       claim_results: list,  # list[ClaimResult]
                       probes: list,         # list[Probe]
                       max_timeline: int = 12) -> list[str]:
    out: list[str] = []
    out.append(f"--- {spec_key} (idx={civ_idx:02d}, slug={slug}) ---")

    # 1) matrix-runner row (load + smoke).
    if matrix_row:
        verdict = "PASS" if matrix_row.get("ok") else "FAIL"
        ai_loaded = matrix_row.get("ai_scripts_loaded", "?")
        probes_n  = matrix_row.get("personality_probes_fired", "?")
        match_ms  = matrix_row.get("match_duration_ms", "?")
        out.append(f"matrix:    {verdict}  ai_loaded={ai_loaded}  "
                   f"probes_fired={probes_n}  match_ms={match_ms}")
    else:
        out.append("matrix:    (no row)")

    # 2) doctrine claims roll-up + every FAIL/UNKNOWN line.
    by_status = Counter(r.status for r in claim_results)
    if claim_results:
        verdict = vdc._verdict_for(claim_results)
        out.append(f"doctrine:  {verdict}  "
                   f"{by_status[vdc.PASS]} PASS / "
                   f"{by_status[vdc.FAIL]} FAIL / "
                   f"{by_status[vdc.UNKNOWN]} UNKNOWN")
        for r in claim_results:
            if r.status == vdc.PASS:
                continue
            mark = "✗" if r.status == vdc.FAIL else "?"
            line = f"    {mark} {r.claim:<28s} expected={r.expected!r}  actual={r.actual!r}"
            if r.note:
                line += f"  ({r.note})"
            out.append(line)
    else:
        out.append("doctrine:  (no spec claims for this civ)")

    # 3) compact event timeline — first hits of each interesting tag,
    # plus the LAST posture/comp snapshot for end-state context.
    seen_milestones: dict[str, Any] = {}  # tag → probe
    ship_lines: list[str] = []
    for p in probes:
        if p.tag in TIMELINE_TAGS and p.tag not in seen_milestones:
            seen_milestones[p.tag] = p
        if p.tag == "tech.ship":
            ship_lines.append(p)

    last_posture = None
    last_comp = None
    for p in probes:
        if p.tag == "posture.snapshot": last_posture = p
        if p.tag == "comp.snapshot":    last_comp    = p

    timeline_rows: list[tuple[int, str]] = []
    for tag, p in seen_milestones.items():
        atMs = int(p.fields.get("atMs", p.t))
        if tag == "meta.boot":
            bs = p.fields.get("buildStyle", "?")
            timeline_rows.append((atMs, f"meta.boot          buildStyle={bs}"))
        elif tag == "tech.ship":
            continue  # cards roll up below
        else:
            short = tag.removeprefix("milestone.").removeprefix("event.")
            extra = " ".join(f"{k}={v}" for k, v in p.fields.items()
                             if k not in ("atMs", "count"))
            timeline_rows.append((atMs, f"{short:<24s} {extra}"))

    if last_posture is not None:
        f = last_posture.fields
        timeline_rows.append((int(f.get("ageMs", last_posture.t)),
            f"posture.snapshot   ws={f.get('ws','?')} bs={f.get('bs','?')} "
            f"mdist={f.get('mdist','?')} walls={f.get('walls','?')} "
            f"docks={f.get('docks','?')} forts={f.get('forts','?')} "
            f"tposts={f.get('tposts','?')} age={f.get('age','?')}"))
    if last_comp is not None:
        f = last_comp.fields
        timeline_rows.append((int(f.get("ageMs", last_comp.t)),
            f"comp.snapshot      vil={f.get('vil','?')} inf={f.get('inf','?')} "
            f"cav={f.get('cav','?')} arty={f.get('arty','?')} "
            f"warship={f.get('warship','?')}"))

    timeline_rows.sort(key=lambda x: x[0])
    if timeline_rows:
        out.append("timeline:")
        for ms, line in timeline_rows[:max_timeline]:
            out.append(f"    {_fmt_ms(ms)}  {line}")
        if len(timeline_rows) > max_timeline:
            out.append(f"    … {len(timeline_rows) - max_timeline} more events truncated")

    # 4) cards summary (one line — names truncated).
    if ship_lines:
        names = [p.fields.get("name", "?") for p in ship_lines]
        out.append(f"cards:     shipped={len(names)}  "
                   f"first3=[{', '.join(names[:3])}]"
                   + ("  …" if len(names) > 3 else ""))

    out.append("")  # trailing blank
    return out


# ─── main ──────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--matrix-dir", type=Path, default=MATRIX_DIR)
    ap.add_argument("--spec",       type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--decks",      type=Path, default=DEFAULT_DECKS)
    ap.add_argument("--out",        type=Path, default=DEFAULT_OUT)
    ap.add_argument("--top-failures", type=int, default=10,
                    help="how many top regression rows to surface at the end")
    ap.add_argument("--max-timeline", type=int, default=12,
                    help="max timeline rows per civ (older events truncated)")
    args = ap.parse_args()

    if not args.spec.exists():
        print(f"missing {args.spec}; run extract_playstyle_spec.py first",
              file=sys.stderr)
        return 2
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    decks = (json.loads(args.decks.read_text(encoding="utf-8"))
             if args.decks.exists() else {})
    matrix_report = _load_matrix_report(args.matrix_dir)
    matrix_rows = {row.get("civ_name", "").lower(): row
                   for row in matrix_report.get("rows", [])}

    # Walk every per-civ artifact dir; even if a civ never produced a
    # match.log we still emit the section so the report enumerates ALL
    # civs the matrix was supposed to cover.
    civ_dirs = sorted([p for p in args.matrix_dir.iterdir() if p.is_dir()
                       and not p.name.startswith("_")],
                      key=lambda p: _slug_from_dir(p)[0])

    if not civ_dirs:
        print(f"no per-civ artifact dirs under {args.matrix_dir}", file=sys.stderr)
        return 2

    sections: list[str] = []
    civ_verdicts: dict[str, str] = {}
    failure_counter: Counter[str] = Counter()
    failure_civs: dict[str, list[str]] = defaultdict(list)

    for d in civ_dirs:
        idx, slug = _slug_from_dir(d)
        log = d / "match.log"
        # parse_probes returns a 3-tuple (probes, plan_closures, flat_closures);
        # this report only needs the flat probe list.
        probes = vdc.parse_probes([log])[0] if log.exists() else []

        # Pick the dominant (civ, ldr) pair for THIS civ's slot. Most
        # match.logs carry probes for 8 AIs in the batch, but the slot's
        # own row is the one we care about for the section header.
        actor_counts = Counter((p.civ, p.ldr) for p in probes)
        if not actor_counts:
            spec_key = None
        else:
            (civ, ldr), _ = actor_counts.most_common(1)[0]
            spec_key = vdc._resolve_spec_key(civ, ldr, spec)

        if spec_key is None:
            # No probes / unresolved — still emit a stub section so we see
            # the gap.
            sections.append(f"--- {slug} (idx={idx:02d}) ---")
            row = matrix_rows.get(slug)
            if row:
                sections.append(f"matrix:    {'PASS' if row.get('ok') else 'FAIL'}  (no probes parsed)")
            else:
                sections.append("matrix:    (no row)  (no probes parsed)")
            sections.append("")
            continue

        # Filter probes to ONLY this civ's actor for the section.
        my_probes = [p for p in probes
                     if vdc._resolve_spec_key(p.civ, p.ldr, spec) == spec_key]
        claims = spec["civs"][spec_key].get("claims", {})
        results = vdc.evaluate_civ(spec_key, claims, my_probes) if claims else []
        if decks:
            results.extend(vdc.evaluate_card_compliance(
                spec_key, my_probes[0].ldr if my_probes else "", my_probes, decks))

        sections.extend(render_civ_section(
            spec_key, idx, slug,
            matrix_rows.get(slug), results, my_probes,
            max_timeline=args.max_timeline,
        ))

        verdict = vdc._verdict_for(results) if results else "UNKNOWN"
        civ_verdicts[spec_key] = verdict
        for r in results:
            if r.status == vdc.FAIL:
                failure_counter[r.claim] += 1
                failure_civs[r.claim].append(spec_key)

    # ─── header (computed last so totals are right) ──────────────────────
    matrix_rows_n = len(matrix_report.get("rows", []))
    matrix_pass   = sum(1 for r in matrix_report.get("rows", []) if r.get("ok"))
    by_v = Counter(civ_verdicts.values())
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    header = [
        f"=== PLAYTEST REPORT  {ts} ===",
        f"matrix:   {matrix_pass}/{matrix_rows_n} loaded ok"
            if matrix_rows_n else "matrix:   (no matrix_report.json)",
        f"doctrine: {by_v[vdc.PASS]} pass / {by_v[vdc.FAIL]} fail / "
        f"{by_v[vdc.UNKNOWN]} unknown  (over {len(civ_verdicts)} civs with claims)",
        "",
    ]

    # ─── regression roll-up ──────────────────────────────────────────────
    regress: list[str] = ["=== TOP REGRESSIONS (claims that fail across many civs) ==="]
    for claim, n in failure_counter.most_common(args.top_failures):
        sample = failure_civs[claim][:5]
        more   = "" if n <= 5 else f" +{n - 5} more"
        regress.append(f"  {n:2d}× {claim:<28s} ({', '.join(sample)}{more})")
    if not failure_counter:
        regress.append("  (no failing claims — green report)")
    regress.append("")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(header + sections + regress) + "\n",
                        encoding="utf-8")
    print(f"wrote {args.out}  ({args.out.stat().st_size} bytes, "
          f"{len(civ_dirs)} civs, {sum(failure_counter.values())} failing claims)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
