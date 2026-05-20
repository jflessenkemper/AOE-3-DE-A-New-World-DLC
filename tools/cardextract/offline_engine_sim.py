"""Offline AoE3 DE engine merge + picker simulator.

Reverse-engineered enough of the engine's mod-merge + civ-picker
enumeration to validate ANW changes WITHOUT launching the game. Cuts
the test loop from ~5 min/civ to ~5 sec for the entire 46-civ matrix.

What it does
============

1. Extracts base ``civs.xml`` from ``Game/Data/Data.bar`` (XMB-compressed).
2. Loads ``data/civmods.xml`` from this repo.
3. Merges the two into a unified civ table using two strategies:
     - ``case_sensitive`` — like a strict XML-aware engine: only
       ``<civ>`` (lowercase) and ``<Name>`` matchups merge.
     - ``case_insensitive`` — folds tag names; treats ``<Civ>``
       and ``<civ>`` as the same entry type.
4. Simulates the SinglePlayer skirmish picker enumeration:
     - Iterates the merged civ table.
     - Filters to civs with a truthy ``main`` field (engine convention).
     - Sorts by display name.
     - Returns the visible-civ list.

Then a Python-level diff vs the live screenshot tells us whether the
fix is the case rewrite, an XML root tag rename, or something else.

Usage::

    from tools.cardextract.offline_engine_sim import (
        load_base_civs, load_civmods, merge, simulate_picker,
    )

    base = load_base_civs()
    mods = load_civmods()
    sens = merge(base, mods, case="sensitive")
    insens = merge(base, mods, case="insensitive")
    print(f"sensitive picker: {len(simulate_picker(sens))}")
    print(f"insensitive picker: {len(simulate_picker(insens))}")
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

# Default base civs.xml location (extracted by extract_base_civs())
_DEFAULT_BASE_CIVS = REPO_ROOT / "artifacts" / "extracted_base_civs.xml"
_DEFAULT_CIVMODS = REPO_ROOT / "data" / "civmods.xml"
_DEFAULT_DATA_BAR = Path(
    "/var/home/jflessenkemper/.local/share/Steam/steamapps/common/AoE3DE/Game/Data/Data.bar"
)


@dataclass
class Civ:
    """One civ entry in the merged engine table."""
    name: str                              # <Name> / <name> value
    fields: dict[str, str] = field(default_factory=dict)  # all single-value fields, lowercased keys
    multi_fields: dict[str, list[str]] = field(default_factory=dict)
    source: str = "base"                   # "base" | "mod" | "merged"
    raw_tag: str = "civ"                   # original tag name (for case-sensitive analysis)


def extract_base_civs(bar_path: Path = _DEFAULT_DATA_BAR,
                      out_path: Path = _DEFAULT_BASE_CIVS) -> Path:
    """Pull civs.xml.XMB from Data.bar, decode it, write XML."""
    sys.path.insert(0, str(REPO_ROOT))
    from tools.cardextract.bar import open_bar
    from tools.cardextract.xmb import parse_xmb

    arc = open_bar(bar_path)
    hits = list(arc.find(lambda e: "civs.xml" in e.normalized_name))
    if not hits:
        raise RuntimeError(f"civs.xml not found in {bar_path}")
    payload = arc.read_payload(hits[0])
    root = parse_xmb(payload)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(out_path, encoding="utf-8", xml_declaration=True)
    return out_path


def _civ_from_element(e: ET.Element) -> Civ:
    """Build Civ from an XML <civ>/<Civ> element. Folds field tag case."""
    name_el = None
    for k in ("Name", "name", "NAME"):
        name_el = e.find(k)
        if name_el is not None:
            break
    if name_el is None:
        return Civ(name="<unnamed>", raw_tag=e.tag)
    fields: dict[str, str] = {}
    multi: dict[str, list[str]] = {}
    for child in e:
        key = child.tag.lower()
        text = (child.text or "").strip()
        if key in fields or key in multi:
            multi.setdefault(key, [fields.pop(key)] if key in fields else multi[key])
            multi[key].append(text)
        else:
            fields[key] = text
    return Civ(name=(name_el.text or "").strip(), fields=fields,
               multi_fields=multi, raw_tag=e.tag)


def load_base_civs(path: Path = _DEFAULT_BASE_CIVS,
                   auto_extract: bool = True) -> list[Civ]:
    """Load base civs from extracted civs.xml. Auto-extracts if missing."""
    if not path.exists():
        if not auto_extract:
            raise FileNotFoundError(path)
        extract_base_civs(out_path=path)
    root = ET.parse(path).getroot()
    civs: list[Civ] = []
    for e in root:
        # Match on lowercased tag for forgiving load
        if e.tag.lower() == "civ":
            c = _civ_from_element(e)
            c.source = "base"
            civs.append(c)
    return civs


def load_civmods(path: Path = _DEFAULT_CIVMODS) -> list[Civ]:
    """Load civmods entries (mod definitions to merge into base)."""
    root = ET.parse(path).getroot()
    civs: list[Civ] = []
    for e in root:
        if e.tag.lower() == "civ":
            c = _civ_from_element(e)
            c.source = "mod"
            civs.append(c)
    return civs


def merge(base: list[Civ], mods: list[Civ],
          case: str = "insensitive") -> list[Civ]:
    """Merge mod entries into base, returning the unified civ table.

    case='sensitive':  only mod entries whose raw_tag matches base raw_tag
                       are recognized as civs. Mismatched mods are dropped.
    case='insensitive': fold tag case; all mod entries are recognized.
    """
    if case not in ("sensitive", "insensitive"):
        raise ValueError(case)

    # Index base by name (engine merges by Name)
    out: "OrderedDict[str, Civ]" = OrderedDict((c.name, c) for c in base)

    base_tags = {c.raw_tag for c in base}  # typically {"civ"}

    for m in mods:
        if case == "sensitive" and m.raw_tag not in base_tags:
            # Engine doesn't recognize this entry — silently drops it.
            continue

        if m.name in out:
            # Merge: mod overrides base fields.
            cur = out[m.name]
            merged = Civ(name=m.name, fields={**cur.fields, **m.fields},
                         multi_fields={**cur.multi_fields, **m.multi_fields},
                         source="merged", raw_tag=cur.raw_tag)
            out[m.name] = merged
        else:
            # New civ added by mod.
            out[m.name] = m
    return list(out.values())


def simulate_picker(merged: list[Civ],
                    *,
                    require_main: bool = True,
                    respect_visible: bool = True,
                    sort_by_display: bool = True) -> list[Civ]:
    """Mimic the SinglePlayer Skirmish 'Select Civilization' picker.

    Engine convention (observed from base civs.xml):
      - Civs with ``<Main>1</Main>`` are user-selectable.
      - Civs without ``<Main>`` or with ``<Main>0</Main>`` are
        scenario-only (Pirate, NativeAmerican, SPCAct1, etc.).
      - Civs with ``<Visible>0</Visible>`` are hidden from the picker
        (TheCircle, SPCBarbaryPirates, etc.). Defaults to visible when
        the field is absent.
      - Picker is alphabetized by DisplayName resolution.
    """
    out: list[Civ] = []
    for c in merged:
        main_v = c.fields.get("main", "")
        if require_main and main_v != "1":
            continue
        visible_v = c.fields.get("visible", "")
        if respect_visible and visible_v == "0":
            continue
        out.append(c)
    if sort_by_display:
        out.sort(key=lambda c: c.name.lower())
    return out


def diagnose_merge_gap(base: list[Civ], mods: list[Civ]) -> dict:
    """Return a diff between case-sensitive and case-insensitive merges."""
    sens = merge(base, mods, case="sensitive")
    insens = merge(base, mods, case="insensitive")
    sens_picker = simulate_picker(sens)
    insens_picker = simulate_picker(insens)

    sens_names = {c.name for c in sens_picker}
    insens_names = {c.name for c in insens_picker}
    only_in_insens = sorted(insens_names - sens_names)

    return {
        "base_civ_count": len(base),
        "mod_civ_count": len(mods),
        "case_sensitive_picker": len(sens_picker),
        "case_insensitive_picker": len(insens_picker),
        "civs_lost_to_case_mismatch": only_in_insens,
        "base_root_tags": sorted({c.raw_tag for c in base}),
        "mod_root_tags": sorted({c.raw_tag for c in mods}),
    }


# --- CLI for quick triage ---

def main() -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--diagnose", action="store_true",
                    help="run merge-gap diagnostic and print result")
    ap.add_argument("--list-picker", action="store_true",
                    help="list civs that would appear in the picker")
    ap.add_argument("--case", choices=["sensitive", "insensitive"],
                    default="insensitive")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    base = load_base_civs()
    mods = load_civmods()

    if args.diagnose:
        report = diagnose_merge_gap(base, mods)
        print(json.dumps(report, indent=2))
        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(json.dumps(report, indent=2))
        return 0

    if args.list_picker:
        merged = merge(base, mods, case=args.case)
        picker = simulate_picker(merged)
        print(f"Picker would show {len(picker)} civs (case={args.case}):")
        for c in picker[:60]:
            print(f"  {c.name:<30}  source={c.source}  main={c.fields.get('main','-')}")
        if len(picker) > 60:
            print(f"  … +{len(picker) - 60} more")
        return 0

    print("usage: --diagnose | --list-picker [--case sensitive|insensitive]")
    return 2


if __name__ == "__main__":
    sys.exit(main())
