"""Refresh the per-nation Development subtree in a_new_world.html.

Inserts a fifth `<details>` block under each nation-node summarising the 17
in-game identity surfaces (lobby name + portrait + blurb, deck-builder cards,
scoreboard flag/name, HUD HC button, player-summary flag/HC/deck, diplomacy
portrait/tooltip, chat portrait/name, end-game flag/name) with the exact
asset path or string ID that backs each surface. Lets a reviewer scan one
panel per civ and audit visual consistency without grepping the codebase.

Reads:
  - data/civmods.xml                                 (all 48 ANW civ UI fields)
  - data/strings/english/stringmods.xml              (mod string overrides)
  - game/ai/*.personality                            (per-leader nameID, icon, chatset)
  - game/ai/chatsetsmods.xml                         (chatset → leader)
  - data/decks_anw.json + data/cards.json
  - data/anwhomecity*.xml                            (HC name/civ/flag)
  - tools/migration.anw_mapping.ANW_CIVS_BY_SLUG     (canonical 48 ANW civs)

Writes:
  - a_new_world.html
        Idempotently rewrites the block bounded by
        `<!-- DEV-START name="<slug>" -->` ... `<!-- DEV-END name="<slug>" -->`
        inside each nation-node. Inserts the markers (and the wrapping
        `<details>` for the subtree) on first run.

CLI:
  python3 tools/cardextract/refresh_dev_subtrees.py [--check]
        --check  exit non-zero if any subtree would change (CI drift gate).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

# Reuse existing parsers/loaders.
from tools.validation.common import (  # noqa: E402
    child_elements,
    find_first_child,
    get_child_text,
    local_name,
)
from tools.migration.anw_mapping import (  # noqa: E402
    ANW_CIVS_BY_SLUG,
    ANW_DEFERRED_SLUGS,
    ANW_HOMECITY_MAP,
    engine_token_for,
)
from tools.validation.validate_personality_overrides import (  # noqa: E402
    load_string_table,
    parse_personality,
)

# ANW migration token map (added during the v1.0 ANW namespace migration).
# Used to surface the post-migration token names in each civ's Development
# subtree so reviewers can spot-check the future state alongside the live one.
try:
    from tools.migration.anw_token_map import by_slug as _anw_by_slug  # noqa: E402
except Exception:  # noqa: BLE001
    _anw_by_slug = None  # type: ignore[assignment]


# ANW civ blurbs — short, consistent flag-hover blurbs for all 48 civs.
# Loaded once at module level (small JSON, no I/O cost). Replaces the
# inconsistent vanilla rollover text with structured player-relevant info.
ANW_BLURBS_PATH = Path(__file__).resolve().parents[2] / "data" / "anw_civ_blurbs.json"
try:
    _ANW_BLURBS = json.loads(ANW_BLURBS_PATH.read_text(encoding="utf-8")) \
        if ANW_BLURBS_PATH.is_file() else {}
except Exception:  # noqa: BLE001
    _ANW_BLURBS = {}

HTML_PATH = REPO / "a_new_world.html"
CIVMODS = REPO / "data" / "civmods.xml"
STRINGS = REPO / "data" / "strings" / "english" / "stringmods.xml"
CARDS = REPO / "data" / "cards.json"
DECKS_ANW = REPO / "data" / "decks_anw.json"
AI_DIR = REPO / "game" / "ai"
CHATSETS = AI_DIR / "chatsetsmods.xml"

AGE_NAMES = ["Discovery", "Colonial", "Fortress", "Industrial", "Imperial"]


# ─── Data classes ─────────────────────────────────────────────────────────────


_AOE_COLOR_RE = re.compile(r"&lt;color=([0-9.]+),\s*([0-9.]+),\s*([0-9.]+)&gt;(.*?)&lt;/color&gt;",
                            re.DOTALL)


def _render_aoe_text(text: str) -> str:
    """Render AOE3-style markup `<color=r, g, b>...</color>` and literal `\\n`s
    into a small styled block. Input is the raw string-table value (already
    contains `&lt;`/`&gt;` escapes from the XML); we keep escaping safe by
    only converting our specific tag pattern."""
    if not text:
        return ""
    # First convert literal '\n' (two chars) into real newlines so <pre> wraps.
    s = text.replace("\\n", "\n").replace("\\r", "")

    def _color_sub(m: re.Match[str]) -> str:
        r, g, b = (float(m.group(i)) for i in (1, 2, 3))
        rr, gg, bb = (max(0, min(255, int(round(c * 255)))) for c in (r, g, b))
        inner = m.group(4)
        # inner is already HTML-safe (came from XML) — emit it verbatim.
        return f'<span style="color:rgb({rr},{gg},{bb})">{inner}</span>'

    s = _AOE_COLOR_RE.sub(_color_sub, s)
    return f'<pre class="dev-blurb">{s}</pre>'


@dataclass
class StringRef:
    """A string-table reference: the ID + resolved value (or empty if missing)."""

    string_id: str = ""
    value: str = ""
    note: str = ""
    rich: bool = False  # True ⇒ value contains AOE color markup; render via _render_aoe_text

    @property
    def populated(self) -> bool:
        return bool(self.string_id) and bool(self.value)

    def render_html(self) -> str:
        if not self.string_id:
            return f'<em>{html.escape(self.note or "(unset)")}</em>'
        if self.value:
            if self.rich:
                return _render_aoe_text(self.value)
            return f'<strong class="dev-str">{html.escape(self.value)}</strong>'
        # No resolved value — heuristic: mod IDs are 400000+, lower IDs come
        # from base-game stringtable. The locID is included here only because
        # there's nothing else to show; once the string resolves it disappears.
        sid_html = html.escape(self.string_id)
        base_game = self.string_id.isdigit() and int(self.string_id) < 400000
        if base_game:
            return f'<em class="dev-base">(unresolved base-game string {sid_html})</em>'
        return f'<em class="dev-base">(unresolved {sid_html})</em>'


@dataclass
class AssetRef:
    """An on-disk asset reference (path + presence)."""

    path: str = ""
    note: str = ""

    @property
    def populated(self) -> bool:
        return bool(self.path)

    def _is_image_path(self) -> bool:
        p = self.path.lower()
        return p.endswith(".png") or p.endswith(".jpg")

    def render_html(self, img_class: str = "") -> str:
        if not self.path:
            return f'<em>{html.escape(self.note or "(unset)")}</em>'
        p = self.path.replace("\\", "/").lstrip("/")
        # Engine-only assets (inside .bar archives)
        if p.startswith("ui/") or p.startswith("objects/"):
            return '<span class="dev-engine-asset">engine asset (inside .bar archive)</span>'
        # .personality references — plain text
        if p.endswith(".personality"):
            return f'<code class="dev-path">{html.escape(p)}</code>'
        if self._is_image_path():
            exists = (REPO / p).is_file()
            if not exists:
                fname = html.escape(p.rsplit("/", 1)[-1])
                return f'<span class="dev-warn">⚠ missing: {fname}</span>'
            src = html.escape(p, quote=True)
            # Pick CSS class
            if img_class:
                css = img_class
            elif "flag" in p.lower():
                css = "dev-thumb-flag"
            else:
                css = "dev-thumb"
            return f'<img class="{css}" src="{src}" alt="">'
        # Fallback: plain path
        path_html = html.escape(p)
        exists = (REPO / p).is_file()
        marker = "" if exists else ' <span class="dev-warn">(missing)</span>'
        return f'<code class="dev-path">{path_html}</code>{marker}'


@dataclass
class CivAssets:
    slug: str
    leader_personality: str  # personality file stem
    chatset_name: str = ""

    # Lobby
    civ_picker_name: StringRef = field(default_factory=StringRef)
    ai_lobby_name: StringRef = field(default_factory=StringRef)
    flag_hover_blurb: StringRef = field(default_factory=StringRef)
    lobby_portrait: AssetRef = field(default_factory=AssetRef)

    # Decks
    deck_source: str = ""
    deck_name: str = ""
    cards_by_age: list[list[tuple[str, str, str]]] = field(default_factory=list)
    # cards_by_age[age_idx] = list[(card_id, card_name, icon_relpath)]

    # In-match HUD
    scoreboard_flag: AssetRef = field(default_factory=AssetRef)
    scoreboard_name: StringRef = field(default_factory=StringRef)
    hud_hc_button: AssetRef = field(default_factory=AssetRef)
    player_summary_flag: AssetRef = field(default_factory=AssetRef)
    player_summary_hc_name: StringRef = field(default_factory=StringRef)
    player_summary_hc_civ: str = ""

    # Diplomacy
    diplomacy_portrait: AssetRef = field(default_factory=AssetRef)

    # Chat
    speaker_portrait: AssetRef = field(default_factory=AssetRef)

    # End-game
    endgame_total_flag: AssetRef = field(default_factory=AssetRef)
    endgame_civ_name: StringRef = field(default_factory=StringRef)


# ─── Loaders ──────────────────────────────────────────────────────────────────


def load_civmods_index() -> dict[str, ET.Element]:
    """Map civmods <Name> → <Civ> element."""
    root = ET.parse(CIVMODS).getroot()
    out: dict[str, ET.Element] = {}
    for civ in child_elements(root):
        if local_name(civ.tag) != "civ":
            continue
        name = get_child_text(civ, "Name")
        if name:
            out[name] = civ
    return out


def get_civmod_field(civ: ET.Element, tag: str) -> str:
    return get_child_text(civ, tag)


def get_matchmaking_portrait(civ: ET.Element) -> str:
    mm = find_first_child(civ, "MatchmakingTextures")
    if mm is None:
        return ""
    return get_child_text(mm, "SmallPortraitTextureWPF")


def load_homecity_meta(homecity_basename: str) -> tuple[StringRef, str, str]:
    """Return (HC name string-ref, HC civ token, HC flag relative path).

    The base-game homecity*.xml uses `<civ>` (token) + a localized `<name>`.
    Mod anwhomecity*.xml does the same.
    """
    path = REPO / "data" / f"{homecity_basename}.xml"
    if not path.is_file():
        return (StringRef(note=f"{path.name} not found"), "", "")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return (StringRef(note=f"parse error: {exc}"), "", "")

    civ_tag = get_child_text(root, "civ")
    name_raw = get_child_text(root, "name")
    flag_path = ""

    name_ref = StringRef()
    # Names in homecity files are typically `$$NNN$$` references into stringtable.
    m = re.match(r"\$\$(\d+)\$\$", name_raw)
    if m:
        name_ref.string_id = m.group(1)
        # value populated later when string-table loader passes it in
    elif name_raw:
        name_ref.value = name_raw
        name_ref.note = "literal text"

    # Try to find a flag asset reference inside the homecity XML.
    flag_el = find_first_child(root, "flag")
    if flag_el is not None and flag_el.text:
        flag_path = flag_el.text.strip()
    return name_ref, civ_tag, flag_path


def load_chatset_for_personality(personality_chatset: str) -> str:
    """Confirm chatset name exists in chatsetsmods.xml; return the name as-is."""
    if not personality_chatset:
        return ""
    if not CHATSETS.is_file():
        return personality_chatset
    txt = CHATSETS.read_text(encoding="utf-8", errors="ignore")
    if f'name="{personality_chatset}"' in txt:
        return personality_chatset
    return personality_chatset  # name retained even if not found; validator can flag


# Vanilla data is loaded once per `refresh_dev_subtrees.py` run (parses 45k
# strings + 126 civs from the Data.bar archive — ~0.3s). Reused for every
# base civ.
_VANILLA_CACHE = None
_VANILLA_TRIED = False


def _vanilla_data_or_none():
    """Return cached VanillaData (or None if AoE3DE install isn't reachable)."""
    global _VANILLA_CACHE, _VANILLA_TRIED
    if _VANILLA_TRIED:
        return _VANILLA_CACHE
    _VANILLA_TRIED = True
    if load_vanilla_data is None:
        return None
    try:
        _VANILLA_CACHE = load_vanilla_data()
    except Exception as exc:  # noqa: BLE001
        print(f"  (vanilla data unavailable: {exc})", file=sys.stderr)
        _VANILLA_CACHE = None
    return _VANILLA_CACHE


def load_decks() -> tuple[dict, dict]:
    return (
        json.loads(DECKS_ANW.read_text(encoding="utf-8")),
        json.loads(CARDS.read_text(encoding="utf-8")),
    )


# ─── Main per-civ collector ───────────────────────────────────────────────────


def collect_civ(slug: str, *, civmods_index: dict[str, ET.Element], strings: dict[str, str],
                 decks_anw: dict, cards: dict) -> CivAssets:
    # Unified ANW lookup (all 48 civs)
    anw_civ = ANW_CIVS_BY_SLUG.get(slug)
    if anw_civ is None:
        raise ValueError(f"slug {slug!r} not in ANW_CIVS_BY_SLUG")

    # Personality file — use the new ANW-migrated name
    # Personality files live at game/ai/anw{stem}.personality for every ANW
    # civ (both base-civ overlays and revolution civs). The stem itself
    # doesn't include the "anw" prefix — see anw_mapping._build_anw_civs.
    personality_path = AI_DIR / f"anw{anw_civ.anw_stem}.personality"
    pinfo = parse_personality(personality_path) if personality_path.is_file() else {
        "nameID": None, "tooltipID": None, "forcedciv": None, "icon": None, "chatset": None,
    }

    civ = CivAssets(
        slug=slug,
        leader_personality=personality_path.name,
        chatset_name=load_chatset_for_personality(pinfo.get("chatset") or ""),
    )

    # ── Surface 2/7/11: AI lobby / scoreboard / diplomacy tooltip name ─────────
    name_id = pinfo.get("nameID") or ""
    civ.ai_lobby_name = StringRef(
        string_id=name_id,
        value=strings.get(name_id, ""),
        note="from .personality <nameID>",
    )

    # ── Surface 4 / 10 / 12 portrait (personality icon) ────────────────────────
    icon_path = pinfo.get("icon") or ""
    if icon_path:
        # Icon paths are typically `resources/images/...png`.
        icon_rel = icon_path.replace("\\", "/").lstrip("/")
        civ.lobby_portrait = AssetRef(path=icon_rel, note="personality <icon>")
        civ.diplomacy_portrait = AssetRef(path=icon_rel, note="reuses personality <icon>")
        civ.speaker_portrait = AssetRef(path=icon_rel, note="reuses personality <icon>")

    civ.scoreboard_name = StringRef(
        string_id=name_id,
        value=strings.get(name_id, ""),
        note="same as AI lobby name",
    )

    # ── civmods.xml fields (all 48 civs have entries post-apply) ─────────────────
    # civmods.xml is keyed by the engine token (e.g. "Russians"), while the
    # ANW mapping uses canonical tokens like "ANWRussians". Translate via
    # engine_token_for() so base-civ slugs (British, Russian, …) resolve.
    civmods_key = engine_token_for(anw_civ.anw_token)
    civ_el = civmods_index.get(civmods_key)

    if civ_el is None:
        raise ValueError(
            f"ANW civ {anw_civ.anw_token!r} (engine token {civmods_key!r}) "
            "has no civmods.xml entry"
        )

    # Surface 1: civ-picker name
    display_id = get_civmod_field(civ_el, "DisplayNameID")
    civ.civ_picker_name = StringRef(
        string_id=display_id,
        value=strings.get(display_id, ""),
        note="civmods.xml <DisplayNameID>",
    )

    # Surface 3: lobby flag-hover blurb (multi-line, with AOE color markup)
    rollover_id = get_civmod_field(civ_el, "RolloverNameID")
    civ.flag_hover_blurb = StringRef(
        string_id=rollover_id,
        value=strings.get(rollover_id, ""),
        note="civmods.xml <RolloverNameID>",
        rich=True,
    )

    # Surface 4 fallback: lobby portrait via HomeCityPreviewWPF if personality has none
    if not civ.lobby_portrait.populated:
        preview = get_civmod_field(civ_el, "HomeCityPreviewWPF")
        if preview:
            civ.lobby_portrait = AssetRef(
                path=preview,
                note="civmods.xml <HomeCityPreviewWPF>",
            )
    # Lobby small portrait too
    small = get_matchmaking_portrait(civ_el)
    if small and not civ.diplomacy_portrait.populated:
        civ.diplomacy_portrait = AssetRef(
            path=small,
            note="civmods.xml <MatchmakingTextures><SmallPortraitTextureWPF>",
        )

    # Surface 6 / 8 / 9 / 15-17: in-match flags
    flag_icon = get_civmod_field(civ_el, "HomeCityFlagIconWPF") or get_civmod_field(civ_el, "PostgameFlagIconWPF")
    flag_button = get_civmod_field(civ_el, "HomeCityFlagButtonWPF")
    postgame_tex = get_civmod_field(civ_el, "PostgameFlagTexture")
    portrait_tex = get_civmod_field(civ_el, "Portrait")

    # Scoreboard flag (uses HomeCityFlagIconWPF / PostgameFlagIconWPF — same png in DE).
    if flag_icon:
        civ.scoreboard_flag = AssetRef(
            path=flag_icon,
            note="civmods.xml <HomeCityFlagIconWPF>",
        )
    elif portrait_tex:
        civ.scoreboard_flag = AssetRef(
            path=portrait_tex.replace("\\", "/"),
            note="civmods.xml <Portrait> (engine asset, not WPF)",
        )

    if flag_button:
        civ.hud_hc_button = AssetRef(path=flag_button, note="civmods.xml <HomeCityFlagButtonWPF>")
    if flag_icon:
        civ.player_summary_flag = AssetRef(path=flag_icon, note="civmods.xml <HomeCityFlagIconWPF>")
    # End-game total flag — DE uses PostgameFlagTexture (engine asset).
    if postgame_tex:
        civ.endgame_total_flag = AssetRef(
            path=postgame_tex.replace("\\", "/"),
            note="civmods.xml <PostgameFlagTexture> (engine asset, not WPF)",
        )

    # End-game civ name == civ-picker name (same DisplayNameID).
    civ.endgame_civ_name = StringRef(
        string_id=display_id,
        value=strings.get(display_id, ""),
        note="same as civ-picker name",
    )

    # ── Surface 13: Player Summary HC + flag + name ────────────────────────────
    # Use ANW-migrated homecity filename
    hc_basename = anw_civ.new_homecity_filename.replace(".xml", "")
    hc_name_ref, hc_civ, hc_flag = load_homecity_meta(hc_basename)
    if hc_name_ref.string_id and not hc_name_ref.value:
        hc_name_ref.value = strings.get(hc_name_ref.string_id, "")
    civ.player_summary_hc_name = hc_name_ref
    civ.player_summary_hc_civ = hc_civ

    # ── Surface 5 / 14: deck (Deck Builder = Player Summary deck) ──────────────
    # decks_anw.json is keyed by a mix of ANW tokens and engine tokens
    # (the 12 base civs we overlay — Aztecs, Chinese, Indians, … — keep
    # their engine token as the deck key). Try ANW token first, then fall
    # back to engine token.
    deck_key = anw_civ.anw_token
    if deck_key not in decks_anw:
        engine_key = engine_token_for(anw_civ.anw_token)
        if engine_key in decks_anw:
            deck_key = engine_key
    deck = decks_anw.get(deck_key, {})
    civ.deck_source = f"data/decks_anw.json[{deck_key!r}]"

    civ.deck_name = '"A New World"'
    cards_by_age: list[list[tuple[str, str, str]]] = [[], [], [], [], []]
    if isinstance(deck, dict):
        for age_str, card_ids in deck.items():
            try:
                idx = int(age_str)
            except ValueError:
                continue
            if not (0 <= idx <= 4):
                continue
            for cid in card_ids:
                meta = cards.get(cid, {})
                cname = meta.get("name") or cid
                cicon = meta.get("icon") or ""
                cards_by_age[idx].append((cid, cname, cicon))
    civ.cards_by_age = cards_by_age

    return civ


# ─── Renderer ─────────────────────────────────────────────────────────────────


def _row(label: str, body_html: str, context: str = "") -> str:
    label_html = html.escape(label)
    if context:
        label_html += f'<span class="dev-ctx">{html.escape(context)}</span>'
    return f'<tr><td class="dev-cell-label">{label_html}</td><td>{body_html}</td></tr>'


def _section_head(text: str) -> str:
    return f'<tr><th colspan="2" class="dev-section">{html.escape(text)}</th></tr>'


def _render_anw_blurb(slug: str) -> str | None:
    """Render the consistent ANW flag-hover blurb for the given civ slug,
    or None if the civ has no entry in `data/anw_civ_blurbs.json`.

    Output format (per civ): a structured 5-line block with parchment
    label headers — civ bonus, unique units, unique buildings, playstyle,
    age up. Replaces the inconsistent vanilla rollover prose.
    """
    if not _ANW_BLURBS:
        return None
    anw = ANW_CIVS_BY_SLUG.get(slug)
    if anw is None:
        return None
    entry = _ANW_BLURBS.get(anw.anw_token)
    if not entry:
        return None

    def _line(label: str, value: str) -> str:
        return (
            f'<div class="dev-blurb-line">'
            f'<span class="dev-blurb-label">{html.escape(label)}</span> '
            f'{html.escape(value)}'
            f'</div>'
        )

    lines: list[str] = []
    if entry.get("civ_bonus"):
        lines.append(_line("Civ bonus:", entry["civ_bonus"]))
    if entry.get("unique_units"):
        lines.append(_line("Unique units:", ", ".join(entry["unique_units"])))
    bldgs = entry.get("unique_buildings") or []
    lines.append(_line("Unique buildings:", ", ".join(bldgs) if bldgs else "(none)"))
    if entry.get("playstyle"):
        lines.append(_line("Playstyle:", entry["playstyle"]))
    if entry.get("age_up"):
        lines.append(_line("Age up:", entry["age_up"]))

    return f'<div class="dev-blurb-anw">{"".join(lines)}</div>'


def render_dev_table(civ: CivAssets) -> str:
    deck_chips_by_age: list[str] = []
    icon_dir = "resources/images/icons/cards"
    for age_idx, cards in enumerate(civ.cards_by_age):
        if not cards:
            continue
        chips: list[str] = []
        for cid, cname, cicon in cards:
            title = html.escape(f"{cname} (id={cid})", quote=True)
            display = html.escape(cname, quote=True)
            if cicon:
                src = html.escape(f"{icon_dir}/{cicon}", quote=True)
                chips.append(
                    f'<span class="card-chip" title="{title}">'
                    f'<img class="card-icon" src="{src}" alt="{display}"></span>'
                )
            else:
                chips.append(
                    f'<span class="card-chip card-chip-noicon" title="{title}">{display}</span>'
                )
        deck_chips_by_age.append(
            f"<dt>{AGE_NAMES[age_idx]}</dt><dd>{''.join(chips)}</dd>"
        )

    deck_html = (
        f'<dl class="deck-grid">{"".join(deck_chips_by_age)}</dl>'
        if deck_chips_by_age
        else "<em>(empty deck)</em>"
    )

    deck_source_label = (
        f'{html.escape(civ.deck_name)} '
        f'<code class="dev-id">{html.escape(civ.deck_source)}</code>'
    )

    hc_civ_html = html.escape(civ.player_summary_hc_civ or "(unset)")
    hc_block = (
        f"{civ.player_summary_hc_name.render_html()} "
        f'<span class="dev-note">civ token: <code>{hc_civ_html}</code></span>'
    )

    rows: list[str] = [
        _section_head("Lobby"),
        _row("Civ-picker name", civ.civ_picker_name.render_html(),
             context="Civ Selection screen → civ list"),
        _row("AI slot name", civ.ai_lobby_name.render_html(),
             context="Lobby → player slot (AI)"),
        _row(
            "Flag-hover blurb",
            (_render_anw_blurb(civ.slug)
             or civ.flag_hover_blurb.render_html()),
            context="Lobby → hover over civ flag",
        ),
        _row("Portrait", civ.lobby_portrait.render_html(img_class="dev-thumb"),
             context="Lobby → AI player portrait"),

        _section_head("Deck Builder"),
        _row("Deck", deck_source_label,
             context="Home City → deck builder"),
        _row("Cards", deck_html,
             context="Home City → deck builder cards"),

        _section_head("In-Match HUD"),
        _row("Scoreboard flag", civ.scoreboard_flag.render_html(img_class="dev-thumb-flag"),
             context="Tab → Scoreboard → flag column"),
        _row("Scoreboard name", civ.scoreboard_name.render_html(),
             context="Tab → Scoreboard → player name"),
        _row("HC button flag", civ.hud_hc_button.render_html(img_class="dev-thumb-flag"),
             context="HUD → Home City button"),
        _row("Player Summary flag", civ.player_summary_flag.render_html(img_class="dev-thumb-flag"),
             context="End-game → Player Summary → flag"),
        _row("Player Summary HC", hc_block,
             context="End-game → Player Summary → city name"),
        _row("Player Summary deck", deck_source_label
             + ' <span class="dev-note">— same 25 cards as Deck Builder; if empty in-game see Known gaps</span>',
             context="End-game → Player Summary → deck tab"),

        _section_head("Diplomacy"),
        _row("Portrait", civ.diplomacy_portrait.render_html(img_class="dev-thumb"),
             context="F4 Diplomacy panel → portrait"),
        _row("Name", civ.scoreboard_name.render_html(),
             context="F4 Diplomacy panel → hover tooltip"),

        _section_head("Chat"),
        _row("Portrait", civ.speaker_portrait.render_html(img_class="dev-thumb"),
             context="Ally/taunt chat → speaker portrait"),
        _row("Name", civ.scoreboard_name.render_html(),
             context="Ally/taunt chat → speaker name"),

        _section_head("End-Game"),
        _row("Score screen flag", civ.endgame_total_flag.render_html(img_class="dev-thumb-flag"),
             context="Score screen → flag"),
        _row("Civ name", civ.endgame_civ_name.render_html(),
             context="Score screen → civ label"),
    ]

    rows.append(_section_head("Provenance"))
    # ANW_CIVS_BY_SLUG is keyed by the same slug the dev block uses, so we can
    # look up canonical token / filenames without the legacy `_anw_by_slug`
    # helper (which referenced an older dataclass shape).
    anw = ANW_CIVS_BY_SLUG.get(civ.slug)
    if anw is not None:
        personality_filename = f"anw{anw.anw_stem}.personality"
        rows.append(_row(
            "Civ token",
            f'<code class="dev-id">{html.escape(anw.anw_token)}</code>',
            context="civmods.xml &lt;Civ&gt;&lt;Name&gt; + .personality &lt;forcedciv&gt;",
        ))
        rows.append(_row(
            "Personality file",
            f'<code class="dev-path">game/ai/{html.escape(personality_filename)}</code>',
        ))
        rows.append(_row(
            "Homecity file",
            f'<code class="dev-path">data/{html.escape(anw.new_homecity_filename)}</code>',
        ))
        if civ.chatset_name:
            rows.append(_row(
                "Chatset",
                f'<code class="dev-id">{html.escape(civ.chatset_name)}</code>',
                context="game/ai/chatsetsmods.xml",
            ))
        # Use the same resolved deck source string as the Deck Builder row.
        # decks_anw.json is keyed by a mix of ANW tokens and engine tokens
        # (XPAztec, DEEthiopians, ...), so the canonical key isn't always
        # anw.anw_token. civ.deck_source captures whichever key actually has
        # the deck after resolution.
        rows.append(_row(
            "Deck key",
            f'<code class="dev-id">{html.escape(civ.deck_source)}</code>',
        ))
    else:
        rows.append(_row("Personality file",
                         f'<code class="dev-path">game/ai/{html.escape(civ.leader_personality)}</code>'))

    return f'<table class="dev-table"><tbody>{"".join(rows)}</tbody></table>'


# ─── HTML rewriter ────────────────────────────────────────────────────────────


def _build_dev_block(slug: str, body_html: str) -> str:
    return (
        f'<details><summary><span class="cat-label">Development</span></summary>\n'
        f'<!-- DEV-START name="{slug}" -->\n'
        f'{body_html}\n'
        f'<!-- DEV-END name="{slug}" -->\n'
        f'</details>'
    )


def _section_span(html_text: str, slug: str) -> tuple[int, int] | None:
    """Return (start, end_exclusive) of the slug's section content (between
    its `<!-- ─── slug ─── -->` marker and the next section's marker, or EOF)."""
    section_re = re.compile(r"<!--\s*[─-]+\s*([^─\-][^<]*?)\s*[─-]+\s*-->")
    matches = list(section_re.finditer(html_text))
    for i, m in enumerate(matches):
        if m.group(1).strip() == slug:
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(html_text)
            return start, end
    return None


def _replace_dev_block(html_text: str, slug: str, body_html: str) -> tuple[str, bool]:
    """Replace or insert the slug's Dev block. Returns (new_text, changed?)."""
    span = _section_span(html_text, slug)
    if span is None:
        print(f"  SKIP {slug}: section comment not found", file=sys.stderr)
        return html_text, False
    sec_start, sec_end = span
    section = html_text[sec_start:sec_end]

    block_html = _build_dev_block(slug, body_html)

    # Marker pattern (idempotent rewrite).
    marker_re = re.compile(
        r'<details>\s*<summary><span class="cat-label">Development</span></summary>\s*'
        r'<!--\s*DEV-START\s+name="' + re.escape(slug) + r'"\s*-->'
        r'.*?'
        r'<!--\s*DEV-END\s+name="' + re.escape(slug) + r'"\s*-->\s*'
        r'</details>',
        re.DOTALL,
    )
    m = marker_re.search(section)
    if m:
        new_section = section[:m.start()] + block_html + section[m.end():]
    else:
        # Insert before the LAST </details> in the section (the nation-node closer).
        last_close = section.rfind("</details>")
        if last_close == -1:
            print(f"  SKIP {slug}: no </details> in section", file=sys.stderr)
            return html_text, False
        new_section = (
            section[:last_close]
            + block_html
            + "\n"
            + section[last_close:]
        )

    if new_section == section:
        return html_text, False
    return html_text[:sec_start] + new_section + html_text[sec_end:], True


CSS_BLOCK = """
/* dev-subtree styles (refresh_dev_subtrees.py) — AOE 3 DE menu palette */
.dev-table{width:100%;border-collapse:collapse;font-size:13px;margin:6px 0;background:rgba(28,18,8,0.55);border:1px solid var(--border,#6e4f24);border-radius:3px}
.dev-table td,.dev-table th{padding:5px 9px;border:1px solid rgba(110,79,36,0.45);vertical-align:top;color:var(--text,#e8d9b3)}
.dev-section{background:rgba(58,38,22,0.85);color:var(--accent,#e9c971);font-family:'Cinzel','Trajan Pro',serif;font-weight:600;letter-spacing:.05em;text-align:left;text-transform:uppercase;font-size:11px}
.dev-cell-label{width:22%;color:var(--accent,#e9c971);font-weight:600;white-space:nowrap;font-family:'EB Garamond',Georgia,serif;line-height:1.4}
.dev-id{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px;color:var(--dim,#a8946a);background:rgba(0,0,0,0.35);padding:1px 5px;border-radius:2px;border:1px solid rgba(110,79,36,0.4)}
.dev-path{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;color:var(--text,#e8d9b3);background:rgba(0,0,0,0.35);padding:1px 5px;border-radius:2px;border:1px solid rgba(110,79,36,0.4);word-break:break-all}
.dev-note{color:var(--dim,#a8946a);font-size:11px;font-style:italic}
.dev-warn{color:#f5a37a;font-weight:600}
.dev-blurb{font-family:'EB Garamond',Georgia,serif;font-size:13.5px;line-height:1.5;background:rgba(20,12,4,0.7);color:var(--text,#e8d9b3);padding:10px 14px;margin:0 0 4px 0;white-space:pre-wrap;border-left:3px solid var(--accent,#e9c971);border-radius:2px;text-shadow:0 1px 0 rgba(0,0,0,0.5)}
.dev-thumb{width:48px;height:48px;object-fit:cover;border-radius:3px;border:1px solid rgba(110,79,36,0.6);background:#1a0e04;display:block}
.dev-thumb-flag{width:52px;height:34px;object-fit:cover;border-radius:2px;border:1px solid rgba(110,79,36,0.6);background:#1a0e04;display:block}
.dev-ctx{display:block;font-size:10px;color:var(--dim,#a8946a);font-style:italic;margin-top:3px;font-family:'EB Garamond',Georgia,serif}
.dev-engine-asset{color:var(--dim,#a8946a);font-size:11px;font-style:italic}
.dev-blurb-anw{font-family:'EB Garamond',Georgia,serif;font-size:13.5px;line-height:1.55;background:rgba(20,12,4,0.7);color:var(--text,#e8d9b3);padding:10px 14px;margin:0;border-left:3px solid var(--accent,#e9c971);border-radius:2px;text-shadow:0 1px 0 rgba(0,0,0,0.5)}
.dev-blurb-line{margin:0 0 4px 0}
.dev-blurb-line:last-child{margin-bottom:0}
.dev-blurb-label{color:var(--accent,#e9c971);font-weight:600;letter-spacing:.02em;margin-right:4px}
.dev-str{font-family:'EB Garamond',Georgia,serif;font-size:14px;color:var(--text,#e8d9b3)}
.dev-base{color:var(--dim,#a8946a);font-size:12px}
"""


# A dev-subtree CSS block is "/* dev-subtree styles ... */" followed by a
# contiguous run of `.dev-...{...}` rules (one per line, the format CSS_BLOCK
# emits). This regex strips every such block so re-injection is idempotent
# even when an earlier buggy run left a stale or duplicate block behind.
_CSS_BLOCK_RE = re.compile(
    r"\n*/\* dev-subtree styles[^\n]*\n(?:\.dev-[^\n]+\n)+",
)


def _ensure_css(html_text: str) -> tuple[str, bool]:
    """Inject/refresh the dev-subtree CSS block immediately before </style>.

    Idempotent: strips any prior (stale or duplicated) dev-subtree CSS blocks
    in the inline <style> and reinserts the canonical CSS_BLOCK. Any drift
    between the generator template and the inline copy is healed on every run.
    """
    style_close = re.search(r"</style>", html_text)
    if not style_close:
        return html_text, False

    head = html_text[:style_close.start()]
    tail = html_text[style_close.start():]
    cleaned_head = _CSS_BLOCK_RE.sub("\n", head)
    new_head = cleaned_head.rstrip() + "\n\n" + CSS_BLOCK.strip() + "\n\n"
    new_text = new_head + tail
    return new_text, new_text != html_text


# ─── Entry point ──────────────────────────────────────────────────────────────


def run(check_only: bool = False) -> int:
    print(f"Loading data sources from {REPO}", file=sys.stderr)
    strings = load_string_table(STRINGS)
    civmods_index = load_civmods_index()
    decks_anw, cards = load_decks()

    html_text = HTML_PATH.read_text(encoding="utf-8")
    original = html_text
    html_text, css_changed = _ensure_css(html_text)

    refreshed = 0
    skipped: list[str] = []
    for slug in ANW_CIVS_BY_SLUG:
        # Skip deferred civs (Americans, Mexicans (Revolution)) — they have no HTML sections
        if slug in ANW_DEFERRED_SLUGS:
            continue
        try:
            civ = collect_civ(slug, civmods_index=civmods_index, strings=strings,
                              decks_anw=decks_anw, cards=cards)
        except Exception as exc:  # noqa: BLE001 — surface the error and continue
            print(f"  ERR  {slug}: {exc}", file=sys.stderr)
            skipped.append(slug)
            continue
        body = render_dev_table(civ)
        html_text, changed = _replace_dev_block(html_text, slug, body)
        if changed:
            refreshed += 1
            print(f"  ok   {slug}: dev subtree refreshed", file=sys.stderr)

    if check_only:
        if html_text != original:
            print(f"DRIFT: {refreshed} dev subtree(s) would change. "
                  f"Run `python3 tools/cardextract/refresh_dev_subtrees.py` to update.",
                  file=sys.stderr)
            return 1
        print("OK: dev subtrees in sync.", file=sys.stderr)
        return 0

    HTML_PATH.write_text(html_text, encoding="utf-8")
    print(f"\nrefreshed: {refreshed}  skipped: {len(skipped)}  css_injected: {css_changed}",
          file=sys.stderr)
    if skipped:
        print(f"  skipped slugs: {skipped}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="Exit non-zero if any dev subtree would change.")
    args = parser.parse_args()
    return run(check_only=args.check)


if __name__ == "__main__":
    sys.exit(main())
