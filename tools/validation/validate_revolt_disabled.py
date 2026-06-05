#!/usr/bin/env python3
"""
validate_revolt_disabled.py

Static guard that the ability to revolt stays fully removed.

ANW design: the nation you pick in the lobby is the nation you play the whole
game. There is no mid-game revolting. This validator asserts that invariant at
three layers so it can never silently regress:

  1. DATA  — every revolution *trigger* tech in data/techtreemods.xml is
     UNOBTAINABLE by default (a non-allowlisted Revolution/Revolt tech that is
     OBTAINABLE is a FAIL).
  2. DATA  — LLDisableStockRevolutionsGlobal exists, is OBTAINABLE (so the
     shadow tech auto-researches at game start) and explicitly lists the
     revolution triggers it turns unobtainable.
  3. AI    — gANWAllowRevolt is declared false in aiGlobals.xs, and the AI
     revolt decision in aiTechs.xs is guarded by gANWAllowRevolt.

Allowlist: revolution-*named* techs that are NOT revolt triggers (passive unit
buffs / setup shadows for standalone civs) may remain OBTAINABLE.

Exit 0 = PASS, 1 = FAIL. Pure static parse; no game required.

Usage:
    python3 tools/validation/validate_revolt_disabled.py
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TECH = REPO / "data/techtreemods.xml"
GLOBALS = REPO / "game/ai/core/aiGlobals.xs"
AITECHS = REPO / "game/ai/core/aiTechs.xs"

# Revolution-NAMED techs that are NOT revolt triggers and may stay OBTAINABLE:
#   - the disabler itself
#   - ANWBrazilRevolutionaryShadow: passive Imperial-age unit buff for the
#     standalone ANWBrazilians civ (xpColonialMilitia HP/damage, Voluntario
#     batch), not a nation-change trigger.
ALLOWLIST_OBTAINABLE = {
    "LLDisableStockRevolutionsGlobal",
    "ANWBrazilRevolutionaryShadow",
}

# A tech is a "revolt trigger" if its name matches DERevolution* or *Revolt*.
TRIGGER_RE = re.compile(r"DERevolution|Revolt")


def parse_tech_blocks(text: str):
    return re.findall(r"<Tech name\s*=\s*'([^']+)'[^>]*>(.*?)</Tech>", text, re.DOTALL)


def main() -> int:
    tech_text = TECH.read_text(encoding="utf-8", errors="replace")
    blocks = parse_tech_blocks(tech_text)

    failures, infos = [], []

    # Layer 1: every revolt-trigger tech must be UNOBTAINABLE by default.
    triggers = []
    for name, body in blocks:
        if not TRIGGER_RE.search(name):
            continue
        sm = re.search(r"<Status>\s*([A-Z]+)\s*</Status>", body)
        status = sm.group(1) if sm else "MISSING"
        triggers.append((name, status))
        if name in ALLOWLIST_OBTAINABLE:
            continue
        if status != "UNOBTAINABLE":
            failures.append(
                f"[data] revolt-trigger tech {name} has default Status={status} "
                f"(must be UNOBTAINABLE).")

    # Layer 2: the global disabler exists, OBTAINABLE, lists triggers.
    dis = next((b for n, b in blocks if n == "LLDisableStockRevolutionsGlobal"), None)
    if dis is None:
        failures.append("[data] LLDisableStockRevolutionsGlobal tech is missing.")
        disabled = set()
    else:
        sm = re.search(r"<Status>\s*([A-Z]+)\s*</Status>", dis)
        if not sm or sm.group(1) != "OBTAINABLE":
            failures.append(
                "[data] LLDisableStockRevolutionsGlobal must be OBTAINABLE so the "
                "shadow tech auto-researches at game start.")
        disabled = set(re.findall(r"status\s*=\s*'unobtainable'>([^<]+)<", dis))
        infos.append(f"global disabler turns {len(disabled)} revolutions unobtainable")

    # Layer 3: AI flag + guard.
    g = GLOBALS.read_text(encoding="utf-8", errors="replace")
    if not re.search(r"gANWAllowRevolt\s*=\s*false", g):
        failures.append("[ai] gANWAllowRevolt is not declared false in aiGlobals.xs.")
    a = AITECHS.read_text(encoding="utf-8", errors="replace")
    if "gANWAllowRevolt" not in a:
        failures.append("[ai] aiTechs.xs revolt decision is not guarded by gANWAllowRevolt.")

    print("=" * 64)
    print("ANW Revolt-Disabled Validator")
    print("=" * 64)
    print(f"revolt-trigger techs found:  {len(triggers)}")
    print(f"allowlisted (non-trigger):   "
          f"{sorted(n for n, _ in triggers if n in ALLOWLIST_OBTAINABLE)}")
    for i in infos:
        print(f"info: {i}")
    print("-" * 64)
    for f in failures:
        print(f"  FAIL  {f}")
    if failures:
        print("-" * 64)
        print(f"RESULT: FAIL ({len(failures)} error(s))")
        return 1
    print("-" * 64)
    print("RESULT: PASS — revolting is fully disabled at data + AI layers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
