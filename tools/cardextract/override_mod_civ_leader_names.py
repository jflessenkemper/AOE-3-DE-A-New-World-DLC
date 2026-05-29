"""Set the PERSONALITY display name (not the civ name) for the 26 mod civs.

BUGFIX (2026-04-22): the previous version overrode strings at the civ's
DisplayNameID (80806-80835), which caused the civ picker/home-city picker
to display the leader name INSTEAD OF the country name. That's wrong —
the country is the civ's identity; the leader belongs to the personality.

Correct architecture:
  - civmods.xml <DisplayNameID> → country string (base-game default, unchanged)
  - anw*.personality <nameID> → NEW mod string (leader name)

This script:
  1. Allocates leader-name strings at IDs LEADER_ID_BASE + offset (default 490250+)
  2. Writes those entries into stringmods.xml under MOD-CIV-LEADER-NAMES markers
  3. REMOVES any prior overrides at the civ DisplayNameIDs (80806-80835 etc.)
  4. Rewrites anw*.personality files' <nameID> and <playerNames><nameID>
     to point to the new leader IDs.

Idempotent.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AI_DIR = REPO / "game" / "ai"
STRINGS_PATH = REPO / "data" / "strings" / "english" / "stringmods.xml"

LEADER_ID_BASE = 490250

# Strings that must PERSIST as country names (they're mod-allocated IDs
# with no base-game fallback, unlike 80806-80835 which fall back cleanly).
PERSIST_CIV_NAMES = {
    490001: "Revolutionary France",
    490003: "Napoleonic France",
}

# (personality_filename_stem, leader_display_name, civ_display_name_id_to_unoverride)
MOD_LEADERS = [
    ("anwnapoleonicfrance",   "Napoleon Bonaparte",        490003),
    ("anwrevfrance","Maximilien Robespierre",    490001),
    ("anwamericans",          "Thomas Jefferson",          80829),
    ("anwmexicans",           "Miguel Hidalgo",            80830),
    ("anwcanadians",          "Isaac Brock",               80807),
    ("anwbrazil",             "Pedro I of Brazil",         80831),
    ("anwargentines",         "José de San Martín",        80833),
    ("anwchileans",           "Bernardo O'Higgins",        80835),
    ("anwperuvians",          "Andrés de Santa Cruz",      80832),
    ("anwcolumbians",         "Simón Bolívar",             80834),
    ("anwhaitians",           "Toussaint L'Ouverture",     80828),
    ("anwindonesians",        "Prince Diponegoro",         80811),
    ("anwsouthafricans",      "Paul Kruger",               80813),
    ("anwfinnish",            "Carl Gustaf Mannerheim",    80809),
    ("anwhungarians",         "Lajos Kossuth",             80810),
    ("anwromanians",          "Alexandru Ioan Cuza",       80812),
    ("anwbarbary",            "Hayreddin Barbarossa",      80806),
    ("anwegyptians",          "Muhammad Ali Pasha",        80808),
    ("anwbajacalifornians",   "Juan Bautista Alvarado",    112806),
    ("anwriogrande",          "Antonio Canales Rosillo",   112814),
    ("anwmayans",             "Jacinto Canek",             112816),
    ("anwtexians",            "Sam Houston",               112826),
]


def escape_xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rewrite_personality(stem: str, new_name_id: int) -> bool:
    """Update <nameID> and <playerNames><nameID> in a .personality file."""
    path = AI_DIR / f"{stem}.personality"
    if not path.exists():
        return False
    txt = path.read_text(encoding="utf-8")
    new_txt = re.sub(r"<nameID>\d+</nameID>", f"<nameID>{new_name_id}</nameID>", txt)
    path.write_text(new_txt, encoding="utf-8")
    return True


def main():
    content = STRINGS_PATH.read_text(encoding="utf-8")

    # 1) Clean ANY previous leader-name injections at civ DisplayNameIDs.
    #    These are the strings that broke the civ picker.
    for _, _, civ_id in MOD_LEADERS:
        content = re.sub(
            r"[ \t]*<String\s+_locID=['\"]" + str(civ_id) + r"['\"][^>]*>[^<]*</String>\s*\r?\n",
            "", content,
        )

    # 1b) Re-inject country-name strings for IDs that have no base-game fallback.
    persist_lines = []
    for cid, country_name in PERSIST_CIV_NAMES.items():
        safe = escape_xml(country_name)
        persist_lines.append(f"      <String _locID='{cid}'>{safe}</String>")
    if persist_lines:
        injection = "\n".join(persist_lines) + "\n"
        content = content.replace("</Language>", injection + "</Language>", 1)

    # 2) Clean prior MOD-CIV-LEADER-NAMES markers.
    start = "<!-- MOD-CIV-LEADER-NAMES-START -->"
    end = "<!-- MOD-CIV-LEADER-NAMES-END -->"
    content = re.sub(
        re.escape(start) + r".*?" + re.escape(end) + r"\r?\n?",
        "", content, flags=re.DOTALL,
    )

    # 3) Allocate new leader IDs and rewrite personality files.
    assignments = []  # (stem, leader_name, new_id)
    for i, (stem, leader, _) in enumerate(MOD_LEADERS):
        new_id = LEADER_ID_BASE + i
        if not rewrite_personality(stem, new_id):
            print(f"  WARN: {stem}.personality not found, skipping")
            continue
        assignments.append((stem, leader, new_id))

    # 4) Inject new strings block under fresh markers before </Language>.
    lines = [start]
    for stem, leader, new_id in assignments:
        safe = escape_xml(leader)
        lines.append(f"      <String _locID='{new_id}'>{safe}</String>  <!-- {stem} -->")
    lines.append(end)
    injection = "\n".join(lines) + "\n"
    content = content.replace("</Language>", injection + "</Language>", 1)

    STRINGS_PATH.write_text(content, encoding="utf-8")

    print(f"wrote {len(assignments)} leader-name strings at IDs "
          f"{LEADER_ID_BASE}-{LEADER_ID_BASE + len(assignments) - 1}")
    print(f"restored {len(MOD_LEADERS)} civ DisplayNameID slots to base-game defaults")
    for stem, leader, new_id in assignments:
        print(f"  {stem}.personality  nameID={new_id}  → {leader!r}")


if __name__ == "__main__":
    main()
