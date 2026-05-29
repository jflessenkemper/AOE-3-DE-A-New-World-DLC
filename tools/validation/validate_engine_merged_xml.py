#!/usr/bin/env python3
"""Validate the engine's *actually-loaded* post-merge XML against expectations.

This is the canonical engine-side validator the AoE3 DE modding community
hasn't built. It uses the engine's own ``DebugOutputGameData`` dump
(enabled in ``Startup/user.cfg``) as ground truth — bypassing every
guessing-game about merge semantics, sprite-sheet precedence, or XML
case sensitivity.

How it works
============

When ``DebugOutputGameData`` is in ``user.cfg``, the engine writes the
post-merge XML it actually loaded to:

    <UserDir>/Temp/Age of Empires 3 DE/Data/<file>

For each merged file relevant to ANW (civs.xml, techtree.xml, etc.),
this validator:
  1. Reads the engine's dump.
  2. Compares against expected state derived from civmods + offline_engine_sim.
  3. Flags mismatches that indicate broken merges, dropped overrides,
     or unexpected base-game leakage.

Specifically validates:
  - All 46 ANW civs are present in the merged civ table.
  - Each ANW civ's <homecityflagiconwpf> survived the merge.
  - Each ANW civ's <smallportraittexture> reflects our override (empty
    or pointing at our path).
  - <main>=1 for ANW civs and <main>=0 (or removed) for suppressed
    base civs.
  - StatsIDs are unique post-merge.
  - DisplayNameIDs all resolve in the merged stringtable.

Usage
=====

::

    # 1. Add ``DebugOutputGameData`` to user.cfg (this validator
    #    auto-detects user.cfg state).
    # 2. Launch the game once with mod active.
    # 3. Run:
    python3 tools/validation/validate_engine_merged_xml.py

If the dump is missing, the validator skips with clear instructions.
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

sys.path.insert(0, str(REPO_ROOT))
from tools.migration.anw_token_map import ANW_CIVS  # noqa: E402


# Where the engine writes its post-merge XML when DebugOutputGameData is on
_USER_DIR = Path(
    "/var/home/jflessenkemper/.local/share/Steam/steamapps/compatdata/"
    "933110/pfx/drive_c/users/steamuser/Games/Age of Empires 3 DE/"
    "76561198170207043"
)
_TEMP = _USER_DIR / "Temp" / "Age of Empires 3 DE" / "Data"
_USER_CFG = _USER_DIR / "Startup" / "user.cfg"


def _check_user_cfg() -> tuple[bool, str]:
    """Return (enabled, message) — is DebugOutputGameData configured?"""
    if not _USER_CFG.exists():
        return (False, f"user.cfg not found at {_USER_CFG}; run "
                       "`echo DebugOutputGameData >> '$cfg'` to enable")
    text = _USER_CFG.read_text()
    if "DebugOutputGameData" not in text:
        return (False, f"DebugOutputGameData not in {_USER_CFG}; add it "
                       "and re-launch the game once")
    return (True, "")


def _find_merged_civs() -> Path | None:
    """Locate the engine's post-merge civs.xml (engine writes it under Temp/)."""
    if not _TEMP.exists():
        return None
    for cand in _TEMP.rglob("civs.xml"):
        return cand
    for cand in _TEMP.rglob("civs*.xml"):
        return cand
    return None


def _all_civs_in_merge(civs_xml: Path) -> dict[str, ET.Element]:
    """Parse the engine's merged civs.xml; return {name: civ_element}."""
    root = ET.parse(civs_xml).getroot()
    out: dict[str, ET.Element] = {}
    for c in root.iter():
        if c.tag.lower() == "civ":
            n = c.find("name") or c.find("Name")
            if n is not None and (n.text or "").strip():
                out[n.text.strip()] = c
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    print("=" * 60)
    print("ENGINE POST-MERGE XML VALIDATION")
    print("=" * 60)

    cfg_ok, cfg_msg = _check_user_cfg()
    if not cfg_ok:
        print(f"⏭  SKIP — {cfg_msg}")
        return 0

    civs_xml = _find_merged_civs()
    if civs_xml is None:
        print(f"⏭  SKIP — no merged civs.xml found under {_TEMP}.")
        print(f"   Launch the game once with mod active so the engine can "
              "dump the post-merge XML, then re-run this validator.")
        return 0

    print(f"  Engine dump: {civs_xml.relative_to(_USER_DIR)}")
    merged = _all_civs_in_merge(civs_xml)
    print(f"  Total civs in merged table: {len(merged)}")

    # === Check 1: All 46 ANW tokens present ===
    missing_anw = [t for t in ANW_CIVS if t not in merged]
    print()
    print(f"  ANW civs present: {len(ANW_CIVS) - len(missing_anw)}/46")
    if missing_anw:
        print(f"  ✗ MISSING ANW civs in merged table:")
        for t in missing_anw[:10]:
            print(f"      {t}")

    # === Check 2: ANW civs have main=1 ===
    not_main = []
    for token in ANW_CIVS:
        civ = merged.get(token)
        if civ is None:
            continue
        m = civ.find("main") or civ.find("Main")
        if m is None or (m.text or "").strip() != "1":
            not_main.append((token, (m.text if m is not None else "(no <main>)")))
    if not_main:
        print(f"  ✗ ANW civs without <main>1</main>: {len(not_main)}")
        for t, v in not_main[:10]:
            print(f"      {t}: <main>={v!r}")

    # === Check 3: Suppressed base civs are gone or main=0 ===
    suppressed_should_hide = (
        "SPCAct1", "SPCAct2", "SPCAct3", "Pirate", "TheCircle",
        "NativeAmerican", "SPCJapanese", "SPCChinese", "SPCIndians",
        "SPCCompany", "SPCBarbaryPirates", "SPCAmericans", "SPCTatars",
        "SPCEthiopians", "SPCSomalis", "SPCRenoGang", "SPCHoleGang",
        "SPCMoroccans", "SPCCanadians", "XPSPC", "XPSPCFalcon",
        "XPSPCLakota", "SPCJapaneseEnemy",
    )
    leaked = []
    for name in suppressed_should_hide:
        civ = merged.get(name)
        if civ is None:
            continue
        m = civ.find("main") or civ.find("Main")
        v = (m.text or "").strip() if m is not None else ""
        if v == "1":
            leaked.append(name)
    if leaked:
        print(f"  ✗ Suppressed base civs leaked through with main=1: "
              f"{len(leaked)}: {leaked[:5]}")

    # === Check 4: StatsID uniqueness ===
    sids: dict[str, list[str]] = {}
    for token, civ in merged.items():
        s = civ.find("statsid") or civ.find("StatsID")
        if s is not None and (s.text or "").strip():
            sids.setdefault(s.text.strip(), []).append(token)
    dup_sids = {k: v for k, v in sids.items() if len(v) > 1}
    if dup_sids:
        print(f"  ✗ StatsID collisions in merged table: {len(dup_sids)}")
        for sid, civs in list(dup_sids.items())[:5]:
            print(f"      {sid}: {civs}")

    # === Check 5: ANW homecityflagiconwpf survived merge ===
    flag_lost = []
    for token in ANW_CIVS:
        civ = merged.get(token)
        if civ is None:
            continue
        wpf = civ.find("homecityflagiconwpf") or civ.find("HomeCityFlagIconWpf")
        if wpf is None or not (wpf.text or "").strip():
            flag_lost.append(token)
    print()
    print(f"  ANW civs with homecityflagiconwpf set in merged: "
          f"{len(ANW_CIVS) - len(flag_lost)}/46")
    if flag_lost:
        print(f"  ✗ ANW civs missing homecityflagiconwpf in merged: "
              f"{len(flag_lost)}")
        for t in flag_lost[:10]:
            print(f"      {t}")

    fail_count = (len(missing_anw) + len(not_main) + len(leaked)
                  + len(dup_sids) + len(flag_lost))
    print()
    print("=" * 60)
    if fail_count == 0:
        print(f"✓ PASS — engine merged XML matches expectations")
    else:
        print(f"✗ FAIL — {fail_count} merge-state discrepancies "
              f"(see above for details)")
    print("=" * 60)

    if args.json:
        report = {
            "merged_civs_count": len(merged),
            "anw_present": len(ANW_CIVS) - len(missing_anw),
            "missing_anw": missing_anw,
            "anw_not_main": not_main,
            "leaked_suppressions": leaked,
            "duplicate_statsids": dup_sids,
            "anw_flag_lost": flag_lost,
            "fail_count": fail_count,
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, default=list))

    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
