#!/usr/bin/env python3
"""Verify every tech-name reference on every ANW civ resolves to a real tech.

Bug class this catches: a civmods entry references a tech that doesn't
exist in either our ``data/techtreemods.xml`` or the base game's
``Game/Data.bar:techtreey.xml`` — silent in the engine (the civ just
doesn't get that age-up bonus / mode behavior), invisible to the
existing static gate.

For each ANW civ in ``civmods.xml``, this validator:
  1. Walks every tech-name-bearing field:
       - ``<agetech>`` × 5 (Age0..Age4) via the ``<tech>`` child element
       - ``<postindustrialtech>``, ``<postimperialtech>``
       - ``<deathmatchtech>``, ``<treatytech>``, ``<empirewarstech>``
  2. Looks up each referenced tech in:
       - ``data/techtreemods.xml`` (our mod's tech table), AND
       - ``artifacts/extracted_base_techtreey.xml`` (base game's tech
         table; auto-extracted from Data.bar on first run).
  3. Reports any tech that resolves in neither.

Auto-extracts the base techtree if not present.

Usage::

    python3 tools/validation/validate_civ_tech_resolution.py
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

sys.path.insert(0, str(REPO_ROOT))


_BASE_TECHTREE = REPO_ROOT / "artifacts" / "extracted_base_techtreey.xml"
_MOD_TECHTREE = REPO_ROOT / "data" / "techtreemods.xml"
_CIVMODS = REPO_ROOT / "data" / "civmods.xml"


def _ensure_base_techtree(bar_path: Path | None = None) -> None:
    """Auto-extract the base techtreey.xml from Data.bar if missing."""
    if _BASE_TECHTREE.exists():
        return
    bar_path = bar_path or Path(
        "/var/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/Game/Data/Data.bar"
    )
    if not bar_path.exists():
        raise RuntimeError(
            f"Base techtree not extracted ({_BASE_TECHTREE}) and "
            f"Data.bar not found ({bar_path}). Cannot validate."
        )
    from tools.cardextract.bar import open_bar
    from tools.cardextract.xmb import parse_xmb

    arc = open_bar(bar_path)
    e = next(arc.find(lambda e: "techtreey.xml" in e.normalized_name.lower()))
    root = parse_xmb(arc.read_payload(e))
    _BASE_TECHTREE.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(_BASE_TECHTREE, encoding="utf-8")


def _collect_techs(path: Path) -> set[str]:
    """All tech names defined in a techtree XML file.

    Returns lowercased names. The AoE3 engine resolves tech-name references
    case-insensitively (vanilla civs.xml ships `YPColonializeChinese` while
    techtreey.xml defines `ypColonializeChinese`); we must mirror that.
    """
    out: set[str] = set()
    if not path.exists():
        return out
    root = ET.parse(path).getroot()
    for el in root.iter():
        if el.tag.lower() == "tech":
            n = el.get("name") or el.get("Name")
            if n:
                out.add(n.lower())
    return out


_TECH_FIELDS_SINGLE = (
    "postindustrialtech", "postimperialtech",
    "deathmatchtech", "treatytech", "empirewarstech",
)


def _civ_tech_refs(civ: ET.Element) -> dict[str, list[str]]:
    """{field_label: [tech_names]} for every tech-name-bearing field."""
    refs: dict[str, list[str]] = {}
    # AgeTech blocks: each is <agetech><age>AgeN</age><tech>X</tech></agetech>
    for at in civ.findall("agetech"):
        age = at.find("age")
        tech = at.find("tech")
        if age is not None and tech is not None and (tech.text or "").strip():
            label = f"agetech[{(age.text or '').strip()}]"
            refs.setdefault(label, []).append(tech.text.strip())
    # Single-tech mode fields
    for fld in _TECH_FIELDS_SINGLE:
        e = civ.find(fld)
        if e is not None and (e.text or "").strip():
            refs.setdefault(fld, []).append(e.text.strip())
    return refs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    print("=" * 60)
    print("CIV TECH-REFERENCE RESOLUTION")
    print("=" * 60)

    _ensure_base_techtree()

    mod_techs = _collect_techs(_MOD_TECHTREE)
    base_techs = _collect_techs(_BASE_TECHTREE)
    all_techs = mod_techs | base_techs
    print(f"  Mod techs:  {len(mod_techs):>6}")
    print(f"  Base techs: {len(base_techs):>6}")
    print(f"  Union:      {len(all_techs):>6}")
    print()

    civmods_root = ET.parse(_CIVMODS).getroot()
    civs_only_anw = [c for c in civmods_root.findall("civ")
                    if (c.find("name").text or "").startswith("ANW")]

    fail_count = 0
    per_civ_fails: list[tuple[str, list[tuple[str, str]]]] = []
    for civ in civs_only_anw:
        token = (civ.find("name").text or "").strip()
        refs = _civ_tech_refs(civ)
        unresolved: list[tuple[str, str]] = []
        for label, names in refs.items():
            for n in names:
                if n.lower() not in all_techs:
                    unresolved.append((label, n))
        if unresolved:
            per_civ_fails.append((token, unresolved))
            fail_count += len(unresolved)

    if fail_count == 0:
        print(f"✓ PASS — every tech reference on every ANW civ resolves "
              f"({len(civs_only_anw)} civs checked, "
              f"{sum(len(v) for v in [_civ_tech_refs(c) for c in civs_only_anw] for v in v.values()) if civs_only_anw else 0} "
              f"refs verified).")
        rc = 0
    else:
        print(f"✗ FAIL — {fail_count} unresolved tech reference(s) across "
              f"{len(per_civ_fails)} civ(s):")
        for token, problems in per_civ_fails[:15]:
            print(f"  {token}:")
            for label, name in problems[:5]:
                print(f"    {label} → {name}  (not in mod or base techs)")
            if len(problems) > 5:
                print(f"    … +{len(problems) - 5} more on this civ")
        if len(per_civ_fails) > 15:
            print(f"  … +{len(per_civ_fails) - 15} more civs with failures")
        rc = 1

    if args.json:
        import json
        report = {
            "mod_techs": len(mod_techs),
            "base_techs": len(base_techs),
            "civs_checked": len(civs_only_anw),
            "fail_count": fail_count,
            "per_civ_fails": [
                {"civ": t,
                 "unresolved": [{"field": f, "tech": n} for f, n in p]}
                for t, p in per_civ_fails
            ],
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2))
        print(f"\nReport: {args.json}")

    return rc


if __name__ == "__main__":
    sys.exit(main())
