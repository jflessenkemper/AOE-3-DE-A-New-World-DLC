"""Generate chatsetsmods.xml tags, stringmods.xml entries, and HTML
reference quote-block updates from a single `quotes.json` source of truth.

Inputs:
  - tools/chatquotes/quotes.json  — per-leader quote data

Outputs:
  - game/ai/chatsetsmods.xml       — per-leader <Chatset> with <Tag> + <Sentence>
  - data/strings/english/stringmods.xml
                                   — <String _locID> entries per quote
  - a_new_world.html    — per-civ Quotes block refreshed
  - game/ai/*.personality          — each personality's <chatset> updated to the leader name

Idempotent via markers.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
QUOTES_JSON = REPO / "tools" / "chatquotes" / "quotes.json"
CHATSETS_PATH = REPO / "game" / "ai" / "chatsetsmods.xml"
STRINGS_PATH = REPO / "data" / "strings" / "english" / "stringmods.xml"
HTML_PATH = REPO / "a_new_world.html"
AI_DIR = REPO / "game" / "ai"

CHAT_START = "<!-- LL-LEADER-QUOTES-START -->"
CHAT_END = "<!-- LL-LEADER-QUOTES-END -->"
STR_START = "<!-- LL-QUOTE-STRINGS-START -->"
STR_END = "<!-- LL-QUOTE-STRINGS-END -->"

# Personality file stem → chatset name (1:1 with leader key in quotes.json)
# For base-civ overrides + the 26 anw civs.
PERSONALITY_CHATSET = {
    "wellington":  "wellington",
    "catherine":   "catherine",
    "maurice":     "maurice",
    "usman":       "usman",
    "menelik":     "menelik",
    "shivaji":     "shivaji",
    "montezuma":   "montezuma",
    "pachacuti":   "pachacuti",
    "napoleon":    "napoleon",
    "washington":  "washington",
    "isabella":    "isabella",
    "henry":       "henry",
    "Frederick":   "Frederick",
    "garibaldi":   "garibaldi",
    "Gustav":      "Gustav",
    "hidalgo":     "hidalgo",
    "Hiawatha":    "Hiawatha",
    "crazyhorse":  "crazyhorse",
    "jean":        "jean",
    "kangxi":      "kangxi",
    "Suleiman":    "suleiman",   # persist `suleiman` lowercase chatset name
    "tokugawa":    "tokugawa",
}

# For each leader chatset, a base-game MP3 path to use as the chat Sound.
# Without a Sound element the engine skips the chat portrait — so we point at
# an EXISTING base-game MP3 in the same vocal family. The quote TEXT is our
# override; the audio is the base-game leader's generic grunt. Not ideal,
# but restores the portrait thumbnail in the chat bubble.
LEADER_SOUND_STUB = {
    # Base civ overrides — use the original personality's MP3 pool
    "wellington":  "chats\\ELIZ0000.mp3",
    "catherine":   "chats\\IVAN0000.mp3",
    "maurice":     "chats\\WILL0000.mp3",
    "usman":       "chats\\AMIN0000.mp3",
    "menelik":     "chats\\TEWO0000.mp3",
    "shivaji":     "chats\\AKBA0000.mp3",
    "montezuma":   "chats\\CUAU0000.mp3",
    "pachacuti":   "chats\\HUAY0000.mp3",
    "napoleon":    "chats\\NAPO0000.mp3",
    "washington":  "chats\\WASH0000.mp3",
    "isabella":    "chats\\ISAB0000.mp3",
    "henry":       "chats\\HENR0000.mp3",
    "Frederick":   "chats\\FRED0000.mp3",
    "garibaldi":   "chats\\GARI0000.mp3",
    "Gustav":      "chats\\GUST0000.mp3",
    "hidalgo":     "chats\\HIDA0000.mp3",
    "Hiawatha":    "chats\\HIAW0000.mp3",
    "crazyhorse":  "chats\\CRAZ0000.mp3",
    "jean":        "chats\\JEAN0000.mp3",
    "kangxi":      "chats\\KANG0000.mp3",
    "suleiman":    "chats\\SULE0000.mp3",
    "tokugawa":    "chats\\TOKU0000.mp3",
    # Mod civs — route to thematically-closest base-game chatset MP3 pool
    "anwnapoleonicfrance":    "chats\\NAPO0000.mp3",
    "anwrevfrance": "chats\\NAPO0000.mp3",
    "anwamericans":           "chats\\WASH0000.mp3",
    "anwmexicans":            "chats\\HIDA0000.mp3",
    "anwcanadians":           "chats\\ELIZ0000.mp3",
    "anwbrazil":              "chats\\HENR0000.mp3",
    "anwargentines":          "chats\\ISAB0000.mp3",
    "anwchileans":            "chats\\ISAB0000.mp3",
    "anwperuvians":           "chats\\ISAB0000.mp3",
    "anwcolumbians":          "chats\\ISAB0000.mp3",
    "anwhaitians":            "chats\\NAPO0000.mp3",
    "anwindonesians":         "chats\\WILL0000.mp3",
    "anwsouthafricans":       "chats\\WILL0000.mp3",
    "anwfinnish":             "chats\\IVAN0000.mp3",
    "anwhungarians":          "chats\\FRED0000.mp3",
    "anwromanians":           "chats\\FRED0000.mp3",
    "anwbarbary":             "chats\\SULE0000.mp3",
    "anwegyptians":           "chats\\SULE0000.mp3",
    "anwbajacalifornians":    "chats\\ISAB0000.mp3",
    "anwriogrande":           "chats\\HIDA0000.mp3",
    "anwmayans":              "chats\\CUAU0000.mp3",
    "anwtexians":             "chats\\WASH0000.mp3",
}

# Map anw*.personality → chatset key. We keep unique chatset names
# per leader so each gets its own quote pool — but ensure the chatset
# name-string exists so the engine can resolve speaker identity.
RVLT_CHATSET = {
    "anwnapoleonicfrance":    "anwnapoleonicfrance",
    "anwrevfrance": "anwrevfrance",
    "anwamericans":           "anwamericans",
    "anwmexicans":            "anwmexicans",
    "anwcanadians":           "anwcanadians",
    "anwbrazil":              "anwbrazil",
    "anwargentines":          "anwargentines",
    "anwchileans":            "anwchileans",
    "anwperuvians":           "anwperuvians",
    "anwcolumbians":          "anwcolumbians",
    "anwhaitians":            "anwhaitians",
    "anwindonesians":         "anwindonesians",
    "anwsouthafricans":       "anwsouthafricans",
    "anwfinnish":             "anwfinnish",
    "anwhungarians":          "anwhungarians",
    "anwromanians":           "anwromanians",
    "anwbarbary":             "anwbarbary",
    "anwegyptians":           "anwegyptians",
    "anwbajacalifornians":    "anwbajacalifornians",
    "anwriogrande":           "anwriogrande",
    "anwmayans":              "anwmayans",
    "anwtexians":             "anwtexians",
}

# Each anw civ's civmods.xml DisplayNameID — we inject BOTH the civ-name
# string (country) AND point the personality at its leader string (via
# nameID). The in-match chat speaker name comes from the personality's
# <playerNames><nameID>. Base civs work because elizabeth.personality (our
# wellington content) is the default personality loaded when British is
# picked — its nameID is 490200 = "Duke of Wellington".
#
# For mod civs the personality is auto-selected from personalities.xml by
# matching <forcedciv>. This works but the chat speaker name depends on
# engine precedence: some versions use civ DisplayNameID, others use
# personality playerNames.nameID. Not fixable here without engine hook.
RVLT_DISPLAY_IDS = {
    "anwbarbary": 80806,
    "anwcanadians": 80807,
    "anwegyptians": 80808,
    "anwfinnish": 80809,
    "anwhungarians": 80810,
    "anwindonesians": 80811,
    "anwromanians": 80812,
    "anwsouthafricans": 80813,
    "anwhaitians": 80828,
    "anwamericans": 80829,
    "anwmexicans": 80830,
    "anwbrazil": 80831,
    "anwperuvians": 80832,
    "anwargentines": 80833,
    "anwcolumbians": 80834,
    "anwchileans": 80835,
    "anwnapoleonicfrance": 490003,
    "anwrevfrance": 490001,
    "anwbajacalifornians": 112806,
    "anwriogrande": 112814,
    "anwmayans": 112816,
    "anwcalifornians": 112822,
    "anwtexians": 112826,
}

# HTML civ-name → leader key used in quotes.json. For 48 civs.
# Mirrors the anchor patterns inject_walling_doctrine uses.
HTML_CIV_TO_LEADER = {
    # 22 base civ HTML sections
    "Aztecs":               "montezuma",
    "British":              "wellington",
    "Chinese":              "kangxi",
    "Dutch":                "maurice",
    "Ethiopians":           "menelik",
    "French":               "napoleon",   # Bourbon France — we use napoleon key for base French too
    "Germans":              "Frederick",
    "Haudenosaunee":        "Hiawatha",
    "Hausa":                "usman",
    "Inca":                 "pachacuti",
    "Indians":              "shivaji",
    "Italians":             "garibaldi",
    "Japanese":             "tokugawa",
    "Lakota":               "crazyhorse",
    "Maltese":              "jean",
    "Mexicans (Standard)":  "hidalgo",
    "Ottomans":              "suleiman",
    "Portuguese":            "henry",
    "Russians":              "catherine",
    "Spanish":               "isabella",
    "Swedes":                "Gustav",
    "United States":         "washington",
    # 26 anw civ HTML sections (spelled per actual HTML anchors)
    "Americans":             "anwamericans",
    "Argentines":            "anwargentines",
    "Barbary":               "anwbarbary",
    "Brazil":                "anwbrazil",
    "Canadians":             "anwcanadians",
    "Chileans":              "anwchileans",
    "Columbians":            "anwcolumbians",
    "Egyptians":             "anwegyptians",
    "Finnish":               "anwfinnish",
    "Haitians":              "anwhaitians",
    "Hungarians":            "anwhungarians",
    "Indonesians":           "anwindonesians",
    "Mayans":                "anwmayans",
    "Mexicans (Revolution)": "anwmexicans",
    "Napoleonic France":     "anwnapoleonicfrance",
    "Peruvians":             "anwperuvians",
    "Revolutionary France":  "anwrevfrance",
    "Romanians":             "anwromanians",
    "South Africans":        "anwsouthafricans",
    "Texians":               "anwtexians",
    "Baja Californians":     "anwbajacalifornians",
    "Rio Grande":            "anwriogrande",
}


def escape_xml(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace("'", "&apos;").replace('"', "&quot;"))


def allocate_string_id(leader_idx: int, trigger_idx: int, base: int) -> int:
    return base + leader_idx * 50 + trigger_idx


def generate(quotes: dict) -> tuple[str, str, dict]:
    """Return (chatsets_block, strings_block, leader_quotes_map) for injection."""
    meta = quotes["_meta"]
    triggers = meta["full_trigger_list"]
    trigger_idx = {t: i for i, t in enumerate(triggers)}
    base_id = meta["string_id_base"]

    leaders = quotes["leaders"]
    leader_keys = sorted(leaders.keys())

    chat_lines = [CHAT_START, "<!-- Generated by tools/chatquotes/generate_chat_quotes.py -->"]
    str_lines = [STR_START]
    per_leader_quotes: dict[str, dict[str, tuple[str, int]]] = {}

    for li, leader_key in enumerate(leader_keys):
        leader = leaders[leader_key]
        quotes_for_leader = {k: v for k, v in leader.items() if k != "display"}
        if not quotes_for_leader:
            continue

        chat_lines.append(f'<Chatset name="{leader_key}">')
        per_leader_quotes[leader_key] = {}

        for trigger_key, quote_text in quotes_for_leader.items():
            if trigger_key not in trigger_idx:
                continue
            ti = trigger_idx[trigger_key]
            sid = allocate_string_id(li, ti, base_id)
            safe = escape_xml(quote_text)

            chat_lines.append(f'   <Tag type="AiChat" name="{trigger_key}" priority="Background">')
            chat_lines.append('      <Sentence>')
            chat_lines.append(f'         <String>{safe}</String>')
            sound = LEADER_SOUND_STUB.get(leader_key, "chats\\ELIZ0000.mp3")
            chat_lines.append(f'         <Sound>{sound}</Sound>')
            chat_lines.append(f'         <StringID>{sid}</StringID>')
            chat_lines.append('      </Sentence>')
            chat_lines.append('   </Tag>')

            str_lines.append(f"      <String _locID='{sid}'>{safe}</String>")
            per_leader_quotes[leader_key][trigger_key] = (quote_text, sid)

        chat_lines.append('</Chatset>')

    chat_lines.append(CHAT_END)
    str_lines.append(STR_END)

    return ("\n".join(chat_lines), "\n".join(str_lines), per_leader_quotes)


def inject_into_chatsets(block: str) -> None:
    path = CHATSETS_PATH
    if not path.exists():
        path.write_text(f"<root>\n{block}\n</root>\n", encoding="utf-8")
        return
    txt = path.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(CHAT_START) + r".*?" + re.escape(CHAT_END), re.DOTALL)
    if pattern.search(txt):
        # Use lambda to avoid backslash-escape interpretation in `block`
        # (DDT / MP3 paths contain \F, \N etc. which break re.sub replacement).
        new_txt = pattern.sub(lambda _m: block, txt)
    else:
        # Insert before </root>
        if "</root>" in txt:
            new_txt = txt.replace("</root>", block + "\n</root>", 1)
        else:
            new_txt = txt + "\n" + block + "\n"
    path.write_text(new_txt, encoding="utf-8")


def inject_into_stringmods(block: str) -> None:
    path = STRINGS_PATH
    txt = path.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(STR_START) + r".*?" + re.escape(STR_END), re.DOTALL)
    if pattern.search(txt):
        new_txt = pattern.sub(lambda _m: block, txt)
    else:
        new_txt = txt.replace("</Language>", block + "\n</Language>", 1)
    path.write_text(new_txt, encoding="utf-8")


def update_personality_chatsets(leader_keys: list[str]) -> int:
    """Rewrite each personality file's <chatset>...</chatset> to use its own
    chatset name (so each leader gets its own voice)."""
    mapping = {**PERSONALITY_CHATSET, **RVLT_CHATSET}
    updated = 0
    for stem, chatset_name in mapping.items():
        p = AI_DIR / f"{stem}.personality"
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8")
        new = re.sub(r"<chatset>[^<]*</chatset>", f"<chatset>{chatset_name}</chatset>", txt)
        if new != txt:
            p.write_text(new, encoding="utf-8")
            updated += 1
    return updated


def update_html_quotes(per_leader_quotes: dict) -> int:
    """For each civ in HTML_CIV_TO_LEADER, refresh its Quotes block
    to show the new flagship quotes.

    We don't remove the existing <details><summary>Quotes</summary>... block
    since it has hand-authored content; instead we INSERT a new
    <details class="ll-flagship-quotes"> block right after EXPLORER-END for
    each civ, between markers for idempotent updates.
    """
    if not HTML_PATH.exists():
        return 0
    txt = HTML_PATH.read_text(encoding="utf-8")
    count = 0
    for civ, leader_key in HTML_CIV_TO_LEADER.items():
        quotes = per_leader_quotes.get(leader_key)
        if not quotes:
            continue

        start_marker = f"<!-- LL-FLAGSHIP-QUOTES-START {civ} -->"
        end_marker = f"<!-- LL-FLAGSHIP-QUOTES-END {civ} -->"
        content = render_html_quote_block(quotes)
        wrapped = f"{start_marker}\n{content}\n{end_marker}"

        pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
        if pattern.search(txt):
            txt = pattern.sub(wrapped, txt)
            count += 1
            continue

        civ_anchor = re.compile(
            r'(<!-- ──────────── ' + re.escape(civ) + r' ──────────── -->.*?<!-- EXPLORER-END -->)',
            re.DOTALL,
        )
        m = civ_anchor.search(txt)
        if not m:
            continue
        insertion = m.group(1) + "\n" + wrapped
        txt = txt[:m.start()] + insertion + txt[m.end():]
        count += 1

    HTML_PATH.write_text(txt, encoding="utf-8")
    return count


def render_html_quote_block(quotes: dict) -> str:
    TRIGGER_LABEL = {
        "ToAllyIntro":              ("Encouragement", "ally at game start"),
        "ToEnemyIntro":             ("Taunt",         "enemy at game start"),
        "ToAllyWhenIWallIn":        ("Fortification", "I wall in"),
        "ToEnemyWhenHeWallsIn":     ("Derision",      "enemy walls in"),
        "ToAllyILoseExplorerEnemy": ("Retreat",       "my explorer dies"),
        "ToAllyBattleOverIWonAsExpected": ("Victory", "battle won"),
    }
    lines = ['<details class="ll-flagship-quotes"><summary>Leader Voice &mdash; Flagship Quotes</summary>']
    for key, (label, trigger_desc) in TRIGGER_LABEL.items():
        if key not in quotes:
            continue
        text, sid = quotes[key]
        safe = html.escape(text, quote=True)
        lines.append(f'<details><summary>{label} <span class="trigger">{trigger_desc}</span></summary>')
        lines.append(f'<ul><li><span class="quote">{safe}</span></li></ul></details>')
    lines.append('</details>')
    return "\n".join(lines)


def main():
    quotes = json.loads(QUOTES_JSON.read_text(encoding="utf-8"))
    chat_block, str_block, per_leader = generate(quotes)

    inject_into_chatsets(chat_block)
    print(f"Injected chatsetsmods.xml block ({len(per_leader)} leaders)")

    inject_into_stringmods(str_block)
    print(f"Injected {sum(len(v) for v in per_leader.values())} strings into stringmods.xml")

    n = update_personality_chatsets(list(per_leader.keys()))
    print(f"Updated {n} personality files' <chatset> field")

    n = update_html_quotes(per_leader)
    print(f"Refreshed {n} HTML civ quote blocks")


if __name__ == "__main__":
    main()
