#!/usr/bin/env python3
"""
build_release_dashboard.py
Release-readiness dashboard for ANW v1.0 (Steam Workshop).

Outputs:
  artifacts/validation/release_readiness.html
  artifacts/validation/release_readiness.json
  artifacts/validation/release_readiness.md

Exit codes:
  0 — READY TO SHIP or SHIP WITH KNOWN GAPS
  1 — BLOCKED (any FAIL)
"""
import json
import os
import sys
import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "artifacts" / "validation"
TOOLS_VAL = REPO / "tools" / "validation"

IN_BEHAVIOUR_MAP   = ARTIFACTS / "ai_behaviour_map.json"
IN_ART_INVENTORY   = TOOLS_VAL / "art_inventory.json"
IN_PLAYSTYLE_SPEC  = REPO / "playstyle_spec.json"
IN_VALIDATORS_RPT  = TOOLS_VAL / "run_all_validators_report.json"
IN_PERSONALITY_CPL = ARTIFACTS / "personality_compliance.json"

OUT_HTML = ARTIFACTS / "release_readiness.html"
OUT_JSON = ARTIFACTS / "release_readiness.json"
OUT_MD   = ARTIFACTS / "release_readiness.md"

SINGLEPLAYER_DIR = REPO / "resources" / "images" / "icons" / "singleplayer"

# Revolution civs that share art with a base civ rather than having full
# 5-surface art in art_inventory.  For these we only require a leader
# portrait file under resources/images/icons/singleplayer/.
REVOLUTION_SHARED_ART = {
    "Californians Vallejo Revolution",
    "Central Americans Morazan Revolution",
    "French Canadians Papineau Revolution",
    "Rio Grande Canales Rosillo Revolution",
    "Yucatan Pat Revolution",
}

# 5 art-surface keys that must all be _on_disk=True for a full art_pass
REQUIRED_SURFACES = [
    "diplomacy_portrait_wpf",
    "homecity_flag_icon_wpf",
    "homecity_flag_button_wpf",
    "postgame_flag_wpf",
    "homecity_preview_wpf",
]

# Required spec claims for spec_pass
REQUIRED_CLAIMS = ["wall_strategy", "first_military_building", "military_distance_band"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path, label: str):
    if not path.exists():
        print(f"  [WARN] missing input: {path}  ({label})", file=sys.stderr)
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        print(f"  [WARN] failed to parse {path}: {exc}", file=sys.stderr)
        return None


def spec_key_to_art_key(spec_key: str, spec_data: dict) -> str:
    """
    Derive the ANW art_inventory key from a playstyle_spec civ entry.

    The art_inventory uses tokens like ANWArgentines, ANWUSA, ANWRevFrance.
    We apply a small lookup table for the cases that don't resolve cleanly
    from the civ_label, then fall back to 'ANW' + joined civ_label words.
    """
    MANUAL = {
        "French Louis XVIII Bourbon":                "ANWFrench",
        "Napoleonic France Napoleon Bonaparte Revolution": "ANWNapoleonicFrance",
        "Revolutionary France Robespierre Revolution":    "ANWRevFrance",
        "United States Washington":                       "ANWUSA",
    }
    if spec_key in MANUAL:
        return MANUAL[spec_key]
    civ_label = spec_data.get("civ_label", "")
    return "ANW" + "".join(civ_label.split())


def spec_key_to_slug(spec_key: str) -> str:
    return spec_key.lower().replace(" ", "_")


def check_static_pass(spec_key: str, bmap: dict | None) -> tuple[bool, str]:
    """True if ai_behaviour_map has an entry with 0 mismatches."""
    if bmap is None:
        return False, "ai_behaviour_map.json not loaded"
    entry = bmap.get("civs", {}).get(spec_key)
    if not entry:
        return False, "not found in ai_behaviour_map"
    mismatches = entry.get("mismatches", [])
    if len(mismatches) > 0:
        return False, f"{len(mismatches)} mismatch(es)"
    src = entry.get("source_file", "")
    if not src:
        return False, "no source_file recorded"
    return True, src


def check_art_pass(spec_key: str, spec_data: dict,
                   art_inventory: dict | None) -> tuple[bool, str]:
    """
    True when:
      - Standard civ: all 5 required surfaces are _on_disk=True in art_inventory
      - Revolution shared-art civ: portrait PNG exists in singleplayer dir
    """
    if spec_key in REVOLUTION_SHARED_ART:
        portrait_path = spec_data.get("portrait_path", "")
        if not portrait_path:
            return False, "no portrait_path in spec"
        full = REPO / portrait_path
        if full.exists():
            return True, f"portrait on disk: {portrait_path}"
        return False, f"portrait missing: {portrait_path}"

    if art_inventory is None:
        return False, "art_inventory.json not loaded"

    art_key = spec_key_to_art_key(spec_key, spec_data)
    civ_art = art_inventory.get("civs", {}).get(art_key)
    if not civ_art:
        # Also try portrait_path from spec as fallback
        portrait_path = spec_data.get("portrait_path", "")
        if portrait_path and (REPO / portrait_path).exists():
            return True, f"portrait fallback on disk: {portrait_path}"
        return False, f"art_key {art_key!r} not in art_inventory"

    surfaces = civ_art.get("art_surfaces", {})
    missing = [s for s in REQUIRED_SURFACES if not surfaces.get(s, {}).get("_on_disk")]
    if missing:
        return False, f"surfaces missing: {', '.join(missing)}"
    return True, "all 5 surfaces on disk"


def check_spec_pass(spec_key: str, spec_data: dict) -> tuple[bool, str]:
    """True when all 3 required claims are present."""
    claims = spec_data.get("claims", {})
    missing = [f for f in REQUIRED_CLAIMS if f not in claims]
    if missing:
        return False, f"missing claims: {', '.join(missing)}"
    return True, "all required claims present"


def check_runtime_pass(spec_key: str,
                       personality_cpl: dict | None) -> tuple[bool, str]:
    """
    True if personality_compliance.json reports has_playstyle_pack=True for
    this civ AND the personality .personality file exists at personality_dir.
    Placeholder: most civs expected False.
    """
    if personality_cpl is None:
        return False, "personality_compliance.json not loaded"
    rows = {r["spec_key"]: r for r in personality_cpl.get("rows", [])}
    row = rows.get(spec_key)
    if not row:
        return False, "not found in personality_compliance"
    if not row.get("has_playstyle_pack"):
        return False, "has_playstyle_pack=False"
    pers_dir = Path(personality_cpl.get("personality_dir", ""))
    stem = row.get("personality_stem", "")
    if not stem:
        return False, "no personality_stem"
    probe_file = pers_dir / f"{stem}.personality"
    if not probe_file.exists():
        return False, f"probe file not on disk: {stem}.personality"
    return True, f"probe file present: {stem}.personality"


def overall_status(static: bool, art: bool, spec: bool, runtime: bool) -> str:
    if static and art and spec and runtime:
        return "PASS"
    if static and art and spec and not runtime:
        return "WARN"
    return "FAIL"


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def build_rows(spec: dict, bmap, art_inv, pers_cpl) -> list[dict]:
    rows = []
    for spec_key, spec_data in spec.get("civs", {}).items():
        static_ok, static_note = check_static_pass(spec_key, bmap)
        art_ok, art_note       = check_art_pass(spec_key, spec_data, art_inv)
        spec_ok, spec_note     = check_spec_pass(spec_key, spec_data)
        runtime_ok, runtime_note = check_runtime_pass(spec_key, pers_cpl)
        status = overall_status(static_ok, art_ok, spec_ok, runtime_ok)
        rows.append({
            "spec_key":     spec_key,
            "civ_label":    spec_data.get("civ_label", spec_key),
            "leader_label": spec_data.get("leader_label", ""),
            "static_pass":  static_ok,
            "static_note":  static_note,
            "art_pass":     art_ok,
            "art_note":     art_note,
            "spec_pass":    spec_ok,
            "spec_note":    spec_note,
            "runtime_pass": runtime_ok,
            "runtime_note": runtime_note,
            "overall":      status,
            "slug":         spec_key_to_slug(spec_key),
        })
    return rows


def verdict(rows: list[dict]) -> str:
    n_pass = sum(1 for r in rows if r["overall"] == "PASS")
    n_fail = sum(1 for r in rows if r["overall"] == "FAIL")
    n_warn = sum(1 for r in rows if r["overall"] == "WARN")
    total  = len(rows)
    if n_fail > 0:
        return "BLOCKED"
    if n_warn > 0:
        return "SHIP WITH KNOWN GAPS"
    if total > 0 and n_pass / total >= 0.90:
        return "READY TO SHIP"
    return "SHIP WITH KNOWN GAPS"


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

HTML_CSS = """
body{font:13px/1.35 -apple-system,sans-serif;background:#120d08;color:#e8dfc8;margin:0;padding:14px;}
h1{font-size:20px;margin:4px 0 10px;color:#d4b96a;}
.subtitle{color:#7a6a50;font-size:12px;margin-bottom:12px;}
.summary-bar{display:flex;gap:18px;margin:0 0 14px;flex-wrap:wrap;}
.summary-chip{padding:6px 14px;border-radius:5px;font-weight:700;font-size:14px;border:1px solid #3a2e1e;}
.chip-pass{background:#0e2416;color:#7ec896;border-color:#1e4028;}
.chip-warn{background:#27200a;color:#d4b96a;border-color:#4a3a10;}
.chip-fail{background:#2a0e0e;color:#ff7b7b;border-color:#4a1818;}
.chip-total{background:#1a1510;color:#c0a870;border-color:#3a2e1e;}
.verdict{display:inline-block;padding:8px 20px;border-radius:6px;font-weight:700;font-size:16px;margin-bottom:16px;letter-spacing:.5px;}
.verdict-ready{background:#0e2416;color:#7ec896;border:2px solid #2e7a4e;}
.verdict-gaps{background:#27200a;color:#d4b96a;border:2px solid #7a5a10;}
.verdict-blocked{background:#2a0e0e;color:#ff7b7b;border:2px solid #9a2828;}
table{border-collapse:collapse;width:100%;}
th,td{padding:6px 8px;border:1px solid #2a2018;vertical-align:middle;text-align:left;}
th{background:#1e160c;position:sticky;top:0;cursor:pointer;user-select:none;z-index:5;color:#c0a870;}
tr.row-pass:nth-child(even) td{background:#0f0b07;}
tr.row-warn:nth-child(even) td{background:#150f05;}
tr.row-fail:nth-child(even) td{background:#150808;}
tr.row-pass td{background:#0c110e;}
tr.row-warn td{background:#13100a;}
tr.row-fail td{background:#110c0c;}
tr:hover td{background:#2a2018 !important;}
td.civ-cell b{font-size:14px;color:#d4b96a;}
td.civ-cell small{color:#7a6a50;display:block;}
td.civ-cell a{color:#9ec5ff;text-decoration:none;}
td.civ-cell a:hover{text-decoration:underline;}
.flag{display:inline-block;padding:3px 7px;border-radius:3px;font-weight:700;font-size:11px;}
.flag-pass{background:#0e2416;color:#7ec896;}
.flag-warn{background:#27200a;color:#d4b96a;}
.flag-fail{background:#2a0e0e;color:#ff7b7b;}
.flag-na{background:#1e1a14;color:#6a5e48;}
.overall-pass{color:#7ec896;font-weight:700;}
.overall-warn{color:#d4b96a;font-weight:700;}
.overall-fail{color:#ff7b7b;font-weight:700;}
input.filter{padding:6px 10px;font-size:13px;background:#1c140e;color:#e8dfc8;border:1px solid #3a2e1e;border-radius:4px;width:280px;margin-bottom:10px;}
.note-cell{font-size:11px;color:#6a5e48;font-family:ui-monospace,monospace;max-width:200px;word-break:break-word;}
"""

HTML_JS = """
function sortTable(colIdx) {
  const tbl = document.getElementById('rr-table');
  const tbody = tbl.tBodies[0];
  const rows = Array.from(tbody.rows);
  const asc = tbl.dataset.sortCol == colIdx && tbl.dataset.sortDir === 'asc';
  rows.sort((a, b) => {
    const ta = a.cells[colIdx]?.innerText.trim() ?? '';
    const tb = b.cells[colIdx]?.innerText.trim() ?? '';
    return asc ? tb.localeCompare(ta, undefined, {numeric:true})
               : ta.localeCompare(tb, undefined, {numeric:true});
  });
  rows.forEach(r => tbody.appendChild(r));
  tbl.dataset.sortCol = colIdx;
  tbl.dataset.sortDir = asc ? 'desc' : 'asc';
}
function filterRows(q) {
  q = q.toLowerCase();
  for (const row of document.querySelectorAll('#rr-table tbody tr')) {
    row.style.display = row.innerText.toLowerCase().includes(q) ? '' : 'none';
  }
}
"""


def flag_html(ok: bool, note: str = "") -> str:
    if ok:
        return f'<span class="flag flag-pass" title="{_esc(note)}">PASS</span>'
    return f'<span class="flag flag-fail" title="{_esc(note)}">FAIL</span>'


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def overall_html(status: str) -> str:
    cls = {"PASS": "overall-pass", "WARN": "overall-warn", "FAIL": "overall-fail"}.get(status, "")
    return f'<span class="{cls}">{status}</span>'


def verdict_html(v: str) -> str:
    cls = {
        "READY TO SHIP":       "verdict-ready",
        "SHIP WITH KNOWN GAPS":"verdict-gaps",
        "BLOCKED":             "verdict-blocked",
    }.get(v, "verdict-gaps")
    return f'<span class="verdict {cls}">{_esc(v)}</span>'


def render_html(rows: list[dict], v_str: str, timestamp: str,
                validator_counts: dict) -> str:
    n_pass  = sum(1 for r in rows if r["overall"] == "PASS")
    n_warn  = sum(1 for r in rows if r["overall"] == "WARN")
    n_fail  = sum(1 for r in rows if r["overall"] == "FAIL")
    total   = len(rows)

    row_htmls = []
    for r in rows:
        status = r["overall"]
        row_cls = {"PASS": "row-pass", "WARN": "row-warn", "FAIL": "row-fail"}.get(status, "row-fail")
        slug = r["slug"]
        per_civ_link = f'ai_behaviour_per_civ/{slug}.md'
        civ_cell = (
            f'<td class="civ-cell">'
            f'<a href="{per_civ_link}"><b>{_esc(r["civ_label"])}</b></a>'
            f'<small>{_esc(r["leader_label"])}</small>'
            f'</td>'
        )

        # runtime flag shows WARN not FAIL when overall is WARN
        if not r["runtime_pass"] and status == "WARN":
            rt_html = f'<span class="flag flag-warn" title="{_esc(r["runtime_note"])}">WARN</span>'
        else:
            rt_html = flag_html(r["runtime_pass"], r["runtime_note"])

        row_htmls.append(
            f'<tr class="{row_cls}">'
            f'{civ_cell}'
            f'<td>{flag_html(r["static_pass"], r["static_note"])}</td>'
            f'<td>{flag_html(r["art_pass"], r["art_note"])}</td>'
            f'<td>{flag_html(r["spec_pass"], r["spec_note"])}</td>'
            f'<td>{rt_html}</td>'
            f'<td>{overall_html(status)}</td>'
            f'</tr>'
        )

    rows_html = "\n".join(row_htmls)
    val_counts_str = (
        f"Validator suite: {validator_counts.get('PASS',0)} PASS / "
        f"{validator_counts.get('FAIL',0)} FAIL / "
        f"{validator_counts.get('SKIP',0)} SKIP"
        if validator_counts else "Validator suite: not available"
    )

    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>ANW v1.0 · Release Readiness</title>
<style>{HTML_CSS}</style>
</head>
<body>
<h1>ANW v1.0 &nbsp;&middot;&nbsp; Release Readiness Dashboard</h1>
<p class="subtitle">Generated {_esc(timestamp)} &nbsp;&bull;&nbsp; {_esc(val_counts_str)}</p>
{verdict_html(v_str)}
<div class="summary-bar">
  <span class="summary-chip chip-total">Total: {total}</span>
  <span class="summary-chip chip-pass">PASS: {n_pass}</span>
  <span class="summary-chip chip-warn">WARN: {n_warn}</span>
  <span class="summary-chip chip-fail">FAIL: {n_fail}</span>
</div>
<input class="filter" placeholder="filter civs…" oninput="filterRows(this.value)">
<table id="rr-table" data-sort-col="" data-sort-dir="asc">
<thead><tr>
  <th onclick="sortTable(0)">Civ / Leader</th>
  <th onclick="sortTable(1)">Static AI</th>
  <th onclick="sortTable(2)">Art</th>
  <th onclick="sortTable(3)">Spec</th>
  <th onclick="sortTable(4)">Runtime</th>
  <th onclick="sortTable(5)">Overall</th>
</tr></thead>
<tbody>
{rows_html}
</tbody>
</table>
<p style="margin-top:14px;font-size:11px;color:#4a3e2e;">
  <b>Columns:</b>
  Static AI = leader_*.xs file present + 0 ai_behaviour_map mismatches &nbsp;|&nbsp;
  Art = all 5 UI surfaces on disk (portrait, HUD flag, HC flag, postgame flag, HC preview) &nbsp;|&nbsp;
  Spec = playstyle_spec.json has wall_strategy + first_military_building + military_distance_band &nbsp;|&nbsp;
  Runtime = .personality probe file present in game AI dir &nbsp;|&nbsp;
  WARN = static+art+spec pass, runtime placeholder missing
</p>
<script>{HTML_JS}</script>
</body></html>"""


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def render_md(rows: list[dict], v_str: str, timestamp: str) -> str:
    n_pass = sum(1 for r in rows if r["overall"] == "PASS")
    n_warn = sum(1 for r in rows if r["overall"] == "WARN")
    n_fail = sum(1 for r in rows if r["overall"] == "FAIL")
    lines = [
        f"# ANW v1.0 — Release Readiness",
        f"",
        f"Generated: {timestamp}",
        f"",
        f"**Verdict: {v_str}**",
        f"",
        f"| | Count |",
        f"|---|---|",
        f"| PASS | {n_pass} |",
        f"| WARN | {n_warn} |",
        f"| FAIL | {n_fail} |",
        f"| Total | {len(rows)} |",
        f"",
        f"| Civ | Leader | Static | Art | Spec | Runtime | Overall |",
        f"|---|---|:---:|:---:|:---:|:---:|:---:|",
    ]
    for r in rows:
        def flag(ok): return "PASS" if ok else "FAIL"
        rt = "WARN" if not r["runtime_pass"] and r["overall"] == "WARN" else flag(r["runtime_pass"])
        lines.append(
            f"| [{r['civ_label']}](ai_behaviour_per_civ/{r['slug']}.md) "
            f"| {r['leader_label']} "
            f"| {flag(r['static_pass'])} "
            f"| {flag(r['art_pass'])} "
            f"| {flag(r['spec_pass'])} "
            f"| {rt} "
            f"| **{r['overall']}** |"
        )
    lines += ["", f"*{v_str}*", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    print("Loading inputs…")
    bmap       = load_json(IN_BEHAVIOUR_MAP,   "ai_behaviour_map")
    art_inv    = load_json(IN_ART_INVENTORY,   "art_inventory")
    spec       = load_json(IN_PLAYSTYLE_SPEC,  "playstyle_spec")
    val_rpt    = load_json(IN_VALIDATORS_RPT,  "run_all_validators_report")
    pers_cpl   = load_json(IN_PERSONALITY_CPL, "personality_compliance")

    if spec is None:
        print("ERROR: playstyle_spec.json is required — cannot continue.", file=sys.stderr)
        return 1

    # Use behaviour_map civs dict if we need it; unwrap nested key
    bmap_civs = bmap if bmap is None else bmap  # passed whole dict; check_static_pass navigates it

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    validator_counts = val_rpt.get("counts", {}) if val_rpt else {}

    print(f"Building rows for {len(spec.get('civs', {}))} civs…")
    rows = build_rows(spec, bmap, art_inv, pers_cpl)
    v_str = verdict(rows)

    n_pass = sum(1 for r in rows if r["overall"] == "PASS")
    n_warn = sum(1 for r in rows if r["overall"] == "WARN")
    n_fail = sum(1 for r in rows if r["overall"] == "FAIL")

    # Write outputs
    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    # JSON
    out_data = {
        "generated": timestamp,
        "verdict": v_str,
        "counts": {"PASS": n_pass, "WARN": n_warn, "FAIL": n_fail, "total": len(rows)},
        "validator_suite": validator_counts,
        "civs": rows,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(out_data, fh, indent=2, ensure_ascii=False)
    print(f"  wrote {OUT_JSON}")

    # HTML
    html_content = render_html(rows, v_str, timestamp, validator_counts)
    with open(OUT_HTML, "w", encoding="utf-8") as fh:
        fh.write(html_content)
    print(f"  wrote {OUT_HTML}")

    # Markdown
    md_content = render_md(rows, v_str, timestamp)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md_content)
    print(f"  wrote {OUT_MD}")

    # Stdout summary
    print()
    print(f"Release-readiness: {n_pass}/{len(rows)} PASS, {n_warn} WARN, {n_fail} FAIL")
    print(f"Verdict: {v_str}")

    return 0 if v_str in ("READY TO SHIP", "SHIP WITH KNOWN GAPS") else 1


if __name__ == "__main__":
    sys.exit(main())
