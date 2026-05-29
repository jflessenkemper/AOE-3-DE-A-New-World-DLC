"""Rewire each leader_*.xs file's build-style call to its bespoke archetype.

The standard 22 leaders each call llUseXxxStyle() exactly once during their
init. Replace that single line with a multi-line bespoke block that picks the
right archetype + applies civ-specific knob overrides to match the central
mapping in leaderCommon.xs::llApplyBuildStyleForActiveCiv().

For leader_revolution_commanders.xs (23 of the 26 revolution civs dispatched
in one big if/else), update each branch's llUseXxxStyle() call the same way.
The other 3 revolution civs (Mexicans Hidalgo, NapoleonicFrance/Napoleon,
Americans Jefferson/Washington) are handled by their own dedicated leader
files.

Idempotent: marker comments wrap the injected block so re-running replaces it.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEADER_DIR = REPO / "game" / "ai" / "leaders"

# Standard-leader bespoke build profiles — one block per file.
# Block lines are written verbatim under the marker.
STANDARD = {
    # leader_napoleon.xs already wired for French (used by both standard French
    # and the campaign Napoleon — keep on Forward Operational Line).
    "leader_napoleon.xs": [
        "llUseForwardOperationalLineStyle(2);",
        "gLLMilitaryDistanceMultiplier = 0.85;",
        "llSetBuildStrongpointProfile(2, 2, 3, true);",
    ],
    "leader_garibaldi.xs": [  # Italians — Risorgimento Redshirt levee
        "llUseRepublicanLeveeStyle(2);",
        "gLLMilitaryDistanceMultiplier = 0.90;",
        "llSetBuildStrongpointProfile(2, 2, 3, true);",
    ],
    "leader_shivaji.xs": [  # Indians — Maratha hill-fort + Sacred Field
        "llUseShrineTradeNodeSpreadStyle(2);",
        "gLLEconomicDistanceMultiplier = 1.10;",
        "llSetBuildStrongpointProfile(2, 1, 2, false);",
    ],
    "leader_pachacuti.xs": [  # Inca — Sacsayhuamán terraced fortress
        "llUseAndeanTerraceFortressStyle(4);",
        "gLLHouseDistanceMultiplier = 0.75;",
        "llSetBuildStrongpointProfile(3, 3, 2, false);",
    ],
    "leader_washington.xs": [  # Americans (Standard) — Continental republic
        "llUseRepublicanLeveeStyle(1);",
        "gLLTownCenterDistanceMultiplier = 1.10;",
    ],
    "leader_usman.xs": [  # Hausa — Sokoto trade-and-cavalry network
        "llUseDistributedEconomicNetworkStyle(2);",
        "gLLEconomicDistanceMultiplier = 1.30;",
    ],
    "leader_gustavus.xs": [  # Swedish — Lion of the North field artillery
        "llUseSiegeTrainConcentrationStyle(1);",
        "gLLMilitaryDistanceMultiplier = 0.85;",
        "llSetBuildStrongpointProfile(2, 2, 3, true);",
    ],
    "leader_hiawatha.xs": [  # Iroquois — Confederation longhouse network
        "llUseShrineTradeNodeSpreadStyle(1);",
        "gLLEconomicDistanceMultiplier = 1.20;",
    ],
    "leader_isabella.xs": [  # Spanish — Reconquista forward line
        "llUseForwardOperationalLineStyle(2);",
        "gLLMilitaryDistanceMultiplier = 0.90;",
        "llSetBuildStrongpointProfile(2, 2, 3, true);",
    ],
    "leader_frederick.xs": [  # Germans — Prussian siege train
        "llUseSiegeTrainConcentrationStyle(2);",
        "gLLMilitaryDistanceMultiplier = 0.85;",
        "llSetBuildStrongpointProfile(2, 2, 2, true);",
    ],
    "leader_catherine.xs": [  # Russians — Cossack voisko muster
        "llUseCossackVoiskoStyle(1);",
        "llSetBuildStrongpointProfile(2, 2, 3, true);",
    ],
    "leader_bourbon.xs": [  # Bourbon Restoration France — royalist compound
        "llUseCompactFortifiedCoreStyle(3, true);",
        "gLLEconomicDistanceMultiplier = 1.05;",
        "llSetBuildStrongpointProfile(3, 2, 2, false);",
    ],
    "leader_henry.xs": [  # Portuguese — Henry the Navigator carrack mercantile
        "llUseNavalMercantileCompoundStyle(2);",
        "gLLEconomicDistanceMultiplier = 1.30;",
    ],
    "leader_menelik.xs": [  # Ethiopians — Menelik II highland citadel
        "llUseHighlandCitadelStyle(3);",
        "gLLHouseDistanceMultiplier = 0.80;",
        "llSetBuildStrongpointProfile(3, 2, 2, false);",
    ],
    "leader_wellington.xs": [  # British (Wellington campaign) — naval mercantile
        "llUseNavalMercantileCompoundStyle(2);",
        "gLLEconomicDistanceMultiplier = 1.30;",
    ],
    "leader_suleiman.xs": [  # Ottomans — Suleiman siege at Vienna and Rhodes
        "llUseSiegeTrainConcentrationStyle(3);",
        "gLLEconomicDistanceMultiplier = 1.05;",
        "llSetBuildStrongpointProfile(2, 2, 2, true);",
    ],
    "leader_maurice.xs": [  # Dutch — Maurice of Nassau trade republic
        "llUseNavalMercantileCompoundStyle(2);",
        "gLLEconomicDistanceMultiplier = 1.40;",
        "gLLHouseDistanceMultiplier = 1.05;",
    ],
    "leader_kangxi.xs": [  # Chinese — Forbidden City compact fortress
        "llUseCompactFortifiedCoreStyle(4, true);",
        "gLLHouseDistanceMultiplier = 0.70;",
        "llSetBuildStrongpointProfile(3, 2, 2, false);",
    ],
    "leader_crazy_horse.xs": [  # Sioux — Lakota mounted wedge
        "llUseSteppeCavalryWedgeStyle(0);",
    ],
    "leader_hidalgo.xs": [  # Mexican (Standard Hidalgo) — insurgent civic militia
        "llUseRepublicanLeveeStyle(1);",
        "gLLEconomicDistanceMultiplier = 1.15;",
        "llSetBuildStrongpointProfile(2, 1, 2, false);",
    ],
    "leader_tokugawa.xs": [  # Japanese — Tokugawa shrine-and-castle network
        "llUseShrineTradeNodeSpreadStyle(3);",
        "gLLEconomicDistanceMultiplier = 1.25;",
        "llSetBuildStrongpointProfile(2, 2, 1, false);",
    ],
    "leader_valette.xs": [  # Maltese — Hospitaller fortress of Birgu
        "llUseHighlandCitadelStyle(5);",
        "llSetBuildStrongpointProfile(4, 3, 2, false);",
    ],
}

# Revolution-commanders dispatch: per ANW* civ → bespoke block lines.
# (3 of the 26 revolution civs have their own dedicated leader file:
#  Mexicans=leader_hidalgo, NapoleonicFrance=leader_napoleon,
#  Americans=leader_washington — they are not in this dispatch.)
REVOLUTION = {
    "ANWCanadians": [
        "llUseCompactFortifiedCoreStyle(2, false);",
        "gLLEconomicDistanceMultiplier = 0.95;",
        "llSetBuildStrongpointProfile(2, 2, 2, false);",
    ],
    "ANWRevFrance": [
        "llUseRepublicanLeveeStyle(0);",
        "gLLMilitaryDistanceMultiplier = 0.90;",
        "llSetBuildStrongpointProfile(1, 1, 3, true);",
    ],
    "ANWBrazil": [
        "llUseDistributedEconomicNetworkStyle(2);",
        "gLLEconomicDistanceMultiplier = 1.35;",
    ],
    "ANWArgentines": [
        "llUseForwardOperationalLineStyle(0);",
        "gLLMilitaryDistanceMultiplier = 0.85;",
        "llSetBuildStrongpointProfile(1, 2, 3, true);",
    ],
    "ANWChileans": [
        "llUseAndeanTerraceFortressStyle(2);",
        "gLLMilitaryDistanceMultiplier = 0.90;",
        "llSetBuildStrongpointProfile(2, 2, 2, false);",
    ],
    "ANWPeruvians": [
        "llUseAndeanTerraceFortressStyle(3);",
        "gLLMilitaryDistanceMultiplier = 0.90;",
        "llSetBuildStrongpointProfile(3, 2, 2, false);",
    ],
    "ANWColumbians": [
        "llUseForwardOperationalLineStyle(0);",
        "gLLMilitaryDistanceMultiplier = 0.90;",
        "llSetBuildStrongpointProfile(1, 1, 3, true);",
    ],
    "ANWMayans": [
        "llUseJungleGuerrillaNetworkStyle(1);",
        "gLLMilitaryDistanceMultiplier = 0.90;",
        "llSetBuildStrongpointProfile(2, 1, 2, true);",
    ],
    "ANWBajaCalifornians": [
        "llUseMobileFrontierScatterStyle(0);",
        "gLLHouseDistanceMultiplier = 1.40;",
        "gLLEconomicDistanceMultiplier = 1.50;",
    ],
    "ANWRioGrande": [
        "llUseMobileFrontierScatterStyle(0);",
        "gLLHouseDistanceMultiplier = 1.35;",
        "gLLTownCenterDistanceMultiplier = 1.50;",
        "llSetBuildStrongpointProfile(1, 0, 2, false);",
    ],
    "ANWTexians": [
        "llUseForwardOperationalLineStyle(0);",
        "gLLMilitaryDistanceMultiplier = 0.90;",
        "llSetBuildStrongpointProfile(2, 1, 3, true);",
    ],
    "ANWHaitians": [
        "llUseJungleGuerrillaNetworkStyle(0);",
        "gLLEconomicDistanceMultiplier = 1.40;",
        "gLLTownCenterDistanceMultiplier = 1.40;",
    ],
    "ANWBarbary": [
        "llUseNavalMercantileCompoundStyle(2);",
        "gLLEconomicDistanceMultiplier = 1.20;",
        "llSetBuildStrongpointProfile(2, 2, 2, true);",
    ],
    "ANWEgyptians": [
        "llUseHighlandCitadelStyle(4);",
        "gLLHouseDistanceMultiplier = 0.75;",
        "llSetBuildStrongpointProfile(3, 3, 2, false);",
    ],
    "ANWSouthAfricans": [
        "llUseNavalMercantileCompoundStyle(1);",
        "gLLEconomicDistanceMultiplier = 1.25;",
        "llSetBuildStrongpointProfile(2, 1, 2, true);",
    ],
    "ANWFinnish": [
        "llUseCompactFortifiedCoreStyle(3, true);",
        "gLLHouseDistanceMultiplier = 0.80;",
        "llSetBuildStrongpointProfile(3, 2, 2, false);",
    ],
    "ANWHungarians": [
        "llUseSteppeCavalryWedgeStyle(1);",
        "gLLMilitaryDistanceMultiplier = 0.90;",
        "llSetBuildStrongpointProfile(2, 1, 3, true);",
    ],
    "ANWRomanians": [
        "llUseCivicMilitiaCenterStyle(2);",
        "gLLEconomicDistanceMultiplier = 1.10;",
        "llSetBuildStrongpointProfile(2, 1, 2, false);",
    ],
    "ANWIndonesians": [
        "llUseShrineTradeNodeSpreadStyle(1);",
        "gLLEconomicDistanceMultiplier = 1.40;",
    ],
}

BEGIN_MARK = "// LL-BUILD-STYLE-BEGIN"
END_MARK = "// LL-BUILD-STYLE-END"


def render_block(lines: list[str], indent: str) -> str:
    body = "\n".join(indent + l for l in lines)
    return (
        f"{indent}{BEGIN_MARK}\n"
        f"{body}\n"
        f"{indent}{END_MARK}"
    )


def replace_first_style_call(text: str, fname: str, lines: list[str]) -> str:
    """Replace the first `llUse...Style(...)` call (or an existing marker block)
    with a marker-wrapped bespoke block of `lines`.
    """
    # If a marker block already exists, replace it
    marker_re = re.compile(
        rf"([ \t]*){re.escape(BEGIN_MARK)}.*?{re.escape(END_MARK)}",
        re.DOTALL,
    )
    m = marker_re.search(text)
    if m:
        indent = m.group(1)
        return text[:m.start()] + render_block(lines, indent) + text[m.end():]
    # Otherwise replace the first generic style call (preserve indent)
    call_re = re.compile(r"^([ \t]*)llUse\w+Style\([^)]*\);[^\n]*", re.MULTILINE)
    m = call_re.search(text)
    if not m:
        raise RuntimeError(f"{fname}: no llUse*Style(...) call found")
    indent = m.group(1)
    return text[:m.start()] + render_block(lines, indent) + text[m.end():]


def rewire_standard_file(path: Path, lines: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    new = replace_first_style_call(text, path.name, lines)
    if new != text:
        path.write_text(new, encoding="utf-8")
        print(f"  rewired {path.name}")
    else:
        print(f"  unchanged {path.name}")


def rewire_revolution_commanders(path: Path, mapping: dict) -> None:
    """In leader_revolution_commanders.xs, find each `if (rvltName == "X")`
    block and replace its single `llUse...Style(...)` call with the bespoke
    block. Branches without an entry in `mapping` are left as-is.
    """
    text = path.read_text(encoding="utf-8")
    # Split into per-civ blocks by scanning for the rvltName checks.
    branch_re = re.compile(
        r'(else\s+if|if)\s*\(\s*rvltName\s*==\s*"(ANW\w+)"\s*\)\s*\{',
    )
    edits: list[tuple[int, int, str, str]] = []  # (start, end, civ, replacement)
    matches = list(branch_re.finditer(text))
    if not matches:
        raise RuntimeError("no rvltName branches found in dispatch file")
    for i, m in enumerate(matches):
        civ = m.group(2)
        if civ not in mapping:
            continue
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        branch_body = text[body_start:body_end]
        # Find the existing style call inside this branch
        marker = re.search(
            rf"([ \t]*){re.escape(BEGIN_MARK)}.*?{re.escape(END_MARK)}",
            branch_body, re.DOTALL,
        )
        if marker:
            indent = marker.group(1)
            new_body = (
                branch_body[:marker.start()]
                + render_block(mapping[civ], indent)
                + branch_body[marker.end():]
            )
        else:
            call = re.search(
                r"^([ \t]*)llUse\w+Style\([^)]*\);[^\n]*",
                branch_body, re.MULTILINE,
            )
            if not call:
                print(f"  WARN {civ}: no style call in branch, skipping")
                continue
            indent = call.group(1)
            new_body = (
                branch_body[:call.start()]
                + render_block(mapping[civ], indent)
                + branch_body[call.end():]
            )
        edits.append((body_start, body_end, civ, new_body))

    # Apply edits in reverse so offsets remain valid
    for body_start, body_end, civ, new_body in reversed(edits):
        text = text[:body_start] + new_body + text[body_end:]
        print(f"  rewired branch {civ}")
    path.write_text(text, encoding="utf-8")


def main() -> int:
    print("Standard leader files:")
    for fname, lines in STANDARD.items():
        rewire_standard_file(LEADER_DIR / fname, lines)
    print("\nRevolution commanders dispatch:")
    rewire_revolution_commanders(LEADER_DIR / "leader_revolution_commanders.xs",
                                 REVOLUTION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
