#!/usr/bin/env python3
"""Build artifacts/validation/visual_art/live_capture_review.html.

A single page that shows EVERY in-game live capture (age-ups + tech tree)
captured so far by the orchestrator, plus a status badge per civ:
  - LIVE = has 5 surfaces (15-18 age-ups + 05 tech tree)
  - PARTIAL = some surfaces present
  - SYNTHETIC_ONLY = only HTML synthetic tech tree, no in-game captures

User browses this to confirm content visually for each nation.
"""
import json, html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'artifacts' / 'validation' / 'visual_art'
OUT = ART / 'live_capture_review.html'

SURFACES = [
    ('15_age_up_colonial.png', 'Age 2 — Colonial politician'),
    ('16_age_up_fortress.png', 'Age 3 — Fortress politician'),
    ('17_age_up_industrial.png', 'Age 4 — Industrial politician'),
    ('18_age_up_imperial.png', 'Age 5 — Imperial politician'),
    ('05_tech_tree.png', 'Tech tree (in-game)'),
]

# Load civ display-name mapping
DISPLAY_NAME = {
    'ANWArgentines': 'Argentine Confederation',
    'ANWAztecs': 'Aztec Triple Alliance',
    'ANWBarbary': 'Regency of Algiers',
    'ANWBrazil': 'Empire of Brazil',
    'ANWBritish': 'British Empire',
    'ANWCanadians': 'Province of Canada',
    'ANWChileans': 'Republic of Chile',
    'ANWChinese': 'Qing Dynasty',
    'ANWColumbians': 'Gran Colombia',
    'ANWDutch': 'Dutch Republic',
    'ANWEgyptians': 'Khedivate of Egypt',
    'ANWEthiopians': 'Ethiopian Empire',
    'ANWFinnish': 'Grand Duchy of Finland',
    'ANWFrench': 'Bourbon France',
    'ANWGermans': 'German Empire',
    'ANWHaitians': 'First Empire of Haiti',
    'ANWHaudenosaunee': 'Haudenosaunee Confederacy',
    'ANWHausa': 'Sokoto Caliphate',
    'ANWHungarians': 'Kingdom of Hungary',
    'ANWInca': 'Inca Empire',
    'ANWIndians': 'Maratha Empire',
    'ANWIndonesians': 'Sultanate of Yogyakarta',
    'ANWItalians': 'Kingdom of Italy',
    'ANWJapanese': 'Tokugawa Shogunate',
    'ANWLakota': 'Lakota Sioux',
    'ANWMaltese': 'Knights of Malta',
    'ANWMayans': 'Cruzob Maya',
    'ANWMexicans': 'First Mexican Empire',
    'ANWNapoleonicFrance': 'France (Napoleonic)',
    'ANWOttomans': 'Ottoman Empire',
    'ANWPeruvians': 'Republic of Peru',
    'ANWPortuguese': 'Portuguese Empire',
    'ANWRevFrance': 'France (Revolutionary)',
    'ANWRomanians': 'United Romanian Principalities',
    'ANWRussians': 'Russian Empire',
    'ANWSouthAfricans': 'South African Republic',
    'ANWSpanish': 'Spanish Empire',
    'ANWSwedes': 'Swedish Empire',
    'ANWTexians': 'Republic of Texas',
    'ANWUSA': 'United States',
}


def civ_status(civ_dir: Path):
    full = civ_dir / 'full'
    if not full.exists():
        return 'synthetic', []
    available = []
    for fname, label in SURFACES:
        p = full / fname
        if p.exists() and p.stat().st_size > 100_000:
            available.append((fname, label))
    if len(available) == len(SURFACES):
        return 'live', available
    if len(available) > 0:
        return 'partial', available
    return 'synthetic', []


def render_civ_section(civ_token: str, civ_dir: Path) -> str:
    display = DISPLAY_NAME.get(civ_token, civ_token.replace('ANW', ''))
    status, surfaces = civ_status(civ_dir)
    badge_color = {'live': '#2ecc71', 'partial': '#f39c12', 'synthetic': '#888'}[status]
    badge_text = {'live': 'LIVE (5/5)', 'partial': f'PARTIAL ({len(surfaces)}/5)',
                  'synthetic': 'SYNTHETIC ONLY'}[status]

    if status == 'synthetic':
        synth = civ_dir / 'synthetic_tech_tree.html'
        synth_link = ''
        if synth.exists():
            synth_link = f'<a href="{civ_token}/synthetic_tech_tree.html" target="_blank">view synthetic tech tree →</a>'
        tiles = f'<div class="tile-row"><div class="empty">No in-game captures yet. {synth_link}</div></div>'
    else:
        tile_html = []
        for fname, label in surfaces:
            rel = f'{civ_token}/full/{fname}'
            tile_html.append(
                f'<figure class="tile">'
                f'<a href="{rel}" target="_blank">'
                f'<img loading="lazy" src="{rel}" alt="{html.escape(label)}"></a>'
                f'<figcaption>{html.escape(label)}</figcaption></figure>'
            )
        tiles = '<div class="tile-row">' + ''.join(tile_html) + '</div>'

    return (
        f'<section class="civ-section" id="{civ_token}">'
        f'<h2>{html.escape(display)} '
        f'<span class="badge" style="background:{badge_color}">{badge_text}</span>'
        f'<span class="token">{civ_token}</span></h2>'
        f'{tiles}'
        f'</section>'
    )


def main():
    civs = sorted([p.name for p in ART.iterdir() if p.is_dir() and p.name.startswith('ANW')])
    sections_html = []
    counts = {'live': 0, 'partial': 0, 'synthetic': 0}
    for civ_token in civs:
        civ_dir = ART / civ_token
        status, _ = civ_status(civ_dir)
        counts[status] += 1
        sections_html.append(render_civ_section(civ_token, civ_dir))

    # TOC at top
    toc_items = []
    for civ_token in civs:
        display = DISPLAY_NAME.get(civ_token, civ_token.replace('ANW', ''))
        status, _ = civ_status(civ_dir := ART / civ_token)
        badge = {'live': '🟢', 'partial': '🟡', 'synthetic': '⚪'}[status]
        toc_items.append(f'<a href="#{civ_token}">{badge} {html.escape(display)}</a>')

    html_out = f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>ANW — Live Capture Review</title>
<style>
body {{ background:#1c1410; color:#e6d4ad; font-family:'Georgia',serif; margin:0; padding:20px 32px; }}
h1 {{ color:#f0d896; border-bottom:2px solid #8b6a3a; padding-bottom:8px; }}
.summary {{ background:#2e2014; padding:12px 16px; border-radius:4px; margin:12px 0 24px;
  display:flex; gap:24px; }}
.summary div {{ flex:1; text-align:center; }}
.summary .num {{ font-size:28px; font-weight:bold; }}
.summary .live {{ color:#2ecc71; }}
.summary .partial {{ color:#f39c12; }}
.summary .synthetic {{ color:#888; }}
.toc {{ display:flex; flex-wrap:wrap; gap:6px 12px; background:#2a1d11; padding:12px;
  border-radius:4px; margin-bottom:24px; font-size:13px; }}
.toc a {{ color:#e6d4ad; text-decoration:none; padding:2px 4px; }}
.toc a:hover {{ color:#f0d896; background:#3a2a1a; }}
.civ-section {{ margin:28px 0; padding:16px 0; border-top:1px solid #4a3520; }}
.civ-section h2 {{ color:#f0d896; margin:0 0 12px; font-size:22px;
  display:flex; align-items:center; gap:14px; }}
.badge {{ font-size:11px; color:#111; padding:3px 8px; border-radius:3px;
  font-weight:bold; letter-spacing:.05em; }}
.token {{ font-size:11px; color:#7a6a45; font-family:monospace; margin-left:auto; }}
.tile-row {{ display:flex; gap:10px; overflow-x:auto; padding:6px 0; }}
.tile {{ flex:0 0 auto; margin:0; max-width:340px; }}
.tile img {{ width:340px; height:auto; border:1px solid #4a3520; border-radius:3px;
  display:block; background:#000; }}
.tile figcaption {{ font-size:11px; color:#b89a64; text-align:center;
  padding-top:4px; max-width:340px; }}
.empty {{ font-style:italic; color:#7a6a45; padding:14px; }}
.empty a {{ color:#c2a060; }}
</style>
</head><body>
<h1>A New World — Live Capture Review</h1>
<div class="summary">
  <div><div class="num live">{counts['live']}</div>LIVE (5/5)</div>
  <div><div class="num partial">{counts['partial']}</div>PARTIAL</div>
  <div><div class="num synthetic">{counts['synthetic']}</div>SYNTHETIC ONLY</div>
  <div><div class="num">{len(civs)}</div>TOTAL CIVS</div>
</div>
<div class="toc">{''.join(toc_items)}</div>
{''.join(sections_html)}
</body></html>
"""
    OUT.write_text(html_out, encoding='utf-8')
    print(f'wrote {OUT}')
    print(f'  live: {counts["live"]}  partial: {counts["partial"]}  synthetic: {counts["synthetic"]}')


if __name__ == '__main__':
    main()
