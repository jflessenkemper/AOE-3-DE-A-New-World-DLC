#!/usr/bin/env python3
"""
validate_probes_vs_spec.py
Post-hoc validator: reads per-civ match.log slices (from matrix_runner artifacts),
parses [ANWP v=2 ...] probe stream, and validates against the NATION_PLAYSTYLE spec
embedded in a_new_world.html.

CLI:
    python3 tools/validation/validate_probes_vs_spec.py \
        --matrix-dir tools/aoe3_automation/artifacts/matrix_runner \
        [--html a_new_world.html] \
        [--out report.md] [--json report.json]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants: wall strategy int → label (from game/ai/aiHeader.xs)
# ---------------------------------------------------------------------------
WALL_STRATEGY_INT_TO_NAME = {
    0: "FortressRing",
    1: "ChokepointSegments",
    2: "CoastalBatteries",
    3: "FrontierPalisades",
    4: "UrbanBarricade",
    5: "MobileNoWalls",
}

# Wall label string from HTML → expected int(s)
WALL_LABEL_TO_INT = {
    "fortress ring":          [0],
    "chokepoint segments":    [1],
    "coastal batteries":      [2],
    "frontier palisades":     [3],
    "urban barricade":        [4],
    "no walls (mobile)":      [5],
    # aliases / partial matches
    "no walls":               [5],
}

# Terrain label tokens from HTML → int (from game/ai/aiHeader.xs)
TERRAIN_LABEL_TO_INT = {
    "coast":         1,
    "river":         2,
    "forest edge":   3,
    "forest":        3,
    "plain":         4,
    "highland":      5,
    "wetland":       6,
    "desert/oasis":  7,
    "desert":        7,
    "oasis":         7,
    "jungle":        8,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize(s: str) -> str:
    """Strip spaces/punctuation/case for fuzzy comparison."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _wall_label_to_ints(label: str) -> list:
    """Return list of valid int values for a wallLabel string."""
    key = label.lower().strip()
    # direct lookup
    for k, v in WALL_LABEL_TO_INT.items():
        if k in key:
            return v
    return []


def _terrain_label_primaries(terrain_label: str) -> list:
    """Return list of terrain ints mentioned in terrainLabel (first term is primary)."""
    parts = re.split(r"[/,;]", terrain_label.lower())
    result = []
    for part in parts:
        part = part.strip()
        for k, v in TERRAIN_LABEL_TO_INT.items():
            if k in part:
                if v not in result:
                    result.append(v)
                break
    return result


# ---------------------------------------------------------------------------
# Parse NATION_PLAYSTYLE from HTML
# ---------------------------------------------------------------------------

def _extract_json_block(html_text: str) -> str:
    """
    Find 'window.NATION_PLAYSTYLE = {' and extract the balanced-brace JS object.
    Returns the raw string suitable for json.loads().
    """
    marker = "window.NATION_PLAYSTYLE = {"
    idx = html_text.find(marker)
    if idx == -1:
        raise ValueError("Could not find window.NATION_PLAYSTYLE in HTML")
    # start at the opening brace
    start = idx + len(marker) - 1
    depth = 0
    i = start
    in_string = False
    escape = False
    while i < len(html_text):
        ch = html_text[i]
        if escape:
            escape = False
        elif ch == "\\" and in_string:
            escape = True
        elif ch == '"' and not escape:
            in_string = not in_string
        elif not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return html_text[start : i + 1]
        i += 1
    raise ValueError("Unbalanced braces in NATION_PLAYSTYLE object")


def _unescape_html_entities(s: str) -> str:
    """Minimal HTML entity unescape for the spec values."""
    replacements = [
        ("&mdash;", "—"), ("&ndash;", "–"), ("&amp;", "&"),
        ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " "),
        ("&#39;", "'"), ("&apos;", "'"), ("&quot;", '"'),
    ]
    for entity, char in replacements:
        s = s.replace(entity, char)
    return s


def parse_nation_playstyle(html_path: str) -> dict:
    """
    Parse NATION_PLAYSTYLE from the HTML file.
    Returns dict keyed by the JS object key (e.g. "Aztecs Montezuma").
    """
    with open(html_path, encoding="utf-8", errors="replace") as f:
        html = f.read()

    html = _unescape_html_entities(html)
    raw = _extract_json_block(html)

    # The embedded object is valid JSON (all values are strings, arrays, booleans)
    # except it may contain HTML entities (already handled above).
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse failed on NATION_PLAYSTYLE: {exc}") from exc

    return data


# ---------------------------------------------------------------------------
# Parse probe lines from match.log
# ---------------------------------------------------------------------------
# Line format:
#   <timestamp_ms>   <hh:mm:ss>:  [ANWP v=2 t=<ms> p=<pid> civ=<name> ldr=<key> tag=<domain.name>] k=v k=v ...
# or (pre-game lines have no timestamp prefix).

PROBE_RE = re.compile(
    r"\[ANWP v=2\s+t=(\d+)\s+p=\d+\s+civ=([^\s]+)\s+ldr=([^\s]+)\s+tag=([^\]]+)\](.*)$"
)

def _parse_kv(kv_str: str) -> dict:
    """Parse a 'k=v k=v ...' string into a dict. Values may be quoted or unquoted."""
    result = {}
    # Match key=value pairs; value is either quoted or runs until next space
    for m in re.finditer(r'(\w+)=("(?:[^"\\]|\\.)*"|[^\s]+)', kv_str):
        k = m.group(1)
        v = m.group(2)
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        result[k] = v
    return result


def parse_probes(log_path: str) -> list:
    """
    Parse all [ANWP v=2 ...] lines from match.log.
    Returns list of dicts: {t, civ, ldr, tag, **kv}.
    """
    probes = []
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = PROBE_RE.search(line)
                if m:
                    t_ms = int(m.group(1))
                    civ = m.group(2)
                    ldr = m.group(3)
                    tag = m.group(4).strip()
                    kv = _parse_kv(m.group(5))
                    probes.append({"t": t_ms, "civ": civ, "ldr": ldr, "tag": tag, **kv})
    except FileNotFoundError:
        pass
    return probes


# ---------------------------------------------------------------------------
# Per-civ checks
# ---------------------------------------------------------------------------

def run_checks(probes: list, spec: dict) -> dict:
    """
    Run 7 checks against probe list and spec dict.
    Returns {
        "checks": {"c1": True/False/None, ...},  # None = INCOMPLETE
        "details": {"c1": "...", ...},
        "verdict": "PASS"/"FAIL"/"INCOMPLETE"
    }
    """
    checks = {}
    details = {}

    by_tag = {}
    for p in probes:
        by_tag.setdefault(p["tag"], []).append(p)

    # ------------------------------------------------------------------
    # Check 1: meta.boot present at t<5000 with buildStyle matching bsTitle
    # ------------------------------------------------------------------
    boot_events = by_tag.get("meta.boot", [])
    early_boots = [p for p in boot_events if p["t"] < 5000]

    bs_title = spec.get("bsTitle", "")
    expected_bs_norm = normalize(bs_title)

    if not boot_events:
        checks["c1"] = None
        details["c1"] = "No meta.boot events found (INCOMPLETE)"
    elif not early_boots:
        checks["c1"] = False
        details["c1"] = f"meta.boot found but not at t<5000 (earliest t={boot_events[0]['t']})"
    else:
        actual_bs = early_boots[0].get("buildStyle", "")
        actual_norm = normalize(actual_bs)
        if expected_bs_norm and actual_norm:
            checks["c1"] = (actual_norm == expected_bs_norm)
            details["c1"] = f"buildStyle={actual_bs!r} vs spec={bs_title!r}"
        else:
            checks["c1"] = None
            details["c1"] = f"buildStyle missing from probe or spec (probe={actual_bs!r}, spec={bs_title!r})"

    # ------------------------------------------------------------------
    # Check 2: meta.boot wallStrategy consistent with HTML wallLabel
    # ------------------------------------------------------------------
    wall_label = spec.get("wallLabel", "")
    expected_wall_ints = _wall_label_to_ints(wall_label)

    if not early_boots:
        checks["c2"] = None
        details["c2"] = "No early meta.boot events"
    else:
        actual_ws_str = early_boots[0].get("wallStrategy", "")
        if actual_ws_str == "":
            checks["c2"] = None
            details["c2"] = f"wallStrategy field missing from meta.boot; wallLabel={wall_label!r}"
        else:
            try:
                actual_ws = int(actual_ws_str)
            except ValueError:
                checks["c2"] = None
                details["c2"] = f"wallStrategy={actual_ws_str!r} is not int"
            else:
                if not expected_wall_ints:
                    checks["c2"] = None
                    details["c2"] = f"Could not map wallLabel={wall_label!r} to int"
                else:
                    checks["c2"] = actual_ws in expected_wall_ints
                    ws_name = WALL_STRATEGY_INT_TO_NAME.get(actual_ws, str(actual_ws))
                    details["c2"] = (
                        f"wallStrategy={actual_ws}({ws_name}) "
                        f"expected={expected_wall_ints}({wall_label!r})"
                    )

    # ------------------------------------------------------------------
    # Check 3: compliance.anchor present with terrPrimVec and terrPrim
    #          matching HTML terrainLabel primary term
    # ------------------------------------------------------------------
    terrain_label = spec.get("terrainLabel", "")
    expected_terr_ints = _terrain_label_primaries(terrain_label)
    primary_terr_int = expected_terr_ints[0] if expected_terr_ints else None

    anchor_events = by_tag.get("compliance.anchor", [])
    if not anchor_events:
        checks["c3"] = None
        details["c3"] = "No compliance.anchor events (INCOMPLETE)"
    else:
        anc = anchor_events[0]
        terr_prim_vec = anc.get("terrPrimVec", "")
        terr_prim_str = anc.get("terrPrim", "")
        if not terr_prim_vec:
            checks["c3"] = False
            details["c3"] = f"terrPrimVec empty in compliance.anchor"
        elif primary_terr_int is None:
            checks["c3"] = None
            details["c3"] = f"Cannot map terrainLabel={terrain_label!r} to int"
        else:
            try:
                actual_tp = int(terr_prim_str.split(":")[0])
            except (ValueError, IndexError):
                checks["c3"] = None
                details["c3"] = f"terrPrim={terr_prim_str!r} not parseable"
            else:
                checks["c3"] = actual_tp in expected_terr_ints
                details["c3"] = (
                    f"terrPrim={actual_tp} expected={expected_terr_ints} "
                    f"({terrain_label!r}), terrPrimVec={terr_prim_vec!r}"
                )

    # ------------------------------------------------------------------
    # Check 4: ≥3 compliance.bldg snapshots; wall logic by wallLabel
    # ------------------------------------------------------------------
    bldg_events = by_tag.get("compliance.bldg", [])
    mobile = "mobile" in wall_label.lower() or "no walls" in wall_label.lower()

    if len(bldg_events) < 3:
        checks["c4"] = None
        details["c4"] = f"Only {len(bldg_events)} compliance.bldg events (<3, INCOMPLETE)"
    else:
        wall_segs_vals = []
        for b in bldg_events:
            try:
                wall_segs_vals.append(int(b.get("wallSegs", 0)))
            except ValueError:
                wall_segs_vals.append(0)

        if mobile:
            # Majority should have wallSegs==0
            zero_count = sum(1 for v in wall_segs_vals if v == 0)
            majority_mobile = zero_count > len(wall_segs_vals) / 2
            checks["c4"] = majority_mobile
            details["c4"] = (
                f"Mobile civ: {zero_count}/{len(wall_segs_vals)} snapshots have wallSegs==0"
            )
        else:
            # At least one snapshot has wallSegs>0
            has_walls = any(v > 0 for v in wall_segs_vals)
            checks["c4"] = has_walls
            details["c4"] = (
                f"Walling civ: wallSegs values={wall_segs_vals[:10]}, "
                f"any>0={has_walls}"
            )

    # ------------------------------------------------------------------
    # Check 5: compliance.army snapshots; dominant unit type vs militaryBullets
    # ------------------------------------------------------------------
    army_events = by_tag.get("compliance.army", [])
    military_bullets = spec.get("militaryBullets", [])
    mb_text = " ".join(military_bullets).lower()

    # Determine what the spec expects
    expect_art = any(kw in mb_text for kw in ["siege", "artillery", "cannon", "falconet"])
    expect_cav = any(kw in mb_text for kw in ["cavalry", "hussar", "dragoon", "hussar", "lancer", "steppe"])
    expect_navy = any(kw in mb_text for kw in ["navy", "naval", "fleet", "galleon", "privateer", "dock"])

    if not army_events:
        checks["c5"] = None
        details["c5"] = "No compliance.army events (INCOMPLETE)"
    else:
        def _int_field(probe, key):
            try:
                return int(probe.get(key, 0))
            except ValueError:
                return 0

        # Collect age-3 window snapshots (t in 600000..1500000 ms = 10..25 min) if any, else all
        age3_window = [p for p in army_events if 600_000 <= p["t"] <= 1_500_000]
        sample = age3_window if age3_window else army_events

        # Aggregate unit totals
        total_art  = sum(_int_field(p, "art")  for p in sample)
        total_cav  = sum(_int_field(p, "cav")  for p in sample)
        total_navy = sum(_int_field(p, "navy") for p in sample)
        total_inf  = sum(_int_field(p, "inf")  for p in sample)

        sub_checks = []
        sub_details = []

        if expect_art:
            ok = total_art > 0
            sub_checks.append(ok)
            sub_details.append(f"art={total_art}(expected>0)")
        if expect_cav:
            ok = total_cav > 0
            sub_checks.append(ok)
            sub_details.append(f"cav={total_cav}(expected>0)")
        if expect_navy:
            ok = total_navy > 0
            sub_checks.append(ok)
            sub_details.append(f"navy={total_navy}(expected>0)")

        if not sub_checks:
            # No specific expectation — just verify army events exist
            checks["c5"] = True
            details["c5"] = (
                f"No specific unit expectations; {len(sample)} snapshots found "
                f"(inf={total_inf} cav={total_cav} art={total_art} navy={total_navy})"
            )
        else:
            checks["c5"] = all(sub_checks)
            details["c5"] = (
                f"militaryBullets checks: {'; '.join(sub_details)}; "
                f"sample={len(sample)} events"
            )

    # ------------------------------------------------------------------
    # Check 6: compliance.age event with newAge≥2 (reached Colonial)
    # ------------------------------------------------------------------
    age_events = by_tag.get("compliance.age", [])
    if not age_events:
        checks["c6"] = None
        details["c6"] = "No compliance.age events (INCOMPLETE)"
    else:
        max_age = 0
        for ae in age_events:
            try:
                new_age = int(ae.get("newAge", 0))
                max_age = max(max_age, new_age)
            except ValueError:
                pass
        reached_colonial = max_age >= 2
        reached_fortress = max_age >= 3
        checks["c6"] = reached_colonial
        details["c6"] = (
            f"maxAge={max_age} "
            f"(colonial={reached_colonial}, fortress={reached_fortress})"
        )

    # ------------------------------------------------------------------
    # Check 7: compliance.combat shows correct plan counts by combatDoctrine
    # ------------------------------------------------------------------
    combat_events = by_tag.get("compliance.combat", [])
    combat_doctrine = spec.get("combatDoctrine", "").lower()

    is_aggressive = "aggressive" in combat_doctrine
    is_reactive   = "reactive" in combat_doctrine
    is_combined   = "combined" in combat_doctrine
    is_forward    = "forward" in combat_doctrine  # forward-leaning → treat as combined

    if not combat_events:
        checks["c7"] = None
        details["c7"] = "No compliance.combat events (INCOMPLETE)"
    else:
        def _int_field(probe, key):
            try:
                return int(probe.get(key, 0))
            except ValueError:
                return 0

        # Use mid-game events only (after 300000 ms = 5 min)
        mid_events = [e for e in combat_events if e["t"] >= 300_000]
        sample = mid_events if mid_events else combat_events

        total_attack  = sum(_int_field(p, "attackPlans")  for p in sample)
        total_defend  = sum(_int_field(p, "defendPlans") for p in sample)

        if is_aggressive:
            ok = total_attack > 0
            checks["c7"] = ok
            details["c7"] = (
                f"Aggressive: attackPlans={total_attack}(expected>0) "
                f"defendPlans={total_defend}"
            )
        elif is_reactive:
            ok = total_defend > 0
            checks["c7"] = ok
            details["c7"] = (
                f"Reactive: defendPlans={total_defend}(expected>0) "
                f"attackPlans={total_attack}"
            )
        elif is_combined or is_forward:
            ok = total_attack > 0 and total_defend > 0
            checks["c7"] = ok
            details["c7"] = (
                f"Combined/Forward: attackPlans={total_attack}(>0), "
                f"defendPlans={total_defend}(>0)"
            )
        else:
            checks["c7"] = None
            details["c7"] = f"Unknown combatDoctrine pattern: {combat_doctrine!r}"

    # ------------------------------------------------------------------
    # Verdict
    # ------------------------------------------------------------------
    values = list(checks.values())
    if any(v is None for v in values) and not any(v is False for v in values):
        verdict = "INCOMPLETE"
    elif all(v is True for v in values):
        verdict = "PASS"
    else:
        verdict = "FAIL"

    return {"checks": checks, "details": details, "verdict": verdict}


# ---------------------------------------------------------------------------
# Slug → HTML spec key matching
# ---------------------------------------------------------------------------

def _slug_to_nation_key(slug: str, spec_keys: list) -> str | None:
    """
    Try to match a directory slug (e.g. '03_aztec_empire') to a NATION_PLAYSTYLE key
    (e.g. 'Aztecs Montezuma').  Uses normalized substring matching.
    """
    # Remove leading index prefix (digits + underscore)
    slug_clean = re.sub(r"^\d+_", "", slug)
    slug_norm = normalize(slug_clean)

    best = None
    best_score = 0
    for key in spec_keys:
        key_norm = normalize(key)
        # Check overlap: how many chars from slug_norm appear in key_norm
        # Simple approach: longest common substring length / union length
        matched = sum(1 for c in slug_norm if c in key_norm)
        score = matched / max(len(slug_norm), len(key_norm), 1)
        if score > best_score:
            best_score = score
            best = key

    # Require at least 40% overlap to avoid wild guesses
    return best if best_score >= 0.40 else None


def _log_slug_from_probes(probes: list, slug: str) -> tuple:
    """Derive (civ, ldr) from first probe or from slug."""
    for p in probes:
        return p.get("civ", ""), p.get("ldr", "")
    # Fallback: guess from slug
    slug_clean = re.sub(r"^\d+_", "", slug).replace("_", " ")
    return slug_clean, ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Validate [ANWP v=2] probe stream against NATION_PLAYSTYLE spec"
    )
    parser.add_argument(
        "--matrix-dir",
        default="tools/aoe3_automation/artifacts/matrix_runner",
        help="Root directory of matrix_runner artifacts",
    )
    parser.add_argument(
        "--html",
        default="a_new_world.html",
        help="Path to a_new_world.html",
    )
    parser.add_argument("--out", default=None, help="Output Markdown file path")
    parser.add_argument("--json", default=None, help="Output JSON file path")
    args = parser.parse_args()

    # Resolve paths relative to script location if not absolute
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent

    matrix_dir = Path(args.matrix_dir)
    if not matrix_dir.is_absolute():
        matrix_dir = repo_root / matrix_dir

    html_path = Path(args.html)
    if not html_path.is_absolute():
        html_path = repo_root / html_path

    # Load spec
    if not html_path.exists():
        print(f"ERROR: HTML file not found: {html_path}", file=sys.stderr)
        sys.exit(1)

    try:
        nation_playstyle = parse_nation_playstyle(str(html_path))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    spec_keys = list(nation_playstyle.keys())

    # Walk artifact dirs
    if not matrix_dir.exists():
        print(f"ERROR: matrix-dir not found: {matrix_dir}", file=sys.stderr)
        sys.exit(1)

    subdirs = sorted(
        d for d in matrix_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )

    results = []

    for subdir in subdirs:
        slug = subdir.name
        log_path = subdir / "match.log"
        result_json_path = subdir / "result.json"

        probes = parse_probes(str(log_path))
        civ_from_log, ldr_from_log = _log_slug_from_probes(probes, slug)

        # Try to read civ_name from result.json for better matching
        civ_from_result = ""
        if result_json_path.exists():
            try:
                with open(result_json_path, encoding="utf-8") as f:
                    rj = json.load(f)
                civ_from_result = rj.get("civ_name", "")
            except (json.JSONDecodeError, OSError):
                pass

        # Try to match to a spec key — prefer result.json civ_name, then probe civ, then slug
        spec_key = None
        for candidate in [civ_from_result, civ_from_log]:
            if candidate:
                cand_norm = normalize(candidate)
                for k in spec_keys:
                    if cand_norm in normalize(k) or normalize(k) in cand_norm:
                        spec_key = k
                        break
            if spec_key:
                break

        if not spec_key:
            spec_key = _slug_to_nation_key(slug, spec_keys)

        spec = nation_playstyle.get(spec_key, {}) if spec_key else {}

        if not probes and not spec:
            # Entirely missing — skip but note
            results.append({
                "slug": slug,
                "civ": civ_from_log or slug,
                "leader": ldr_from_log,
                "spec_key": spec_key,
                "checks": {},
                "details": {},
                "verdict": "INCOMPLETE",
                "note": "No match.log and no spec match",
            })
            continue

        if not probes:
            # Has spec but no log
            results.append({
                "slug": slug,
                "civ": spec.get("nation", civ_from_log or slug),
                "leader": spec.get("leader", ldr_from_log),
                "spec_key": spec_key,
                "checks": {f"c{i}": None for i in range(1, 8)},
                "details": {f"c{i}": "No match.log" for i in range(1, 8)},
                "verdict": "INCOMPLETE",
                "note": "match.log missing",
            })
            continue

        if not spec:
            # Has log but no spec match
            check_result = run_checks(probes, {})
            results.append({
                "slug": slug,
                "civ": civ_from_log or slug,
                "leader": ldr_from_log,
                "spec_key": None,
                "checks": check_result["checks"],
                "details": check_result["details"],
                "verdict": "INCOMPLETE",
                "note": f"No spec match for slug {slug!r}",
            })
            continue

        check_result = run_checks(probes, spec)
        results.append({
            "slug": slug,
            "civ": spec.get("nation", civ_from_log),
            "leader": spec.get("leader", ldr_from_log),
            "spec_key": spec_key,
            "checks": check_result["checks"],
            "details": check_result["details"],
            "verdict": check_result["verdict"],
            "note": "",
        })

    # ------------------------------------------------------------------
    # Build output
    # ------------------------------------------------------------------
    pass_count = sum(1 for r in results if r["verdict"] == "PASS")
    fail_count = sum(1 for r in results if r["verdict"] == "FAIL")
    incomplete_count = sum(1 for r in results if r["verdict"] == "INCOMPLETE")

    # Markdown table
    check_labels = ["C1:boot", "C2:wall", "C3:terr", "C4:bldg", "C5:army", "C6:age", "C7:cmbt"]
    header = "| Civ | Leader | " + " | ".join(check_labels) + " | Verdict |"
    sep    = "|-----|--------|" + "|".join([":---:"] * len(check_labels)) + "|---------|"

    rows = [header, sep]
    for r in results:
        checks = r["checks"]
        def fmt(v):
            if v is True:  return "PASS"
            if v is False: return "FAIL"
            return "–"
        cells = [fmt(checks.get(f"c{i}")) for i in range(1, 8)]
        row = (
            f"| {r['civ']} | {r['leader']} | "
            + " | ".join(cells)
            + f" | **{r['verdict']}** |"
        )
        rows.append(row)

    summary_line = f"\n**Summary:** {pass_count} PASS / {fail_count} FAIL / {incomplete_count} INCOMPLETE (of {len(results)} civs)"
    md_lines = ["# Probe Validation Report\n", "\n".join(rows), summary_line]

    # Details section
    md_lines.append("\n\n## Per-Civ Details\n")
    for r in results:
        md_lines.append(f"### {r['civ']} ({r['slug']})\n")
        if r.get("note"):
            md_lines.append(f"> {r['note']}\n")
        for i in range(1, 8):
            key = f"c{i}"
            v = r["checks"].get(key)
            d = r["details"].get(key, "")
            label = check_labels[i - 1]
            status = "PASS" if v is True else ("FAIL" if v is False else "INCOMPLETE")
            md_lines.append(f"- **{label}** [{status}]: {d}")
        md_lines.append("")

    md_output = "\n".join(md_lines)

    # JSON output
    json_output = {
        "civs": [
            {
                "slug": r["slug"],
                "civ": r["civ"],
                "leader": r["leader"],
                "spec_key": r["spec_key"],
                "checks": r["checks"],
                "verdict": r["verdict"],
                "details": r["details"],
                "note": r.get("note", ""),
            }
            for r in results
        ],
        "summary": {
            "pass": pass_count,
            "fail": fail_count,
            "incomplete": incomplete_count,
            "total": len(results),
        },
    }

    # Write files
    if args.out:
        out_path = Path(args.out)
        if not out_path.is_absolute():
            out_path = repo_root / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(md_output, encoding="utf-8")
        print(f"Markdown report written to {out_path}")

    if args.json:
        json_path = Path(args.json)
        if not json_path.is_absolute():
            json_path = repo_root / json_path
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(json_output, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"JSON report written to {json_path}")

    # Always print summary and table to stdout
    print(md_output)
    print(f"\nSummary: {pass_count} PASS / {fail_count} FAIL / {incomplete_count} INCOMPLETE")


if __name__ == "__main__":
    main()
