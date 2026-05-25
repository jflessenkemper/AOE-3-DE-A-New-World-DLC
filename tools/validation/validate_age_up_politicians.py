#!/usr/bin/env python3
"""Catch free-age-up exploits and missing politician options in ANW home cities.

ANW-specific civs have an ANWAge0<Civ> tech block in techtreemods.xml listing
which politicians become obtainable.  Within the block the four age-up tiers
(Commerce / Fortress / Industrial / Imperial) are separated by blank lines.

Checks:
  1. Each ANW civ must expose >= 2 politician options per age tier.
  2. Any politician tech defined in techtreemods.xml with a <Cost> element
     must have total cost > 0 (free-age-up exploit guard).

Vanilla civs inherit politicians from the base-game techtree and are SKIPped.

Exit codes: 0 = all PASS/SKIP, 1 = any FAIL.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

_POLITICIAN_RE = re.compile(r"Politician|DEPolitic|UnlockPolitic", re.IGNORECASE)
_TECH_BLOCK_RE = re.compile(
    r"<Tech\s+name\s*=\s*['\"]([^'\"]+)['\"][^>]*>(.*?)</Tech>",
    re.DOTALL | re.IGNORECASE,
)
_OBTAINABLE_RE = re.compile(
    r"<Effect[^>]+type\s*=\s*['\"]TechStatus['\"][^>]*"
    r"status\s*=\s*['\"]obtainable['\"][^>]*>\s*([^<]+)\s*</Effect>",
    re.IGNORECASE,
)
_COST_RE = re.compile(
    r"<Cost\s+resourcetype\s*=\s*['\"][^'\"]+['\"]>\s*([\d.]+)\s*</Cost>",
    re.IGNORECASE,
)

AGE_LABELS = ["Commerce", "Fortress", "Industrial", "Imperial"]

# Homecity filename slug → ANWAge0 tech name for non-obvious mappings.
_SLUG_MAP: dict[str, str] = {
    "brazil": "ANWAge0Brazilians",
    "egyptians": "ANWAge0Egypt",
    "mayans": "ANWAge0Maya",
    "texians": "ANWAge0Texas",
    "revfrance": "ANWAge0RevolutionaryFrench",
    "napoleonicfrance": "ANWAge0NapoleonicFrench",
}


def _politician_groups(block_body: str) -> list[list[str]]:
    """Return 4 lists of politician tech names, one per age tier."""
    m = re.search(r"<Effects>(.*?)</Effects>", block_body, re.DOTALL | re.IGNORECASE)
    if not m:
        return [[], [], [], []]
    paragraphs: list[list[str]] = [[]]
    for line in m.group(1).splitlines():
        stripped = line.strip()
        if stripped:
            paragraphs[-1].append(stripped)
        elif paragraphs[-1]:
            paragraphs.append([])
    groups: list[list[str]] = []
    for para in paragraphs:
        polits = [
            mo.group(1).strip()
            for mo in _OBTAINABLE_RE.finditer("\n".join(para))
            if _POLITICIAN_RE.search(mo.group(1))
        ]
        if polits:
            groups.append(polits)
    while len(groups) < 4:
        groups.append([])
    if len(groups) > 4:
        for extra in groups[4:]:
            groups[3].extend(extra)
        groups = groups[:4]
    return groups


def _tech_costs(text: str) -> dict[str, float]:
    """Return {tech_name: total_cost} for techs with explicit <Cost> in techtreemods."""
    costs: dict[str, float] = {}
    for m in _TECH_BLOCK_RE.finditer(text):
        vals = [float(v) for v in _COST_RE.findall(m.group(2))]
        if vals:
            costs[m.group(1)] = sum(vals)
    return costs


def _anwage0_blocks(text: str) -> dict[str, str]:
    """Return {tech_name: body_text} for every ANWAge0* tech."""
    return {
        m.group(1): m.group(2)
        for m in _TECH_BLOCK_RE.finditer(text)
        if m.group(1).startswith("ANWAge0")
    }


def validate(repo_root: Path, min_per_age: int = 2) -> tuple[list[dict], int, int]:
    """Run all checks. Returns (results, fail_count, total_politicians)."""
    tt_path = repo_root / "data" / "techtreemods.xml"
    if not tt_path.exists():
        print(f"ERROR: {tt_path} not found", file=sys.stderr)
        sys.exit(2)
    tt_text = tt_path.read_text(encoding="utf-8", errors="replace")
    age0 = _anwage0_blocks(tt_text)
    costs = _tech_costs(tt_text)

    hc_files = sorted((repo_root / "data").glob("anwhomecity*.xml"))
    if not hc_files:
        print("ERROR: no anwhomecity*.xml found", file=sys.stderr)
        sys.exit(2)

    # Suffix lookup: lowercase("ANWAge0Canadians"[7:]) == "canadians"
    by_suffix = {t[7:].lower(): t for t in age0}

    results: list[dict] = []
    fails_total = 0
    total_polits = 0

    for hc in hc_files:
        slug = hc.stem.replace("anwhomecity", "")
        tech = _SLUG_MAP.get(slug) or by_suffix.get(slug)

        if not tech or tech not in age0:
            results.append({"civ": slug.title(), "status": "SKIP",
                            "reason": "base-game politicians (no ANWAge0 block)",
                            "groups": [], "fails": []})
            continue

        groups = _politician_groups(age0[tech])
        civ_total = sum(len(g) for g in groups)
        total_polits += civ_total
        fails: list[str] = []

        for label, group in zip(AGE_LABELS, groups):
            if len(group) < min_per_age:
                fails.append(f"only {len(group)}/{min_per_age} at {label} age")

        for group in groups:
            for tn in group:
                if tn in costs and costs[tn] <= 0:
                    fails.append(f"politician '{tn}' has zero cost in techtreemods.xml")

        if fails:
            fails_total += 1
        results.append({
            "civ": slug.title(), "age0_tech": tech, "status": "FAIL" if fails else "PASS",
            "total_politicians": civ_total,
            "groups": [{"age": AGE_LABELS[i], "count": len(groups[i]),
                        "politicians": groups[i]} for i in range(4)],
            "fails": fails,
        })

    return results, fails_total, total_polits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    ap.add_argument("--json", type=Path, metavar="PATH")
    ap.add_argument("--min-per-age", type=int, default=2)
    args = ap.parse_args()

    repo_root = args.repo_root.resolve()
    print("=" * 60)
    print("AGE-UP POLITICIAN VALIDATOR")
    print("=" * 60)

    results, fail_count, total_polits = validate(repo_root, args.min_per_age)

    for r in results:
        civ = r["civ"]
        if r["status"] == "SKIP":
            print(f"  ~ {civ}: {r['reason']}")
        elif r["status"] == "PASS":
            counts = "/".join(str(g["count"]) for g in r["groups"])
            print(f"  \u2713 {civ}: {r['total_politicians']} politicians "
                  f"({counts} per age), all checks pass")
        else:
            print(f"  \u2717 {civ}: FAIL")
            for f in r["fails"]:
                print(f"      - {f}")

    print()
    anw = sum(1 for r in results if r["status"] != "SKIP")
    skip = sum(1 for r in results if r["status"] == "SKIP")
    print(f"Total: {len(results)} civs ({anw} ANW-validated, {skip} vanilla-skipped), "
          f"{total_polits} politicians, {fail_count} FAIL(s)")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({
            "total_civs": len(results), "anw_validated": anw, "vanilla_skipped": skip,
            "total_politicians": total_polits, "fail_count": fail_count, "results": results,
        }, indent=2), encoding="utf-8")
        print(f"Report: {args.json}")

    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
