#!/usr/bin/env python3
# ============================================================================
# DEPRECATED / OBSOLETE — DO NOT GATE. The per-civ Development tables and their
# <!-- DEV-START name="..." --> / <!-- DEV-END --> comment markers were
# intentionally removed from a_new_world.html in commit 6db1026 ("Remove
# dev-tree subsections + Dev Trees Only button from reference site"). With zero
# DEV-START blocks left in the HTML this validator can never pass — it is kept
# only for git history. Current coverage of the dev-subtree concept lives in the
# GATED validate_dev_subtrees.py; HTML art-wiring is covered by the GATED
# civmods_art_consistency / civ_asset_existence / art_coverage / civ_crossrefs.
# ============================================================================
"""Validate the per-civ Development tables in a_new_world.html against mod data.

The Development table is the QA reference the modder consults to know what
should appear on every screen of the game (Lobby, Deck Builder, In-Match HUD,
Diplomacy, Chat, End-Game) for each civilization. This validator proves that
each row of every civ's Development table is internally consistent and points
at real data on disk.

Validations performed per civ:

  1. Every ``<img src="resources/...">`` referenced in the table resolves to a
     file on disk (deduped per civ, since the same flag/portrait recurs).
  2. ``data/decks_anw.json`` contains the Provenance "Deck key" civ token, and
     the cards listed in the Deck Builder "Cards" cell match (set-equal,
     ignoring whitespace/order) the actual deck JSON contents flattened across
     ages.
  3. The Provenance ``Personality file`` path exists.
  4. The Provenance ``Homecity file`` path exists.
  5. The Provenance ``Chatset`` token has a matching ``<Chatset name="...">``
     entry in ``game/ai/chatsetsmods.xml``.
  6. The Provenance ``Civ token`` is present as a ``<civ><name>...</name></civ>``
     entry inside ``data/civmods.xml``.
  7. The same flag image appears in Lobby (implicit), Scoreboard flag,
     HC-button flag, Player-Summary flag and End-Game score-screen flag --
     they must all be identical.
  8. Same Portrait image across Lobby/Diplomacy/Chat must be identical.
  9. AI slot name == Scoreboard name == Diplomacy Name == Chat Name.
 10. Civ-picker name == End-Game Civ name.

Outputs two artifacts under ``artifacts/validation/dev_tree/``:

  * ``dev_tree_findings.json`` - structured per-civ results.
  * ``dev_tree_findings.md``   - human-readable summary grouped by severity.

Exit 0 iff zero BLOCKER and zero MAJOR findings; otherwise exit 1.

Usage::

    python3 tools/validation/validate_dev_tree.py
    python3 tools/validation/validate_dev_tree.py \
        --html a_new_world.html \
        --out artifacts/validation/dev_tree/
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:
    from bs4 import BeautifulSoup, Tag
except ImportError as exc:  # pragma: no cover - dep is required
    raise SystemExit(
        "beautifulsoup4 is required. Install with: "
        ".venv/bin/python -m pip install beautifulsoup4"
    ) from exc

# Make tools/ importable so we can use the ANW→engine-token map for civmods
# lookups (civmods.xml still uses engine tokens like "British" / "XPAztec",
# but the dev block writes the canonical ANW token like "ANWBritish").
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    from tools.migration.anw_mapping import engine_token_for as _engine_token_for
except Exception:  # noqa: BLE001
    _engine_token_for = lambda tok: tok  # noqa: E731 - graceful fallback


# ---------------------------------------------------------------------------
# Severity buckets
# ---------------------------------------------------------------------------

BLOCKER = "BLOCKER"
MAJOR = "MAJOR"
MINOR = "MINOR"

SEVERITY_ORDER = {BLOCKER: 0, MAJOR: 1, MINOR: 2}


@dataclass
class Finding:
    severity: str
    category: str
    message: str

    def as_markdown(self) -> str:
        return f"- **[{self.severity}]** *{self.category}* {self.message}"


@dataclass
class CivResult:
    civ_token: str
    civ_display: str
    data_name: str
    ok: bool = True
    findings: list[Finding] = field(default_factory=list)

    def add(self, severity: str, category: str, message: str) -> None:
        self.findings.append(Finding(severity, category, message))
        if severity in (BLOCKER, MAJOR):
            self.ok = False


# ---------------------------------------------------------------------------
# HTML parsing - per-civ Development table
# ---------------------------------------------------------------------------

# A row's label cell appears as: <td class="dev-cell-label">Civ-picker name<...
# We match on the leading text portion, before any nested <span class="dev-ctx">.
_DEV_START_RE = re.compile(
    r'<!--\s*DEV-START\s+name="([^"]+)"\s*-->(.*?)<!--\s*DEV-END\s+name="\1"\s*-->',
    re.DOTALL,
)


@dataclass
class DevTable:
    """Parsed Development table for one civ."""

    name: str  # value of `name="..."` on the DEV-START comment
    data_name: str  # value of nation-node data-name attribute
    civ_picker_name: str = ""
    ai_slot_name: str = ""
    portrait_lobby: str = ""
    deck_key_label: str = ""  # the dev-id text from the Deck row, e.g. data/decks_anw.json['XPAztec']
    cards_text: str = ""  # raw text of the "Cards" cell (legacy "Age0: A, B" format)
    card_ids_html: set[str] = field(default_factory=set)
    # Card IDs extracted directly from <span class="card-chip" title="Name (id=ID)"> chips
    # in the Cards cell. This is the modern markup; cards_text is kept for backwards
    # compatibility with the older flat-text format only.
    scoreboard_flag: str = ""
    scoreboard_name: str = ""
    hc_button_flag: str = ""
    player_summary_flag: str = ""
    player_summary_hc: str = ""
    player_summary_civ_token: str = ""
    portrait_diplomacy: str = ""
    name_diplomacy: str = ""
    portrait_chat: str = ""
    name_chat: str = ""
    score_screen_flag: str = ""
    civ_name_endgame: str = ""
    civ_token: str = ""
    personality_file: str = ""
    homecity_file: str = ""
    chatset_id: str = ""
    deck_key_provenance: str = ""
    image_refs: list[tuple[str, str]] = field(default_factory=list)
    # All images referenced anywhere in the table, paired with the row label
    # they appeared in (for diagnostic messages). Deduped by src elsewhere.
    # Blurb fields (from Flag-hover blurb row)
    blurb_history: str = ""   # text of .dev-blurb-history div
    blurb_playstyle: str = ""
    blurb_key_units: str = ""
    blurb_key_bonus: str = ""
    blurb_age_up: str = ""


def _row_label(row: Tag) -> str:
    label_cell = row.find("td", class_="dev-cell-label")
    if not label_cell:
        return ""
    # Strip the trailing context span text; keep only the leading text node(s).
    parts: list[str] = []
    for child in label_cell.children:
        if getattr(child, "name", None) == "span" and "dev-ctx" in (child.get("class") or []):
            break
        if isinstance(child, str):
            parts.append(child)
        else:
            parts.append(child.get_text(" ", strip=True))
    return "".join(parts).strip()


def _row_value_cell(row: Tag) -> Tag | None:
    cells = row.find_all("td", recursive=False)
    if len(cells) >= 2:
        return cells[1]
    return None


def _value_text(cell: Tag | None) -> str:
    if cell is None:
        return ""
    return cell.get_text(" ", strip=True)


def _value_str_strong(cell: Tag | None) -> str:
    """Read the primary `<strong class="dev-str">` content of a value cell."""
    if cell is None:
        return ""
    strong = cell.find("strong", class_="dev-str")
    if strong is not None:
        return strong.get_text(" ", strip=True)
    return _value_text(cell)


def _value_code(cell: Tag | None, cls: str | None = None) -> str:
    if cell is None:
        return ""
    if cls:
        code = cell.find("code", class_=cls)
    else:
        code = cell.find("code")
    return code.get_text(strip=True) if code is not None else ""


def _value_img_src(cell: Tag | None) -> str:
    if cell is None:
        return ""
    img = cell.find("img")
    return (img.get("src", "") if img is not None else "").strip()


_DECK_KEY_RE = re.compile(
    r"""data/decks_anw\.json\s*\[\s*['"]([^'"]+)['"]\s*\]""",
)


def _extract_deck_key(label: str) -> str:
    if not label:
        return ""
    m = _DECK_KEY_RE.search(label)
    return m.group(1) if m else ""


def _section_of_row(row: Tag) -> str:
    """Return the lowercase text of the most recent <th class="dev-section">."""
    prev = row.find_previous("th", class_="dev-section")
    return prev.get_text(" ", strip=True).lower() if prev else ""


def parse_dev_tables(html_path: Path) -> tuple[list[DevTable], list[str]]:
    """Parse every DEV-START/DEV-END block in the HTML.

    We pair each block with its enclosing ``<details class="nation-node">``
    to recover the ``data-name`` attribute (used for cross-references against
    other parts of the toolchain).
    """
    raw = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "html.parser")
    warnings: list[str] = []

    # Pre-build a map: dev-table element -> nation-node element.
    nation_nodes = soup.find_all("details", class_="nation-node")

    tables: list[DevTable] = []
    # Walk DEV-START/END comment pairs in source order. For each block, find the
    # corresponding parsed <table class="dev-table"> by index.
    dev_tables_in_doc = soup.find_all("table", class_="dev-table")
    block_iter = list(_DEV_START_RE.finditer(raw))

    if len(block_iter) != len(dev_tables_in_doc):
        warnings.append(
            f"DEV-START/END comment count ({len(block_iter)}) does not match "
            f"<table class='dev-table'> count ({len(dev_tables_in_doc)}); "
            "results may be misaligned."
        )

    # Build a quick lookup of nation-node ancestors keyed by id() of the
    # tables we walk; falls back to None when a table has no nation-node
    # parent (shouldn't happen).
    table_to_node: dict[int, Tag] = {}
    for tbl in dev_tables_in_doc:
        node = tbl.find_parent("details", class_="nation-node")
        if node is not None:
            table_to_node[id(tbl)] = node

    for idx, match in enumerate(block_iter):
        if idx >= len(dev_tables_in_doc):
            break
        name = match.group(1).strip()
        tbl = dev_tables_in_doc[idx]
        node = table_to_node.get(id(tbl))
        data_name = node.get("data-name", "").strip() if node is not None else ""

        dev = DevTable(name=name, data_name=data_name or name)

        for row in tbl.find_all("tr"):
            # Skip section-header rows
            if row.find("th", class_="dev-section"):
                continue
            label = _row_label(row).rstrip(": ").strip()
            if not label:
                continue
            section = _section_of_row(row)
            cell = _row_value_cell(row)
            if cell is None:
                continue

            # Track every image referenced in the table (regardless of section)
            for img in cell.find_all("img"):
                src = (img.get("src") or "").strip()
                if src:
                    dev.image_refs.append((label, src))

            label_l = label.lower()
            # ----- Lobby -----
            if section.startswith("lobby"):
                if label_l == "civ-picker name":
                    dev.civ_picker_name = _value_str_strong(cell)
                elif label_l == "ai slot name":
                    dev.ai_slot_name = _value_str_strong(cell)
                elif label_l == "portrait":
                    dev.portrait_lobby = _value_img_src(cell)
                elif label_l == "flag-hover blurb":
                    # Parse the blurb divs for completeness validation.
                    # Two schemas are supported:
                    #   (legacy) <div class="dev-blurb-history"> + <div class="dev-blurb-gameplay">
                    #            with "Playstyle / Key units / Key bonus / Age up" lines.
                    #   (anw)    <div class="dev-blurb-anw"> with "Civ bonus / Unique units
                    #            / Unique buildings / Playstyle / Age up" lines.
                    hist_div = cell.find("div", class_="dev-blurb-history")
                    if hist_div is not None:
                        dev.blurb_history = hist_div.get_text(" ", strip=True)
                    # ANW schema replaces the history block with a structured 5-line
                    # blurb. Treat the whole rendered blurb as the "history" text for
                    # length-check purposes so we don't penalise civs that use the
                    # new schema.
                    anw_div = cell.find("div", class_="dev-blurb-anw")
                    if anw_div is not None and not dev.blurb_history:
                        dev.blurb_history = anw_div.get_text(" ", strip=True)
                    blurb_container = cell.find("div", class_="dev-blurb-gameplay") or anw_div
                    if blurb_container is not None:
                        for line_div in blurb_container.find_all("div", class_="dev-blurb-line"):
                            label_span = line_div.find("span", class_="dev-blurb-label")
                            if label_span is None:
                                continue
                            line_label = label_span.get_text(strip=True).rstrip(":").lower()
                            # Get text after the label span
                            label_span.extract()
                            line_text = line_div.get_text(" ", strip=True)
                            if line_label == "playstyle":
                                dev.blurb_playstyle = line_text
                            elif line_label in ("key units", "unique units"):
                                dev.blurb_key_units = line_text
                            elif line_label in ("key bonus", "civ bonus"):
                                dev.blurb_key_bonus = line_text
                            elif line_label == "age up":
                                dev.blurb_age_up = line_text

            # ----- Deck Builder -----
            elif section.startswith("deck builder"):
                if label_l == "deck":
                    dev.deck_key_label = _value_code(cell, "dev-id") or _value_text(cell)
                elif label_l == "cards":
                    # Modern markup: card chips are <span class="card-chip"
                    # title="Card Name (id=CardID)">. Pull IDs from the title.
                    for chip in cell.find_all("span", class_="card-chip"):
                        title = chip.get("title", "")
                        m = re.search(r"\(id=([A-Za-z0-9_]+)\)", title)
                        if m:
                            dev.card_ids_html.add(m.group(1))
                    # Legacy fallback: replace <br> with separators so Age0/Age1/...
                    # blocks survive text extraction (only used if no card chips found).
                    for br in cell.find_all("br"):
                        br.replace_with(" | ")
                    dev.cards_text = cell.get_text(" ", strip=True)

            # ----- In-Match HUD -----
            elif section.startswith("in-match hud"):
                if label_l == "scoreboard flag":
                    dev.scoreboard_flag = _value_img_src(cell)
                elif label_l == "scoreboard name":
                    dev.scoreboard_name = _value_str_strong(cell)
                elif label_l == "hc button flag":
                    dev.hc_button_flag = _value_img_src(cell)
                elif label_l == "player summary flag":
                    dev.player_summary_flag = _value_img_src(cell)
                elif label_l == "player summary hc":
                    dev.player_summary_hc = _value_str_strong(cell)
                    note_code = cell.find("code")
                    if note_code is not None:
                        dev.player_summary_civ_token = note_code.get_text(strip=True)
                elif label_l == "player summary deck":
                    if not dev.deck_key_label:
                        dev.deck_key_label = _value_code(cell, "dev-id") or _value_text(cell)

            # ----- Diplomacy -----
            elif section.startswith("diplomacy"):
                if label_l == "portrait":
                    dev.portrait_diplomacy = _value_img_src(cell)
                elif label_l == "name":
                    dev.name_diplomacy = _value_str_strong(cell)

            # ----- Chat -----
            elif section.startswith("chat"):
                if label_l == "portrait":
                    dev.portrait_chat = _value_img_src(cell)
                elif label_l == "name":
                    dev.name_chat = _value_str_strong(cell)

            # ----- End-Game -----
            elif section.startswith("end-game"):
                if label_l == "score screen flag":
                    dev.score_screen_flag = _value_img_src(cell)
                elif label_l == "civ name":
                    dev.civ_name_endgame = _value_str_strong(cell)

            # ----- Provenance -----
            elif section.startswith("provenance"):
                if label_l == "civ token":
                    dev.civ_token = _value_code(cell, "dev-id") or _value_code(cell)
                elif label_l == "personality file":
                    dev.personality_file = _value_code(cell, "dev-path") or _value_code(cell)
                elif label_l == "homecity file":
                    dev.homecity_file = _value_code(cell, "dev-path") or _value_code(cell)
                elif label_l == "chatset":
                    dev.chatset_id = _value_code(cell, "dev-id") or _value_code(cell)
                elif label_l == "deck key":
                    dev.deck_key_provenance = _value_code(cell, "dev-id") or _value_code(cell)

        tables.append(dev)

    return tables, warnings


# ---------------------------------------------------------------------------
# Cards cell parsing
# ---------------------------------------------------------------------------

_CARD_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]+$")


def parse_html_cards(text: str) -> set[str]:
    """Parse the dev-table 'Cards' cell text into a set of card identifiers.

    Cell text after `<br>` substitution looks like::

        Age0: A, B | Age1: C, D | Age2: E, F | Age3: G, H

    We split on the ``Age\\d+:`` markers and accumulate every comma-separated
    token that looks like a card identifier (alphanumeric + underscore).
    """
    if not text:
        return set()
    parts = re.split(r"Age\d+\s*:\s*", text)
    cards: set[str] = set()
    for part in parts:
        if not part.strip():
            continue
        for tok in re.split(r"[\s,|]+", part):
            tok = tok.strip(",.; ")
            if tok and _CARD_TOKEN_RE.match(tok):
                cards.add(tok)
    return cards


def flatten_deck_json(entry: Any) -> set[str]:
    """Flatten a decks_anw.json value (age-keyed dict or flat list) into a set."""
    if isinstance(entry, dict):
        out: set[str] = set()
        for _age, cards in entry.items():
            if isinstance(cards, list):
                out.update(c for c in cards if isinstance(c, str))
        return out
    if isinstance(entry, list):
        return {c for c in entry if isinstance(c, str)}
    return set()


# ---------------------------------------------------------------------------
# Mod-data loaders
# ---------------------------------------------------------------------------

def _xml_text(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


def load_civmods_tokens(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return set()
    out: set[str] = set()

    # civmods.xml uses mixed-case element names (<Civ>, <Name>, ...). The
    # author of this helper assumed lowercase; ElementTree's findall is
    # case-sensitive, so the original code returned an empty set even when
    # the file was well-formed. Iterate every direct child and match by
    # lower-cased local name to handle both styles.
    def _local(elem) -> str:
        tag = elem.tag
        if "}" in tag:
            tag = tag.rsplit("}", 1)[-1]
        return tag.lower()

    def _find_child(parent, name_lower: str):
        for child in parent:
            if _local(child) == name_lower:
                return child
        return None

    root = tree.getroot()
    for civ in root:
        if _local(civ) != "civ":
            continue
        name = _xml_text(_find_child(civ, "name"))
        if name:
            out.add(name)
    return out


_CHATSET_RE = re.compile(r'<Chatset\s+name="([^"]+)"', re.IGNORECASE)


def load_chatsets(path: Path) -> set[str]:
    if not path.exists():
        return set()
    raw = path.read_text(encoding="utf-8", errors="replace")
    out: set[str] = set()
    for line in raw.splitlines():
        # Skip commented-out chatsets (a leading <!-- on the line).
        stripped = line.lstrip()
        if stripped.startswith("<!--"):
            continue
        for m in _CHATSET_RE.finditer(line):
            out.add(m.group(1))
    return out


def load_decks_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_dev_table(
    dev: DevTable,
    repo_root: Path,
    civmods_tokens: set[str],
    chatsets: set[str],
    decks: dict[str, Any],
) -> CivResult:
    """Run every validation against one parsed Development table."""
    civ_display = dev.civ_picker_name or dev.data_name or dev.name
    result = CivResult(
        civ_token=dev.civ_token,
        civ_display=civ_display,
        data_name=dev.data_name,
    )

    # ---- 1. image refs exist on disk --------------------------------------
    seen_imgs: dict[str, list[str]] = {}
    for label, src in dev.image_refs:
        seen_imgs.setdefault(src, []).append(label)
    for src, labels in seen_imgs.items():
        rel = src.replace("\\", "/")
        # Reject absolute URLs.
        if rel.startswith(("http://", "https://", "//")):
            result.add(
                MAJOR, "image_ref",
                f"image src `{src}` (rows: {', '.join(sorted(set(labels)))}) "
                "is an absolute URL, expected a repo-relative resources/... path.",
            )
            continue
        target = (repo_root / rel).resolve()
        if not target.exists():
            result.add(
                BLOCKER, "image_ref",
                f"image `{src}` (rows: {', '.join(sorted(set(labels)))}) "
                "does not exist on disk.",
            )

    # ---- 2. deck JSON path + cards comparison -----------------------------
    deck_key_label = _extract_deck_key(dev.deck_key_label)
    deck_key_prov = _extract_deck_key(dev.deck_key_provenance)
    # The Deck-Builder row carries the canonical key; fall back to Provenance.
    deck_key = deck_key_label or deck_key_prov
    if not deck_key:
        result.add(
            MAJOR, "deck",
            "no deck key parsed from Deck Builder/Provenance row "
            "(expected data/decks_anw.json['<token>']).",
        )
    elif deck_key not in decks:
        result.add(
            BLOCKER, "deck",
            f"deck key `{deck_key}` is not present in data/decks_anw.json.",
        )
    else:
        json_cards = flatten_deck_json(decks[deck_key])
        # Prefer card IDs pulled from <span class="card-chip" title="...(id=X)"> chips
        # (modern markup); fall back to text-parsing the cell for the older
        # "Age0: A, B | Age1: ..." format when no chips were emitted.
        html_cards = dev.card_ids_html or parse_html_cards(dev.cards_text)
        if not html_cards:
            result.add(
                MAJOR, "deck",
                "Deck Builder 'Cards' cell parsed to an empty card set; "
                "comparison against data/decks_anw.json was skipped.",
            )
        else:
            missing_in_json = sorted(html_cards - json_cards)
            extra_in_json = sorted(json_cards - html_cards)
            for c in missing_in_json:
                result.add(
                    MAJOR, "deck_cards",
                    f"card `{c}` listed in HTML but absent from "
                    f"decks_anw.json[{deck_key!r}].",
                )
            for c in extra_in_json:
                result.add(
                    MAJOR, "deck_cards",
                    f"card `{c}` present in decks_anw.json[{deck_key!r}] "
                    "but missing from HTML Cards row.",
                )

    # Deck-key consistency between Deck Builder and Provenance rows.
    if deck_key_label and deck_key_prov and deck_key_label != deck_key_prov:
        result.add(
            MAJOR, "deck",
            f"deck-key mismatch between Deck Builder ({deck_key_label!r}) "
            f"and Provenance ({deck_key_prov!r}) rows.",
        )

    # ---- 3. personality file exists ---------------------------------------
    if not dev.personality_file:
        result.add(MAJOR, "personality", "no personality file path in Provenance row.")
    else:
        target = (repo_root / dev.personality_file.replace("\\", "/")).resolve()
        if not target.exists():
            result.add(
                BLOCKER, "personality",
                f"personality file `{dev.personality_file}` does not exist on disk.",
            )

    # ---- 4. homecity file exists ------------------------------------------
    if not dev.homecity_file:
        result.add(MAJOR, "homecity", "no homecity file path in Provenance row.")
    else:
        target = (repo_root / dev.homecity_file.replace("\\", "/")).resolve()
        if not target.exists():
            result.add(
                BLOCKER, "homecity",
                f"homecity file `{dev.homecity_file}` does not exist on disk.",
            )

    # ---- 5. chatset present in chatsetsmods.xml ---------------------------
    if not dev.chatset_id:
        result.add(MAJOR, "chatset", "no chatset id in Provenance row.")
    elif dev.chatset_id not in chatsets:
        result.add(
            BLOCKER, "chatset",
            f"chatset `{dev.chatset_id}` not declared in game/ai/chatsetsmods.xml.",
        )

    # ---- 6. civ token present in civmods.xml ------------------------------
    if not dev.civ_token:
        result.add(MAJOR, "civmods", "no civ token in Provenance row.")
    else:
        # civmods.xml is keyed by engine tokens (British / XPAztec / DEHausa),
        # but the Provenance row writes the canonical ANW token (ANWBritish /
        # ANWAztecs / ANWHausa). Resolve to the engine token before lookup.
        engine_tok = _engine_token_for(dev.civ_token)
        if engine_tok in civmods_tokens or dev.civ_token in civmods_tokens:
            pass  # found, no finding
        else:
            # Revolution-only civs are dispatched via revolution scripts and
            # intentionally lack a <Civ><Name> entry in civmods.xml. Detect
            # the canonical pattern (home-city XML + .personality file both
            # present) and demote BLOCKER → MINOR so the overall report stays
            # accurate.
            civtok = dev.civ_token.lower()
            hc_file = repo_root / "data" / (
                f"anwhomecity{civtok.removeprefix('anw')}.xml"
            )
            pers_file = repo_root / "game" / "ai" / f"{civtok}.personality"
            if hc_file.exists() and pers_file.exists():
                result.add(
                    MINOR, "civmods",
                    f"civ token `{dev.civ_token}` is a revolution-only civ "
                    f"(home city + .personality present, no civmod entry "
                    f"expected).",
                )
            else:
                result.add(
                    BLOCKER, "civmods",
                    f"civ token `{dev.civ_token}` not present as <civ><name> in "
                    "data/civmods.xml.",
                )

    # ---- 7. flag-image consistency across sections ------------------------
    # NOTE: AoE3 DE ships two distinct flag asset families per civ:
    #   - `flag_hc_<civ>.png` for the HUD Home City button (small, square)
    #   - `Flag_<Civ>.png`    for scoreboard / diplomacy / post-game (larger)
    # The HC button flag is intentionally a different asset, so we don't
    # compare it against the scoreboard family. We only require the
    # in-match HUD / end-game flags (scoreboard, player summary, score
    # screen) to match each other.
    flag_rows: list[tuple[str, str]] = [
        ("Scoreboard flag", dev.scoreboard_flag),
        ("Player Summary flag", dev.player_summary_flag),
        ("End-Game score screen flag", dev.score_screen_flag),
    ]
    flag_rows = [(lbl, src) for lbl, src in flag_rows if src]
    if flag_rows:
        canonical_flag = flag_rows[0][1]
        for lbl, src in flag_rows[1:]:
            if src != canonical_flag:
                result.add(
                    MAJOR, "flag_consistency",
                    f"`{lbl}` uses `{src}` but `{flag_rows[0][0]}` uses "
                    f"`{canonical_flag}` -- expected identical flag image "
                    "across all in-match HUD/end-game sections.",
                )

    # ---- 8. portrait-image consistency across sections --------------------
    portrait_rows: list[tuple[str, str]] = [
        ("Lobby Portrait", dev.portrait_lobby),
        ("Diplomacy Portrait", dev.portrait_diplomacy),
        ("Chat Portrait", dev.portrait_chat),
    ]
    portrait_rows = [(lbl, src) for lbl, src in portrait_rows if src]
    if portrait_rows:
        canonical_portrait = portrait_rows[0][1]
        for lbl, src in portrait_rows[1:]:
            if src != canonical_portrait:
                result.add(
                    MAJOR, "portrait_consistency",
                    f"`{lbl}` uses `{src}` but `{portrait_rows[0][0]}` uses "
                    f"`{canonical_portrait}` -- expected identical leader "
                    "portrait across Lobby/Diplomacy/Chat.",
                )

    # ---- 9. leader-name consistency across sections -----------------------
    name_rows: list[tuple[str, str]] = [
        ("AI slot name", dev.ai_slot_name),
        ("Scoreboard name", dev.scoreboard_name),
        ("Diplomacy Name", dev.name_diplomacy),
        ("Chat Name", dev.name_chat),
    ]
    name_rows = [(lbl, val) for lbl, val in name_rows if val]
    if name_rows:
        canonical_name = name_rows[0][1]
        for lbl, val in name_rows[1:]:
            if val != canonical_name:
                result.add(
                    MAJOR, "leader_name_consistency",
                    f"`{lbl}` is `{val}` but `{name_rows[0][0]}` is "
                    f"`{canonical_name}` -- leader name must match across "
                    "AI slot/Scoreboard/Diplomacy/Chat.",
                )

    # ---- 10. civ-display name consistency (Lobby vs End-Game) -------------
    if dev.civ_picker_name and dev.civ_name_endgame and \
            dev.civ_picker_name != dev.civ_name_endgame:
        result.add(
            MAJOR, "civ_name_consistency",
            f"Civ-picker name `{dev.civ_picker_name}` does not match End-Game "
            f"Civ name `{dev.civ_name_endgame}`.",
        )

    # ---- 11. blurb completeness (MINOR) -----------------------------------
    # The Flag-hover blurb must have a non-placeholder history paragraph
    # (at least 30 chars) and all four gameplay lines non-empty/non-placeholder.
    _PLACEHOLDER_RE = re.compile(r"^(TODO|TBD|PLACEHOLDER|FILL ?IN)$", re.IGNORECASE)

    def _is_placeholder(text: str) -> bool:
        return not text or bool(_PLACEHOLDER_RE.match(text.strip()))

    if _is_placeholder(dev.blurb_history):
        result.add(
            MINOR, "blurb",
            "dev-blurb-history is missing or placeholder "
            f"(got: {dev.blurb_history!r:.80}).",
        )
    elif len(dev.blurb_history) < 30:
        result.add(
            MINOR, "blurb",
            f"dev-blurb-history is too short ({len(dev.blurb_history)} chars < 30); "
            f"likely a stub: {dev.blurb_history!r:.80}",
        )

    for line_name, line_val in (
        ("Playstyle", dev.blurb_playstyle),
        ("Key units", dev.blurb_key_units),
        ("Key bonus", dev.blurb_key_bonus),
        ("Age up", dev.blurb_age_up),
    ):
        if _is_placeholder(line_val):
            result.add(
                MINOR, "blurb",
                f"dev-blurb-gameplay '{line_name}' line is missing or placeholder "
                f"(got: {line_val!r:.80}).",
            )

    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def write_json_report(out_path: Path, results: list[CivResult]) -> None:
    payload = []
    for r in results:
        payload.append({
            "civ_token": r.civ_token,
            "civ_display": r.civ_display,
            "data_name": r.data_name,
            "ok": r.ok,
            "findings": [asdict(f) for f in r.findings],
        })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_markdown_report(
    out_path: Path,
    results: list[CivResult],
    parser_warnings: list[str],
) -> None:
    total = len(results)
    pass_count = sum(1 for r in results if r.ok and not r.findings)
    blocker_count = sum(
        1 for r in results for f in r.findings if f.severity == BLOCKER
    )
    major_count = sum(
        1 for r in results for f in r.findings if f.severity == MAJOR
    )
    minor_count = sum(
        1 for r in results for f in r.findings if f.severity == MINOR
    )

    lines: list[str] = []
    lines.append("# A New World - Development Tree Validation Report")
    lines.append("")
    lines.append(
        f"**{pass_count}/{total} civs PASS, {blocker_count} BLOCKER, "
        f"{major_count} MAJOR, {minor_count} MINOR**"
    )
    lines.append("")

    if parser_warnings:
        lines.append("## Parser warnings")
        lines.append("")
        for w in parser_warnings:
            lines.append(f"- {w}")
        lines.append("")

    # Group findings by severity then by civ.
    for severity in (BLOCKER, MAJOR, MINOR):
        bucket: list[tuple[CivResult, list[Finding]]] = []
        for r in results:
            findings = [f for f in r.findings if f.severity == severity]
            if findings:
                bucket.append((r, findings))
        if not bucket:
            continue
        total_in_bucket = sum(len(fs) for _, fs in bucket)
        lines.append(f"## {severity} ({total_in_bucket})")
        lines.append("")
        for r, findings in bucket:
            label = r.civ_token or r.data_name or r.civ_display or "(unknown civ)"
            lines.append(f"### {label} - {r.civ_display}")
            lines.append("")
            for f in findings:
                lines.append(f"- *{f.category}*: {f.message}")
            lines.append("")

    # Per-civ pass list at the bottom (compact).
    lines.append("## Per-civ status")
    lines.append("")
    for r in sorted(results, key=lambda x: (x.civ_token or "").lower()):
        label = r.civ_token or r.data_name or "(?)"
        status = "PASS" if r.ok and not r.findings else "FAIL"
        n_block = sum(1 for f in r.findings if f.severity == BLOCKER)
        n_major = sum(1 for f in r.findings if f.severity == MAJOR)
        n_minor = sum(1 for f in r.findings if f.severity == MINOR)
        lines.append(
            f"- `{label}` ({r.civ_display}): **{status}** -- "
            f"BLOCKER={n_block} MAJOR={n_major} MINOR={n_minor}"
        )
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description=(
            "Validate the per-civ Development tables in a_new_world.html "
            "against the actual mod data on disk."
        ),
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=repo_root / "a_new_world.html",
        help="Path to the reference HTML document (default: %(default)s).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=repo_root / "artifacts" / "validation" / "dev_tree",
        help="Directory to write findings JSON+MD into (default: %(default)s).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=repo_root,
        help="Repository root for resolving relative paths (default: %(default)s).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress info logging; only emit summary line at the end.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    html_path = args.html
    if not html_path.is_absolute():
        html_path = (Path.cwd() / html_path).resolve()
    if not html_path.exists():
        print(f"error: HTML reference not found: {html_path}", file=sys.stderr)
        return 1

    repo_root = args.repo_root
    if not repo_root.is_absolute():
        repo_root = (Path.cwd() / repo_root).resolve()

    out_dir = args.out
    if not out_dir.is_absolute():
        out_dir = (Path.cwd() / out_dir).resolve()

    if not args.quiet:
        print(f"[*] Parsing {html_path}")

    tables, warnings = parse_dev_tables(html_path)
    if not tables:
        print("error: no DEV-START blocks found; HTML appears malformed.", file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"[+] Parsed {len(tables)} Development tables")

    civmods_tokens = load_civmods_tokens(repo_root / "data" / "civmods.xml")
    chatsets = load_chatsets(repo_root / "game" / "ai" / "chatsetsmods.xml")
    decks = load_decks_json(repo_root / "data" / "decks_anw.json")

    if not civmods_tokens:
        warnings.append("data/civmods.xml not found or empty; civ-token checks will fail.")
    if not chatsets:
        warnings.append("game/ai/chatsetsmods.xml not found or empty; chatset checks will fail.")
    if not decks:
        warnings.append("data/decks_anw.json not found or empty; deck checks will fail.")

    results: list[CivResult] = []
    for dev in tables:
        results.append(
            validate_dev_table(dev, repo_root, civmods_tokens, chatsets, decks)
        )

    json_path = out_dir / "dev_tree_findings.json"
    md_path = out_dir / "dev_tree_findings.md"
    write_json_report(json_path, results)
    write_markdown_report(md_path, results, warnings)

    if not args.quiet:
        print(f"[+] Wrote JSON: {json_path}")
        print(f"[+] Wrote MD:   {md_path}")

    blocker = sum(1 for r in results for f in r.findings if f.severity == BLOCKER)
    major = sum(1 for r in results for f in r.findings if f.severity == MAJOR)
    minor = sum(1 for r in results for f in r.findings if f.severity == MINOR)
    pass_count = sum(1 for r in results if r.ok and not r.findings)
    summary = (
        f"civs={len(results)} pass={pass_count} "
        f"blocker={blocker} major={major} minor={minor}"
    )
    print(summary)

    return 0 if (blocker == 0 and major == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
