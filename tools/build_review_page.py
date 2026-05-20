#!/usr/bin/env python3
"""
build_review_page.py — Lean single-civ review HTML.

The big a_new_world_columns.html dumps every civmods.xml/locID/file-path/personality
knob into the page — useful for engineering, painful for reviewing what a *player*
will actually see in-game. This builder produces a stripped-down per-civ page
that keeps ONLY user-visible content:

  - civ name, leader, doctrine (header)
  - civ bonus / playstyle / age-up / unique units (quotes a player reads)
  - lobby rollover description (the long blurb on hover)
  - HC building names + rollovers
  - All cards by age — icon + name + description, exactly as in the deck UI
  - Visual confirmation thumbnails (in-game captures)
  - Art surfaces a player sees: HC flag, HC button, HC scene, leader portrait,
    postgame flag, matchmaking avatar

DROPPED on purpose (player never sees these):
  - locID numbers, displaynameid/rollovernameid/heroname source tags
  - resources/.../*.png paths, art/ui/.../*.ddt paths, .gr2/.cam files
  - civ_token, statsID, culture, allied/unallied numeric IDs
  - AI personality knob table (llSetMilitaryFocus etc.)
  - Vanilla asset parity counts (555/555 voice lines etc.)
  - "Source: leader_X.xs" annotations
  - Capture meta timestamps

Usage::

  python3 tools/build_review_page.py                  # defaults to ANWBritish
  python3 tools/build_review_page.py ANWBrazil        # any civ token
  python3 tools/build_review_page.py ANWBritish --out review.html
"""
from __future__ import annotations

import argparse
import html as html_module
import os
import sys

# Reuse the heavy data loaders from the main builder.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_civ_columns as bcc  # noqa: E402


# Surfaces a player actually sees in-game, in the order they encounter them.
# Filenames come from civmods.xml; we only render the thumbnail + label.
_PLAYER_VISIBLE_ART = [
    ("Leader portrait (CPAI)",      "homecitypreviewwpf"),
    ("Home City flag (large)",      "homecityflagiconwpf"),
    ("Home City flag (button)",     "homecityflagbuttonwpf"),
    ("Post-game flag",              "postgameflagiconwpf"),
]


def _esc(s: str) -> str:
    return html_module.escape(s or "")


def _esc_ingame(s: str) -> str:
    """Escape for HTML, but turn the engine's literal '\\n' into a real newline
    so reviewers see the same paragraph breaks the player sees in-game.

    AoE3 stringtable XML stores newlines as the two characters backslash+n
    (rather than a literal newline in the XML), and the engine renders them
    as line breaks when displayed. Our review surface uses ``white-space:
    pre-wrap``, so a real newline will render correctly.
    """
    s = (s or "").replace("\\n", "\n").replace("\\r", "")
    return html_module.escape(s)


def render_header(civ_token, display_name, leader, doctrine, civ_bonus,
                  portrait_path, bg_color, text_color):
    portrait_html = ""
    if portrait_path and os.path.exists(os.path.join(bcc.MOD_ROOT, portrait_path)):
        portrait_html = (
            f'<img class="hero-portrait" loading="lazy"'
            f' src="{_esc(portrait_path)}" alt="{_esc(display_name)}">'
        )
    bonus_html = (
        f'<div class="civ-bonus">{_esc(civ_bonus)}</div>'
        if civ_bonus else ""
    )
    return f"""
<header class="review-header" style="background:{bg_color};color:{text_color}">
  {portrait_html}
  <div class="head-meta">
    <h1 class="civ-name">{_esc(display_name)}</h1>
    <div class="civ-leader-line">
      <span class="leader">{_esc(leader)}</span>
      <span class="sep">·</span>
      <span class="doctrine">{_esc(doctrine)}</span>
    </div>
    {bonus_html}
  </div>
</header>
"""


def render_quotes(rows):
    """Render the *user-visible* strings only. No locIDs in tooltips."""
    # Group rows by section. We deliberately bucket so the user reads them
    # in the order they'd encounter them on screen.
    sections = [
        ("Lobby & loading screens", [
            "Lobby picker — civ name",
            "Lobby picker — rollover description",
            "Loading screen — leader name",
            "Home City — HC title",
        ]),
        ("Tech tree / picker tooltip", [
            "Tech tree — doctrine name",
            "Tech tree — doctrine summary",
        ]),
        ("Playstyle blurbs (in-picker)", [
            "Civ bonus tooltip",
            "Playstyle description",
            "Age up method",
            "Unique unit name",
        ]),
        ("Home City buildings", []),  # populated dynamically
    ]
    by_label = {}
    for r in rows:
        by_label.setdefault(r["location_label"], []).append(r["string_text"])

    parts = ['<section class="quotes"><h2>Text the player sees</h2>']
    used = set()
    for sect_title, labels in sections:
        items = []
        if sect_title == "Home City buildings":
            for lbl, texts in by_label.items():
                if lbl.startswith("HC building"):
                    used.add(lbl)
                    for t in texts:
                        items.append((lbl, t))
        else:
            for lbl in labels:
                if lbl in by_label:
                    used.add(lbl)
                    for t in by_label[lbl]:
                        items.append((lbl, t))
        if not items:
            continue
        parts.append(f'<div class="quote-group"><h3>{_esc(sect_title)}</h3>')
        for lbl, txt in items:
            parts.append(
                f'<div class="quote-row">'
                f'<div class="quote-label">{_esc(lbl)}</div>'
                f'<div class="quote-text">{_esc_ingame(txt)}</div>'
                f'</div>'
            )
        parts.append('</div>')

    # Anything else with non-card strings, lumped at the end ("Other in-game strings").
    leftover = [
        (lbl, txt)
        for lbl, texts in by_label.items()
        for txt in texts
        if lbl not in used
        and not lbl.startswith("Cards >")
        and not lbl.startswith("Leader name")  # canonical name, duplicate of header
    ]
    if leftover:
        parts.append('<div class="quote-group"><h3>Other in-game strings</h3>')
        for lbl, txt in leftover:
            parts.append(
                f'<div class="quote-row">'
                f'<div class="quote-label">{_esc(lbl)}</div>'
                f'<div class="quote-text">{_esc_ingame(txt)}</div>'
                f'</div>'
            )
        parts.append('</div>')

    parts.append('</section>')
    return "\n".join(parts)


def render_cards_by_age(civ_token, decks, cards):
    """Render the deck exactly as a player would scroll through it: icon + name + description."""
    dk = bcc.deck_key(civ_token)
    deck = decks.get(dk, {})
    age_order = [("0", "Discovery"), ("1", "Colonial"), ("2", "Fortress"),
                 ("3", "Industrial"), ("4", "Imperial")]
    total = sum(len(deck.get(a, [])) for a, _ in age_order)
    parts = [f'<section class="cards"><h2>Home City Cards ({total})</h2>']

    if total == 0:
        parts.append('<p class="empty">No deck defined for this civ.</p></section>')
        return "\n".join(parts)

    for age_key, age_label in age_order:
        card_ids = deck.get(age_key, [])
        if not card_ids:
            continue
        parts.append(f'<div class="age-block age-{age_key}">')
        parts.append(f'<h3>{_esc(age_label)} <span class="age-count">({len(card_ids)})</span></h3>')
        parts.append('<div class="card-grid">')
        for cid in card_ids:
            info = cards.get(cid, {})
            name = info.get("name") or cid
            desc = info.get("desc") or ""
            icon = info.get("icon") or ""
            icon_html = ""
            if icon:
                rel = f"resources/images/icons/cards/{icon}"
                if os.path.exists(os.path.join(bcc.MOD_ROOT, rel)):
                    icon_html = f'<img class="card-icon" loading="lazy" src="{_esc(rel)}" alt="{_esc(name)}">'
            if not icon_html:
                icon_html = '<div class="card-icon placeholder">·</div>'
            parts.append(
                f'<article class="card">'
                f'{icon_html}'
                f'<div class="card-text">'
                f'<div class="card-name">{_esc(name)}</div>'
                f'<div class="card-desc">{_esc_ingame(desc)}</div>'
                f'</div>'
                f'</article>'
            )
        parts.append('</div></div>')

    parts.append('</section>')
    return "\n".join(parts)


def render_art_surfaces(civ_el):
    """Render the handful of art surfaces a player actually sees, with no path strings."""
    parts = ['<section class="art"><h2>Art surfaces (what shows on screen)</h2>',
             '<div class="art-grid">']
    for label, field in _PLAYER_VISIBLE_ART:
        raw = (civ_el.findtext(field) or "").strip()
        if not raw:
            continue
        # Normalise slashes for the browser
        rel = raw.replace("\\", "/")
        fs_path = os.path.join(bcc.MOD_ROOT, rel)
        if not os.path.exists(fs_path):
            continue
        parts.append(
            f'<figure class="art-thumb">'
            f'<img loading="lazy" src="{_esc(rel)}" alt="{_esc(label)}">'
            f'<figcaption>{_esc(label)}</figcaption>'
            f'</figure>'
        )
    parts.append('</div></section>')
    return "\n".join(parts)


def render_visual_confirmation(civ_token, display_name):
    """Render the in-game capture thumbnails — passthrough to the existing renderer."""
    host = bcc.load_capture_manifest(civ_token, ally=False)
    ally = bcc.load_capture_manifest(civ_token, ally=True)
    if not host and not ally:
        return ""
    # Reuse the existing renderer; it already strips locIDs and just shows thumbs.
    inner = bcc.render_captures_section(civ_token, display_name, host, ally)
    return f'<section class="visual-confirmation"><h2>Visual confirmation (real in-game captures)</h2>{inner}</section>'


_CSS = """
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  background: #15151c;
  color: #e8e8ee;
  line-height: 1.5;
}
.review-header {
  display: flex;
  gap: 24px;
  align-items: center;
  padding: 28px 36px;
  border-bottom: 2px solid rgba(255,255,255,0.1);
}
.review-header .hero-portrait {
  width: 96px;
  height: 96px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.25);
  background: rgba(0,0,0,0.3);
}
.review-header .civ-name {
  margin: 0;
  font-size: 32px;
  font-weight: 600;
}
.review-header .civ-leader-line {
  font-size: 16px;
  margin-top: 4px;
  opacity: 0.92;
}
.review-header .civ-leader-line .sep { margin: 0 8px; opacity: 0.5; }
.review-header .civ-leader-line .doctrine { font-weight: 600; }
.review-header .civ-bonus {
  margin-top: 10px;
  font-size: 14px;
  background: rgba(0,0,0,0.30);
  padding: 6px 12px;
  border-radius: 4px;
  display: inline-block;
}
main { max-width: 1280px; margin: 0 auto; padding: 24px 32px 80px; }
section { margin-top: 36px; }
section > h2 {
  font-size: 22px;
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255,255,255,0.12);
}
section > h2::before {
  content: "▸";
  margin-right: 8px;
  opacity: 0.6;
}
.quote-group h3 {
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #9090b0;
  margin: 18px 0 6px;
}
.quote-row {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 16px;
  padding: 6px 0;
  border-bottom: 1px dashed rgba(255,255,255,0.06);
}
.quote-label { color: #b8b8d0; font-size: 13px; }
.quote-text { color: #fff; font-size: 14px; white-space: pre-wrap; }
.age-block { margin-bottom: 24px; }
.age-block h3 {
  font-size: 16px;
  margin: 12px 0 8px;
  border-left: 4px solid currentColor;
  padding-left: 8px;
}
.age-block.age-0 h3 { color: #9aa9ff; }
.age-block.age-1 h3 { color: #62c46c; }
.age-block.age-2 h3 { color: #d3b855; }
.age-block.age-3 h3 { color: #c97c46; }
.age-block.age-4 h3 { color: #cf5b5b; }
.age-count { opacity: 0.6; font-weight: 400; font-size: 13px; }
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 12px;
}
.card {
  display: flex;
  gap: 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 4px;
  padding: 10px;
}
.card-icon {
  width: 52px;
  height: 52px;
  flex: 0 0 52px;
  border-radius: 3px;
  object-fit: cover;
  background: rgba(0,0,0,0.4);
}
.card-icon.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,0.3);
}
.card-text { flex: 1; min-width: 0; }
.card-name { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
.card-desc { font-size: 12.5px; color: #d0d0e0; }
.art-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
}
.art-thumb img {
  width: 100%;
  height: 130px;
  object-fit: contain;
  background: rgba(0,0,0,0.25);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 4px;
}
.art-thumb figcaption {
  text-align: center;
  font-size: 12px;
  margin-top: 4px;
  color: #b0b0c8;
}
/* Visual-confirmation grid (reuses captures-grid from main columns CSS) */
.visual-confirmation .captures-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.visual-confirmation .capture-thumb {
  margin: 0;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 4px;
  padding: 6px;
}
.visual-confirmation .capture-thumb img {
  width: 100%;
  height: 130px;
  object-fit: cover;
  border-radius: 3px;
}
.visual-confirmation .capture-thumb figcaption {
  font-size: 12px;
  text-align: center;
  margin-top: 4px;
  color: #b0b0c8;
}
.visual-confirmation .captures-section .section-label {
  display: none;  /* "Visual confirmation" already shown by our h2 */
}
.empty { color: rgba(255,255,255,0.5); font-style: italic; }
.review-nav {
  padding: 10px 36px;
  background: #1a1a24;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  font-size: 13px;
}
.review-nav a {
  color: #9aa9ff;
  text-decoration: none;
  font-weight: 500;
}
.review-nav a:hover { text-decoration: underline; }
"""


def _load_all():
    """Load every data source the renderer needs. Cached across civs in --all."""
    return {
        "civmods":         bcc.load_civmods(),
        "strings":         bcc.load_strings(),
        "strings_by_civ":  bcc.load_strings_by_civ(),
        "blurbs":          bcc.load_blurbs(),
        "spec":            bcc.load_playstyle_spec(),
        "decks":           bcc.load_decks(),
        "cards":           bcc.load_cards(),
        "colors":          bcc.load_playercolors(),
    }


def build_review(civ_token: str, out_path: str, ctx: dict | None = None) -> str:
    ctx = ctx or _load_all()
    civmods       = ctx["civmods"]
    strings       = ctx["strings"]
    strings_by_civ = ctx["strings_by_civ"]
    blurbs        = ctx["blurbs"]
    spec          = ctx["spec"]
    decks         = ctx["decks"]
    cards         = ctx["cards"]
    colors        = ctx["colors"]

    civ_el = civmods.get(civ_token)
    if civ_el is None:
        raise SystemExit(f"civ token {civ_token!r} not found in civmods.xml")

    display_id = civ_el.findtext("displaynameid") or ""
    display_name = strings.get(display_id, civ_token)

    hc_file = civ_el.findtext("homecityfilename") or ""
    hc = bcc.load_homecity(hc_file) if hc_file else {}

    # Leader name (prefer canonical playstyle_spec.json label)
    spec_entry, _ = bcc.find_spec_entry(civ_token, spec)
    leader = spec_entry.get("leader_label", "") if spec_entry else ""
    if not leader and hc:
        raw = hc.get("heroname", "")
        if raw.startswith("$$") and raw.endswith("$$"):
            leader = strings.get(raw[2:-2], "")

    doctrine = spec_entry.get("doctrine_label", "") if spec_entry else ""

    blurb = blurbs.get(bcc.blurb_key(civ_token), {})
    civ_bonus = blurb.get("civ_bonus", "")

    # Pick a portrait — prefer the CPAI avatar (used in lobby/diplomacy)
    cpai_fn = bcc._CPAI_PORTRAIT.get(civ_token)
    if cpai_fn:
        portrait = bcc._CPAI_PORTRAIT_BASE + cpai_fn
    else:
        portrait = civ_el.findtext("homecitypreviewwpf") or ""

    color_entry = colors.get(civ_token, {"r": 40, "g": 40, "b": 60})
    r, g, b = color_entry["r"], color_entry["g"], color_entry["b"]
    bg_style = f"linear-gradient(160deg,rgb({r},{g},{b}),rgb({max(0,r-30)},{max(0,g-30)},{max(0,b-30)}))"
    txt_color = bcc.text_color(r, g, b)

    rows = bcc.collect_strings_for_civ(
        civ_token, civ_el, hc, strings, blurbs, spec, decks, cards, strings_by_civ
    )

    head = render_header(civ_token, display_name, leader, doctrine, civ_bonus,
                         portrait, bg_style, txt_color)
    quotes = render_quotes(rows)
    deck_html = render_cards_by_age(civ_token, decks, cards)
    art_html = render_art_surfaces(civ_el)
    captures_html = render_visual_confirmation(civ_token, display_name)

    nav_html = (
        '<nav class="review-nav">'
        '<a href="review_index.html">← back to all civs</a>'
        '</nav>'
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{_esc(display_name)} — review</title>
<style>{_CSS}</style>
</head>
<body>
{nav_html}
{head}
<main>
{quotes}
{deck_html}
{art_html}
{captures_html}
</main>
{nav_html}
</body>
</html>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


def _civ_review_filename(civ_token: str) -> str:
    """Filename used for per-civ review pages — kept stable so the index links work."""
    return f"a_new_world_{civ_token.lower()}_review.html"


def build_index(ctx: dict, out_path: str, civ_tokens: list) -> str:
    """Render an index page that lists every reviewed civ with a portrait + name."""
    civmods = ctx["civmods"]
    strings = ctx["strings"]
    spec    = ctx["spec"]
    blurbs  = ctx["blurbs"]
    colors  = ctx["colors"]

    cards_html = []
    for tok in civ_tokens:
        civ_el = civmods.get(tok)
        if civ_el is None:
            continue
        display_id = civ_el.findtext("displaynameid") or ""
        display_name = strings.get(display_id, tok)

        spec_entry, _ = bcc.find_spec_entry(tok, spec)
        leader = spec_entry.get("leader_label", "") if spec_entry else ""
        doctrine = spec_entry.get("doctrine_label", "") if spec_entry else ""
        blurb = blurbs.get(bcc.blurb_key(tok), {})
        civ_bonus = blurb.get("civ_bonus", "")

        cpai_fn = bcc._CPAI_PORTRAIT.get(tok)
        portrait_rel = ""
        if cpai_fn:
            portrait_rel = bcc._CPAI_PORTRAIT_BASE + cpai_fn
        elif civ_el is not None:
            portrait_rel = civ_el.findtext("homecitypreviewwpf") or ""
        portrait_rel = (portrait_rel or "").replace("\\", "/")

        color_entry = colors.get(tok, {"r": 40, "g": 40, "b": 60})
        r, g, b = color_entry["r"], color_entry["g"], color_entry["b"]
        bg = (f"linear-gradient(160deg,rgb({r},{g},{b}),"
              f"rgb({max(0,r-30)},{max(0,g-30)},{max(0,b-30)}))")
        tc = bcc.text_color(r, g, b)

        portrait_html = ""
        if portrait_rel and os.path.exists(os.path.join(bcc.MOD_ROOT, portrait_rel)):
            portrait_html = (
                f'<img class="index-portrait" loading="lazy"'
                f' src="{_esc(portrait_rel)}" alt="{_esc(display_name)}">'
            )
        sub = []
        if leader:   sub.append(_esc(leader))
        if doctrine: sub.append(f'<span class="doctrine">{_esc(doctrine)}</span>')
        sub_line = " · ".join(sub)

        href = _civ_review_filename(tok)
        cards_html.append(
            f'<a class="index-card" href="{_esc(href)}" '
            f'style="background:{bg};color:{tc};">'
            f'{portrait_html}'
            f'<div class="index-meta">'
            f'<div class="index-name">{_esc(display_name)}</div>'
            f'<div class="index-sub">{sub_line}</div>'
            f'<div class="index-bonus">{_esc(civ_bonus)}</div>'
            f'</div>'
            f'</a>'
        )

    index_css = _CSS + """
.index-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
  padding: 0;
}
.index-card {
  display: flex;
  gap: 12px;
  padding: 14px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.10);
  text-decoration: none;
  transition: transform .12s ease, box-shadow .12s ease;
}
.index-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(0,0,0,0.45);
}
.index-portrait {
  width: 56px;
  height: 56px;
  flex: 0 0 56px;
  border-radius: 4px;
  object-fit: cover;
  background: rgba(0,0,0,0.3);
  border: 1px solid rgba(255,255,255,0.18);
}
.index-meta { flex: 1; min-width: 0; }
.index-name { font-size: 17px; font-weight: 600; margin-bottom: 2px; }
.index-sub  { font-size: 13px; opacity: 0.9; margin-bottom: 6px; }
.index-sub .doctrine { font-weight: 600; }
.index-bonus {
  font-size: 12px;
  opacity: 0.85;
  background: rgba(0,0,0,0.30);
  padding: 4px 8px;
  border-radius: 3px;
  display: inline-block;
}
.index-intro {
  max-width: 920px;
  margin: 0 0 24px;
  padding: 14px 18px;
  background: rgba(255,255,255,0.04);
  border-left: 3px solid rgba(255,255,255,0.30);
  border-radius: 3px;
  font-size: 14px;
  color: #c8c8e0;
}
"""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ANW v1.0 — civ review index</title>
<style>{index_css}</style>
</head>
<body>
<header class="review-header" style="background:linear-gradient(160deg,#262638,#1a1a28);color:#fff;">
  <div class="head-meta">
    <h1 class="civ-name">A New World — civ review</h1>
    <div class="civ-leader-line">
      <span class="leader">{len(cards_html)} picker civs</span>
      <span class="sep">·</span>
      <span class="doctrine">v1.0 release readiness</span>
    </div>
  </div>
</header>
<main>
<div class="index-intro">
Every card below opens a stripped-down per-civ review page: in-game strings,
home-city deck, art surfaces, and real in-game capture thumbnails — no
locIDs, no file paths, no engineering metadata. Pick a civ to start.
</div>
<div class="index-grid">
{''.join(cards_html)}
</div>
</main>
</body>
</html>
"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("civ_token", nargs="?", default="ANWBritish",
                    help="civ token to render (default ANWBritish; ignored with --all)")
    ap.add_argument("--out", default=None,
                    help="output HTML path (default a_new_world_<civ>_review.html)")
    ap.add_argument("--all", action="store_true",
                    help="render every ANW picker civ + an index page")
    args = ap.parse_args()

    if args.all:
        ctx = _load_all()
        civ_tokens = sorted([k for k in ctx["civmods"].keys() if k.startswith("ANW")])
        for tok in civ_tokens:
            out = os.path.join(bcc.MOD_ROOT, _civ_review_filename(tok))
            build_review(tok, out, ctx)
        idx = os.path.join(bcc.MOD_ROOT, "review_index.html")
        build_index(ctx, idx, civ_tokens)
        print(f"wrote {len(civ_tokens)} per-civ review pages + index → review_index.html")
        return

    out = args.out or os.path.join(
        bcc.MOD_ROOT,
        f"a_new_world_{args.civ_token.lower()}_review.html",
    )
    out_path = build_review(args.civ_token, out)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
