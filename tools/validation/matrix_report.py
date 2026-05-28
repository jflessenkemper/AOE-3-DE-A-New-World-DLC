#!/usr/bin/env python3
"""matrix_report.py — Build artifacts/validation/cross_civ_matrix.html

Cross-civilisation compliance matrix showing all 40 ANW civs across all doctrine
claim dimensions. Data sources:
  1. playstyle_spec.json — canonical spec claims per civ
  2. artifacts/validation/doctrine_compliance_report.json — runtime results (partial)

Civs with no runtime data are shown as "NOT TESTED" in muted grey.
Civs with runtime data show PASS/FAIL/UNKNOWN per claim.

Output: artifacts/validation/cross_civ_matrix.html
"""
from __future__ import annotations

import argparse
import html
import json
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Ordered claim columns to display
CLAIM_COLUMNS = [
    ("wall_strategy",           "Wall Strategy"),
    ("first_military_building", "1st Mil Bldg"),
    ("first_barracks_before_ms","Barracks ≤ T"),
    ("first_dock_before_ms",    "Dock ≤ T"),
    ("first_wall_before_ms",    "Wall ≤ T"),
    ("military_distance_band",  "Mil Dist Band"),
    ("expects_forward",         "Fwd Base"),
    ("expects_cavalry",         "Cavalry"),
    ("expects_infantry",        "Infantry"),
    ("expects_artillery",       "Artillery"),
    ("expects_naval",           "Naval"),
    ("expects_treaty",          "Treaty"),
]

WALL_STRATEGY_NAMES = {
    0: "0 fortress",
    1: "1 jungle",
    2: "2 harbor",
    3: "3 perimeter",
    4: "4 rolling",
    5: "5 forward",
}

STATUS_CSS = {
    "PASS":        "status-pass",
    "FAIL":        "status-fail",
    "UNKNOWN":     "status-unknown",
    "NOT_TESTED":  "status-notested",
    "SKIP":        "status-skip",
}

STATUS_LABEL = {
    "PASS":       "PASS",
    "FAIL":       "FAIL",
    "UNKNOWN":    "?",
    "NOT_TESTED": "—",
    "SKIP":       "skip",
}


def fmt_spec_value(claim_key: str, val: object) -> str:
    if val is None:
        return "–"
    if claim_key == "wall_strategy":
        return WALL_STRATEGY_NAMES.get(val, str(val))
    if claim_key == "military_distance_band" and isinstance(val, list):
        return f"[{val[0]}, {val[1]}]"
    if claim_key.endswith("_before_ms") and isinstance(val, int):
        mins = val // 60000
        secs = (val % 60000) // 1000
        return f"≤{mins}:{secs:02d}"
    if isinstance(val, bool):
        return "yes" if val else "no"
    return str(val)


def build_html(spec: dict, compliance: dict) -> str:
    civs_spec = spec.get("civs", {})
    civs_compliance = compliance.get("civs", {})
    release_ready = compliance.get("release_readiness", {})

    # Build per-civ cell data
    rows: list[dict] = []
    for civ_key, civ in civs_spec.items():
        claims_spec = civ.get("claims", {})
        runtime = civs_compliance.get(civ_key)
        verdict = runtime["verdict"] if runtime else "NOT_TESTED"

        # Build per-claim cell data
        cells: list[dict] = []
        for claim_key, _ in CLAIM_COLUMNS:
            spec_val = claims_spec.get(claim_key)
            if spec_val is None:
                # This civ doesn't have this claim
                cells.append({"status": "SKIP", "spec": "–", "actual": "–", "note": "n/a"})
                continue

            spec_fmt = fmt_spec_value(claim_key, spec_val)

            if runtime is None:
                cells.append({"status": "NOT_TESTED", "spec": spec_fmt, "actual": "–", "note": "no runtime data"})
                continue

            # Find matching claim in runtime report
            matching_claim = None
            for c in runtime.get("claims", []):
                if c.get("claim") == claim_key:
                    matching_claim = c
                    break

            if matching_claim is None:
                cells.append({"status": "NOT_TESTED", "spec": spec_fmt, "actual": "–", "note": "claim not in report"})
            else:
                status = matching_claim.get("status", "UNKNOWN")
                actual_raw = matching_claim.get("actual")
                actual_fmt = str(actual_raw) if actual_raw is not None else "None"
                note = matching_claim.get("note", "")
                cells.append({"status": status, "spec": spec_fmt, "actual": actual_fmt, "note": note})

        rows.append({
            "civ_key": civ_key,
            "civ_label": civ.get("civ_label", civ_key),
            "leader_label": civ.get("leader_label", ""),
            "doctrine_label": civ.get("doctrine_label", ""),
            "verdict": verdict,
            "cells": cells,
        })

    # Summary stats
    n_total = len(rows)
    n_tested = sum(1 for r in rows if r["verdict"] != "NOT_TESTED")
    n_pass = sum(1 for r in rows if r["verdict"] == "PASS")
    n_fail = sum(1 for r in rows if r["verdict"] == "FAIL")
    n_untested = n_total - n_tested

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    # --- HTML generation ---
    col_headers = "".join(
        f'<th title="{claim_key}">{html.escape(label)}</th>'
        for claim_key, label in CLAIM_COLUMNS
    )

    row_html_parts: list[str] = []
    for row in rows:
        verdict_css = STATUS_CSS.get(row["verdict"], "status-notested")
        verdict_lbl = STATUS_LABEL.get(row["verdict"], row["verdict"])
        cells_html = ""
        for cell in row["cells"]:
            css = STATUS_CSS.get(cell["status"], "status-notested")
            lbl = STATUS_LABEL.get(cell["status"], cell["status"])
            title_text = html.escape(f"spec: {cell['spec']}\nactual: {cell['actual']}\n{cell['note']}")
            cells_html += f'<td class="cell {css}" title="{title_text}">{lbl}</td>'

        row_html_parts.append(
            f'<tr class="civ-row">'
            f'<td class="civ-name">'
            f'<span class="civ-label">{html.escape(row["civ_label"])}</span>'
            f'<span class="leader-label">{html.escape(row["leader_label"])}</span>'
            f'</td>'
            f'<td class="doctrine-label">{html.escape(row["doctrine_label"])}</td>'
            f'<td class="verdict-cell {verdict_css}">{verdict_lbl}</td>'
            f'{cells_html}'
            f'</tr>'
        )

    rows_html = "\n".join(row_html_parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ANW Cross-Civ Doctrine Compliance Matrix</title>
<style>
  :root {{
    --bg: #1a1a2e; --surface: #16213e; --border: #0f3460;
    --text: #e0e0e0; --muted: #888;
    --pass: #22c55e; --fail: #ef4444; --unknown: #f59e0b;
    --notested: #555; --skip: #334;
    --header-bg: #0f3460;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font: 13px/1.4 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); padding: 16px; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 4px; }}
  .meta {{ color: var(--muted); font-size: 0.8rem; margin-bottom: 16px; }}
  .summary {{ display: flex; gap: 24px; margin-bottom: 16px; font-size: 0.85rem; }}
  .summary span {{ padding: 4px 10px; border-radius: 4px; font-weight: 600; }}
  .s-pass {{ background: #14532d; color: var(--pass); }}
  .s-fail {{ background: #7f1d1d; color: var(--fail); }}
  .s-unknown {{ background: #451a03; color: var(--unknown); }}
  .s-notested {{ background: #222; color: var(--muted); }}
  .matrix-wrapper {{ overflow-x: auto; }}
  table {{ border-collapse: collapse; min-width: 100%; }}
  th, td {{ border: 1px solid var(--border); padding: 4px 6px; white-space: nowrap; }}
  th {{ background: var(--header-bg); font-size: 0.75rem; text-align: center; position: sticky; top: 0; z-index: 2; }}
  th:first-child, th:nth-child(2), th:nth-child(3) {{ text-align: left; }}
  td.civ-name {{ min-width: 120px; }}
  .civ-label {{ display: block; font-weight: 600; font-size: 0.82rem; }}
  .leader-label {{ display: block; font-size: 0.72rem; color: var(--muted); }}
  td.doctrine-label {{ font-size: 0.75rem; color: #9ca3af; }}
  td.cell {{ text-align: center; font-size: 0.75rem; font-weight: 600; min-width: 52px; cursor: default; }}
  td.verdict-cell {{ text-align: center; font-weight: 700; font-size: 0.8rem; min-width: 60px; }}
  .status-pass {{ background: #052e16; color: var(--pass); }}
  .status-fail {{ background: #450a0a; color: var(--fail); }}
  .status-unknown {{ background: #291700; color: var(--unknown); }}
  .status-notested {{ background: #1c1c1c; color: var(--notested); }}
  .status-skip {{ background: #1a1a1a; color: #444; }}
  tr:hover td {{ filter: brightness(1.3); }}
  .legend {{ margin-top: 20px; font-size: 0.75rem; color: var(--muted); }}
  .legend span {{ margin-right: 16px; }}
</style>
</head>
<body>
<h1>ANW Cross-Civ Doctrine Compliance Matrix</h1>
<div class="meta">Generated {ts} &nbsp;|&nbsp; Source: playstyle_spec.json + doctrine_compliance_report.json</div>
<div class="summary">
  <span class="s-pass">PASS: {n_pass}</span>
  <span class="s-fail">FAIL: {n_fail}</span>
  <span class="s-notested">NOT TESTED: {n_untested}</span>
  <span style="color:var(--muted)">Total civs: {n_total}</span>
</div>
<div class="matrix-wrapper">
<table>
<thead>
<tr>
  <th>Civilisation</th>
  <th>Doctrine</th>
  <th>Verdict</th>
  {col_headers}
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
</div>
<div class="legend">
  <strong>Cell legend:</strong>
  <span style="color:var(--pass)">PASS</span>
  <span style="color:var(--fail)">FAIL</span>
  <span style="color:var(--unknown)">? = UNKNOWN (probe fired but no data)</span>
  <span style="color:var(--muted)">— = NOT TESTED (no runtime log)</span>
  <span style="color:#444">skip = claim not applicable to this civ</span>
  <br><br>
  Hover a cell to see the spec value, observed value, and note.
</div>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build cross-civ doctrine compliance matrix HTML.")
    parser.add_argument(
        "--spec",
        type=Path,
        default=REPO_ROOT / "playstyle_spec.json",
    )
    parser.add_argument(
        "--compliance",
        type=Path,
        default=REPO_ROOT / "artifacts" / "validation" / "doctrine_compliance_report.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "artifacts" / "validation" / "cross_civ_matrix.html",
    )
    args = parser.parse_args()

    if not args.spec.exists():
        print(f"ERROR: spec not found: {args.spec}")
        raise SystemExit(1)

    with open(args.spec) as f:
        spec = json.load(f)

    compliance: dict = {}
    if args.compliance.exists():
        with open(args.compliance) as f:
            compliance = json.load(f)
    else:
        print(f"WARNING: compliance report not found at {args.compliance}; showing spec-only matrix")

    html_content = build_html(spec, compliance)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html_content)
    print(f"[matrix_report] Written {args.out}")
    print(f"[matrix_report] Civs: {len(spec.get('civs', {}))}")


if __name__ == "__main__":
    main()
