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
        card_names = []
        for card_id in age_cards:
            card_info = cards.get(card_id, {})
            card_name = card_info.get("name", card_id)
            if not card_name:
                card_name = card_id
            card_names.append(html_module.escape(card_name))
        age_label = {
            "0": "Discovery", "1": "Colonial", "2": "Fortress",
            "3": "Industrial", "4": "Imperial"
        }.get(age, f"Age {age}")
        cards_html_parts.append(
            f'<div class="age-row age-{age}"><span class="age-lbl">{age_label}</span>'
            f' {", ".join(card_names)}</div>'
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

    def art_row(label, path_or_key, is_file_path=True):
        nonlocal imgs_resolved, imgs_missing
        if not path_or_key:
            parts.append(
                f'<div class="art-row"><span class="art-lbl">{html_module.escape(label)}</span>'
                f'<span class="empty">—</span></div>'
            )
            return
        if is_file_path:
            tag, ok = img_tag(path_or_key, label, 56)
            if ok:
                imgs_resolved += 1
            else:
                imgs_missing += 1
            parts.append(
                f'<div class="art-row"><span class="art-lbl">{html_module.escape(label)}</span>'
                f'{tag}</div>'
            )
        else:
            parts.append(
                f'<div class="art-row"><span class="art-lbl">{html_module.escape(label)}</span>'
                f'<code class="path-text" title="{html_module.escape(path_or_key)}">{html_module.escape(path_or_key)}</code></div>'
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

    # Homecity XML fields
    if hc:
        visual    = hc.get("visual", "")
        water     = hc.get("watervisual", "")
        bg        = hc.get("backgroundvisual", "")
        camera    = hc.get("camera", "")
        ws_cam    = hc.get("widescreencamera", "")
        pathdata  = hc.get("pathdata", "")
        lightset  = hc.get("lightset", "")
        watertype = hc.get("watertype", "")
        ambient   = hc.get("ambientsounds", "")
        xsai      = hc.get("xsai", "")

        art_row("HC scene",    visual, False)
        art_row("HC water",    water, False)
        art_row("HC bg",       bg, False)
        art_row("Camera",      camera, False)
        art_row("WS camera",   ws_cam, False)
        art_row("Path data",   pathdata, False)
        art_row("Light set",   lightset, False)
        art_row("Water type",  watertype, False)
        art_row("Ambient",     ambient, False)
        art_row("XSAI",        xsai, False)

    # Personality
    pers_path = personality_path_str(civ_token)
    art_row("Personality", pers_path, False)

    return "".join(parts), imgs_resolved, imgs_missing

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
  /* Scrollbar always visible so layout is stable */
  scrollbar-width: thin;
  scrollbar-color: rgba(255,255,255,0.25) transparent;
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
  margin-bottom: 2px;
  word-break: break-word;
  overflow: hidden;
  max-height: 2.9em;
  padding: 1px 3px;
  border-radius: 3px;
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
  margin-right: 4px;
  font-size: 8px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  opacity: 0.85;
  padding: 0 3px;
  border-radius: 2px;
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
"""

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
</body>
</html>
"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"Written: {OUTPUT_HTML}")
    print(f"Columns: {num_cols}")
    print(f"Art assets resolved as <img>: {total_resolved}")
    print(f"Art assets shown as path-text: {total_missing}")
    print(f"File size: {os.path.getsize(OUTPUT_HTML):,} bytes")

if __name__ == "__main__":
    build()
