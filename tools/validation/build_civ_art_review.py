#!/usr/bin/env python3
"""Build artifacts/validation/visual_art/civ_art_review.html.

A static, no-game-required review page that shows EVERY ANW civ's actual
mod art surfaces — leader portrait (lobby + diplomacy + scoreboard),
flag, postgame flag, and home-city panel button. All assets come straight
from the mod's own files (resources/images/...), so this works whether or
not the game is installed.

This is the "I visually confirmed every civ" review the user asked for
when full in-game capture is not feasible (capture cap ~3/45, see memory
project_anw_visual_capture_ceiling).
"""
from __future__ import annotations
import html
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INVENTORY = REPO / 'tools' / 'validation' / 'art_inventory.json'
OUT = REPO / 'artifacts' / 'validation' / 'visual_art' / 'civ_art_review.html'

# Engine-canonical display name per civ token (matches lobby/picker text)
DISPLAY_NAME = {
    'ANWArgentines':       'Argentine Confederation',
    'ANWAztecs':           'Aztec Triple Alliance',
    'ANWBarbary':          'Regency of Algiers',
    'ANWBrazil':           'Empire of Brazil',
    'ANWBritish':          'British Empire',
    'ANWCanadians':        'Province of Canada',
    'ANWChileans':         'Republic of Chile',
    'ANWChinese':          'Qing Dynasty',
    'ANWColumbians':       'Gran Colombia',
    'ANWDutch':            'Dutch Republic',
    'ANWEgyptians':        'Khedivate of Egypt',
    'ANWEthiopians':       'Ethiopian Empire',
    'ANWFinnish':          'Grand Duchy of Finland',
    'ANWFrench':           'Bourbon France',
    'ANWGermans':          'German Empire',
    'ANWHaitians':         'First Empire of Haiti',
    'ANWHaudenosaunee':    'Haudenosaunee Confederacy',
    'ANWHausa':            'Sokoto Caliphate',
    'ANWHungarians':       'Kingdom of Hungary',
    'ANWInca':             'Inca Empire',
    'ANWIndians':          'Maratha Empire',
    'ANWIndonesians':      'Sultanate of Yogyakarta',
    'ANWItalians':         'Kingdom of Italy',
    'ANWJapanese':         'Tokugawa Shogunate',
    'ANWLakota':           'Lakota Sioux',
    'ANWMaltese':          'Knights of Malta',
    'ANWMayans':           'Cruzob Maya',
    'ANWMexicans':         'First Mexican Empire',
    'ANWNapoleonicFrance': 'France (Napoleonic)',
    'ANWOttomans':         'Ottoman Empire',
    'ANWPeruvians':        'Republic of Peru',
    'ANWPortuguese':       'Portuguese Empire',
    'ANWRevFrance':        'France (Revolutionary)',
    'ANWRomanians':        'United Romanian Principalities',
    'ANWRussians':         'Russian Empire',
    'ANWSouthAfricans':    'South African Republic',
    'ANWSpanish':          'Spanish Empire',
    'ANWSwedes':           'Swedish Empire',
    'ANWTexians':          'Republic of Texas',
    'ANWUSA':              'United States',
}

# Per-civ leader / strategy summary (sourced from data/anw_civ_blurbs.json
# already used by synthetic tech trees; pulled inline here for one-file build)
BLURBS_FILE = REPO / 'data' / 'anw_civ_blurbs.json'


def load_blurbs():
    if not BLURBS_FILE.exists():
        return {}
    try:
        return json.loads(BLURBS_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def rel_repo_to_review(p: Path) -> str:
    """Convert a repo-relative path to one relative to the review HTML's dir.

    The review HTML lives at artifacts/validation/visual_art/, so paths to
    files at the repo root need to come back up via ../../../."""
    return '../../../' + p


def asset_block(label: str, path: str, repo_root: Path) -> str:
    """One image tile + caption. Greys out missing files."""
    abs_p = repo_root / path
    exists = abs_p.exists() if path else False
    rel = rel_repo_to_review(path) if path else ''
    if exists:
        tile = (f'<a href="{html.escape(rel)}" target="_blank">'
                f'<img loading="lazy" src="{html.escape(rel)}" '
                f'alt="{html.escape(label)}"></a>')
    else:
        tile = '<div class="missing">— absent —</div>'
    return (
        f'<figure class="tile {"ok" if exists else "missing"}">'
        f'<div class="frame">{tile}</div>'
        f'<figcaption><b>{html.escape(label)}</b><br>'
        f'<code>{html.escape(path or "(none)")}</code></figcaption>'
        f'</figure>'
    )


def civ_section(civ_token: str, civ_record: dict, blurb: dict,
                repo_root: Path) -> str:
    display = DISPLAY_NAME.get(civ_token, civ_token.replace('ANW', ''))
    surfaces = civ_record.get('art_surfaces', {})

    # Pull canonical engine-side art paths from civmods.xml-derived inventory.
    # Fall back to the html_* paths or civmods_* root-level fields.
    leader = (surfaces.get('diplomacy_portrait_wpf', {}).get('path')
              or civ_record.get('civmods_portrait_wpf')
              or civ_record.get('html_portrait') or '')
    lobby = (civ_record.get('civmods_portrait_wpf')
             or civ_record.get('html_portrait') or '')
    flag = (surfaces.get('homecity_flag_icon_wpf', {}).get('path')
            or civ_record.get('civmods_flag_wpf')
            or civ_record.get('html_flag') or '')
    flag_btn = surfaces.get('homecity_flag_button_wpf', {}).get('path') or ''
    postgame = (surfaces.get('postgame_flag_wpf', {}).get('path')
                or civ_record.get('civmods_postgame_wpf') or '')
    hc_panel = surfaces.get('homecity_preview_wpf', {}).get('path') or ''
    hc_xml = surfaces.get('homecity_filename', {}).get('path') or ''

    leader_name = blurb.get('leader', '?')
    strategy = blurb.get('strategy', '')
    one_liner = blurb.get('one_liner', '')

    # Status summary
    surface_total = 0
    surface_present = 0
    for k, v in surfaces.items():
        if k.endswith('_art') or k == 'custom_leader_portrait_hires':
            continue  # optional hi-res / art-dir surfaces, not required
        if k == 'homecity_visual_scene':
            continue  # engine-internal ref, resolved by game install
        if not isinstance(v, dict):
            continue
        if v.get('path'):
            surface_total += 1
            if v.get('_on_disk'):
                surface_present += 1
    badge_color = '#2ecc71' if surface_present == surface_total else '#f39c12'

    return (
        f'<section class="civ" id="{civ_token}">'
        f'<header>'
        f'<h2>{html.escape(display)} '
        f'<span class="badge" style="background:{badge_color}">'
        f'{surface_present}/{surface_total} surfaces on disk</span>'
        f'<span class="token">{civ_token}</span></h2>'
        f'<div class="leader-line">'
        f'<b>Leader:</b> {html.escape(leader_name)} · '
        f'<b>Strategy:</b> {html.escape(strategy)}'
        f'</div>'
        f'<div class="blurb">{html.escape(one_liner)}</div>'
        f'</header>'
        f'<div class="tile-grid">'
        f'{asset_block("Leader portrait (diplomacy / scoreboard)", leader, repo_root)}'
        f'{asset_block("Lobby / picker portrait", lobby, repo_root)}'
        f'{asset_block("HUD / lobby flag", flag, repo_root)}'
        f'{asset_block("Home-city flag button", flag_btn, repo_root)}'
        f'{asset_block("Post-game flag", postgame, repo_root)}'
        f'{asset_block("Home-city preview", hc_panel, repo_root)}'
        f'</div>'
        f'<div class="meta-foot">'
        f'<code>{html.escape(hc_xml)}</code> · home-city XML'
        f'</div>'
        f'</section>'
    )


def main():
    inv = json.loads(INVENTORY.read_text(encoding='utf-8'))
    blurbs = load_blurbs()
    repo_root = REPO

    civ_tokens = sorted(t for t in inv['civs'].keys() if t.startswith('ANW'))

    # Aggregate counts
    total_civs = len(civ_tokens)
    fully_present = 0
    for civ_token in civ_tokens:
        surfaces = inv['civs'][civ_token].get('art_surfaces', {})
        ok = all(
            (not v.get('path')) or v.get('_on_disk')
            for k, v in surfaces.items()
            if isinstance(v, dict)
            and not k.endswith('_art')
            and k not in ('custom_leader_portrait_hires', 'homecity_visual_scene')
        )
        if ok:
            fully_present += 1

    # TOC
    toc_html = []
    for civ_token in civ_tokens:
        display = DISPLAY_NAME.get(civ_token, civ_token)
        toc_html.append(
            f'<a href="#{civ_token}">{html.escape(display)}</a>'
        )

    # Sections
    sections = []
    for civ_token in civ_tokens:
        blurb = blurbs.get(civ_token, {})
        sections.append(civ_section(civ_token, inv['civs'][civ_token],
                                    blurb, repo_root))

    out = f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>A New World — Per-Civ Art Review (all 40 civs)</title>
<style>
:root {{ --bg:#1c1410; --fg:#e6d4ad; --accent:#f0d896; --muted:#7a6a45;
        --tile-bg:#231810; --border:#5b4525; --code-bg:#0f0905; }}
body {{ background:var(--bg); color:var(--fg); font-family:'Georgia',serif;
       margin:0; padding:20px 32px; }}
h1 {{ color:var(--accent); border-bottom:2px solid #8b6a3a;
     padding-bottom:8px; margin:0 0 6px; }}
.sub {{ color:#b89a64; font-size:13px; letter-spacing:.08em;
       text-transform:uppercase; margin-bottom:18px; }}
.banner {{ background:#2e2014; padding:14px 18px; border-radius:5px;
          margin-bottom:18px; font-size:14px; line-height:1.55; }}
.banner strong {{ color:var(--accent); }}
.toc {{ display:flex; flex-wrap:wrap; gap:6px 14px; background:#2a1d11;
       padding:12px; border-radius:4px; margin-bottom:24px; font-size:13px; }}
.toc a {{ color:var(--fg); text-decoration:none; padding:2px 4px;
         border-radius:2px; }}
.toc a:hover {{ background:#3a2a1a; color:var(--accent); }}

.civ {{ margin:24px 0; padding:18px 16px; border-top:1px solid #4a3520;
       background:#22170f; border-radius:6px; }}
.civ h2 {{ color:var(--accent); margin:0 0 6px; font-size:22px;
          display:flex; align-items:center; gap:14px; flex-wrap:wrap; }}
.badge {{ font-size:11px; color:#111; padding:3px 8px; border-radius:3px;
         font-weight:bold; letter-spacing:.05em; }}
.token {{ font-size:11px; color:var(--muted); font-family:monospace;
         margin-left:auto; }}
.leader-line {{ font-size:13px; color:#ccba87; margin:2px 0 4px; }}
.blurb {{ font-size:13px; color:#b89a64; font-style:italic;
         margin-bottom:14px; }}

.tile-grid {{ display:grid;
             grid-template-columns:repeat(auto-fill, minmax(220px, 1fr));
             gap:14px; }}
.tile {{ margin:0; background:var(--tile-bg); border:1px solid var(--border);
        border-radius:4px; padding:8px; }}
.tile.missing {{ opacity:0.5; }}
.tile .frame {{ height:200px; display:flex; align-items:center;
               justify-content:center; background:#0a0604;
               border-radius:3px; overflow:hidden; }}
.tile img {{ max-width:100%; max-height:200px; display:block; }}
.tile .missing {{ color:#7a6a45; font-style:italic; padding:14px;
                 text-align:center; }}
.tile figcaption {{ padding-top:8px; font-size:11px; color:#b89a64;
                   line-height:1.45; }}
.tile b {{ color:var(--fg); }}
code {{ background:var(--code-bg); color:#c2a060; padding:1px 5px;
       border-radius:2px; font-size:10px; word-break:break-all; }}
.meta-foot {{ margin-top:10px; font-size:11px; color:var(--muted); }}
</style></head><body>
<h1>A New World — Per-Civ Art Review</h1>
<div class="sub">All 40 ANW civs · mod-side art surfaces · no game required</div>

<div class="banner">
  <strong>{fully_present}/{total_civs}</strong> civs have every required
  art surface on disk (lobby portrait, diplomacy/scoreboard portrait,
  HUD &amp; home-city flag, post-game flag, home-city preview).
  This is a static audit pulled from
  <code>tools/validation/art_inventory.json</code> + civmods.xml —
  no in-game capture needed.
  Use the <a href="british_review.html"
  style="color:var(--accent);text-decoration:underline">British reference</a>
  page for what the in-game UI looks like with these assets loaded.
</div>

<div class="toc">{''.join(toc_html)}</div>

{''.join(sections)}

</body></html>
"""
    OUT.write_text(out, encoding='utf-8')
    print(f'wrote {OUT}')
    print(f'  civs: {total_civs}  fully-present: {fully_present}')


if __name__ == '__main__':
    main()
