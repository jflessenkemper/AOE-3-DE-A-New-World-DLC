#!/usr/bin/env python3
"""
build_civ_columns.py — Generate a_new_world_columns.html
Horizontal-scroll civ review page: one column per nation, 100vh height, no vertical scroll.

Run from any directory; all paths are resolved relative to this script's location.
"""
import os, json, re, html as html_module
import xml.etree.ElementTree as ET

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
MOD_ROOT     = os.path.dirname(SCRIPT_DIR)
DATA_DIR     = os.path.join(MOD_ROOT, "data")
GAME_DIR     = os.path.join(MOD_ROOT, "game")
RESOURCES    = os.path.join(MOD_ROOT, "resources")
OUTPUT_HTML  = os.path.join(MOD_ROOT, "a_new_world_columns.html")

# Capture artifacts root (host-perspective manifests live here)
VISUAL_ART_DIR = os.path.join(MOD_ROOT, "artifacts", "validation", "visual_art")

# URL base used in the generated HTML — maps to the staging step in pages-deploy.yml:
#   cp -r artifacts/validation/visual_art _site/artifacts/visual_art
VISUAL_ART_URL_BASE = "artifacts/visual_art"

# Manifest schema version this generator understands
MANIFEST_SCHEMA_VERSION = 1

# Human-readable surface names for crop names
CROP_SURFACE_LABELS = {
    "lobby_portrait":          "Lobby portrait",
    "loading_flag":            "Loading flag",
    "home_city_button":        "Home City button",
    "hud_flag_corner":         "HUD flag corner",
    "home_city_scene":         "Home City scene",
    "tech_tree_overview":      "Tech tree overview",
    "diplomacy_panel":         "Diplomacy panel",
    "scoreboard_player_row":   "Scoreboard row",
    "esc_menu_player_summary": "ESC menu summary",
    "endgame_flag":            "Endgame flag",
    "diplomacy_ally_portrait": "Ally portrait",
}

def surface_label(crop_name):
    """Return a human-readable label for a crop/surface name."""
    if crop_name in CROP_SURFACE_LABELS:
        return CROP_SURFACE_LABELS[crop_name]
    # Fallback: title-case with underscores replaced by spaces
    return crop_name.replace("_", " ").title()


def capture_dir_key(civ_token):
    """
    Return the directory name used under artifacts/validation/visual_art/ for a civ.

    The capture pipeline uses ANW-prefixed tokens (e.g. ANWBritish) as directory
    names.  The civmods/playercolors data uses the base tokens (e.g. British).
    blurb_key() already contains the canonical ANW mapping, so reuse it.
    """
    return blurb_key(civ_token)


def load_capture_manifest(civ_token, ally=False):
    """
    Load and validate a capture manifest for a civ.

    For host perspective:  artifacts/validation/visual_art/<dir_key>/manifest.json
    For ally perspective:  artifacts/validation/visual_art/allies/<dir_key>/manifest.json

    Returns the parsed dict if schema_version==1 and status=="complete", else None.
    """
    dir_key = capture_dir_key(civ_token)
    if ally:
        manifest_path = os.path.join(VISUAL_ART_DIR, "allies", dir_key, "manifest.json")
    else:
        manifest_path = os.path.join(VISUAL_ART_DIR, dir_key, "manifest.json")

    if not os.path.exists(manifest_path):
        return None

    try:
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    if data.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        return None
    if data.get("status") != "complete":
        return None

    return data

# ── Load data sources ──────────────────────────────────────────────────────────
def load_strings():
    path = os.path.join(DATA_DIR, "strings", "english", "stringmods.xml")
    tree = ET.parse(path)
    strings = {}
    for elem in tree.getroot().iter("String"):
        loc_id = elem.get("_locID")
        if loc_id and elem.text:
            strings[loc_id] = elem.text.strip()
    return strings

def load_civmods():
    path = os.path.join(DATA_DIR, "civmods.xml")
    tree = ET.parse(path)
    civs = {}
    for civ in tree.getroot().findall(".//civ"):
        name = civ.findtext("name")
        if name:
            civs[name] = civ
    return civs

def load_playercolors():
    path = os.path.join(DATA_DIR, "playercolors.xml")
    tree = ET.parse(path)
    colors = {}
    for c in tree.getroot().findall(".//Color"):
        civ = c.get("civ")
        if civ:
            colors[civ] = {
                "r": int(c.get("r", 80)),
                "g": int(c.get("g", 80)),
                "b": int(c.get("b", 80)),
                "leader": c.get("leader", ""),
            }
    return colors

def load_homecity(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None
    tree = ET.parse(path)
    root = tree.getroot()
    data = {}
    for child in root:
        tag = child.tag
        if tag not in data:
            data[tag] = child.text.strip() if child.text else ""
    # Cards by age
    cards_by_age = {}
    for card in root.findall(".//cards/card"):
        age = card.findtext("age") or "0"
        name_elem = card.findtext("name") or ""
        age_key = str(int(float(age))) if age.strip() else "0"
        cards_by_age.setdefault(age_key, []).append(name_elem)
    data["cards_by_age"] = cards_by_age
    return data

def load_blurbs():
    path = os.path.join(DATA_DIR, "anw_civ_blurbs.json")
    with open(path) as f:
        return json.load(f)

def load_playstyle_spec():
    path = os.path.join(MOD_ROOT, "playstyle_spec.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        spec = json.load(f)
    # The spec has civs keyed by display label
    civs_raw = spec.get("civs", {})
    # Build mapping: civ_label -> data
    result = {}
    for key, val in civs_raw.items():
        if isinstance(val, dict):
            civ_label = val.get("civ_label", "")
            result[key] = val
    return civs_raw

def load_decks():
    path = os.path.join(DATA_DIR, "decks_anw.json")
    with open(path) as f:
        return json.load(f)

def load_cards():
    path = os.path.join(DATA_DIR, "cards.json")
    with open(path) as f:
        return json.load(f)

def load_personality(civ_name):
    """Load rushboom value from .personality file."""
    # Normalise civ_name to filename: remove prefix ANW/DE/XP, lowercase
    lower = civ_name.lower()
    for prefix in ("anw", "de", "xp"):
        if lower.startswith(prefix):
            lower = lower[len(prefix):]
            break
    # Try with anw prefix first
    candidates = [
        f"anw{lower}.personality",
        f"{lower}.personality",
    ]
    for fname in candidates:
        path = os.path.join(GAME_DIR, "ai", fname)
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
            m = re.search(r"<rushboom>(\d+)</rushboom>", content)
            if m:
                val = int(m.group(1))
                label = {0: "Boom", 1: "Rush", 2: "Balanced"}.get(val, str(val))
                return label, fname
            return "?", fname
    return "?", None

def personality_path_str(civ_name):
    lower = civ_name.lower()
    for prefix in ("anw", "de", "xp"):
        if lower.startswith(prefix):
            lower = lower[len(prefix):]
            break
    fname = f"anw{lower}.personality"
    path = os.path.join(GAME_DIR, "ai", fname)
    if os.path.exists(path):
        return f"game/ai/{fname}"
    return f"game/ai/anw{lower}.personality (missing)"

def resolve_img(rel_path):
    """Return (rel_path_for_html, exists) for a resource path."""
    if not rel_path:
        return None, False
    # Normalise backslashes
    rel_path = rel_path.replace("\\", "/")
    # Possible base locations
    candidates = [
        os.path.join(MOD_ROOT, rel_path),
        os.path.join(MOD_ROOT, "resources", rel_path),
        os.path.join(MOD_ROOT, "data", rel_path),
    ]
    for c in candidates:
        if os.path.exists(c):
            # Return path relative to MOD_ROOT (= same dir as output HTML)
            rel = os.path.relpath(c, MOD_ROOT)
            return rel.replace("\\", "/"), True
    return rel_path, False

def img_tag(path, alt="", size=50):
    rel, exists = resolve_img(path)
    if exists:
        return (
            f'<img loading="lazy" src="{html_module.escape(rel)}" '
            f'alt="{html_module.escape(alt)}" '
            f'title="{html_module.escape(rel)}" '
            f'style="width:{size}px;height:{size}px;object-fit:contain;'
            f'border:1px solid rgba(255,255,255,0.2);border-radius:2px;background:#0004;">'
        ), True
    else:
        return (
            f'<span class="path-missing" title="{html_module.escape(path)}">'
            f'<code>{html_module.escape(rel)}</code></span>'
        ), False

# ── CIV key normalisation ──────────────────────────────────────────────────────
def blurb_key(civ_token):
    """Map civmods token to blurbs key (ANWXxx style)."""
    mappings = {
        "French":       "ANWFrench",
        "British":      "ANWBritish",
        "Germans":      "ANWGermans",
        "Russians":     "ANWRussians",
        "Spanish":      "ANWSpanish",
        "Ottomans":     "ANWOttomans",
        "Portuguese":   "ANWPortuguese",
        "Dutch":        "ANWDutch",
        "DEItalians":   "ANWItalians",
        "DEMaltese":    "ANWMaltese",
        "DESwedish":    "ANWSwedes",
        "Chinese":      "ANWChinese",
        "Japanese":     "ANWJapanese",
        "Indians":      "ANWIndians",
        "XPAztec":      "ANWAztecs",
        "XPIroquois":   "ANWHaudenosaunee",
        "DEInca":       "ANWInca",
        "XPSioux":      "ANWLakota",
        "DEAmericans":  "ANWUSA",
        "DEMexicans":   "ANWMexicans",
        "DEEthiopians": "ANWEthiopians",
        "DEHausa":      "ANWHausa",
    }
    if civ_token in mappings:
        return mappings[civ_token]
    return civ_token  # ANW* tokens match directly

def deck_key(civ_token):
    """Map civmods token to decks_anw.json key."""
    # Most ANW civs match directly; base civs also match directly
    return civ_token

# ── Playstyle spec lookup ──────────────────────────────────────────────────────
def find_spec_entry(civ_token, spec):
    """Try to find a matching playstyle spec entry for a civ token."""
    # The spec uses human-readable keys like 'Hungarians Kossuth Revolution'
    # Try to match by civ_label in the values
    b_key = blurb_key(civ_token)
    # Strip ANW prefix and convert to base name
    base = b_key[3:] if b_key.startswith("ANW") else b_key
    base_lower = base.lower()
    for key, val in spec.items():
        if not isinstance(val, dict):
            continue
        civ_label = val.get("civ_label", "")
        if civ_label.lower() == base_lower:
            return val, key
        if base_lower in key.lower():
            return val, key
    return None, None

# ── Colour helpers ─────────────────────────────────────────────────────────────
def luminance(r, g, b):
    def c(x):
        x /= 255
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * c(r) + 0.7152 * c(g) + 0.0722 * c(b)

def text_color(r, g, b):
    return "#fff" if luminance(r, g, b) < 0.35 else "#111"

def bg_style(r, g, b):
    return (
        f"background:linear-gradient(160deg,"
        f"rgb({r},{g},{b}) 0%,"
        f"rgb({max(r-30,0)},{max(g-30,0)},{max(b-30,0)}) 100%);"
    )

# ── Section renderers ──────────────────────────────────────────────────────────
def render_text_section(civ_token, civ_el, strings, hc, blurbs, spec, decks, cards, colors):
    bk = blurb_key(civ_token)
    blurb = blurbs.get(bk, {})
    spec_entry, spec_key = find_spec_entry(civ_token, spec)

    # Display name
    display_id = civ_el.findtext("displaynameid") or ""
    display_name = strings.get(display_id, civ_token)

    # Stats id
    statsid = civ_el.findtext("statsid") or ""

    # Culture
    culture = civ_el.findtext("culture") or ""

    # Allied/Unallied IDs
    allied_id    = civ_el.findtext("alliedid") or ""
    unallied_id  = civ_el.findtext("unalliedid") or ""
    allied_other = civ_el.findtext("alliedotherid") or ""

    # Leader name from homecity
    leader_name = ""
    if hc:
        hero_name_raw = hc.get("heroname", "")
        if hero_name_raw.startswith("$$") and hero_name_raw.endswith("$$"):
            loc_id = hero_name_raw[2:-2]
            leader_name = strings.get(loc_id, hero_name_raw)
        else:
            leader_name = hero_name_raw

    # Leader from playercolors
    color_entry = colors.get(civ_token, {})
    pc_leader = color_entry.get("leader", "")

    # Doctrine
    doctrine_label   = spec_entry.get("doctrine_label",   "") if spec_entry else ""
    doctrine_summary = spec_entry.get("doctrine_summary", "") if spec_entry else ""

    # Blurb
    civ_bonus = blurb.get("civ_bonus", "") if blurb else ""
    playstyle  = blurb.get("playstyle", "") if blurb else ""
    age_up     = blurb.get("age_up", "") if blurb else ""

    # Unique units
    unique_units = []
    if blurb and blurb.get("unique_units"):
        unique_units = blurb["unique_units"][:5]

    # Cards by age
    dk = deck_key(civ_token)
    deck_data = decks.get(dk, {})
    cards_html_parts = []
    for age in ["0", "1", "2", "3", "4"]:
        age_cards = deck_data.get(age, [])
        if not age_cards:
            continue
        card_html_items = []
        for card_id in age_cards:
            card_info = cards.get(card_id, {})
            card_name = card_info.get("name") or card_id
            card_desc = card_info.get("desc") or ""
            card_icon = card_info.get("icon") or ""
            tooltip = card_name + (f"\n\n{card_desc}" if card_desc else "")
            tooltip_attr = html_module.escape(tooltip[:400], quote=True)
            icon_rendered = False
            if card_icon:
                icon_rel = f"resources/images/icons/cards/{card_icon}"
                if os.path.exists(os.path.join(MOD_ROOT, icon_rel)):
                    card_html_items.append(
                        f'<img class="card-img" loading="lazy" '
                        f'src="{html_module.escape(icon_rel)}" '
                        f'alt="{html_module.escape(card_name)}" '
                        f'title="{tooltip_attr}">'
                    )
                    icon_rendered = True
            if not icon_rendered:
                card_html_items.append(
                    f'<span class="card-text" title="{tooltip_attr}">'
                    f'{html_module.escape(card_name)}</span>'
                )
        age_label = {
            "0": "Discovery", "1": "Colonial", "2": "Fortress",
            "3": "Industrial", "4": "Imperial"
        }.get(age, f"Age {age}")
        cards_html_parts.append(
            f'<div class="age-row age-{age}"><span class="age-lbl">{age_label}</span>'
            f'<span class="age-cards">{"".join(card_html_items)}</span></div>'
        )

    # Rush/boom
    rushboom, personality_fname = load_personality(civ_token)

    # Personality path
    pers_path = personality_path_str(civ_token)

    rows = []
    def row(label, value, mono=False):
        if not value:
            value = '<span class="empty">—</span>'
        cls = "mono" if mono else ""
        rows.append(
            f'<tr><td class="lbl">{html_module.escape(label)}</td>'
            f'<td class="{cls}">{value}</td></tr>'
        )

    row("Display name", f'<strong>{html_module.escape(display_name)}</strong>')
    row("Civ token",    f'<code>{html_module.escape(civ_token)}</code>', mono=True)
    row("Stats ID",     html_module.escape(statsid))
    row("Culture",      html_module.escape(culture))
    row("Leader (HC)",  html_module.escape(leader_name) if leader_name else "")
    if pc_leader and pc_leader != leader_name:
        row("Leader (PC)", html_module.escape(pc_leader))
    row("Allied ID",   html_module.escape(allied_id))
    row("Unallied ID", html_module.escape(unallied_id))
    row("Other ID",    html_module.escape(allied_other))
    row("AI Rush/Boom", html_module.escape(rushboom))
    row("Doctrine",    html_module.escape(doctrine_label))
    row("Doctrine sum.", html_module.escape(doctrine_summary))

    if civ_bonus:
        rows.append(
            f'<tr><td class="lbl">Civ bonus</td>'
            f'<td class="blurb-cell">{html_module.escape(civ_bonus)}</td></tr>'
        )
    if playstyle:
        rows.append(
            f'<tr><td class="lbl">Playstyle</td>'
            f'<td class="blurb-cell">{html_module.escape(playstyle[:160])}</td></tr>'
        )
    if age_up:
        row("Age up", html_module.escape(age_up))
    if unique_units:
        row("Unique units", html_module.escape(", ".join(unique_units)))

    rows_html = "\n".join(rows)
    cards_html = "\n".join(cards_html_parts) if cards_html_parts else '<span class="empty">No deck data</span>'

    return f"""
<div class="text-section">
  <table class="info-table">
    <tbody>{rows_html}</tbody>
  </table>
  <div class="cards-section">
    <div class="section-label">Cards</div>
    {cards_html}
  </div>
</div>
"""

def render_art_section(civ_token, civ_el, hc, strings):
    imgs_resolved = 0
    imgs_missing  = 0
    parts = []

    def art_row(label, path_or_key):
        """Render an image row. Skip silently if path is empty or doesn't resolve."""
        nonlocal imgs_resolved, imgs_missing
        if not path_or_key:
            return
        tag, ok = img_tag(path_or_key, label, 56)
        if not ok:
            imgs_missing += 1
            return
        imgs_resolved += 1
        parts.append(
            f'<div class="art-row"><span class="art-lbl">{html_module.escape(label)}</span>'
            f'{tag}</div>'
        )

    # Portrait (3D flag from civmods)
    portrait = civ_el.findtext("portrait") or ""
    art_row("Portrait (3D)", portrait)

    # Homecity flag texture
    hc_flag_tex = civ_el.findtext("homecityflagtexture") or ""
    art_row("HC flag tex", hc_flag_tex)

    # Post-game flag texture
    pg_flag_tex = civ_el.findtext("postgameflagtexture") or ""
    art_row("PG flag tex", pg_flag_tex)

    # WPF paths (actual PNG resources)
    hc_flag_icon = civ_el.findtext("homecityflagiconwpf") or ""
    art_row("HC flag icon", hc_flag_icon)

    pg_flag_icon = civ_el.findtext("postgameflagiconwpf") or ""
    art_row("PG flag icon", pg_flag_icon)

    hc_preview   = civ_el.findtext("homecitypreviewwpf") or ""
    art_row("HC preview", hc_preview)

    hc_flag_btn  = civ_el.findtext("homecityflagbuttonwpf") or ""
    art_row("HC flag btn", hc_flag_btn)

    return "".join(parts), imgs_resolved, imgs_missing

# ── Capture thumbnail section renderer ────────────────────────────────────────
def render_captures_section(civ_token, display_name, manifest, ally_manifest):
    """
    Render the "Visual confirmation" section for a civ column.

    manifest      — host-perspective manifest dict (or None)
    ally_manifest — ally-perspective manifest dict (or None)

    Returns an HTML string, or "" if no captures exist for this civ.
    """
    thumbs = []  # list of dicts: {thumb_url, full_url, crop_name, label}
    dir_key = capture_dir_key(civ_token)

    def collect_crops(mf, url_dir_key, is_ally=False):
        """Extract thumbnail entries from a manifest."""
        for capture in mf.get("captures", []):
            for crop in capture.get("crops", []):
                crop_name = crop.get("name", "")
                # For ally, only emit the ally portrait crop
                if is_ally and crop_name != "diplomacy_ally_portrait":
                    continue
                thumb_path = crop.get("thumb_path", "")
                crop_path  = crop.get("crop_path", "")
                if not thumb_path or not crop_path:
                    continue
                # Build URL-relative paths from the deployed base
                # thumb_path is like "thumbs/lobby_portrait.webp"
                # crop_path  is like "crops/lobby_portrait.png"
                thumb_url = f"{VISUAL_ART_URL_BASE}/{url_dir_key}/{thumb_path}"
                full_url  = f"{VISUAL_ART_URL_BASE}/{url_dir_key}/{crop_path}"
                thumbs.append({
                    "thumb_url": thumb_url,
                    "full_url":  full_url,
                    "crop_name": crop_name,
                    "label":     surface_label(crop_name),
                })

    if manifest:
        collect_crops(manifest, dir_key, is_ally=False)

    if ally_manifest:
        # The ally manifest lives under artifacts/validation/visual_art/allies/<dir_key>/
        # and is deployed to artifacts/visual_art/allies/<dir_key>/
        collect_crops(ally_manifest, f"allies/{dir_key}", is_ally=True)

    if not thumbs:
        return ""

    dn_esc = html_module.escape(display_name)
    tok_esc = html_module.escape(civ_token)

    figure_parts = []
    for t in thumbs:
        label_esc      = html_module.escape(t["label"])
        thumb_url_esc  = html_module.escape(t["thumb_url"])
        full_url_esc   = html_module.escape(t["full_url"])
        crop_name_esc  = html_module.escape(t["crop_name"])
        aria            = html_module.escape(f"Open {display_name} {t['label']} full size")
        figure_parts.append(
            f'<figure class="capture-thumb" tabindex="0"'
            f' data-full-src="{full_url_esc}"'
            f' data-civ="{tok_esc}"'
            f' data-surface="{crop_name_esc}"'
            f' aria-label="{aria}">'
            f'<img loading="lazy" src="{thumb_url_esc}" alt="{label_esc}">'
            f'<figcaption>{label_esc}</figcaption>'
            f'</figure>'
        )

    figures_html = "\n      ".join(figure_parts)
    return f"""<div class="captures-section">
  <div class="section-label">Visual confirmation</div>
  <div class="captures-grid">
      {figures_html}
  </div>
</div>
"""


# ── Doctrine evidence renderer (smart walls, elite units, hero+army) ────────
DOCTRINE_SURFACES = [
    ("doctrine_wall_planning",   "Wall planning (T+0:30)"),
    ("doctrine_wall_chokepoint", "Wall chokepoint (T+5:00)"),
    ("doctrine_wall_closure",    "Wall closure (T+10:00)"),
    ("doctrine_elite_units",     "Elite composition (T+15:00)"),
    ("doctrine_hero_attack",     "Hero leading army (T+18:00)"),
    ("doctrine_endgame_state",   "Late-game state (T+22:00)"),
]


def render_doctrine_section(civ_token, display_name):
    """Render doctrine evidence screenshots — embedded directly in the civ column.

    Reads from artifacts/validation/visual_art/<dir_key>/doctrine/<surface>.png
    (full 1920x1080 PNGs).  No manifest required — file existence is the only
    gate.  Captured by tools/aoe3_automation/anw_doctrine_capture_runner.py.

    Returns "" if no doctrine PNGs exist for this civ.
    """
    dir_key = capture_dir_key(civ_token)
    doctrine_dir = os.path.join(VISUAL_ART_DIR, dir_key, "doctrine")
    if not os.path.isdir(doctrine_dir):
        return ""

    figure_parts = []
    for surface_name, label in DOCTRINE_SURFACES:
        png_path = os.path.join(doctrine_dir, f"{surface_name}.png")
        if not os.path.exists(png_path):
            continue
        # URL relative to deployed _site/artifacts/visual_art/<dir_key>/doctrine/
        full_url = f"{VISUAL_ART_URL_BASE}/{dir_key}/doctrine/{surface_name}.png"
        label_esc = html_module.escape(label)
        full_url_esc = html_module.escape(full_url)
        surface_esc = html_module.escape(surface_name)
        tok_esc = html_module.escape(civ_token)
        aria = html_module.escape(f"Open {display_name} {label} doctrine evidence")
        figure_parts.append(
            f'<figure class="doctrine-thumb" tabindex="0"'
            f' data-full-src="{full_url_esc}"'
            f' data-civ="{tok_esc}"'
            f' data-surface="{surface_esc}"'
            f' aria-label="{aria}">'
            f'<img loading="lazy" src="{full_url_esc}" alt="{label_esc}">'
            f'<figcaption>{label_esc}</figcaption>'
            f'</figure>'
        )

    if not figure_parts:
        return ""

    figures_html = "\n      ".join(figure_parts)
    return f"""<div class="doctrine-section">
  <div class="section-label">AI Doctrine Evidence (live game)</div>
  <div class="doctrine-grid">
      {figures_html}
  </div>
</div>
"""


# ── Main column renderer ───────────────────────────────────────────────────────
def render_column(civ_token, civmods, strings, colors, blurbs, spec, decks, cards):
    civ_el = civmods.get(civ_token)
    if civ_el is None:
        return f'<section class="civ-col" id="{html_module.escape(civ_token)}" style="background:#333;color:#fff;"><div class="col-header">{html_module.escape(civ_token)}</div><p>No civmods data</p></section>', 0, 0

    color_entry = colors.get(civ_token, {"r": 60, "g": 60, "b": 80})
    r, g, b = color_entry["r"], color_entry["g"], color_entry["b"]
    tc = text_color(r, g, b)
    bg = bg_style(r, g, b)

    # Display name for header
    display_id = civ_el.findtext("displaynameid") or ""
    display_name = strings.get(display_id, civ_token)

    # Load homecity
    hc_file = civ_el.findtext("homecityfilename") or ""
    hc = load_homecity(hc_file) if hc_file else {}

    # Leader name (for header sub-line)
    leader_name_hdr = ""
    if hc:
        hero_name_raw = hc.get("heroname", "")
        if hero_name_raw.startswith("$$") and hero_name_raw.endswith("$$"):
            loc_id = hero_name_raw[2:-2]
            leader_name_hdr = strings.get(loc_id, hero_name_raw)
        else:
            leader_name_hdr = hero_name_raw
    color_entry2 = colors.get(civ_token, {})
    pc_leader = color_entry2.get("leader", "")
    if not leader_name_hdr and pc_leader:
        leader_name_hdr = pc_leader

    # Doctrine label for header sub-line
    spec_entry, _ = find_spec_entry(civ_token, spec)
    doctrine_label_hdr = spec_entry.get("doctrine_label", "") if spec_entry else ""

    text_html = render_text_section(
        civ_token, civ_el, strings, hc, blurbs, spec, decks, cards, colors
    )
    art_html, resolved, missing = render_art_section(civ_token, civ_el, hc, strings)

    # Load capture manifests (host + ally perspectives)
    host_manifest  = load_capture_manifest(civ_token, ally=False)
    ally_manifest  = load_capture_manifest(civ_token, ally=True)
    captures_html  = render_captures_section(civ_token, display_name, host_manifest, ally_manifest)
    doctrine_html  = render_doctrine_section(civ_token, display_name)

    # Leader image for header (try homecitypreviewwpf)
    leader_preview = civ_el.findtext("homecitypreviewwpf") or ""
    header_img = ""
    if leader_preview:
        tag, ok = img_tag(leader_preview, display_name, 40)
        if ok:
            header_img = tag

    # Sub-line: leader name + doctrine
    sub_parts = []
    if leader_name_hdr:
        sub_parts.append(html_module.escape(leader_name_hdr))
    if doctrine_label_hdr:
        sub_parts.append(f'<span class="hdr-doctrine">{html_module.escape(doctrine_label_hdr)}</span>')
    sub_line = ""
    if sub_parts:
        sub_line = f'<div class="col-sub">{" · ".join(sub_parts)}</div>'

    col = f"""<section class="civ-col" id="{html_module.escape(civ_token)}" style="{bg}color:{tc}">
  <div class="col-header">
    {header_img}
    <div class="hdr-text">
      <span class="col-name">{html_module.escape(display_name)}</span>
      {sub_line}
    </div>
  </div>
  <div class="col-body">
    {text_html}
    <div class="art-section">
      <div class="section-label">Art &amp; Assets</div>
      {art_html}
      {captures_html}
      {doctrine_html}
    </div>
  </div>
</section>
"""
    return col, resolved, missing

# ── CSS ────────────────────────────────────────────────────────────────────────
CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }

html {
  overflow-x: scroll;
  overflow-y: hidden;
  height: 100%;
  /* Firefox: thick, always-visible horizontal scrollbar */
  scrollbar-width: auto;
  scrollbar-color: rgba(255,255,255,0.45) rgba(0,0,0,0.40);
}
/* WebKit/Blink (Chrome, Edge, Safari): styled, thick horizontal scrollbar */
html::-webkit-scrollbar {
  height: 16px;
  background: rgba(0,0,0,0.40);
}
html::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.40);
  border-radius: 8px;
  border: 2px solid rgba(0,0,0,0.40);
}
html::-webkit-scrollbar-thumb:hover {
  background: rgba(255,255,255,0.65);
}
html::-webkit-scrollbar-track {
  background: rgba(0,0,0,0.30);
}

body {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  height: 100vh;
  overflow: hidden;
  font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
  /* Base 11px — small enough to fit dense data, big enough to read */
  font-size: 11px;
  line-height: 1.4;
}

/* ── Column ── */
.civ-col {
  flex: 0 0 clamp(290px, 14vw, 370px);
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(0,0,0,0.35);
  position: relative;
}

/* Right-edge shadow to visually separate columns */
.civ-col::after {
  content: "";
  position: absolute;
  top: 0; right: 0; bottom: 0;
  width: 5px;
  background: linear-gradient(to right, transparent, rgba(0,0,0,0.30));
  pointer-events: none;
}

/* ── Header ── */
.col-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 7px;
  /* Dark overlay: anchors text against any civ hue (WCAG AA safe) */
  background: rgba(0,0,0,0.52);
  border-bottom: 2px solid rgba(255,255,255,0.18);
  flex-shrink: 0;
}
.col-header img {
  width: 40px; height: 40px;
  object-fit: cover;
  border-radius: 50%;
  border: 2px solid rgba(255,255,255,0.40);
  flex-shrink: 0;
}
.hdr-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow: hidden;
}
.col-name {
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.01em;
  line-height: 1.15;
  color: #fff;
  text-shadow: 0 1px 3px rgba(0,0,0,0.6);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.col-sub {
  font-size: 9.5px;
  font-weight: 500;
  color: rgba(255,255,255,0.80);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hdr-doctrine {
  font-style: italic;
  color: rgba(255,220,130,0.90);
}

/* ── Body split: text top / art bottom ── */
.col-body {
  flex: 1 1 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* Semi-opaque content surface behind text — key contrast fix */
.text-section {
  flex: 0 0 54%;
  overflow: hidden;
  padding: 4px 6px;
  background: rgba(0,0,0,0.42);
  border-bottom: 1px solid rgba(255,255,255,0.12);
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.art-section {
  flex: 0 0 46%;
  overflow: hidden;
  padding: 3px 6px;
  background: rgba(0,0,0,0.28);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* ── Info table ── */
.info-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 10px;
}
.info-table tr:hover td {
  background: rgba(255,255,255,0.06);
}
.info-table td {
  padding: 1.5px 3px;
  vertical-align: top;
}
.info-table .lbl {
  width: 36%;
  color: rgba(255,255,255,0.62);
  font-weight: 600;
  white-space: nowrap;
  font-size: 9px;
  padding-right: 4px;
}
.info-table .mono code {
  font-family: ui-monospace, 'Cascadia Code', Menlo, monospace;
  font-size: 9px;
  background: rgba(0,0,0,0.35);
  padding: 0 3px;
  border-radius: 2px;
}
.info-table .blurb-cell {
  font-size: 9.5px;
  line-height: 1.35;
  color: rgba(255,255,255,0.88);
}

/* ── Cards section ── */
.cards-section {
  flex: 1 1 auto;
  overflow: hidden;
  font-size: 9px;
  line-height: 1.35;
}
.age-row {
  margin-bottom: 3px;
  display: flex;
  align-items: flex-start;
  gap: 4px;
  padding: 2px 3px;
  border-radius: 3px;
  overflow: hidden;
}
/* Age-band colour coding */
.age-row.age-0 { background: rgba(130,130,130,0.22); }  /* Discovery — gray  */
.age-row.age-1 { background: rgba(160,130, 70,0.22); }  /* Colonial  — tan   */
.age-row.age-2 { background: rgba( 60,100,180,0.25); }  /* Fortress  — blue  */
.age-row.age-3 { background: rgba(180,130, 20,0.25); }  /* Industrial— amber */
.age-row.age-4 { background: rgba(160, 40, 40,0.25); }  /* Imperial  — red   */

.age-lbl {
  display: inline-block;
  font-weight: 700;
  font-size: 8px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  opacity: 0.90;
  padding: 1px 3px;
  border-radius: 2px;
  flex-shrink: 0;
  align-self: center;
  min-width: 52px;
}
/* Stronger pill colours for the label itself */
.age-row.age-0 .age-lbl { background: rgba(160,160,160,0.35); }
.age-row.age-1 .age-lbl { background: rgba(180,145, 80,0.40); }
.age-row.age-2 .age-lbl { background: rgba( 80,130,210,0.40); }
.age-row.age-3 .age-lbl { background: rgba(200,155, 30,0.40); }
.age-row.age-4 .age-lbl { background: rgba(190, 55, 55,0.40); }

.age-row:hover {
  background: rgba(255,255,255,0.10) !important;
}

/* Card thumbnails inside an age-row */
.age-cards {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 2px;
  vertical-align: middle;
}
.card-img {
  width: 22px;
  height: 22px;
  object-fit: contain;
  border: 1px solid rgba(255,255,255,0.18);
  border-radius: 2px;
  background: rgba(0,0,0,0.30);
  cursor: help;
  transition: transform 0.12s, border-color 0.12s, box-shadow 0.12s;
}
.card-img:hover {
  transform: scale(1.45);
  border-color: rgba(255,255,255,0.65);
  box-shadow: 0 0 6px rgba(0,0,0,0.55);
  z-index: 2;
  position: relative;
}
.card-text {
  display: inline-block;
  font-size: 8.5px;
  padding: 0 3px;
  border-radius: 2px;
  background: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.80);
  cursor: help;
}

/* ── Art rows ── */
.art-row {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  margin-bottom: 2px;
  overflow: hidden;
  max-height: 62px;
}
.art-lbl {
  font-size: 8px;
  font-weight: 600;
  color: rgba(255,255,255,0.60);
  min-width: 58px;
  max-width: 68px;
  flex-shrink: 0;
  padding-top: 2px;
  line-height: 1.2;
}
.art-row img {
  width: 56px;
  height: 56px;
  object-fit: contain;
  border: 1px solid rgba(255,255,255,0.22);
  border-radius: 3px;
  background: rgba(0,0,0,0.30);
  flex-shrink: 0;
  transition: box-shadow 0.15s, border-color 0.15s;
}
.art-row img:hover {
  border-color: rgba(255,255,255,0.55);
  box-shadow: 0 0 6px rgba(255,255,255,0.25);
}

/* Engine-path text: monospace, truncated, full path on hover title */
.path-text {
  font-family: ui-monospace, 'Cascadia Code', Menlo, monospace;
  font-size: 8.5px;
  color: rgba(255,255,255,0.72);
  background: rgba(0,0,0,0.30);
  padding: 1px 4px;
  border-radius: 2px;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  line-height: 1.4;
  cursor: default;
}
.path-missing code {
  font-family: ui-monospace, 'Cascadia Code', Menlo, monospace;
  font-size: 8.5px;
  color: rgba(255,120,120,0.75);
  word-break: break-all;
}

.section-label {
  font-size: 8.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: rgba(255,255,255,0.55);
  margin-bottom: 3px;
  flex-shrink: 0;
  border-bottom: 1px solid rgba(255,255,255,0.10);
  padding-bottom: 1px;
}

.empty { opacity: 0.38; font-style: italic; }

/* ── Visual capture thumbnails ── */
.captures-section {
  flex-shrink: 0;
  margin-top: 4px;
  padding-top: 3px;
  border-top: 1px solid rgba(255,255,255,0.10);
}

/* 4 or 5 column grid — thumbs are 56-72px tall; 2 rows of 5 fit without overflow */
.captures-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 3px;
  /* No overflow here — constraint is honoured by column height */
}

.capture-thumb {
  cursor: pointer;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  border-radius: 3px;
  border: 1px solid rgba(255,255,255,0.18);
  background: rgba(0,0,0,0.30);
  overflow: hidden;
  transition: transform 0.12s ease, box-shadow 0.12s ease, filter 0.12s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,0.45);
  outline: none;
}

.capture-thumb:hover {
  transform: scale(1.04);
  filter: brightness(1.1);
  box-shadow: 0 2px 8px rgba(0,0,0,0.65);
  border-color: rgba(255,255,255,0.50);
}

.capture-thumb:focus-visible {
  outline: 2px solid rgba(100,180,255,0.85);
  outline-offset: 1px;
}

.capture-thumb img {
  width: 100%;
  height: 56px;
  object-fit: cover;
  display: block;
}

.capture-thumb figcaption {
  font-size: 7px;
  font-weight: 600;
  text-align: center;
  color: rgba(255,255,255,0.72);
  padding: 1px 2px 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  line-height: 1.2;
}

/* ── Doctrine evidence section (AI live-game proofs) ── */
.doctrine-section {
  flex-shrink: 0;
  margin-top: 4px;
  padding-top: 3px;
  border-top: 1px solid rgba(255,220,140,0.22);
}

.doctrine-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 3px;
}

.doctrine-thumb {
  cursor: pointer;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  border-radius: 3px;
  border: 1px solid rgba(255,220,140,0.32);
  background: rgba(60,40,10,0.40);
  transition: transform 80ms ease, box-shadow 80ms ease;
}

.doctrine-thumb:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(0,0,0,0.65);
  border-color: rgba(255,220,140,0.85);
}

.doctrine-thumb:focus-visible {
  outline: 2px solid rgba(255,220,140,0.85);
  outline-offset: 1px;
}

.doctrine-thumb img {
  width: 100%;
  height: 64px;
  object-fit: cover;
  display: block;
}

.doctrine-thumb figcaption {
  font-size: 7px;
  font-weight: 600;
  text-align: center;
  color: rgba(255,220,140,0.88);
  padding: 1px 2px 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  line-height: 1.2;
}

/* ── Lightbox modal ── */
.capture-modal {
  position: fixed;
  inset: 0;
  z-index: 9000;
  background: rgba(0,0,0,0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  /* No overflow rules here — intentional, to avoid conflicting with
     the no-vertical-scroll constraint on the column layout */
}

/* When hidden attribute is present the browser hides it — no extra CSS needed */
.capture-modal[hidden] {
  display: none;
}

.modal-close {
  position: absolute;
  top: 14px;
  right: 18px;
  background: rgba(255,255,255,0.10);
  border: 1px solid rgba(255,255,255,0.25);
  color: #fff;
  font-size: 22px;
  line-height: 1;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
  z-index: 9001;
}

.modal-close:hover {
  background: rgba(255,255,255,0.22);
}

.modal-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  max-width: 95vw;
  max-height: 90vh;
}

#modal-img {
  max-width: 95vw;
  max-height: 83vh;
  object-fit: contain;
  border-radius: 4px;
  box-shadow: 0 4px 32px rgba(0,0,0,0.8);
  display: block;
}

#modal-caption {
  color: rgba(255,255,255,0.82);
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.02em;
  text-align: center;
  text-shadow: 0 1px 3px rgba(0,0,0,0.6);
}
"""

# ── Lightbox JS (vanilla, no framework) ───────────────────────────────────────
# Uses __CIV_DISPLAY_MAP__ as a substitution token — replaced at build time
# via str.replace() to avoid Python format() conflicts with JS braces.
LIGHTBOX_JS = r"""
(function () {
  'use strict';

  // Map from civ_token -> human display name, injected by the generator
  var CIV_DISPLAY = __CIV_DISPLAY_MAP__;

  // Surface labels matching CROP_SURFACE_LABELS in the Python generator
  var SURFACE_LABELS = {
    lobby_portrait:          'Lobby portrait',
    loading_flag:            'Loading flag',
    home_city_button:        'Home City button',
    hud_flag_corner:         'HUD flag corner',
    home_city_scene:         'Home City scene',
    tech_tree_overview:      'Tech tree overview',
    diplomacy_panel:         'Diplomacy panel',
    scoreboard_player_row:   'Scoreboard row',
    esc_menu_player_summary: 'ESC menu summary',
    endgame_flag:            'Endgame flag',
    diplomacy_ally_portrait: 'Ally portrait'
  };

  function surfaceLabel(name) {
    return SURFACE_LABELS[name] || name.replace(/_/g, ' ').replace(/\b\w/g, function(c){ return c.toUpperCase(); });
  }

  var modal    = document.getElementById('capture-modal');
  var modalImg = document.getElementById('modal-img');
  var caption  = document.getElementById('modal-caption');

  function openModal(figure) {
    var fullSrc  = figure.dataset.fullSrc;
    var civToken = figure.dataset.civ;
    var surface  = figure.dataset.surface;
    var civName  = CIV_DISPLAY[civToken] || civToken;
    modalImg.src = fullSrc;
    modalImg.alt = civName + ' \u2014 ' + surfaceLabel(surface);
    caption.textContent = civName + ' \u2014 ' + surfaceLabel(surface);
    modal.removeAttribute('hidden');
    modal.focus();
  }

  function closeModal() {
    modal.setAttribute('hidden', '');
    modalImg.src = '';  // free memory
  }

  function getAllThumbs(figure) {
    var col = figure.closest('.civ-col');
    if (!col) return [];
    return Array.from(col.querySelectorAll('.capture-thumb, .doctrine-thumb'));
  }

  // Track the currently open figure for arrow navigation
  var currentFigure = null;

  // Event delegation — click on any .capture-thumb
  document.addEventListener('click', function (e) {
    var fig = e.target.closest('.capture-thumb, .doctrine-thumb');
    if (fig) {
      currentFigure = fig;
      openModal(fig);
      return;
    }
    // Close on backdrop click (not on image or caption)
    if (e.target === modal) {
      closeModal();
      currentFigure = null;
    }
  });

  function navigateAndTrack(direction) {
    if (!currentFigure) return;
    var thumbs = getAllThumbs(currentFigure);
    if (thumbs.length === 0) return;
    var idx  = thumbs.indexOf(currentFigure);
    var next = (idx + direction + thumbs.length) % thumbs.length;
    currentFigure = thumbs[next];
    openModal(currentFigure);
  }

  // Keyboard handler
  document.addEventListener('keydown', function (e) {
    if (modal.hasAttribute('hidden')) return;
    if (e.key === 'Escape') {
      closeModal();
      currentFigure = null;
    } else if (e.key === 'ArrowLeft') {
      navigateAndTrack(-1);
    } else if (e.key === 'ArrowRight') {
      navigateAndTrack(1);
    }
  });

  // Close button
  document.querySelector('.modal-close').addEventListener('click', function () {
    closeModal();
    currentFigure = null;
  });

  // Keyboard activation on thumbnails (Enter / Space)
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var fig = document.activeElement && document.activeElement.closest('.capture-thumb, .doctrine-thumb');
    if (fig) {
      e.preventDefault();
      currentFigure = fig;
      openModal(fig);
    }
  });

  // Pre-cache on hover (pointer: fine devices only)
  var supportsPointerFine = window.matchMedia && window.matchMedia('(pointer: fine)').matches;
  if (supportsPointerFine) {
    document.addEventListener('mouseover', function (e) {
      var fig = e.target.closest('.capture-thumb, .doctrine-thumb');
      if (fig && fig.dataset.fullSrc && !fig._precached) {
        fig._precached = true;
        var img = new Image();
        img.src = fig.dataset.fullSrc;
      }
    });
  }

  // Vertical wheel -> horizontal scroll. The body is a flex row; the html
  // element is the scroll container (overflow-x: scroll, overflow-y: hidden).
  // Translate primarily-vertical wheel events into scrollLeft delta so a
  // mouse wheel scrolls across columns naturally. Touchpad horizontal
  // gestures (deltaX dominant) pass through unchanged; modal-open suppresses.
  function horizScrollHandler(e) {
    var modal = document.getElementById('capture-modal');
    if (modal && !modal.hidden) return;
    if (Math.abs(e.deltaX) >= Math.abs(e.deltaY)) return;
    if (e.deltaY === 0) return;
    e.preventDefault();
    var dy = e.deltaY;
    // Normalise deltaMode: 0=pixels, 1=lines (~16px each), 2=pages.
    if (e.deltaMode === 1) dy *= 16;
    else if (e.deltaMode === 2) dy *= window.innerHeight;
    // window.scrollBy works regardless of which element is the scroll root
    // (some browsers route this to body, others to documentElement).
    window.scrollBy({ left: dy, top: 0, behavior: 'auto' });
  }
  // Bind on both window and document to maximise capture coverage; passive
  // false is required so preventDefault() actually suppresses native vertical
  // scroll (which would be a no-op anyway since body is overflow:hidden, but
  // some browsers still emit a console "Unable to preventDefault" warning).
  window.addEventListener('wheel', horizScrollHandler, { passive: false });
  document.addEventListener('wheel', horizScrollHandler, { passive: false });

  // Keyboard navigation: Left/Right arrows = scroll one column,
  // PageUp/PageDown = scroll one viewport, Home/End = jump.
  document.addEventListener('keydown', function (e) {
    var modal = document.getElementById('capture-modal');
    if (modal && !modal.hidden) return;
    var col = 380;  // ~one column width
    var vp = window.innerWidth;
    if (e.key === 'ArrowRight') { window.scrollBy({left:  col, top: 0}); e.preventDefault(); }
    else if (e.key === 'ArrowLeft')  { window.scrollBy({left: -col, top: 0}); e.preventDefault(); }
    else if (e.key === 'PageDown')   { window.scrollBy({left:  vp,  top: 0}); e.preventDefault(); }
    else if (e.key === 'PageUp')     { window.scrollBy({left: -vp,  top: 0}); e.preventDefault(); }
    else if (e.key === 'Home')       { window.scrollTo({left: 0, top: 0}); e.preventDefault(); }
    else if (e.key === 'End')        { window.scrollTo({left: document.documentElement.scrollWidth, top: 0}); e.preventDefault(); }
  });
}());
"""

# ── CIV display name map builder ──────────────────────────────────────────────
def build_civ_display_map(civ_order, civmods, strings):
    """Return a JS object literal mapping civ_token -> display name."""
    pairs = []
    for token in civ_order:
        civ_el = civmods.get(token)
        if civ_el is not None:
            display_id   = civ_el.findtext("displaynameid") or ""
            display_name = strings.get(display_id, token)
        else:
            display_name = token
        # Escape for JS string literal
        safe_token = token.replace("'", "\\'")
        safe_name  = display_name.replace("'", "\\'")
        pairs.append(f"  '{safe_token}': '{safe_name}'")
    return "{\n" + ",\n".join(pairs) + "\n}"


# ── CIV order (same as playercolors.xml, which has 45 entries) ────────────────
def get_civ_order():
    path = os.path.join(DATA_DIR, "playercolors.xml")
    tree = ET.parse(path)
    return [c.get("civ") for c in tree.getroot().findall(".//Color") if c.get("civ")]

# ── Build ──────────────────────────────────────────────────────────────────────
def build():
    print("Loading data sources...")
    strings = load_strings()
    civmods = load_civmods()
    colors  = load_playercolors()
    blurbs  = load_blurbs()
    spec    = load_playstyle_spec()
    decks   = load_decks()
    cards   = load_cards()

    civ_order = get_civ_order()
    print(f"Building {len(civ_order)} columns...")

    columns_html = []
    total_resolved = 0
    total_missing  = 0

    for civ_token in civ_order:
        col_html, resolved, missing = render_column(
            civ_token, civmods, strings, colors, blurbs, spec, decks, cards
        )
        columns_html.append(col_html)
        total_resolved += resolved
        total_missing  += missing

    # Total width calculation for comment
    num_cols   = len(civ_order)
    approx_w_px = num_cols * 320  # approximate based on clamp midpoint

    first3 = [f'id="{c}"' for c in civ_order[:3]]

    # Build a JS mapping from civ_token -> display_name for modal captions
    civ_display_map_js = build_civ_display_map(civ_order, civmods, strings)

    lightbox_js = LIGHTBOX_JS.replace("__CIV_DISPLAY_MAP__", civ_display_map_js)

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ANW Civ Review Columns — A New World</title>
<style>
{CSS}
</style>
</head>
<body>
<!-- {num_cols} columns, ~{approx_w_px}px total width (overflow-x: scroll on html) -->
<!-- First 3 column IDs: {", ".join(first3)} -->
{"".join(columns_html)}
<!-- Shared lightbox modal — one instance for the entire page -->
<div id="capture-modal" class="capture-modal" hidden>
  <button class="modal-close" aria-label="Close (Esc)">&times;</button>
  <div class="modal-content">
    <img id="modal-img" src="" alt="">
    <div id="modal-caption"></div>
  </div>
</div>
<script>
{lightbox_js}
</script>
</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"Written: {OUTPUT_HTML}")
    print(f"Columns: {num_cols}")
    print(f"Art assets resolved as <img>: {total_resolved}")
    print(f"Art assets skipped (path missing): {total_missing}")
    print(f"File size: {os.path.getsize(OUTPUT_HTML):,} bytes")

if __name__ == "__main__":
    build()
