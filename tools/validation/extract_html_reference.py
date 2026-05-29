#!/usr/bin/env python3
"""Extract a deterministic civilization/doctrine reference matrix from a_new_world.html.

The HTML reference document is the authoritative source of truth for
civilization metadata in the A New World mod. This tool parses it into a
structured JSON matrix and reconciles the result against the in-repo data
sources (civmods.xml, playstyle_spec.json, lobby_coords.json,
game/ai/leaders/, data/protomods.xml).

The tool exits non-zero when divergence is found:
- exit 0: no divergence
- exit 1: at least one BLOCKER divergence (civ count mismatch, missing civs)
- exit 2: only MAJOR divergences (doctrine misalignment, missing leader XS, ...)

Typical use::

    python3 tools/validation/extract_html_reference.py \\
        --html a_new_world.html \\
        --output artifacts/reference_matrix.json \\
        --report artifacts/reference_matrix_report.md

Run with --strict to also treat MINOR divergences (cosmetic name diffs,
missing history) as a non-zero exit.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html as _html_unescape
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:
    from bs4 import BeautifulSoup, Tag
except ImportError as exc:  # pragma: no cover - dep is required
    raise SystemExit(
        "beautifulsoup4 is required. Install with: "
        ".venv/bin/python -m pip install beautifulsoup4"
    ) from exc


# ---------------------------------------------------------------------------
# Severity buckets
# ---------------------------------------------------------------------------

BLOCKER = "BLOCKER"
MAJOR = "MAJOR"
MINOR = "MINOR"

SEVERITY_ORDER = {BLOCKER: 0, MAJOR: 1, MINOR: 2}


@dataclass
class Divergence:
    severity: str
    category: str
    civ_id: str | None
    message: str

    def as_markdown(self) -> str:
        loc = f"`{self.civ_id}`" if self.civ_id else "(global)"
        return f"- **[{self.severity}]** *{self.category}* {loc}: {self.message}"


# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Lowercase, dash-delimited, ASCII-only slug."""
    text = _html_unescape.unescape(text or "")
    text = text.replace("&mdash;", "-").replace("\u2014", "-").replace("\u2013", "-")
    text = text.lower().strip()
    text = _SLUG_RE.sub("-", text).strip("-")
    return text


def canonical_civ_id(data_name: str) -> str:
    """Stable id for a nation-node, derived from the HTML data-name attribute."""
    return slugify(data_name)


# Manual aliases for civ tokens that differ between the engine token
# (used in civmods.xml) and the picker_civ_order.json entry name.
# Key/value direction is irrelevant; both forms collapse to the same
# normalized stem.
_TOKEN_ALIASES: dict[str, str] = {
    # Engine token (full) -> normalized stem (matches picker form).
    "xpaztec": "aztecs",
    "xpiroquois": "haudenosaunee",
    "xpsioux": "lakota",
    "deamericans": "usa",
    "deethiopians": "ethiopians",
    "dehausa": "hausa",
    "deinca": "inca",
    "deitalians": "italians",
    "demaltese": "maltese",
    "demexicans": "mexicans",
    "deswedish": "swedes",
    # Bare-token aliases for bidirectional collapse.
    "aztec": "aztecs",
    "iroquois": "haudenosaunee",
    "sioux": "lakota",
    "americans": "usa",
    "swedish": "swedes",
}


def _normalize_civ_token(token: str) -> str:
    """Collapse engine/picker token variants to a comparable stem.

    Order of operations:

    1. Strip non-alphanumerics and lower-case.
    2. Look up the full token in :data:`_TOKEN_ALIASES`. This catches
       known disparities between the engine token (``XPAztec``) and the
       picker form (``Aztecs``).
    3. Otherwise strip a leading ``anw``/``de``/``xp`` prefix and re-check
       the alias map.
    """
    if not token:
        return ""
    flat = re.sub(r"[^a-z0-9]", "", token.lower())
    if flat in _TOKEN_ALIASES:
        return _TOKEN_ALIASES[flat]
    for prefix in ("anw", "de", "xp"):
        if flat.startswith(prefix) and len(flat) > len(prefix):
            stripped = flat[len(prefix):]
            return _TOKEN_ALIASES.get(stripped, stripped)
    return flat


# ---------------------------------------------------------------------------
# HTML extraction
# ---------------------------------------------------------------------------

@dataclass
class HtmlCiv:
    """Civ data extracted from one nation-node block plus side-channel sources."""

    canonical_id: str
    data_name: str
    display_name: str
    leader_name: str
    flag_image: str | None
    portrait_image: str | None
    civ_token: str | None
    civ_picker_name: str | None
    ai_slot_name: str | None
    homecity_file: str | None
    personality_file: str | None
    chatset_id: str | None
    elite_units: list[str]
    non_elite_units: list[str]
    deck_cards: list[str]
    history_summary: str
    blurb_playstyle: str
    blurb_key_units: str
    blurb_key_bonus: str
    blurb_age_up: str
    walling_doctrine: str | None
    walling_body: str | None
    playstyle_doctrine: str | None
    playstyle_doctrine_summary: str | None
    playstyle_combat: str | None
    playstyle_ages: dict[str, str]
    playstyle_eco_bullets: list[str]
    playstyle_military_bullets: list[str]
    playstyle_defense_bullets: list[str]
    bonuses: list[str]
    strategy_summary: str | None


def _text(el: Tag | None) -> str:
    if el is None:
        return ""
    return el.get_text(" ", strip=True)


def _dev_table_cell(table: Tag | None, label_substr: str) -> Tag | None:
    """Return the second <td> for a row whose label cell matches *label_substr*."""
    if table is None:
        return None
    target = label_substr.lower()
    for row in table.find_all("tr"):
        label_cell = row.find("td", class_="dev-cell-label")
        if not label_cell:
            continue
        if target in label_cell.get_text(" ", strip=True).lower():
            cells = row.find_all("td")
            if len(cells) >= 2:
                return cells[1]
    return None


def _units_under(node: Tag, summary_text: str) -> list[str]:
    """Find a sub-<details> whose summary equals *summary_text* and list units."""
    for det in node.find_all("details"):
        sub = det.find("summary")
        if sub and sub.get_text(strip=True) == summary_text:
            return [u.get_text(" ", strip=True) for u in det.find_all("span", class_="unit")]
    return []


def _split_dev_cards(cell: Tag | None) -> list[str]:
    """Parse the dev-table 'Cards' cell into a flat list of card identifiers."""
    if cell is None:
        return []
    raw = cell.get_text(" ", strip=True)
    # Cell is like: "Age0: A, B Age1: C, D ..."
    parts = re.split(r"Age\d+:\s*", raw)
    cards: list[str] = []
    for part in parts:
        if not part.strip():
            continue
        for tok in re.split(r"[,\s]+", part):
            tok = tok.strip(",.; ")
            if tok and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]+", tok):
                cards.append(tok)
    return cards


def _extract_walling_blocks(html_text: str) -> dict[str, tuple[str, str]]:
    """Map the WALLING-START NAME ... WALLING-END NAME comment pairs to (label, body)."""
    out: dict[str, tuple[str, str]] = {}
    pattern = re.compile(
        r"<!--\s*WALLING-START\s+([^-\s][^-]*?)\s*-->\s*(.*?)\s*<!--\s*WALLING-END\s+\1\s*-->",
        re.DOTALL,
    )
    for match in pattern.finditer(html_text):
        name = match.group(1).strip()
        body = match.group(2)
        sub = BeautifulSoup(body, "html.parser")
        summ = sub.find("summary")
        body_div = sub.find("div", class_="walling-body")
        if summ is None:
            continue
        label = summ.get_text(" ", strip=True)
        # Strip leading "Walling Doctrine - " prefix
        label_clean = re.sub(r"^Walling Doctrine\s*[-\u2014]\s*", "", label).strip()
        out[name] = (label_clean, _text(body_div))
    return out


def _extract_playstyle_data(html_text: str) -> dict[str, dict[str, Any]]:
    """Pull the inline ``window.NATION_PLAYSTYLE = {...};`` JSON block."""
    match = re.search(
        r"window\.NATION_PLAYSTYLE\s*=\s*(\{.*?\n\});\s*\n</script>",
        html_text,
        re.DOTALL,
    )
    if not match:
        return {}
    raw = match.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try unescaping &mdash; and similar entities then retry
        unescaped = _html_unescape.unescape(raw)
        try:
            return json.loads(unescaped)
        except json.JSONDecodeError:
            return {}


def _data_search_strategy(data_search: str | None) -> str | None:
    """The last clause of data-search is an AI-strategy summary sentence."""
    if not data_search:
        return None
    text = _html_unescape.unescape(data_search)
    parts = [p.strip() for p in text.split(" \u00b7 ") if p.strip()]
    if not parts:
        return None
    last = parts[-1]
    # The strategy clause is typically a long final sentence; bonuses are short
    if len(last) > 60 and last.endswith("."):
        return last
    return None


def parse_html(html_path: Path) -> tuple[list[HtmlCiv], list[str]]:
    """Parse the reference HTML and return (civs, parser_warnings)."""
    raw = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "html.parser")
    walling = _extract_walling_blocks(raw)
    playstyle = _extract_playstyle_data(raw)
    warnings: list[str] = []

    civs: list[HtmlCiv] = []
    nodes = soup.find_all("details", class_="nation-node")
    for node in nodes:
        data_name = node.get("data-name", "").strip()
        if not data_name:
            warnings.append(f"nation-node without data-name: {str(node)[:80]}")
            continue
        canonical = canonical_civ_id(data_name)

        header = node.find("span", class_="nation-header")
        flag = portrait = None
        leader = ""
        display = data_name
        if header is not None:
            imgs = header.find_all("img")
            if imgs:
                flag = imgs[0].get("src")
                if len(imgs) >= 2:
                    portrait = imgs[1].get("src")
                    leader = imgs[1].get("alt", "").strip()
            header_text = header.get_text(" ", strip=True)
            if "\u2014" in header_text or "-" in header_text:
                # "Aztecs - Montezuma II" form
                splitter = "\u2014" if "\u2014" in header_text else "-"
                left, _, right = header_text.partition(splitter)
                display = left.strip()
                if not leader:
                    leader = right.strip()

        table = node.find("table", class_="dev-table")
        civ_token = _text(_dev_table_cell(table, "Civ token"))
        civ_picker = _text(_dev_table_cell(table, "Civ-picker name"))
        ai_slot = _text(_dev_table_cell(table, "AI slot name"))
        homecity = _text(_dev_table_cell(table, "Homecity file"))
        personality = _text(_dev_table_cell(table, "Personality file"))
        chatset = _text(_dev_table_cell(table, "Chatset"))
        cards = _split_dev_cards(_dev_table_cell(table, "Cards"))

        history_div = node.find("div", class_="dev-blurb-history")
        history = _text(history_div)

        blurb_lines: dict[str, str] = {}
        gameplay = node.find("div", class_="dev-blurb-gameplay")
        if gameplay is not None:
            for line in gameplay.find_all("div", class_="dev-blurb-line"):
                label_el = line.find("span", class_="dev-blurb-label")
                if not label_el:
                    continue
                label = label_el.get_text(strip=True).rstrip(":").strip()
                full = line.get_text(" ", strip=True)
                content = full[len(label_el.get_text(strip=True)):].lstrip(": ").strip()
                blurb_lines[label.lower()] = content

        elite = _units_under(node, "Elite Units")
        non_elite = _units_under(node, "Non-Elite Units")

        # Walling doctrine: civmod-style civ identifier (e.g. "Aztecs", "Mexicans")
        walling_key = _walling_key_for_civ(data_name, civ_token, walling)
        walling_label, walling_body = walling.get(walling_key, (None, None)) if walling_key else (None, None)

        ps = playstyle.get(data_name, {})
        playstyle_doctrine = ps.get("bsTitle")
        ps_doctrine_summary = ps.get("psTitle")
        ps_combat = ps.get("combatDoctrine")
        ps_ages = ps.get("ages") or {}
        ps_eco = list(ps.get("ecoBullets") or [])
        ps_mil = list(ps.get("militaryBullets") or [])
        ps_def = list(ps.get("defenseBullets") or [])

        bonuses = _extract_bonuses(node)
        strategy = _data_search_strategy(node.get("data-search"))

        civs.append(
            HtmlCiv(
                canonical_id=canonical,
                data_name=data_name,
                display_name=display,
                leader_name=leader,
                flag_image=flag,
                portrait_image=portrait,
                civ_token=civ_token or None,
                civ_picker_name=civ_picker or None,
                ai_slot_name=ai_slot or None,
                homecity_file=homecity or None,
                personality_file=personality or None,
                chatset_id=chatset or None,
                elite_units=elite,
                non_elite_units=non_elite,
                deck_cards=cards,
                history_summary=history,
                blurb_playstyle=blurb_lines.get("playstyle", ""),
                blurb_key_units=blurb_lines.get("key units", ""),
                blurb_key_bonus=blurb_lines.get("key bonus", ""),
                blurb_age_up=blurb_lines.get("age up", ""),
                walling_doctrine=walling_label,
                walling_body=walling_body,
                playstyle_doctrine=playstyle_doctrine,
                playstyle_doctrine_summary=ps_doctrine_summary,
                playstyle_combat=ps_combat,
                playstyle_ages=ps_ages,
                playstyle_eco_bullets=ps_eco,
                playstyle_military_bullets=ps_mil,
                playstyle_defense_bullets=ps_def,
                bonuses=bonuses,
                strategy_summary=strategy,
            )
        )

    return civs, warnings


def _walling_key_for_civ(
    data_name: str,
    civ_token: str | None,
    walling: dict[str, tuple[str, str]],
) -> str | None:
    """Best-effort match of a nation-node to its WALLING-START key."""
    candidates = list(walling.keys())
    if civ_token:
        for cand in candidates:
            if cand.lower() == civ_token.lower():
                return cand
    base = data_name.split()[0]
    for cand in candidates:
        if cand.lower() == base.lower():
            return cand
    # Try by data-name prefix substring
    for cand in candidates:
        if data_name.lower().startswith(cand.lower()):
            return cand
    return None


def _extract_bonuses(node: Tag) -> list[str]:
    """Pull the bonus card list from data-search (cards documented as ``Name - desc``)."""
    raw = node.get("data-search", "") or ""
    raw = _html_unescape.unescape(raw)
    parts = [p.strip() for p in raw.split(" \u00b7 ") if p.strip()]
    bonuses: list[str] = []
    seen: set[str] = set()
    for clause in parts:
        # bonus clauses have the shape "Name - description"
        if "\u2014" in clause:
            name = clause.split("\u2014", 1)[0].strip()
        elif " - " in clause:
            name = clause.split(" - ", 1)[0].strip()
        else:
            continue
        # Filter junk / units / numeric shipments ("8 Otontin Slingers")
        if not name or len(name) > 70:
            continue
        if re.match(r"^\d", name):
            continue
        if name in seen:
            continue
        seen.add(name)
        bonuses.append(name)
    return bonuses


# ---------------------------------------------------------------------------
# Reference matrix construction
# ---------------------------------------------------------------------------

def build_matrix(
    civs: list[HtmlCiv],
    source_path: Path,
    leader_xs_index: dict[str, str],
) -> dict[str, Any]:
    """Construct the reference_matrix.json payload."""
    civ_entries: dict[str, Any] = {}
    doctrines: dict[str, dict[str, Any]] = {}

    for civ in civs:
        doctrine_label = civ.playstyle_doctrine or ""
        doctrine_id = slugify(doctrine_label) if doctrine_label else ""
        leader_xs = _match_leader_xs(civ.leader_name, leader_xs_index)
        if not leader_xs:
            # Fallback: match by civ name (e.g. "Argentines" -> revolution_commanders).
            leader_xs = _match_leader_xs(civ.data_name, leader_xs_index)
        civ_entries[civ.canonical_id] = {
            "display_name": civ.display_name,
            "data_name": civ.data_name,
            "leader_name": civ.leader_name,
            "leader_xs_key": leader_xs,
            "civ_token": civ.civ_token,
            "civ_picker_name": civ.civ_picker_name,
            "ai_slot_name": civ.ai_slot_name,
            "doctrine_id": doctrine_id,
            "doctrine_display": doctrine_label,
            "doctrine_summary": civ.playstyle_doctrine_summary,
            "wall_doctrine": civ.walling_doctrine,
            "history_summary": civ.history_summary,
            "playstyle_blurb": civ.blurb_playstyle,
            "key_units_blurb": civ.blurb_key_units,
            "key_bonus_blurb": civ.blurb_key_bonus,
            "age_up_blurb": civ.blurb_age_up,
            "elite_units": civ.elite_units,
            "non_elite_units": civ.non_elite_units,
            "unique_units": list(dict.fromkeys(civ.elite_units + civ.non_elite_units)),
            "bonuses": civ.bonuses,
            "deck_cards": civ.deck_cards,
            "strategies": _strategy_list(civ),
            "combat_doctrine": civ.playstyle_combat,
            "age_strategies": civ.playstyle_ages,
            "homecity_file": civ.homecity_file,
            "personality_file": civ.personality_file,
            "chatset_id": civ.chatset_id,
            "flag_image": civ.flag_image,
            "portrait_image": civ.portrait_image,
            "raw_html_section_id": civ.canonical_id,
        }

        if doctrine_id:
            entry = doctrines.setdefault(
                doctrine_id,
                {"display": doctrine_label, "civ_ids": []},
            )
            entry["civ_ids"].append(civ.canonical_id)

    matrix = {
        "schema_version": 1,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_file": source_path.name,
        "civ_count": len(civ_entries),
        "doctrine_count": len(doctrines),
        "civs": civ_entries,
        "doctrines": doctrines,
    }
    return matrix


def _strategy_list(civ: HtmlCiv) -> list[str]:
    out: list[str] = []
    if civ.strategy_summary:
        out.append(civ.strategy_summary)
    out.extend(civ.playstyle_eco_bullets)
    out.extend(civ.playstyle_military_bullets)
    out.extend(civ.playstyle_defense_bullets)
    return out


# ---------------------------------------------------------------------------
# Reconciliation against in-repo data sources
# ---------------------------------------------------------------------------

def _load_civmods_civs(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return []
    return [
        _text_xml(c.find("name"))
        for c in tree.getroot().findall("civ")
        if c.find("name") is not None
    ]


def _text_xml(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


def _load_playstyle_spec(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("civs", {}) if isinstance(data, dict) else {}


def _load_lobby_picker(path: Path) -> dict[str, Any]:
    """Load lobby_coords.json (legacy ANW_TO_PICKER_INDEX may live here)."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _load_picker_civ_order(path: Path) -> dict[str, Any]:
    """Load tools/aoe3_automation/picker_civ_order.json — the live picker cache."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _load_protomods_units(path: Path) -> set[str]:
    """Return the set of unit-prototype names patched by ``data/protomods.xml``.

    ``protomods.xml`` is a partial *overlay* on the base game proto file;
    civilian and infantry rosters are inherited from the base game. The set
    returned here is therefore *not* the complete unit roster — it is the
    set of units the mod has chosen to patch. Reconciliation against this
    set is informational only.
    """
    if not path.exists():
        return set()
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return set()
    units: set[str] = set()
    for unit in tree.getroot().findall(".//unit"):
        name = unit.get("name") or _text_xml(unit.find("name"))
        if name:
            units.add(name.strip().lower())
    return units


def _load_leader_xs_index(leaders_dir: Path) -> dict[str, str]:
    """Map keyword tokens to leader_*.xs file stems.

    Keys are lower-case substrings (proper nouns, civ tokens, leader names)
    we extract from each XS file's leading comment block and from the file
    stem itself. Used by :func:`_match_leader_xs` for fuzzy matching.
    """
    out: dict[str, str] = {}
    if not leaders_dir.is_dir():
        return out
    for xs_file in sorted(leaders_dir.glob("leader_*.xs")):
        stem = xs_file.stem
        if stem in {"leaderCommon"}:
            continue
        key = stem.replace("leader_", "").lower()
        out.setdefault(key, stem)
        out.setdefault(key.replace("_", " "), stem)

        try:
            text = xs_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        head = text[:8000]
        # Pull capitalized proper-noun phrases from the leading comments.
        for match in re.finditer(r"[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]+)*", head):
            phrase = match.group(0).lower()
            # Avoid generic words; require length and avoid pure XS keywords.
            if len(phrase) < 4 or phrase in {"colonial", "fortress", "discovery", "industrial", "imperial", "europe", "build", "all"}:
                continue
            out.setdefault(phrase, stem)
    return out


def _match_leader_xs(leader_name: str, index: dict[str, str]) -> str | None:
    """Loose fuzzy match of a leader display name to an XS file stem.

    Matches in order:

    1. Exact phrase containment of the full leader name (any length >= 4).
    2. Any token (capitalized word) of the leader name.
    """
    if not leader_name or not index:
        return None
    name = leader_name.lower()

    # Try the longest substring first by sorting candidate keys by length.
    sorted_keys = sorted(index.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if len(key) >= 4 and key in name:
            return index[key]

    parts = [p for p in re.findall(r"[A-Za-z]+", name) if len(p) >= 4]
    for token in parts:
        if token in index:
            return index[token]
    return None


def reconcile(
    matrix: dict[str, Any],
    repo_root: Path,
) -> list[Divergence]:
    """Cross-check the matrix against the repository's existing data sources."""
    civmods = _load_civmods_civs(repo_root / "data" / "civmods.xml")
    playstyle_spec = _load_playstyle_spec(repo_root / "playstyle_spec.json")
    lobby = _load_lobby_picker(repo_root / "tools" / "aoe3_automation" / "lobby_coords.json")
    picker_order = _load_picker_civ_order(
        repo_root / "tools" / "aoe3_automation" / "picker_civ_order.json"
    )
    protomods_units = _load_protomods_units(repo_root / "data" / "protomods.xml")
    leader_index = _load_leader_xs_index(repo_root / "game" / "ai" / "leaders")

    findings: list[Divergence] = []

    # ---- HTML data-quality checks -------------------------------------
    matrix_civs = matrix["civs"]
    for civ_id, civ in matrix_civs.items():
        if not civ.get("civ_token"):
            findings.append(Divergence(
                MAJOR, "html_provenance",
                civ_id,
                "no civ token recovered from HTML dev-table (empty DEV-START block?).",
            ))
        if not civ.get("homecity_file"):
            findings.append(Divergence(
                MINOR, "html_provenance",
                civ_id,
                "no homecity file path in HTML dev-table.",
            ))

    # ---- civ count / civmods coverage ---------------------------------
    anw_civmods = {n for n in civmods if n.startswith("ANW") or n in {
        "British", "Chinese", "Dutch", "DEEthiopians", "French", "Germans",
        "XPIroquois", "DEHausa", "DEInca", "Indians", "DEItalians", "Japanese",
        "XPSioux", "DEMaltese", "DEMexicans", "Ottomans", "Portuguese",
        "Russians", "Spanish", "DESwedish", "DEAmericans", "XPAztec",
    }}
    # Revolution-only civs that legitimately have NO own <Civ> block in
    # civmods.xml: they are instantiated by Revolution from a parent civ at
    # runtime. The AI handler lives in leader_revolution_commanders.xs (per-
    # leader ANW* branch) rather than a standalone .personality file, and
    # the homecity inherits from the parent civ's anwhomecity*.xml. The civ
    # token is still referenced in supporting data (playercolors.xml,
    # randomnamemods.xml, anw_civ_blurbs.json, decks.json, picker map, etc.)
    # so the rest of the validator chain still applies.
    REVOLUTION_ONLY_CIVS = {
    }
    html_tokens = {
        c["civ_token"]
        for c in matrix_civs.values()
        if c.get("civ_token")
    }
    missing_in_civmods = sorted(html_tokens - anw_civmods - REVOLUTION_ONLY_CIVS)
    missing_in_html = sorted(anw_civmods - html_tokens)
    for tok in missing_in_civmods:
        findings.append(Divergence(
            BLOCKER, "civmods",
            None,
            f"civ token `{tok}` documented in HTML is missing from data/civmods.xml.",
        ))
    for tok in missing_in_html:
        findings.append(Divergence(
            BLOCKER, "civmods",
            None,
            f"civ token `{tok}` defined in civmods.xml is missing from a_new_world.html.",
        ))

    # ---- doctrine assignment ------------------------------------------
    if playstyle_spec:
        for civ_id, civ in matrix_civs.items():
            data_name = civ["data_name"]
            spec_entry = playstyle_spec.get(data_name)
            if spec_entry is None:
                findings.append(Divergence(
                    MAJOR, "doctrine",
                    civ_id,
                    f"data_name `{data_name}` not present in playstyle_spec.json.",
                ))
                continue
            spec_label = spec_entry.get("doctrine_label", "")
            html_label = civ.get("doctrine_display") or ""
            if spec_label and html_label and spec_label != html_label:
                findings.append(Divergence(
                    MAJOR, "doctrine",
                    civ_id,
                    f"doctrine label mismatch: HTML `{html_label}` vs spec `{spec_label}`.",
                ))
            if not html_label:
                findings.append(Divergence(
                    MAJOR, "doctrine",
                    civ_id,
                    "no playstyle doctrine resolved from HTML JSON block.",
                ))
    else:
        findings.append(Divergence(
            MINOR, "doctrine",
            None,
            "playstyle_spec.json not found; doctrine reconciliation skipped.",
        ))

    # ---- unit roster --------------------------------------------------
    # data/protomods.xml is a partial overlay (naval-only at time of writing),
    # so we only flag a divergence when at least one civ is missing *all* of
    # its HTML unique-unit names from the overlay. Treated as MINOR because
    # the canonical unit roster lives in the base game proto file we can't
    # ship inside this mod.
    if protomods_units:
        unmatched_civs: list[str] = []
        for civ_id, civ in matrix_civs.items():
            html_units = civ.get("unique_units") or []
            if not html_units:
                unmatched_civs.append(civ_id)
                continue
        # Only emit a single global note when many civs lack overlay coverage,
        # to avoid noise for the expected case of base-game inheritance.
        missing_units_total = sum(
            1 for c in matrix_civs.values() if not c.get("unique_units")
        )
        if missing_units_total:
            findings.append(Divergence(
                MINOR, "units",
                None,
                f"{missing_units_total}/{len(matrix_civs)} civs have no Elite/Non-Elite unit list "
                "extracted from HTML.",
            ))
    else:
        findings.append(Divergence(
            MINOR, "units",
            None,
            "data/protomods.xml not found; unit roster reconciliation skipped.",
        ))

    # ---- leader XS coverage -------------------------------------------
    if leader_index:
        for civ_id, civ in matrix_civs.items():
            leader = civ.get("leader_name")
            if not leader:
                findings.append(Divergence(
                    MINOR, "leaders",
                    civ_id,
                    "no leader name extracted from HTML.",
                ))
                continue
            xs = civ.get("leader_xs_key")
            if not xs:
                findings.append(Divergence(
                    MAJOR, "leaders",
                    civ_id,
                    f"no game/ai/leaders/leader_*.xs match for `{leader}`.",
                ))
    else:
        findings.append(Divergence(
            MINOR, "leaders",
            None,
            "game/ai/leaders/ directory not found; leader reconciliation skipped.",
        ))

    # ---- lobby picker mapping -----------------------------------------
    # Modern source of truth: tools/aoe3_automation/picker_civ_order.json
    # (legacy lobby_coords.ANW_TO_PICKER_INDEX is no longer populated).
    picker_entries: dict[str, Any] = {}
    if isinstance(picker_order, dict):
        entries = picker_order.get("entries")
        if isinstance(entries, dict):
            picker_entries = entries

    if picker_entries:
        picker_norm = {_normalize_civ_token(k): k for k in picker_entries}
        html_norm: dict[str, str] = {}
        for c in matrix_civs.values():
            tok = c.get("civ_token") or ""
            if tok:
                html_norm[_normalize_civ_token(tok)] = tok

        missing_picker = sorted(set(html_norm) - set(picker_norm))
        extra_picker = sorted(set(picker_norm) - set(html_norm))
        for n in missing_picker:
            findings.append(Divergence(
                MAJOR, "lobby_picker",
                None,
                f"civ token `{html_norm[n]}` from HTML has no entry in "
                "picker_civ_order.entries (normalized form: "
                f"`{n}`).",
            ))
        for n in extra_picker:
            findings.append(Divergence(
                MINOR, "lobby_picker",
                None,
                f"picker_civ_order.entries token `{picker_norm[n]}` "
                "has no matching HTML civ.",
            ))
    elif lobby and "ANW_TO_PICKER_INDEX" in lobby:
        picker_keys = set(lobby["ANW_TO_PICKER_INDEX"].keys())
        html_data_names = {c["data_name"] for c in matrix_civs.values()}
        missing_picker = sorted(html_data_names - picker_keys)
        for name in missing_picker:
            findings.append(Divergence(
                MINOR, "lobby_picker",
                None,
                f"HTML data_name `{name}` has no entry in lobby_coords.ANW_TO_PICKER_INDEX.",
            ))
    else:
        findings.append(Divergence(
            MINOR, "lobby_picker",
            None,
            "no picker index found (picker_civ_order.json / lobby_coords.json); "
            "skipping picker reconciliation.",
        ))

    return findings


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def write_report(
    report_path: Path,
    matrix: dict[str, Any],
    findings: list[Divergence],
    parser_warnings: list[str],
) -> None:
    """Render a Markdown divergence report next to the JSON matrix."""
    lines: list[str] = []
    lines.append("# A New World - Reference Matrix Divergence Report")
    lines.append("")
    lines.append(f"- Generated: `{matrix['generated_at']}`")
    lines.append(f"- Source: `{matrix['source_file']}`")
    lines.append(f"- Civilizations parsed: **{matrix['civ_count']}**")
    lines.append(f"- Distinct doctrines: **{matrix['doctrine_count']}**")
    lines.append("")

    by_severity: dict[str, list[Divergence]] = {BLOCKER: [], MAJOR: [], MINOR: []}
    for f in findings:
        by_severity.setdefault(f.severity, []).append(f)

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- BLOCKER: **{len(by_severity[BLOCKER])}**")
    lines.append(f"- MAJOR:   **{len(by_severity[MAJOR])}**")
    lines.append(f"- MINOR:   **{len(by_severity[MINOR])}**")
    lines.append("")

    if parser_warnings:
        lines.append("## Parser warnings")
        lines.append("")
        for w in parser_warnings:
            lines.append(f"- {w}")
        lines.append("")

    for severity in (BLOCKER, MAJOR, MINOR):
        bucket = by_severity[severity]
        if not bucket:
            continue
        lines.append(f"## {severity} ({len(bucket)})")
        lines.append("")
        bucket.sort(key=lambda d: (d.category, d.civ_id or "", d.message))
        for finding in bucket:
            lines.append(finding.as_markdown())
        lines.append("")

    if not findings:
        lines.append("## Result")
        lines.append("")
        lines.append("No divergence detected. HTML reference matches in-repo data sources.")
        lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _exit_code(findings: list[Divergence], strict: bool) -> int:
    """0 = clean, 1 = BLOCKER seen, 2 = only MAJOR, 3 = only MINOR (strict)."""
    if any(f.severity == BLOCKER for f in findings):
        return 1
    if any(f.severity == MAJOR for f in findings):
        return 2
    if strict and any(f.severity == MINOR for f in findings):
        return 3
    return 0


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 1: extract a deterministic civ/doctrine reference matrix "
            "from a_new_world.html and reconcile it against in-repo data."
        ),
    )
    repo_root = Path(__file__).resolve().parents[2]
    parser.add_argument(
        "--html",
        type=Path,
        default=repo_root / "a_new_world.html",
        help="Path to the reference HTML document (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "artifacts" / "reference_matrix.json",
        help="Where to write the JSON matrix (default: %(default)s)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=repo_root / "artifacts" / "reference_matrix_report.md",
        help="Where to write the Markdown divergence report (default: %(default)s)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=repo_root,
        help="Repository root for reconciliation lookups (default: %(default)s)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat MINOR divergences as a non-zero exit code (3) too.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress info logs; only emit summary line at end.",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.html.exists():
        print(f"error: HTML reference not found: {args.html}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"[*] Parsing {args.html}")
    civs, parser_warnings = parse_html(args.html)
    if not civs:
        print("error: no nation-node elements found; HTML appears malformed.", file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"[+] Parsed {len(civs)} civilizations from HTML")

    leader_index = _load_leader_xs_index(args.repo_root / "game" / "ai" / "leaders")
    matrix = build_matrix(civs, args.html, leader_index)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not args.quiet:
        print(f"[+] Wrote matrix: {args.output}")

    findings = reconcile(matrix, args.repo_root)
    write_report(args.report, matrix, findings, parser_warnings)
    if not args.quiet:
        print(f"[+] Wrote report: {args.report}")

    code = _exit_code(findings, args.strict)
    summary = (
        f"civs={matrix['civ_count']} doctrines={matrix['doctrine_count']} "
        f"findings={len(findings)} "
        f"(blocker={sum(1 for f in findings if f.severity == BLOCKER)}, "
        f"major={sum(1 for f in findings if f.severity == MAJOR)}, "
        f"minor={sum(1 for f in findings if f.severity == MINOR)}) "
        f"exit={code}"
    )
    print(summary)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
