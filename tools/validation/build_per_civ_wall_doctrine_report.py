#!/usr/bin/env python3
"""Build per-civ wall doctrine compliance HTML report.

Reads:
  - artifacts/validation/per_civ_wall_knobs.json  (validation results)
  - tools/ai_design/wall_knob_calibration.py       (CALIBRATION dict + doctrine comments)
  - a_new_world.html                               (walling-block doctrine HTML summaries)

Writes:
  - artifacts/validation/per_civ_wall_doctrine_report.html

Usage:
    python3 tools/validation/build_per_civ_wall_doctrine_report.py
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
JSON_PATH = REPO_ROOT / "artifacts" / "validation" / "per_civ_wall_knobs.json"
CALIBRATION_PY = REPO_ROOT / "tools" / "ai_design" / "wall_knob_calibration.py"
HTML_SRC = REPO_ROOT / "a_new_world.html"
OUT_PATH = REPO_ROOT / "artifacts" / "validation" / "per_civ_wall_doctrine_report.html"

STRATEGY_LABELS = {
    0: "FortressRing",
    1: "Choke",
    2: "Coastal",
    3: "Frontier",
    4: "Urban",
    5: "Mobile",
}

# Subtle background tints per strategy (HSL)
STRATEGY_COLORS = {
    0: "#e8f0fe",   # blue-tinted  — Fortress
    1: "#fef9e7",   # yellow-tinted — Choke
    2: "#e0f7fa",   # cyan-tinted  — Coastal
    3: "#f9fbe7",   # green-tinted — Frontier
    4: "#fce4ec",   # pink-tinted  — Urban
    5: "#f3e5f5",   # purple-tinted — Mobile
}


# ---------------------------------------------------------------------------
# 1. Load JSON results
# ---------------------------------------------------------------------------
def load_json_results(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 2. Load CALIBRATION from wall_knob_calibration.py
# ---------------------------------------------------------------------------
def load_calibration(path: Path) -> dict:
    """Import CALIBRATION dict from the calibration module."""
    try:
        spec = importlib.util.spec_from_file_location("wall_knob_calibration", path)
        mod = importlib.util.module_from_spec(spec)
        # Prevent argparse from consuming our sys.argv
        _saved_argv = sys.argv[:]
        sys.argv = [str(path)]
        spec.loader.exec_module(mod)
        sys.argv = _saved_argv
        return mod.CALIBRATION
    except Exception as exc:
        print(f"[WARN] importlib load failed ({exc}), falling back to ast.parse", file=sys.stderr)
        return _load_calibration_ast(path)


def _load_calibration_ast(path: Path) -> dict:
    """Fallback: extract CALIBRATION via ast.literal_eval on the dict body."""
    import ast
    src = path.read_text()
    # Find CALIBRATION = { ... }  (greedy to end of dict)
    m = re.search(r"^CALIBRATION\s*=\s*(\{.+?\n\})", src, re.DOTALL | re.MULTILINE)
    if not m:
        raise RuntimeError("Could not locate CALIBRATION dict in calibration file")
    # Replace dict(...) constructor calls with {}-style dicts for literal_eval
    block = m.group(1)
    # Replace   "KEY": dict(a=1, b=2)  ->  "KEY": {"a": 1, "b": 2}
    def _dict_call_to_literal(m2):
        body = m2.group(1)
        # Turn kw=val pairs into "kw": val
        items = re.sub(r'(\w+)\s*=\s*', r'"\1": ', body)
        return "{" + items + "}"
    block = re.sub(r'\bdict\(([^)]+)\)', _dict_call_to_literal, block, flags=re.DOTALL)
    return ast.literal_eval(block)


# ---------------------------------------------------------------------------
# 3. Parse walling-block summaries from a_new_world.html
# ---------------------------------------------------------------------------
# The HTML uses comment markers:
#   <!-- WALLING-START CivName -->
#   <details class="walling-block"><summary>Walling Doctrine &mdash; ...</summary>
#   <!-- WALLING-END -->
# Some markers have no name: <!-- WALLING-START --> — those are inside a
# <details class="nation-node" data-name="Civ ..."> block.

def parse_walling_blocks(html_path: Path) -> dict[str, str]:
    """Return mapping: html_civ_label -> doctrine summary text.

    Two marker styles exist in the HTML:
      A) Named:   <!-- WALLING-START CivName --> ... <details class="walling-block">...
      B) Unnamed: <!-- WALLING-START --> inside a nation-node block that has data-name="...".
         For unnamed markers we scan backwards from the marker position to find the
         nearest preceding data-name= attribute within the same nation-node.
    """
    src = html_path.read_text(encoding="utf-8")

    result: dict[str, str] = {}

    # --- Pattern A: named markers ---
    named_re = re.compile(
        r'<!--\s*WALLING-START\s+([^-\n][^\n]*?)\s*-->'   # label (no leading dash, single line)
        r'[^<]*'                                            # optional whitespace/newlines
        r'<details class="walling-block">'
        r'<summary>(Walling Doctrine\s*&mdash;\s*[^<]+)</summary>',
        re.DOTALL,
    )
    for m in named_re.finditer(src):
        label = m.group(1).strip()
        summary = _decode_html_entities(m.group(2).strip())
        result[label] = summary

    # --- Pattern B: blank markers — look backward to find the nearest data-name ---
    # Find all blank WALLING-START positions
    blank_re = re.compile(r'<!--\s*WALLING-START\s*-->')
    summary_re = re.compile(
        r'<details class="walling-block">'
        r'<summary>(Walling Doctrine\s*&mdash;\s*[^<]+)</summary>'
    )
    data_name_re = re.compile(r'data-name="([^"]+)"')

    for blank_m in blank_re.finditer(src):
        start_pos = blank_m.start()

        # Search backwards (in the text before this marker) for the nearest data-name
        preceding = src[:start_pos]
        # Find the last data-name occurrence before this position
        dn_matches = list(data_name_re.finditer(preceding))
        if not dn_matches:
            continue
        data_name = dn_matches[-1].group(1).strip()

        # Find the doctrine summary that follows the blank marker
        sm = summary_re.search(src, blank_m.end())
        if sm is None:
            continue
        summary = _decode_html_entities(sm.group(1).strip())

        # Store under full data-name and also under first word
        result[data_name] = summary
        civ_word = data_name.split()[0]
        if civ_word not in result:
            result[civ_word] = summary

    return result


def _decode_html_entities(s: str) -> str:
    """Decode common HTML entities."""
    s = s.replace("&mdash;", "\u2014")
    s = s.replace("&ndash;", "\u2013")
    s = s.replace("&amp;", "&")
    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    s = s.replace("&#x27;", "'")
    s = s.replace("&nbsp;", "\u00a0")
    return s


# ---------------------------------------------------------------------------
# 4. Build civ → doctrine summary mapping using a canonical lookup table
# ---------------------------------------------------------------------------

# Maps engine key → (html label variants to try, in order)
# These come from the WALLING-START comment labels and data-name prefixes seen in the HTML.
ENGINE_TO_HTML_LABEL: dict[str, list[str]] = {
    "DEInca":              ["Inca"],
    "Germans":             ["Germans Frederick Great", "Germans"],
    "Ottomans":            ["Ottomans Suleiman", "Ottomans"],
    "DEMaltese":           ["Maltese"],
    "Chinese":             ["Chinese"],
    "French":              ["French"],
    "Indians":             ["Indians"],
    "DEEthiopians":        ["Ethiopians"],
    "ANWCanadians":        ["Canadians"],
    "ANWChileans":         ["Chileans"],
    "ANWPeruvians":        ["Peruvians"],
    "ANWEgyptians":        ["Egyptians"],
    "ANWFinnish":          ["Finnish"],
    "XPAztec":             ["Aztecs"],
    "ANWHaitians":         ["Haitians"],
    "ANWIndonesians":      ["Indonesians"],
    "ANWMayans":           ["Mayans"],
    "British":             ["British"],
    "Portuguese":          ["Portuguese Henry Navigator", "Portuguese"],
    "Dutch":               ["Dutch"],
    "ANWBarbary":          ["Barbary States"],
    "ANWSouthAfricans":    ["South Africans"],
    "ANWBrazil":           ["Brazil"],
    "DEHausa":             ["Hausa"],
    "Russians":            ["Russians Ivan Terrible", "Russians"],
    "ANWRomanians":        ["Romanians"],
    "ANWRevFrance":        ["French Republic"],
    "DEItalians":          ["Italians"],
    "DEMexicans":          ["Mexicans"],
    "DEAmericans":         ["United States Washington", "United"],
    "ANWNapoleonicFrance": ["Napoleonic France"],
    "ANWArgentines":       ["Argentines"],
    "ANWColumbians":       ["Columbians"],
    "XPIroquois":          ["Haudenosaunee"],
    "ANWHungarians":       ["Hungarians"],
    "Japanese":            ["Japanese"],
    "XPSioux":             ["Lakota"],
    "Spanish":             ["Spanish Isabella Castile", "Spanish"],
    "DESwedish":           ["Swedes Gustavus Adolphus Swedish", "Swedes"],
    "ANWTexians":          ["Texians"],
}

# Human-readable display names for each engine key
DISPLAY_NAMES: dict[str, str] = {
    "DEInca":              "Inca (Pachacuti)",
    "Germans":             "Germans (Frederick)",
    "Ottomans":            "Ottomans (Suleiman)",
    "DEMaltese":           "Maltese (Valette)",
    "Chinese":             "Chinese (Kangxi)",
    "French":              "French (Louis XVIII)",
    "Indians":             "Indians (Shivaji)",
    "DEEthiopians":        "Ethiopians (Menelik)",
    "ANWCanadians":        "Canadians (Brock)",
    "ANWChileans":         "Chileans (O'Higgins)",
    "ANWPeruvians":        "Peruvians (Santa Cruz)",
    "ANWEgyptians":        "Egyptians (Muhammad Ali)",
    "ANWFinnish":          "Finnish (Mannerheim)",
    "XPAztec":             "Aztecs (Montezuma)",
    "ANWHaitians":         "Haitians (Toussaint)",
    "ANWIndonesians":      "Indonesians (Diponegoro)",
    "ANWMayans":           "Mayans (Canek)",
    "British":             "British (Elizabeth)",
    "Portuguese":          "Portuguese (Henry)",
    "Dutch":               "Dutch (Maurice)",
    "ANWBarbary":          "Barbary (Barbarossa)",
    "ANWSouthAfricans":    "South Africans (Kruger)",
    "ANWBrazil":           "Brazil (Pedro I)",
    "DEHausa":             "Hausa (Usman)",
    "Russians":            "Russians (Ivan IV)",
    "ANWRomanians":        "Romanians (Cuza)",
    "ANWRevFrance":        "Rev. France (Robespierre)",
    "DEItalians":          "Italians (Garibaldi)",
    "DEMexicans":          "Mexicans (Hidalgo)",
    "DEAmericans":         "Americans (Washington)",
    "ANWNapoleonicFrance": "Napoleonic France (Napoleon)",
    "ANWArgentines":       "Argentines (San Martín)",
    "ANWColumbians":       "Colombians (Bolívar)",
    "XPIroquois":          "Iroquois (Hiawatha)",
    "ANWHungarians":       "Hungarians (Kossuth)",
    "Japanese":            "Japanese (Tokugawa)",
    "XPSioux":             "Sioux (Chief Gall)",
    "Spanish":             "Spanish (Isabella)",
    "DESwedish":           "Swedish (Gustavus)",
    "ANWTexians":          "Texians (Sam Houston)",
}


def lookup_doctrine_summary(engine_key: str, html_map: dict[str, str]) -> str:
    """Return the HTML doctrine summary for engine_key, or '(not found)' if missing."""
    candidates = ENGINE_TO_HTML_LABEL.get(engine_key, [engine_key])
    for label in candidates:
        if label in html_map:
            return html_map[label]
    # Last resort: try case-insensitive partial match on first word of engine_key
    prefix = re.sub(r'^(ANW|DE|XP)', '', engine_key).lower()
    for k, v in html_map.items():
        if k.lower().startswith(prefix):
            return v
    return "(not found in HTML)"


# ---------------------------------------------------------------------------
# 5. Build the HTML report
# ---------------------------------------------------------------------------
KNOB_COLS = [
    ("radius",       "Radius"),
    ("gates",        "Gates"),
    ("age2stone",    "Age2Stone"),
    ("trigger_age",  "TrigAge"),
    ("seg_len",      "SegLen"),
    ("towers",       "Towers"),
    ("secondary",    "Secondary"),
    ("vils",         "Vils"),
    ("fwd_bias",     "FwdBias"),
    ("outer_ring",   "OuterRing"),
    ("outposts",     "Outposts"),
    ("repair",       "Repair"),
    ("closure_pct",  "Closure%"),
    ("no_water",     "NoWater"),
]


def build_html(results: list[dict], calibration: dict, html_map: dict[str, str]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")

    # Sort by strategy
    results_sorted = sorted(results, key=lambda r: (r["strategy"], r["civ"]))

    rows_html = []
    unmatched: list[str] = []

    for r in results_sorted:
        engine_key = r["engine_key"]
        strategy = r["strategy"]
        status = r["status"]
        mismatches = r.get("mismatches", [])

        cal = calibration.get(engine_key, {})
        doctrine_summary = lookup_doctrine_summary(engine_key, html_map)
        if doctrine_summary == "(not found in HTML)":
            unmatched.append(engine_key)

        strategy_label = STRATEGY_LABELS.get(strategy, f"Strategy{strategy}")
        bg_color = STRATEGY_COLORS.get(strategy, "#ffffff")
        display_name = DISPLAY_NAMES.get(engine_key, engine_key)

        status_badge = (
            '<span class="badge pass">PASS</span>'
            if status == "PASS"
            else f'<span class="badge fail">FAIL<br><small>{", ".join(mismatches)}</small></span>'
        )

        # Extract "after the dash" part from doctrine summary for brevity
        # "Walling Doctrine — FortressRing: Vauban Star Fort" → "FortressRing: Vauban Star Fort"
        doc_display = doctrine_summary
        if "\u2014" in doc_display:
            doc_display = doc_display.split("\u2014", 1)[1].strip()

        # Build knob cells
        knob_cells = ""
        for knob_key, _ in KNOB_COLS:
            val = cal.get(knob_key, "—")
            knob_cells += f"<td>{val}</td>"

        comment = cal.get("doctrine", "—")

        rows_html.append(f"""
  <tr style="background:{bg_color}">
    <td class="civ-name">{display_name}</td>
    <td class="engine-key"><code>{engine_key}</code></td>
    <td class="strategy-cell">{strategy} — {strategy_label}</td>
    <td class="doctrine-col" title="{_esc(doctrine_summary)}">{_esc(doc_display)}</td>
    <td class="comment-col">{_esc(comment)}</td>
    {knob_cells}
    <td class="status-cell">{status_badge}</td>
  </tr>""")

    rows_joined = "\n".join(rows_html)

    knob_headers = "".join(f"<th>{label}</th>" for _, label in KNOB_COLS)

    unmatched_note = ""
    if unmatched:
        unmatched_note = f'<p class="warn">WARNING: {len(unmatched)} civ(s) had no HTML doctrine block match: {", ".join(unmatched)}</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ANW Per-Civ Wall Doctrine Compliance Report</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 13px;
    margin: 0;
    padding: 16px;
    background: #f5f5f5;
    color: #222;
  }}
  h1 {{ font-size: 1.3em; margin: 0 0 4px; }}
  .meta {{ color: #666; font-size: 0.85em; margin-bottom: 12px; }}
  .summary-bar {{
    display: flex; gap: 16px; flex-wrap: wrap;
    margin-bottom: 12px; font-size: 0.9em;
  }}
  .summary-bar span {{
    padding: 4px 10px; border-radius: 4px; font-weight: bold;
  }}
  .summary-bar .total {{ background: #e3e3e3; }}
  .summary-bar .pass  {{ background: #c8e6c9; color: #1b5e20; }}
  .summary-bar .fail  {{ background: #ffcdd2; color: #b71c1c; }}
  .warn {{
    background: #fff3e0; border-left: 4px solid #f57c00;
    padding: 8px 12px; margin-bottom: 12px;
  }}
  .table-wrap {{ overflow-x: auto; }}
  table {{
    border-collapse: collapse;
    width: 100%;
    min-width: 1400px;
    background: #fff;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12);
  }}
  th {{
    background: #37474f;
    color: #fff;
    padding: 6px 8px;
    text-align: left;
    font-size: 0.8em;
    position: sticky;
    top: 0;
    white-space: nowrap;
  }}
  td {{
    padding: 5px 8px;
    border-bottom: 1px solid #e0e0e0;
    vertical-align: top;
  }}
  tr:hover td {{ filter: brightness(0.96); }}
  .civ-name {{ font-weight: 600; white-space: nowrap; min-width: 160px; }}
  .engine-key {{ white-space: nowrap; }}
  .engine-key code {{ font-size: 0.85em; background: #f0f0f0; padding: 1px 4px; border-radius: 3px; }}
  .strategy-cell {{ white-space: nowrap; font-weight: 500; }}
  .doctrine-col {{ max-width: 220px; font-size: 0.85em; }}
  .comment-col {{ max-width: 200px; font-size: 0.8em; color: #444; }}
  .status-cell {{ text-align: center; white-space: nowrap; }}
  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-weight: bold;
    font-size: 0.85em;
  }}
  .badge.pass {{ background: #c8e6c9; color: #1b5e20; }}
  .badge.fail {{ background: #ffcdd2; color: #b71c1c; }}
  .legend {{
    display: flex; flex-wrap: wrap; gap: 10px;
    margin: 12px 0; font-size: 0.82em;
  }}
  .legend-item {{ padding: 3px 10px; border-radius: 3px; }}
</style>
</head>
<body>
<h1>ANW Per-Civ Wall Doctrine Compliance Report</h1>
<div class="meta">Generated: {ts} &nbsp;|&nbsp; Source: per_civ_wall_knobs.json + wall_knob_calibration.py + a_new_world.html</div>

<div class="summary-bar">
  <span class="total">Total: {total}</span>
  <span class="pass">PASS: {passed}</span>
  <span class="fail">FAIL: {total - passed}</span>
</div>

<div class="legend">
  <strong>Strategy key:</strong>
  <span class="legend-item" style="background:{STRATEGY_COLORS[0]}">0 — FortressRing</span>
  <span class="legend-item" style="background:{STRATEGY_COLORS[1]}">1 — Choke</span>
  <span class="legend-item" style="background:{STRATEGY_COLORS[2]}">2 — Coastal</span>
  <span class="legend-item" style="background:{STRATEGY_COLORS[3]}">3 — Frontier</span>
  <span class="legend-item" style="background:{STRATEGY_COLORS[4]}">4 — Urban</span>
  <span class="legend-item" style="background:{STRATEGY_COLORS[5]}">5 — Mobile</span>
</div>

{unmatched_note}

<div class="table-wrap">
<table>
<thead>
<tr>
  <th>Civ</th>
  <th>Engine Key</th>
  <th>Strategy</th>
  <th>HTML Doctrine Summary</th>
  <th>Calibration Comment</th>
  {knob_headers}
  <th>Status</th>
</tr>
</thead>
<tbody>
{rows_joined}
</tbody>
</table>
</div>

</body>
</html>
"""


def _esc(s: str) -> str:
    """HTML-escape a string for safe insertion."""
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


# ---------------------------------------------------------------------------
# 6. Main
# ---------------------------------------------------------------------------
def main():
    # Load inputs
    json_data = load_json_results(JSON_PATH)
    calibration = load_calibration(CALIBRATION_PY)
    html_map = parse_walling_blocks(HTML_SRC)

    results = json_data["results"]
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")

    # Build and write report
    html_content = build_html(results, calibration, html_map)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html_content, encoding="utf-8")

    print(f"{passed}/{total} PASS — report at {OUT_PATH}")


if __name__ == "__main__":
    main()
