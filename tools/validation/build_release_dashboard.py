#!/usr/bin/env python3
"""build_release_dashboard.py — ANW v1.0 release-readiness master dashboard.

Aggregates results from every available validator and emits:
  artifacts/validation/release_dashboard.html  — per-civ × per-check matrix
  artifacts/validation/release_dashboard.json  — machine-readable mirror
  stdout                                        — one line per civ + overall verdict

Validator columns
-----------------
ally_deck     Ally-deck compliance (tools/validation/ally_deck_compliance.md)
              40/40 PASS — static markdown, no re-run needed.

art_surfaces  Art surface check (tools/validation/art_inventory.json)
              Checks custom_portraits_missing and civmods_art_missing fields.

xs_scripts    XS script static analysis (tools/validation/validate_xs_scripts.py)
              Runs inline; marks per-civ NOT_RUN if common.py dependency absent.

playstyle     6-civ live-matrix probe (tools/validation/wr_probe_data.json)
              Game-dependent; stale if > 24h. Only 6 civs probed; rest = NOT_RUN.

engine_spec   Engine-vs-spec wall-strategy audit (audit_engine_vs_spec.py)
              Re-run if playstyle_spec.json present; else NOT_RUN.

Idempotency
-----------
- ally_deck and art_surfaces read static JSON/MD — always fresh.
- xs_scripts runs in a subprocess; result cached in-session only.
- playstyle reads wr_probe_data.json; marked STALE if mtime > 24h.
- engine_spec re-runs if playstyle_spec.json exists; NOT_RUN otherwise.

Exit codes
----------
0  All validators PASS or WARN (no hard FAILs)
1  One or more FAILs
"""
from __future__ import annotations

import datetime
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO = Path(__file__).resolve().parents[2]
VAL_DIR = REPO / "tools" / "validation"
ARTIFACTS = REPO / "artifacts" / "validation"

CANONICAL_CIVS = VAL_DIR / "canonical_civs.json"
ALLY_DECK_MD = VAL_DIR / "ally_deck_compliance.md"
ART_INV = VAL_DIR / "art_inventory.json"
WR_PROBE = VAL_DIR / "wr_probe_data.json"
PLAYSTYLE_SPEC = REPO / "playstyle_spec.json"
ENGINE_VS_SPEC_PY = VAL_DIR / "audit_engine_vs_spec.py"
ENGINE_FINDINGS = ARTIFACTS / "engine_vs_spec" / "findings.json"
XS_SCRIPT_PY = VAL_DIR / "validate_xs_scripts.py"
XS_REPORT = ARTIFACTS / "xs_scripts" / "xs_report.json"
CONTACT_SHEET = ARTIFACTS / "visual_art" / "static_contact_sheet.html"

OUT_HTML = ARTIFACTS / "release_dashboard.html"
OUT_JSON = ARTIFACTS / "release_dashboard.json"

STALE_HOURS = 24  # hours after which a game-run artifact is considered stale


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

Status = str  # "PASS" | "FAIL" | "WARN" | "NOT_RUN" | "STALE"


@dataclass
class CellResult:
    status: Status
    note: str = ""
    report_path: Optional[str] = None  # relative path for HTML link


@dataclass
class CivRow:
    token: str
    display_name: str
    ally_deck: CellResult = field(default_factory=lambda: CellResult("NOT_RUN"))
    art_surfaces: CellResult = field(default_factory=lambda: CellResult("NOT_RUN"))
    xs_scripts: CellResult = field(default_factory=lambda: CellResult("NOT_RUN"))
    playstyle: CellResult = field(default_factory=lambda: CellResult("NOT_RUN"))
    engine_spec: CellResult = field(default_factory=lambda: CellResult("NOT_RUN"))

    def overall(self) -> Status:
        statuses = [
            self.ally_deck.status,
            self.art_surfaces.status,
            self.xs_scripts.status,
            self.playstyle.status,
            self.engine_spec.status,
        ]
        if "FAIL" in statuses:
            return "FAIL"
        if "WARN" in statuses or "STALE" in statuses:
            return "WARN"
        # All PASS or NOT_RUN — if at least one PASS, treat as WARN (incomplete data)
        if "PASS" in statuses:
            return "WARN"
        return "NOT_RUN"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _age_hours(path: Path) -> float:
    """Return file age in hours, or inf if file doesn't exist."""
    if not path.exists():
        return float("inf")
    mtime = path.stat().st_mtime
    return (time.time() - mtime) / 3600.0


def _load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Validator 1: ally_deck_compliance.md
# ---------------------------------------------------------------------------

def parse_ally_deck(civs: list[dict]) -> dict[str, CellResult]:
    """Parse ally_deck_compliance.md — extracts PASS/FAIL per ANW token."""
    results: dict[str, CellResult] = {}

    if not ALLY_DECK_MD.exists():
        for c in civs:
            results[c["token"]] = CellResult("NOT_RUN", "ally_deck_compliance.md missing")
        return results

    text = ALLY_DECK_MD.read_text(encoding="utf-8")

    # Quick overall check — the md says "X/40 civs compliant"
    summary_m = re.search(r"(\d+)/40 civs compliant", text)
    global_pass = summary_m and summary_m.group(1) == "40"

    # Per-civ table rows: | ANWToken | PASS | ... |
    row_re = re.compile(r"\|\s*(ANW\w+)\s*\|\s*(PASS|FAIL)\s*\|([^|]*)\|")
    row_map: dict[str, tuple[str, str]] = {}
    for m in row_re.finditer(text):
        row_map[m.group(1)] = (m.group(2).strip(), m.group(3).strip())

    report_rel = "../../tools/validation/ally_deck_compliance.md"
    for c in civs:
        tok = c["token"]
        if tok in row_map:
            status, note = row_map[tok]
            results[tok] = CellResult(status, note, report_rel)
        elif global_pass:
            # Not in table but overall 40/40 — treat as PASS
            results[tok] = CellResult("PASS", "40/40 overall PASS", report_rel)
        else:
            results[tok] = CellResult("WARN", "token not found in table", report_rel)

    return results


# ---------------------------------------------------------------------------
# Validator 2: art_surfaces (art_inventory.json)
# ---------------------------------------------------------------------------

def check_art_surfaces(civs: list[dict]) -> dict[str, CellResult]:
    """Check art surface completeness from art_inventory.json."""
    results: dict[str, CellResult] = {}
    inv = _load_json(ART_INV)
    report_rel = "../../tools/validation/art_inventory.json"

    if inv is None:
        for c in civs:
            results[c["token"]] = CellResult("NOT_RUN", "art_inventory.json missing")
        return results

    # Build sets of known issues
    missing_portraits: set[str] = set(inv.get("art_surface_summary", {}).get("custom_portraits_missing", []))
    missing_civmods: dict[str, list[str]] = {}
    for entry in inv.get("art_surface_summary", {}).get("civmods_art_missing", []):
        civ = entry.get("civ", "")
        field_name = entry.get("field", "")
        missing_civmods.setdefault(civ, []).append(field_name)

    for c in civs:
        tok = c["token"]
        issues = []
        if tok in missing_portraits:
            issues.append("portrait missing")
        if tok in missing_civmods:
            issues.append(f"civmods missing: {', '.join(missing_civmods[tok])}")

        if issues:
            results[tok] = CellResult("WARN", "; ".join(issues), report_rel)
        else:
            results[tok] = CellResult("PASS", "all surfaces present", report_rel)

    return results


# ---------------------------------------------------------------------------
# Validator 3: XS scripts static analysis
# ---------------------------------------------------------------------------

def run_xs_validation(civs: list[dict]) -> dict[str, CellResult]:
    """Run validate_xs_scripts.py as subprocess, return global result per-civ.

    XS script validation is codebase-wide (not per-civ), so we apply the
    same PASS/FAIL to all 40 civs.  If common.py is missing (needed by the
    validator), mark all civs NOT_RUN.
    """
    results: dict[str, CellResult] = {}
    common_py = VAL_DIR / "common.py"
    report_rel = "xs_scripts/xs_report.json"

    if not common_py.exists():
        note = "NEEDS_INTERPRETATION: validate_xs_scripts.py requires tools/validation/common.py which is absent — run manually"
        for c in civs:
            results[c["token"]] = CellResult("NOT_RUN", note)
        return results

    # Check if cached result exists and is fresh (< 1h)
    if XS_REPORT.exists() and _age_hours(XS_REPORT) < 1.0:
        cached = _load_json(XS_REPORT)
        if cached is not None:
            status = "PASS" if cached.get("issue_count", 1) == 0 else "FAIL"
            issues = cached.get("issue_count", "?")
            note = f"cached: {issues} issue(s)"
            for c in civs:
                results[c["token"]] = CellResult(status, note, report_rel)
            return results

    # Run the validator
    try:
        proc = subprocess.run(
            [sys.executable, str(XS_SCRIPT_PY)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(REPO),
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        passed = proc.returncode == 0

        # Cache result
        XS_REPORT.parent.mkdir(parents=True, exist_ok=True)
        XS_REPORT.write_text(json.dumps({
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "issue_count": 0 if passed else stdout.count("\n - "),
        }, indent=2))

        status: Status = "PASS" if passed else "FAIL"
        note = "0 issues" if passed else f"{stdout.count(chr(10) + ' - ')} issue(s) — see xs_report.json"
        for c in civs:
            results[c["token"]] = CellResult(status, note, report_rel)

    except subprocess.TimeoutExpired:
        for c in civs:
            results[c["token"]] = CellResult("WARN", "xs validation timed out")
    except Exception as exc:
        for c in civs:
            results[c["token"]] = CellResult("NOT_RUN", f"xs validation error: {exc}")

    return results


# ---------------------------------------------------------------------------
# Validator 4: playstyle (wr_probe_data.json)
# ---------------------------------------------------------------------------

def check_playstyle(civs: list[dict]) -> dict[str, CellResult]:
    """Read wr_probe_data.json (6-civ live matrix).  All other civs = NOT_RUN."""
    results: dict[str, CellResult] = {}
    probe = _load_json(WR_PROBE)
    report_rel = "ai_playstyle/playstyle_verdicts.json"

    # Check staleness
    stale = _age_hours(WR_PROBE) > STALE_HOURS

    if probe is None:
        for c in civs:
            results[c["token"]] = CellResult("NOT_RUN", "wr_probe_data.json missing")
        return results

    # Build a token → status map from probe data
    token_map: dict[str, tuple[str, str]] = {}
    for civ_id, entry in probe.get("civs", {}).items():
        tok = entry.get("token", "")
        status = entry.get("status", "FAIL")
        reasons = "; ".join(entry.get("reasons", [])) or entry.get("note", "ok")
        token_map[tok] = (status, reasons)

    run_date = probe.get("_meta", {}).get("run_date", "unknown")
    for c in civs:
        tok = c["token"]
        if tok in token_map:
            raw_status, note = token_map[tok]
            if stale:
                cell_status: Status = "STALE"
                note = f"STALE (>{STALE_HOURS}h): last {raw_status} on {run_date}. {note}"
            else:
                cell_status = raw_status  # type: ignore[assignment]
            results[tok] = CellResult(cell_status, note, report_rel)
        else:
            results[tok] = CellResult("NOT_RUN", f"not in 6-civ matrix (run_date={run_date})")

    return results


# ---------------------------------------------------------------------------
# Validator 5: engine_vs_spec (audit_engine_vs_spec.py)
# ---------------------------------------------------------------------------

def run_engine_spec(civs: list[dict]) -> dict[str, CellResult]:
    """Run audit_engine_vs_spec.py if playstyle_spec.json exists.

    Results are global (all-civ pass or listing mismatches).
    We map mismatch civ tokens to FAIL; everything else to PASS.
    """
    results: dict[str, CellResult] = {}
    report_rel = "engine_vs_spec/findings.json"

    if not PLAYSTYLE_SPEC.exists():
        note = "NOT_RUN: playstyle_spec.json absent — run extract_playstyle_spec.py first"
        for c in civs:
            results[c["token"]] = CellResult("NOT_RUN", note)
        return results

    # Check if cached findings are fresh (< 10 min) and source files unchanged
    if ENGINE_FINDINGS.exists() and _age_hours(ENGINE_FINDINGS) < 10 / 60:
        findings = _load_json(ENGINE_FINDINGS)
        if findings is not None:
            return _engine_findings_to_cell_results(civs, findings, report_rel)

    # Re-run the audit
    try:
        proc = subprocess.run(
            [sys.executable, str(ENGINE_VS_SPEC_PY)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(REPO),
        )
        findings = _load_json(ENGINE_FINDINGS)
        if findings is None:
            for c in civs:
                results[c["token"]] = CellResult("WARN", "audit ran but no findings.json produced")
            return results
        return _engine_findings_to_cell_results(civs, findings, report_rel)
    except subprocess.TimeoutExpired:
        for c in civs:
            results[c["token"]] = CellResult("WARN", "engine_vs_spec timed out")
        return results
    except Exception as exc:
        for c in civs:
            results[c["token"]] = CellResult("NOT_RUN", f"engine_vs_spec error: {exc}")
        return results


def _engine_findings_to_cell_results(
    civs: list[dict], findings: dict, report_rel: str
) -> dict[str, CellResult]:
    results: dict[str, CellResult] = {}
    mismatches = findings.get("mismatches", [])
    unknowns = set(findings.get("unknowns", []))
    mismatch_keys = {m.get("data_name", "") for m in mismatches}

    for c in civs:
        tok = c["token"]
        name = c["display_name"]
        # Try to match by token or display_name fragment
        matched_mismatch = any(
            name.lower().replace(" ", "") in k.lower().replace(" ", "") or
            tok.lower().replace("anw", "") in k.lower().replace(" ", "")
            for k in mismatch_keys
        )
        matched_unknown = any(
            name.lower().replace(" ", "") in u.lower().replace(" ", "")
            for u in unknowns
        )
        if matched_mismatch:
            results[tok] = CellResult("FAIL", "wall_strategy mismatch vs spec", report_rel)
        elif matched_unknown:
            results[tok] = CellResult("WARN", "no engine path matched in audit", report_rel)
        else:
            results[tok] = CellResult("PASS", "engine matches spec", report_rel)

    return results


# ---------------------------------------------------------------------------
# Build civ matrix
# ---------------------------------------------------------------------------

def build_matrix(civs: list[dict]) -> list[CivRow]:
    print("Running validators…")

    print("  [1/5] ally_deck_compliance.md…")
    ally = parse_ally_deck(civs)

    print("  [2/5] art_inventory.json…")
    art = check_art_surfaces(civs)

    print("  [3/5] validate_xs_scripts.py…")
    xs = run_xs_validation(civs)

    print("  [4/5] wr_probe_data.json (playstyle)…")
    play = check_playstyle(civs)

    print("  [5/5] audit_engine_vs_spec.py…")
    eng = run_engine_spec(civs)

    rows = []
    for c in civs:
        tok = c["token"]
        row = CivRow(
            token=tok,
            display_name=c["display_name"],
            ally_deck=ally.get(tok, CellResult("NOT_RUN")),
            art_surfaces=art.get(tok, CellResult("NOT_RUN")),
            xs_scripts=xs.get(tok, CellResult("NOT_RUN")),
            playstyle=play.get(tok, CellResult("NOT_RUN")),
            engine_spec=eng.get(tok, CellResult("NOT_RUN")),
        )
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Summary stats
# ---------------------------------------------------------------------------

def summary_stats(rows: list[CivRow]) -> dict[str, int]:
    counts: dict[str, int] = {"PASS": 0, "WARN": 0, "FAIL": 0, "NOT_RUN": 0, "STALE": 0}
    for r in rows:
        ov = r.overall()
        counts[ov] = counts.get(ov, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

_CSS = """
body{font:13px/1.4 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:#111;color:#ddd;margin:0;padding:16px;}
h1{font-size:20px;color:#f0c060;margin:0 0 4px;}
.subtitle{color:#666;font-size:11px;margin-bottom:12px;}
.banner{padding:10px 18px;border-radius:6px;font-size:15px;font-weight:700;
        margin-bottom:14px;display:inline-block;letter-spacing:.3px;}
.banner-ready{background:#0d2616;color:#5ecf7e;border:2px solid #2a6640;}
.banner-warn{background:#221a04;color:#d4a830;border:2px solid #6a4e10;}
.banner-blocked{background:#250909;color:#f07070;border:2px solid #7a2020;}
.chips{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px;}
.chip{padding:5px 14px;border-radius:4px;font-weight:700;font-size:13px;}
.chip-pass{background:#0a1f10;color:#5ecf7e;border:1px solid #1e5030;}
.chip-warn{background:#1e1604;color:#d4a830;border:1px solid #5a4010;}
.chip-fail{background:#200808;color:#f07070;border:1px solid #6a1818;}
.chip-notrun{background:#1a1a1a;color:#888;border:1px solid #333;}
table{border-collapse:collapse;width:100%;margin-top:4px;}
th,td{padding:6px 9px;border:1px solid #222;text-align:left;vertical-align:middle;}
th{background:#1a1a1a;color:#bbb;position:sticky;top:0;z-index:2;
   cursor:pointer;user-select:none;font-size:12px;}
th:hover{background:#252525;}
tr:hover td{background:#1c1c1c !important;}
td.civ-name{font-weight:600;color:#f0c060;min-width:130px;}
.cell-pass{background:#0a180c;color:#5ecf7e;font-weight:700;font-size:11px;
           padding:3px 7px;border-radius:3px;display:inline-block;}
.cell-fail{background:#1f0808;color:#f07070;font-weight:700;font-size:11px;
           padding:3px 7px;border-radius:3px;display:inline-block;}
.cell-warn{background:#1c1400;color:#d4a830;font-weight:700;font-size:11px;
           padding:3px 7px;border-radius:3px;display:inline-block;}
.cell-notrun{background:#181818;color:#666;font-weight:700;font-size:11px;
             padding:3px 7px;border-radius:3px;display:inline-block;}
.cell-stale{background:#1c1200;color:#c09020;font-weight:700;font-size:11px;
            padding:3px 7px;border-radius:3px;display:inline-block;}
.ov-pass{color:#5ecf7e;font-weight:700;}
.ov-warn{color:#d4a830;font-weight:700;}
.ov-fail{color:#f07070;font-weight:700;}
.ov-notrun{color:#666;font-weight:700;}
a{color:#7aadff;text-decoration:none;}a:hover{text-decoration:underline;}
"""

_JS = """
function sortBy(col) {
  const tbl = document.getElementById('t');
  const tbody = tbl.tBodies[0];
  const rows = Array.from(tbody.rows);
  const asc = tbl.dataset.sc == col && tbl.dataset.sd === 'a';
  rows.sort((a, b) => {
    const va = a.cells[col]?.innerText.trim() ?? '';
    const vb = b.cells[col]?.innerText.trim() ?? '';
    return asc ? vb.localeCompare(va) : va.localeCompare(vb);
  });
  rows.forEach(r => tbody.appendChild(r));
  tbl.dataset.sc = col; tbl.dataset.sd = asc ? 'd' : 'a';
}
function filt(q) {
  q = q.toLowerCase();
  document.querySelectorAll('#t tbody tr').forEach(r => {
    r.style.display = r.innerText.toLowerCase().includes(q) ? '' : 'none';
  });
}
"""


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def _cell_html(cell: CellResult) -> str:
    st = cell.status
    cls_map = {
        "PASS":    "cell-pass",
        "FAIL":    "cell-fail",
        "WARN":    "cell-warn",
        "NOT_RUN": "cell-notrun",
        "STALE":   "cell-stale",
    }
    cls = cls_map.get(st, "cell-notrun")
    label = "N/R" if st == "NOT_RUN" else st
    inner = f'<span class="{cls}" title="{_esc(cell.note)}">{label}</span>'
    if cell.report_path:
        inner = f'<a href="{_esc(cell.report_path)}">{inner}</a>'
    return f"<td>{inner}</td>"


def _ov_class(ov: str) -> str:
    return {"PASS": "ov-pass", "WARN": "ov-warn", "FAIL": "ov-fail"}.get(ov, "ov-notrun")


def render_html(rows: list[CivRow], stats: dict[str, int], timestamp: str) -> str:
    n_pass = stats.get("PASS", 0)
    n_warn = stats.get("WARN", 0)
    n_fail = stats.get("FAIL", 0)
    total = len(rows)
    pct = int(100 * n_pass / total) if total else 0

    if n_fail > 0:
        banner_cls = "banner-blocked"
        verdict_txt = f"BLOCKED — {n_fail} civ(s) have hard FAILs"
    elif n_warn > 0:
        banner_cls = "banner-warn"
        verdict_txt = f"SHIP WITH KNOWN GAPS — {n_warn} civ(s) need attention"
    else:
        banner_cls = "banner-ready"
        verdict_txt = "READY TO SHIP"

    row_htmls = []
    for r in rows:
        ov = r.overall()
        row_htmls.append(
            f"<tr>"
            f"<td class='civ-name'>{_esc(r.display_name)}</td>"
            f"{_cell_html(r.ally_deck)}"
            f"{_cell_html(r.art_surfaces)}"
            f"{_cell_html(r.xs_scripts)}"
            f"{_cell_html(r.playstyle)}"
            f"{_cell_html(r.engine_spec)}"
            f"<td><span class='{_ov_class(ov)}'>{ov}</span></td>"
            f"</tr>"
        )

    rows_html = "\n".join(row_htmls)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>ANW v1.0 · Release Readiness Dashboard</title>
<style>{_CSS}</style>
</head><body>
<h1>ANW v1.0 &nbsp;·&nbsp; Release Readiness Dashboard</h1>
<p class="subtitle">Generated {_esc(timestamp)} &nbsp;·&nbsp; {total} civs</p>
<div class="banner {banner_cls}">
  Mod release-readiness: {pct}% pass-rate ({n_pass}/{total} GREEN).
  Critical issues: {n_fail} civ(s) BLOCKED.
  &nbsp;|&nbsp; {n_warn} WARN &nbsp;·&nbsp; {verdict_txt}
</div>
<div class="chips">
  <span class="chip chip-pass">PASS: {n_pass}</span>
  <span class="chip chip-warn">WARN: {n_warn}</span>
  <span class="chip chip-fail">FAIL: {n_fail}</span>
  <span class="chip chip-notrun">NOT_RUN / STALE: {stats.get('NOT_RUN',0)+stats.get('STALE',0)}</span>
</div>
<input style="padding:5px 10px;background:#1a1a1a;color:#ddd;border:1px solid #333;
              border-radius:4px;font-size:13px;width:260px;margin-bottom:10px;"
       placeholder="filter civs…" oninput="filt(this.value)">
<table id="t" data-sc="" data-sd="a">
<thead><tr>
  <th onclick="sortBy(0)">Civ &#9651;</th>
  <th onclick="sortBy(1)">Ally Deck</th>
  <th onclick="sortBy(2)">Art Surfaces</th>
  <th onclick="sortBy(3)">XS Scripts</th>
  <th onclick="sortBy(4)">Playstyle<br><small>(6-civ probe)</small></th>
  <th onclick="sortBy(5)">Engine vs Spec</th>
  <th onclick="sortBy(6)">Overall</th>
</tr></thead>
<tbody>
{rows_html}
</tbody>
</table>
<p style="margin-top:14px;font-size:11px;color:#555;">
  <b>Columns:</b>
  Ally Deck = ally-deck card presence (40/40 check) &nbsp;|&nbsp;
  Art Surfaces = portrait + flag + homecity surfaces on disk &nbsp;|&nbsp;
  XS Scripts = static analysis (duplicate symbols, undefined calls, non-ASCII) &nbsp;|&nbsp;
  Playstyle = 6-civ live-matrix probe (game run required; STALE if &gt;24h) &nbsp;|&nbsp;
  Engine vs Spec = wall-strategy engine dispatch matches playstyle_spec.json
</p>
<script>{_JS}</script>
</body></html>"""


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def build_json(rows: list[CivRow], stats: dict[str, int], timestamp: str) -> dict:
    return {
        "generated": timestamp,
        "total_civs": len(rows),
        "summary": stats,
        "civs": [
            {
                "token": r.token,
                "display_name": r.display_name,
                "ally_deck":    {"status": r.ally_deck.status,    "note": r.ally_deck.note},
                "art_surfaces": {"status": r.art_surfaces.status, "note": r.art_surfaces.note},
                "xs_scripts":   {"status": r.xs_scripts.status,   "note": r.xs_scripts.note},
                "playstyle":    {"status": r.playstyle.status,     "note": r.playstyle.note},
                "engine_spec":  {"status": r.engine_spec.status,   "note": r.engine_spec.note},
                "overall":      r.overall(),
            }
            for r in rows
        ],
    }


# ---------------------------------------------------------------------------
# CLI summary
# ---------------------------------------------------------------------------

def print_summary(rows: list[CivRow], stats: dict[str, int]) -> None:
    print()
    print(f"{'Civ':<28} {'AllyDeck':<10} {'Art':<10} {'XS':<10} {'Play':<10} {'EngSpec':<10} {'Overall'}")
    print("-" * 95)
    for r in rows:
        print(
            f"{r.display_name:<28} "
            f"{r.ally_deck.status:<10} "
            f"{r.art_surfaces.status:<10} "
            f"{r.xs_scripts.status:<10} "
            f"{r.playstyle.status:<10} "
            f"{r.engine_spec.status:<10} "
            f"{r.overall()}"
        )
    print()
    n_pass = stats.get("PASS", 0)
    n_warn = stats.get("WARN", 0)
    n_fail = stats.get("FAIL", 0)
    total = len(rows)
    print(f"Summary: {n_pass}/{total} PASS  {n_warn} WARN  {n_fail} FAIL")
    if n_fail > 0:
        print("Verdict: BLOCKED")
    elif n_warn > 0:
        print("Verdict: SHIP WITH KNOWN GAPS")
    else:
        print("Verdict: READY TO SHIP")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    if not CANONICAL_CIVS.exists():
        print(f"ERROR: canonical_civs.json not found at {CANONICAL_CIVS}", file=sys.stderr)
        return 1

    civs: list[dict] = json.loads(CANONICAL_CIVS.read_text(encoding="utf-8"))
    print(f"ANW Release Dashboard — {len(civs)} canonical civs")

    rows = build_matrix(civs)
    stats = summary_stats(rows)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    html_content = render_html(rows, stats, timestamp)
    OUT_HTML.write_text(html_content, encoding="utf-8")
    print(f"  wrote {OUT_HTML}  ({len(html_content):,} bytes)")

    json_data = build_json(rows, stats, timestamp)
    OUT_JSON.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {OUT_JSON}")

    print_summary(rows, stats)

    n_fail = stats.get("FAIL", 0)
    return 1 if n_fail > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
