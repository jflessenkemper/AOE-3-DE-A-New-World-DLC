#!/usr/bin/env python3
"""Catch shipped deck cards that have no <effect> in techtreemods.xml or
the base techtreey.xml — cards that do nothing in-game.

Usage::

    python3 tools/validation/validate_deck_card_effects.py
    python3 tools/validation/validate_deck_card_effects.py \\
        --json artifacts/validation/deck_card_effects.json
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

_MOD_TECHTREE = REPO_ROOT / "data" / "techtreemods.xml"
_BASE_TECHTREE = REPO_ROOT / "artifacts" / "extracted_base_techtreey.xml"
_DECKS_ANW = REPO_ROOT / "data" / "decks_anw.json"
_DECKS_MAIN = REPO_ROOT / "data" / "decks.json"


def _collect_tech_effects(path: Path) -> dict[str, int]:
    """Return {tech_name: effect_count} for every <Tech> in a techtree XML.

    effect_count = number of <effect> children inside <Effects>; 0 = no-op.
    """
    if not path.exists():
        return {}
    root = ET.parse(path).getroot()
    result: dict[str, int] = {}
    for el in root.iter():
        if el.tag.lower() != "tech":
            continue
        name = el.get("name") or el.get("Name") or el.get("NAME")
        if not name:
            continue
        count = 0
        for sub in el:
            if sub.tag.lower() == "effects":
                for child in sub:
                    if child.tag.lower() == "effect":
                        count += 1
        if name not in result:  # first occurrence wins (mod overrides base)
            result[name] = count
    return result


def _load_deck_cards(path: Path) -> dict[str, list[str]]:
    """Return {civ: [card, …]} for all civs in a decks JSON (deduped)."""
    if not path.exists():
        return {}
    raw: dict[str, dict[str, list[str]]] = json.loads(path.read_text(encoding="utf-8"))
    per_civ: dict[str, list[str]] = {}
    for civ, ages in raw.items():
        cards: list[str] = []
        seen: set[str] = set()
        for card_list in ages.values():
            for card in card_list:
                if card not in seen:
                    seen.add(card)
                    cards.append(card)
        per_civ[civ] = cards
    return per_civ


def check_deck_card_effects(
    mod_techtree: Path = _MOD_TECHTREE,
    base_techtree: Path = _BASE_TECHTREE,
    decks_anw: Path = _DECKS_ANW,
    decks_main: Path = _DECKS_MAIN,
) -> tuple[dict, list[str]]:
    """Run the check and return (report_dict, warning_lines).

    report_dict keys: "per_civ", "total_cards", "total_fails",
                      "missing_from_techtree", "empty_effects".
    """
    mod_techs = _collect_tech_effects(mod_techtree)
    base_techs = _collect_tech_effects(base_techtree)

    # Merged view: mod wins on overlap (mod can override base techs).
    all_techs: dict[str, int] = {**base_techs, **mod_techs}

    per_civ_anw = _load_deck_cards(decks_anw)
    per_civ_main = _load_deck_cards(decks_main)
    per_civ: dict[str, list[str]] = {**per_civ_anw, **per_civ_main}

    per_civ_results: list[dict] = []
    total_cards = total_fails = 0
    missing_list: list[str] = []
    empty_list: list[str] = []
    warnings: list[str] = []

    for civ in sorted(per_civ):
        cards = per_civ[civ]
        fails: list[dict] = []
        for card in cards:
            if card not in all_techs:
                fails.append({"card": card, "reason": "not_in_techtree"})
                missing_list.append(card)
            elif all_techs[card] == 0:
                fails.append({"card": card, "reason": "empty_effects_block"})
                empty_list.append(card)
        total_cards += len(cards)
        total_fails += len(fails)
        per_civ_results.append({
            "civ": civ,
            "total": len(cards),
            "fails": len(fails),
            "fail_detail": fails,
        })

    report = {
        "per_civ": per_civ_results,
        "total_cards": total_cards,
        "total_fails": total_fails,
        "missing_from_techtree": sorted(set(missing_list)),
        "empty_effects": sorted(set(empty_list)),
    }

    if not mod_techtree.exists():
        warnings.append(f"WARN: mod techtree not found: {mod_techtree}")
    if not base_techtree.exists():
        warnings.append(f"WARN: base techtree not found: {base_techtree}")

    return report, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mod-techtree", type=Path, default=_MOD_TECHTREE)
    ap.add_argument("--base-techtree", type=Path, default=_BASE_TECHTREE)
    ap.add_argument("--decks-anw", type=Path, default=_DECKS_ANW)
    ap.add_argument("--decks-main", type=Path, default=_DECKS_MAIN)
    ap.add_argument("--json", type=Path, metavar="PATH",
                    help="Write JSON report (e.g. artifacts/validation/deck_card_effects.json)")
    args = ap.parse_args()

    report, warnings = check_deck_card_effects(
        mod_techtree=args.mod_techtree,
        base_techtree=args.base_techtree,
        decks_anw=args.decks_anw,
        decks_main=args.decks_main,
    )

    for w in warnings:
        print(w, file=sys.stderr)

    print("=" * 60)
    print("DECK CARD EFFECTS CHECK")
    print("=" * 60)

    any_fail = False
    for entry in report["per_civ"]:
        civ = entry["civ"]
        total = entry["total"]
        fails = entry["fails"]
        if fails == 0:
            print(f"  \u2713 {civ}: {total}/{total} cards have <effect> blocks")
        else:
            any_fail = True
            print(f"  \u2717 {civ}: {total - fails}/{total} cards OK, "
                  f"{fails} FAIL")
            for detail in entry["fail_detail"]:
                reason = ("no <effect> in techtree"
                          if detail["reason"] == "not_in_techtree"
                          else "empty <Effects/> block — no-op card")
                print(f"      \u2715 {detail['card']}: {reason}")

    print()
    total_cards = report["total_cards"]
    total_fails = report["total_fails"]
    missing_count = len(report["missing_from_techtree"])
    empty_count = len(report["empty_effects"])
    verdict = "FAIL" if any_fail else "PASS"
    print(f"Total cards checked: {total_cards}  |  FAILs: {total_fails}  "
          f"(missing from techtree: {missing_count}, "
          f"empty effects block: {empty_count})  |  {verdict}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Report: {args.json}")

    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
