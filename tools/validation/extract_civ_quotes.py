"""
extract_civ_quotes.py — parse AI leader quotes and chatset lines per civ.

Public API
----------
extract_insults_compliments(xs_path)  -> dict[civName, {insults, compliments}]
extract_shared_tactical_lines(xs_path) -> dict[key, str]
extract_chatset_lines(xml_path)        -> dict[chatset_name, list[dict]]
quotes_for_spec_token(...)             -> dict with all surfaces for one token
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Mapping tables
# ---------------------------------------------------------------------------

# Spec calibration-key → aiLeaderQuotes civName branch (post-llNormalizeCivName).
_CALIB_TO_QUOTES_CIVNAME: dict[str, str] = {
    # ANW revolution civs
    "ANWArgentines": "ANWArgentines", "ANWBarbary": "ANWBarbary",
    "ANWBrazil": "ANWBrazil", "ANWCanadians": "ANWCanadians",
    "ANWChileans": "ANWChileans", "ANWColumbians": "ANWColumbians",
    "ANWEgyptians": "ANWEgyptians", "ANWFinnish": "ANWFinnish",
    "ANWHaitians": "ANWHaitians", "ANWHungarians": "ANWHungarians",
    "ANWIndonesians": "ANWIndonesians", "ANWMayans": "ANWMayans",
    "ANWNapoleonicFrance": "ANWNapoleonicFrance",
    "ANWPeruvians": "ANWPeruvians",
    "ANWRevFrance": "ANWNapoleonicFrance",  # shares quotes branch
    "ANWRomanians": "ANWRomanians", "ANWSouthAfricans": "ANWSouthAfricans",
    "ANWTexians": "ANWTexians",
    # DE / XP — normalized via llNormalizeCivName
    "DEAmericans": "UnitedStates", "DEEthiopians": "Ethiopians",
    "DEHausa": "Hausa", "DEInca": "Inca", "DEItalians": "Italians",
    "DEMaltese": "Maltese", "DEMexicans": "Mexicans", "DESwedish": "Swedes",
    "XPAztec": "Aztecs", "XPIroquois": "Haudenosaunee", "XPSioux": "Lakota",
    # base civs map to themselves
    "British": "British", "Chinese": "Chinese", "Dutch": "Dutch",
    "French": "French", "Germans": "Germans", "Indians": "Indians",
    "Japanese": "Japanese", "Ottomans": "Ottomans", "Portuguese": "Portuguese",
    "Russians": "Russians", "Spanish": "Spanish",
}

# Calibration-key → chatset name (lowercased anw_<stem>).
_CALIB_TO_CHATSET_NAME: dict[str, str] = {
    # ANW revolution civs
    "ANWArgentines": "anw_argentines", "ANWBarbary": "anw_barbary",
    "ANWBrazil": "anw_brazil", "ANWCanadians": "anw_canadians",
    "ANWChileans": "anw_chileans", "ANWColumbians": "anw_columbians",
    "ANWEgyptians": "anw_egyptians", "ANWFinnish": "anw_finnish",
    "ANWHaitians": "anw_haitians", "ANWHungarians": "anw_hungarians",
    "ANWIndonesians": "anw_indonesians", "ANWMayans": "anw_mayans",
    "ANWNapoleonicFrance": "anw_napoleonicfrance", "ANWPeruvians": "anw_peruvians",
    "ANWRevFrance": "anw_revfrance", "ANWRomanians": "anw_romanians",
    "ANWSouthAfricans": "anw_southafricans", "ANWTexians": "anw_texians",
    # DE / XP
    "DEAmericans": "anw_usa", "DEEthiopians": "anw_ethiopians",
    "DEHausa": "anw_hausa", "DEInca": "anw_inca", "DEItalians": "anw_italians",
    "DEMaltese": "anw_maltese", "DEMexicans": "anw_mexicans",
    "DESwedish": "anw_swedes", "XPAztec": "anw_aztecs",
    "XPIroquois": "anw_haudenosaunee", "XPSioux": "anw_lakota",
    # base civs
    "British": "anw_british", "Chinese": "anw_chinese", "Dutch": "anw_dutch",
    "French": "anw_french", "Germans": "anw_germans", "Indians": "anw_indians",
    # Ottomans/Suleiman retained its base-game chatset name ("suleiman") in
    # chatsetsmods.xml instead of being re-emitted as "anw_ottomans". Map
    # directly so the Ottomans card shows its 6 engine lines.
    "Japanese": "anw_japanese", "Ottomans": "suleiman",
    "Portuguese": "anw_portuguese", "Russians": "anw_russians",
    "Spanish": "anw_spanish",
}

# ---------------------------------------------------------------------------
# Regex patterns for XS parsing
# ---------------------------------------------------------------------------

# Matches a civ branch of the form:
#   (else )?if (\(?civName == "Foo"\)? (|| (civName == "Bar"))?) { ... }
# Captures: civ1, optional civ2, quote_index_0 return, default return.
_BRANCH_RE = re.compile(
    r'(?:else\s+)?if\s*\(\s*'
    r'\(?civName\s*==\s*"(?P<civ1>[A-Za-z0-9_]+)"\)?'
    r'(?:\s*\|\|\s*\(civName\s*==\s*"(?P<civ2>[A-Za-z0-9_]+)"\))?'
    r'\s*\)'
    r'\s*\{'
    r'\s*if\s*\(quoteIndex\s*==\s*0\)\s*\{\s*return\s*\("(?P<q0>[^"]+)"\);\s*\}'
    r'\s*return\s*\("(?P<q1>[^"]+)"\);'
    r'\s*\}',
    re.DOTALL,
)

# Matches a single-line tactical function: string llGet...(void) { return ("..."); }
_TACTICAL_RE = re.compile(
    r'string\s+(?P<fn>llGetLegendaryLeader(?:Retreat|Rout|BulkAssault|Decapitation)Line)'
    r'\s*\(void\)\s*\{\s*return\s*\("(?P<line>[^"]+)"\);\s*\}',
    re.DOTALL,
)

# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def extract_shared_tactical_lines(xs_path: Path) -> dict[str, str]:
    """Return {"retreat": str, "rout": str, "bulk_assault": str, "decapitation": str}
    parsed from the 4 single-line functions near lines 127-145."""
    text = xs_path.read_text(encoding="utf-8")
    fn_to_key = {
        "llGetLegendaryLeaderRetreatLine": "retreat",
        "llGetLegendaryLeaderRoutLine": "rout",
        "llGetLegendaryLeaderBulkAssaultLine": "bulk_assault",
        "llGetLegendaryLeaderDecapitationLine": "decapitation",
    }
    result: dict[str, str] = {}
    for m in _TACTICAL_RE.finditer(text):
        key = fn_to_key.get(m.group("fn"))
        if key:
            result[key] = m.group("line")
    return result


def _parse_quote_function(fn_body: str) -> dict[str, dict[str, list[str]]]:
    """Walk a function body and return {civName: {insults|compliments: [q0, q1]}}."""
    out: dict[str, dict[str, list[str]]] = {}
    for m in _BRANCH_RE.finditer(fn_body):
        lines = [m.group("q0"), m.group("q1")]
        civ1 = m.group("civ1")
        out[civ1] = lines
        civ2 = m.group("civ2")
        if civ2:
            out[civ2] = lines  # both aliases point to same lines
    return out


def extract_insults_compliments(xs_path: Path) -> dict[str, dict[str, list[str]]]:
    """Parse aiLeaderQuotes.xs and return:
    {
      "<civName>": {"insults": ["line a", "line b"], "compliments": ["line a", "line b"]},
      ...
    }
    For OR'd branches (e.g. (civName == "Haudenosaunee") || (civName == "XPIroquois")),
    emit one entry per civName, both pointing at the same lines.
    """
    text = xs_path.read_text(encoding="utf-8")

    # Slice out the two function bodies.
    insult_start_marker = "string llGetLegendaryLeaderInsult(void)"
    compliment_start_marker = "string llGetLegendaryLeaderCompliment(void)"

    insult_start = text.index(insult_start_marker)
    compliment_start = text.index(compliment_start_marker)

    insult_body = text[insult_start:compliment_start]
    compliment_body = text[compliment_start:]

    insults_map = _parse_quote_function(insult_body)
    compliments_map = _parse_quote_function(compliment_body)

    # Merge into a combined per-civName dict.
    all_civs = set(insults_map) | set(compliments_map)
    result: dict[str, dict[str, list[str]]] = {}
    for civ in all_civs:
        result[civ] = {
            "insults": insults_map.get(civ, []),
            "compliments": compliments_map.get(civ, []),
        }
    return result


def extract_chatset_lines(xml_path: Path) -> dict[str, list[dict]]:
    """Parse chatsetsmods.xml and return:
    {
      "anw_argentines": [
        {"tag": "ToAllyIntro", "string": "...", "sound": "chats\\SANM0000.mp3", "string_id": "491012"},
        ...
      ],
      ...
    }
    Uses xml.etree.ElementTree; XML comments (<!-- -->) are skipped automatically.
    'suleiman' and other non-anw_ blocks are included as-is.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    result: dict[str, list[dict]] = {}
    for chatset in root.iter("Chatset"):
        name = chatset.get("name", "")
        tags: list[dict] = []
        for tag in chatset.findall("Tag"):
            tag_name = tag.get("name", "")
            sentence = tag.find("Sentence")
            if sentence is None:
                continue
            string_el = sentence.find("String")
            sound_el = sentence.find("Sound")
            sid_el = sentence.find("StringID")
            tags.append({
                "tag": tag_name,
                "string": string_el.text if string_el is not None else "",
                "sound": sound_el.text if sound_el is not None else "",
                "string_id": sid_el.text if sid_el is not None else "",
            })
        result[name] = tags
    return result


def quotes_for_spec_token(
    spec_token: str,
    calib_key: str | None,
    insults_compliments: dict,
    shared: dict,
    chatsets: dict,
) -> dict:
    """Resolve all surfaces for one spec token.

    Returns:
    {
      "insults": [...],
      "compliments": [...],
      "shared_tactical": {"retreat": str, "rout": str, "bulk_assault": str, "decapitation": str},
      "chatset": [...],
      "quotes_civname": str,
      "chatset_name": str,
    }
    """
    quotes_civname = ""
    chatset_name = ""
    insults: list[str] = []
    compliments: list[str] = []
    chatset_entries: list[dict] = []

    if calib_key:
        quotes_civname = _CALIB_TO_QUOTES_CIVNAME.get(calib_key, calib_key)
        chatset_name = _CALIB_TO_CHATSET_NAME.get(calib_key, "")

        civ_data = insults_compliments.get(quotes_civname, {})
        insults = civ_data.get("insults", [])
        compliments = civ_data.get("compliments", [])

        if chatset_name:
            chatset_entries = chatsets.get(chatset_name, [])

    return {
        "insults": insults,
        "compliments": compliments,
        "shared_tactical": shared,
        "chatset": chatset_entries,
        "quotes_civname": quotes_civname,
        "chatset_name": chatset_name,
    }


# ---------------------------------------------------------------------------
# __main__ sanity-check
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[2]
    xs_path = repo_root / "game" / "ai" / "core" / "aiLeaderQuotes.xs"
    xml_path = repo_root / "game" / "ai" / "chatsetsmods.xml"

    shared = extract_shared_tactical_lines(xs_path)
    ic = extract_insults_compliments(xs_path)
    chatsets = extract_chatset_lines(xml_path)

    insult_civs = sorted(k for k, v in ic.items() if v["insults"])
    compliment_civs = sorted(k for k, v in ic.items() if v["compliments"])
    only_insults = set(insult_civs) - set(compliment_civs)
    only_compliments = set(compliment_civs) - set(insult_civs)
    both = set(insult_civs) & set(compliment_civs)

    summary = {
        "insults_parsed": len(insult_civs),
        "compliments_parsed": len(compliment_civs),
        "civs_with_both": len(both),
        "civs_only_insults": sorted(only_insults),
        "civs_only_compliments": sorted(only_compliments),
        "chatsets_parsed": len(chatsets),
        "chatset_names": sorted(chatsets.keys()),
        "all_civnames": sorted(ic.keys()),
        "shared_tactical": shared,
    }

    print(json.dumps(summary, indent=2))

    # Spot-check one civ.
    print("\n--- Spot-check: Aztecs ---")
    print(json.dumps(ic.get("Aztecs", {}), indent=2))
    print("\n--- Spot-check: ANWArgentines ---")
    print(json.dumps(ic.get("ANWArgentines", {}), indent=2))
    print("\n--- Spot-check chatset: anw_argentines ---")
    print(json.dumps(chatsets.get("anw_argentines", []), indent=2))
